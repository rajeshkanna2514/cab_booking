import traceback
import datetime
import stripe
import razorpay

from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.conf import settings

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated,AllowAny

from rest_framework_simplejwt.tokens import RefreshToken

from .models import Booking, Payment, Rating, User
from .emails import generate_otp, send_otp_mail

from django.http import JsonResponse
from .utils import get_google_maps_client


class DistanceView(APIView):
    def post(self, request):
        try:
           
            origin = request.data.get('origin')
            destination = request.data.get('destination')
            if not origin or not destination:
                return JsonResponse({'error': 'Origin and destination are required'}, status=400)

            gmaps = get_google_maps_client()
            directions_result = gmaps.directions(origin, destination)

            if not directions_result:
                return JsonResponse({'error': 'Could not get directions'}, status=400)

            distance = directions_result[0]['legs'][0]['distance']['text']
            duration = directions_result[0]['legs'][0]['duration']['text']

            return JsonResponse({
                'distance': distance,
                'duration': duration
            }, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
           
class RegisterView(APIView):
    def post(self, request):
        data = request.data
        if 'otp' in data:
            return self.verify_and_register(data)
        else:
            return self.send_otp(data)

    def send_otp(self, data):
        try:
            email = data['email']
            email_otp = generate_otp()
            user, created = User.objects.get_or_create(email=email)
            user.otp = email_otp
            user.otp_created = timezone.now()
            user.save()
            send_otp_mail(email, email_otp)
            return Response({"Msg": f"OTP {email_otp} sent to your email {email}"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"msg": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def verify_and_register(self, data):
        try:
            
            email = data['email']
            otp = data['otp']
            user = User.objects.get(email=email)
         
            if user.otp != str(otp):
                return Response({"Msg": "Enter Valid OTP"}, status=status.HTTP_400_BAD_REQUEST)
            
            if timezone.now() >= user.otp_created + datetime.timedelta(minutes=3):
                user.delete()
                return Response({"msg": "OTP has expired"}, status=status.HTTP_400_BAD_REQUEST)

            username = data['username']
            password = data['password']
            role = data['role']
            user.username = username
            user.password = make_password(password)
            user.role = role

            if role == 'admin':
                user.is_admin = True
                user.is_staff = True
            elif role == 'customer':
                user.phone_no = data.get('phone_no')
                user.is_customer = True
                user.is_staff = True
            elif role == 'driver':
                user.phone_no = data.get('phone_no')
                user.license_no = data.get('license_no')
                user.vehicle = data.get('vehicle')
                user.vehicle_no = data.get('vehicle_no')
                user.is_driver = True
                user.is_staff = True
            else:
                return Response({"Msg": f"{role} cannot be registered"}, status=status.HTTP_404_NOT_FOUND)

            user.is_verified = True
            user.otp = None
            user.otp_created = None
            user.save()

            return Response({"Msg": "User registered successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"Msg": str(e)}, status=status.HTTP_400_BAD_REQUEST)



class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        data = request.data
        email = data.get('email')
        otp = data.get('otp')
        if email and otp:
            return self.verify_otp(email, otp)
        elif email:
            return self.send_otp(email)
        else:
            return Response({"msg": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
    def verify_otp(self, email, otp):
        try:
            user = User.objects.get(email=email, otp=otp)
            if timezone.now() > user.otp_created + datetime.timedelta(minutes=5):
                return Response({"msg": "OTP has expired"}, status=status.HTTP_400_BAD_REQUEST)
            user.is_verified = True
            user.otp = None
            user.otp_created = None
            user.save()
            refresh = RefreshToken.for_user(user)
            token = {
                "refresh": str(refresh),
                "access": str(refresh.access_token)
            }

            response_data = {"msg": "OTP verified successfully", "token": token}

            if user.is_driver:
                bookings = Booking.objects.filter(vehicle=user.vehicle, status='requested')
                booking_details = [
                    {
                        "booking_id": booking.id,
                        "pickup_location": booking.pickup_location,
                        "drop_location": booking.drop_location,
                        "vehicle": booking.vehicle,
                        "status":booking.status,
                        "total_cost": booking.total_cost
                    }
                    for booking in bookings
                ]
                response_data["bookings"] = booking_details
            return Response(response_data, status=status.HTTP_200_OK)
        except:
            return Response({"msg": "Invalid OTP "}, status=status.HTTP_400_BAD_REQUEST)
        
    def send_otp(self, email):
        try:
            user = User.objects.get(email=email)
            otp = generate_otp()
            user.otp = otp
            user.otp_created = timezone.now()
            user.save()
            send_otp_mail(email, otp)
            return Response({f"msg": "Login Successfully. OTP sent to email.  {otp}"}, status=status.HTTP_200_OK)
        
        except User.DoesNotExist:
            return Response({"msg": "User does not exist"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"msg": str(e)}, status=status.HTTP_400_BAD_REQUEST)


        
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self,request,format=None):
        try:
            refresh_token = request.data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"msg":"Logout Sccessfully"},status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"msg":str(e)},status=status.HTTP_400_BAD_REQUEST)

class BookingView(APIView):
    def post(self,request,format=None):
        data = request.data
        
        if 'pickup_location'in data:
            return self.booking_customer(data)
        else:
            return self.cancel_booking(data)
       
    def booking_customer(self,data):    
        try:
            pickup_location = data['pickup_location']
            drop_location = data['drop_location']
            vehicle = data['vehicle']
            status = data['status']
            distance_km = float(data['distance_km'])
    
            user = User.objects.get(id=data['customer_id'])
            otp =generate_otp()
            email = user.email
            
            if not email:
                return Response({"msg":"Enter Valid email"})
            if not user.is_customer:
                return Response({"msg":"Only customer can be booking"})
          
            price_per_km = None
            if vehicle == 'bike':
                price_per_km = 5
            elif vehicle == 'auto':
                price_per_km = 10
            elif vehicle == 'car':
                price_per_km = 15
            else:
                return Response({"msg": "Invalid vehicle type"})
            
            total_cost = distance_km * price_per_km
            booking = Booking.objects.create(  
                customer = user,
                pickup_location=pickup_location,
                drop_location = drop_location,
                vehicle = vehicle,      
                status = status,       
                price_per_km=price_per_km,
                distance_km=distance_km,
                total_cost= total_cost  
                )
            user.otp=otp
            user.otp_created=timezone.now()
            send_otp_mail(email,otp)
           
            user.save()
            return Response({"msg": "Booking created successfully","total_cost": total_cost,"OTP is send to your Mail": otp})
        except Exception as e:
            return Response(traceback.format_exc())
        
    def cancel_booking(self,data):
        try:
            booking_id = data['booking_id'] 
            customer_id = data['customer_id'] 
            
            booking = Booking.objects.get(id=booking_id,customer_id=customer_id)
            customer = booking.customer
            if booking.status=="cancelled":
                return Response({"Msg":"Customer cancelled already"})
            if booking.status == "half_pickup":
                vehicle_type = booking.vehicle
                if vehicle_type == "bike":
                    booking.cancellation_fee = 0.10*(booking.distance_km*booking.price_per_km)
                elif vehicle_type == "auto":
                    booking.cancellation_fee = 0.15*(booking.distance_km*booking.price_per_km)
                elif vehicle_type == "car":
                    booking.cancellation_fee = 0.15*(booking.distance_km*booking.price_per_km)
            elif booking.status == "pickuppoint":
                booking.cancellation_fee = 0.20*(booking.distance_km*booking.price_per_km) 
            booking.status="cancelled" 
           
            customer.wallet = (customer.wallet or 0) - booking.cancellation_fee
            if customer.wallet < 0 :
                customer.cancellation_count += 1
                if customer.cancellation_count >3:
                    return Response({"msg": "After the Payment Customer can start next Booking"})
            else:
                customer.cancellation_count = 0
                     
            driver = booking.drivers
            superuser = User.objects.get(is_superuser=True)
            if driver:
                driver_share = booking.cancellation_fee*0.75
                driver.wallet=(driver.wallet or 0)+driver_share
            if superuser:
                superuser_share = booking.cancellation_fee*0.25
                superuser.wallet=(superuser.wallet or 0)+superuser_share
            superuser.save()  
            driver.save()  
            customer.save()
            booking.save()
            response_data = {
                "Cancellation_fees":booking.cancellation_fee,
                "Customer_Wallet":customer.wallet,
                "Driver_share":driver_share,
                "Superuser_Share":superuser_share,
                "total_cost":booking.total_cost,
                "msg":"Booking is Cancelled"
            }
            return Response(response_data,status=200)
        except:
            return Response({"msg":traceback.format_exc()},status=400)        

class WalletView(APIView):
    def post(self,request):
        try:
            data = request.data
            customer_id = data['customer_id']
            wallet_recharge = data.get('wallet_recharge')
            customer = User.objects.get(id=customer_id)
            customer.wallet += wallet_recharge
            customer.save()
            return Response({"Msg":f"Wallet added {wallet_recharge}"})
        except Exception as e:
            return Response({"Msg": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class Driver_AcceptBooking(APIView):
    def post(self,request):
        data = request.data
        try:
            booking_id = data['booking_id']
            drivers_id = data['drivers_id']
            status = data.get('status')
            
            driver = User.objects.get(id=drivers_id)
 
            if not driver.is_driver:
                return Response({"msg":"Only Driver can be accept"},status=404)
            
            statuses = ['accepted', 'half_pickup', 'pickuppoint', 'pickup', 'drop']
            current_bookings = Booking.objects.filter(drivers=driver, status__in=statuses,vehicle=driver.vehicle)
            if current_bookings.exists() and status == "accepted":
                return Response({"msg": "Driver can only accept new bookings after completing the current customer"}, status=403)
            booking = Booking.objects.get(id=booking_id)
            customer = booking.customer
            if status == "accepted":
                booking.status="accepted"
                driver.driver_status="accepted"  
            elif status == "half_pickup":
                booking.status="half_pickup"   
            elif status == "pickuppoint":
                booking.status="pickuppoint"    
            elif status == "pickup":
                otp = data['otp']
                if customer.otp!=str(otp):
                    return Response({"Msg":"Enter the valid OTP"},status=400)
                if timezone.now() >= customer.otp_created + datetime.timedelta(minutes=50):
                    return Response({"msg": "OTP has expired"}, status=400)
                booking.status="pickup"
                customer.otp=None
                customer.otp_created=None
            elif status == "drop":
                booking.status="drop"        
            elif status == "completed":      
                booking.status="completed"
                if booking.status =="completed":
                    driver.driver_status="requested" 
            elif status == "cancelled":
                booking.status="cancelled"      
            else:
                return Response({"msg":"Invalid status"})  
           
            booking.drivers=driver
            booking.save()
            customer.save()
            driver.save()  
            response_data = {
                "Customer":customer.email,
                "driver":driver.email,
                "status":booking.status,
                "distance_km":booking.distance_km,
                "tota_cost":booking.total_cost,
                "msg":f"Booking status {status} Successfully"
            }
            return Response(response_data,status=200)    
        except Exception as e:
            return Response({"msg":traceback.format_exc()},status=400)
        
stripe.api_key = settings.STRIPE_SECRET_KEY
class PaymentView(APIView):
    def post(self,request,format=None):
        try:
           
            data = request.data 
            booking_id = data['booking_id']
            payment_method = data['payment_method']
           
            payment,created = Payment.objects.get_or_create(booking_id=booking_id,defaults={'payment_method':payment_method})
            booking = Booking.objects.get(id=booking_id)
            driver = booking.drivers
            customer = booking.customer
            payment_method=payment.payment_method
            if booking.status != "completed":
                return Response({"Msg": "Only completed bookings can be pay payment"}, status=status.HTTP_400_BAD_REQUEST)
            if payment_method == "cash_on":
                payment.payment_method="cash_on"    
            elif payment_method == "wallet":
                payment.payment_method="wallet"
                if customer.wallet >= booking.total_cost:
                    customer.wallet = customer.wallet-booking.total_cost
                    driver.wallet = driver.wallet+booking.total_cost
                    customer.save()
                    driver.save()
                else:
                    return Response({"msg":"Customer want to Recharge a Wallet"})    
            elif payment_method in ["creditordebit", "upi"]:
                try:
                    stripe_customer = stripe.Customer.create(
                        email=customer.email,
                        name=customer.username,
                        source="tok_visa"  
                    )
                    charge = stripe.Charge.create(
                        amount=int(booking.total_cost), 
                        currency="usd",
                        customer=stripe_customer.id,
                        description=f"Payment for booking {booking_id}"
                    )
                    # payment.payment_method = payment_method
                except stripe.error.StripeError as e:
                    return Response({"msg": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"msg":"Enter the Correct payment Method"}) 
            payment.paid = True
            booking.save()
            payment.save()
           
            response_data = {
                "msg":"payment paid successfully",
                "booking_id" : booking.id,
                "payment":payment.payment_method,
                "vehicle":booking.vehicle,
                "totalcost":booking.total_cost,
             }
            return Response(response_data,status=status.HTTP_200_OK)     
        except:
            return Response(traceback.format_exc(),status=status.HTTP_400_BAD_REQUEST)    

class RatingView(APIView):
    def post(self,request,format=None):
        try:
            data =request.data
            booking_id = data['booking_id']
            comment = data['comment']
            rating = data['rating']
            
            booking = Booking.objects.get(id=booking_id)
            if booking.status != "completed":
                return Response({"msg":"Completed Customer only gives rating"},status=status.HTTP_400_BAD_REQUEST)
            rate= Rating.objects.create(booking=booking,comment=comment,rating=rating)
            rate.save()
            return Response({"Msg":"Have a Niceday,Thank you"},status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"Msg":str(e)},status=400)        
        

    
        

        




























































































































































# class BookingView(APIView):
#     def post(self,request):
#         try:    
#             data = request.data
#             pickup_location = data['pickup_location']
#             drop_location = data['drop_location']
#             vehicle = data['vehicle']
#             status = data['status']
#             distance_km = float(data['distance_km'])
          

#             user = User.objects.get(id=data['user_id'])
#             driver = Driver.objects.get(id=data['user_id'])
#             booking,created = Booking.objects.update_or_create(
#                 user=user,
#                 driver = driver,
#                 defaults={
#                     "pickup_location":pickup_location,
#                     "drop_location":drop_location,
#                     "vehicle":vehicle,
#                     "status":status,
#                     "distance_km":distance_km, 
                
#                 },)
#             booking.total_cost = booking.cal_total_cost()
#             booking.save()
    
#             if created:
#                 msg="Cab Booked "
#             else:
#                 msg="Booking Updated"
            
#             return Response({"Msg":msg})
#         except Exception as e:
#             return Response({"Error":str(e)})
        
#     def delete(self,request,id,format=None):
#         try:
#             booking = Booking.objects.get(id=id)
#             booking.status="cancelled"
#             booking.delete()
#             return Response({"Msg":"Booking is cancelled"},status=status.HTTP_205_RESET_CONTENT)
#         except Booking.DoesNotExist:
#             return Response({"Msg":"Booking Does Not exist"},status=status.HTTP_204_NO_CONTENT)    
         
        
# class DriverView(APIView):
#     def post(self,request,id=None):
#         try:
            
#             data = request.data
#             booking = Booking.objects.get(id=data['id'])
           
#             if data['status']=='accepted':
#                 booking.status = "accepted"
#                 booking.save()
#                 return Response({"msg":"Booking accepted"},status=status.HTTP_200_OK)
#             else:
#                 booking.status = "cancelled"
#                 booking.save()
#                 return Response({"msg":"Driver Denied Request"},status=status.HTTP_205_RESET_CONTENT)
#         except Exception as e:
#             return Response({"msg":str(e)},status=status.HTTP_400_BAD_REQUEST) 
#         except Booking.DoesNotExist:
#             return Response({"msg": "Booking does not exist"}, status=status.HTTP_404_NOT_FOUND)   


        

# class RatingView(APIView):
#     def post(self,request,format=None):
#         try:
#             data =request.data
#             comment = data['comment']
#             rating = data['rating']
            
#             user = User.objects.get(id=data['user_id'])
#             driver = Driver.objects.get(id=data['driver_id'])

#             star = Rating.objects.create(user=user,driver=driver,comment=comment,rating=rating)

#             star.save()
#             return Response({"Msg":"Have a Niceday,Thank you"},status=status.HTTP_200_OK)
#         except Exception as e:
#             return Response({"Msg":str(e)},status=status.htt)

# try:
        #     data = request.data 
        #     username = data['username']
        #     email = data['email']
        #     password = data['password']
        #     phone_no = data['phone_no']
        #     license_no = data['license_no']
        #     vehicle = data['vehicle']
        #     vehicle_no = data['vehicle_no']
        #     role = data['role']
        #     otp = generate_otp()
        #     if role == 'driver': 
        #         driver = User.objects.filter(email=email).create(username=username,email=email,password=password,phone_no=phone_no,license_no=license_no,vehicle=vehicle,vehicle_no=vehicle_no)   
        #         driver.is_driver=True
        #         driver.is_staff=True
        #         driver.otp = otp
        #         driver.save()
        #         send_otp_mail(email,otp)
        #     elif role != 'driver':
        #         driver.delete()
        #         return Response({"Msg":"Only Driver Can be Register"},status=status.HTTP_404_NOT_FOUND)
        #     else:
        #         try:
        #             email = data['email']
        #             otp = data['otp']
        #             user = User.objects.get(email=email,otp=otp)
                    
        #             if user.otp != otp:
        #                 return Response({"Msg":"Invalid Otp"},status=status.HTTP_400_BAD_REQUEST)
                    
        #             if timezone.now() > user.otp_created + datetime.timedelta(minutes=3):
        #                 return Response({"Msg": "OTP has expired"}, status=status.HTTP_400_BAD_REQUEST)
        #             return Response({"Msg":"OTP has been verified"},status=status.HTTP_200_OK)
        #         except User.DoesNotExist:
        #             return Response({"msg":"Does not exist"},status=status.HTTP_204_NO_CONTENT)
                
        #     return Response({"Msg":"Driver Register successfully"},status=status.HTTP_200_OK)
        # except Exception as e:
        #     return Response({"Error":str(e)},status=status.HTTP_400_BAD_REQUEST)
        

               # try:
        #     data = request.data
        #     username = data['username']
        #     email = data['email']
        #     password = data['password']
        #     is_verified = False
        #     role = data['role']
        #     if role == 'customer':
        #         otp = generate_otp()
        #         if User.objects.filter(email=email).exists():
        #             return Response("Email is already exist")
        #         customer = User.objects.create(username=username,email=email,password=password,otp=otp)
        #         customer.is_customer=True
        #         customer.is_staff=True
                
        #         customer.otp = otp
        #         customer.save()

        #         send_otp_mail(email, otp)

        #         return Response({"Msg":"Customer Register Successfully and otp send to your mail"},status=status.HTTP_200_OK)

        #     elif role != 'customer':
        #         customer.delete()
        #         return Response({"Msg":"Only customer can Register"},status=status.HTTP_404_NOT_FOUND)
        # except Exception as e:
        #     return Response({'Msg':str(e)},status=status.HTTP_400_BAD_REQUEST)



    #     class VerifyOtp(APIView):
    # def post(self,request):
    #     try:
    #         data = request.data
    #         email = data['email']
    #         otp = data['otp']
    #         user = User.objects.get(email=email,otp=otp)
            
            # if user.otp != otp:
            #     return Response({"Msg":"Invalid Otp"},status=status.HTTP_400_BAD_REQUEST)
            
        #     if timezone.now() > user.otp_created + datetime.timedelta(minutes=3):
        #         return Response({"Msg": "OTP has expired"}, status=status.HTTP_400_BAD_REQUEST)
           
       
        #     user.is_verified=True
        #     user.otp = None
        #     user.otp_created = None
        #     user.save()

        #     return Response({"Msg":"OTP Verified Successfully"},status=status.HTTP_200_OK)
        # except Exception as e:
        #     return Response({"msg":str(e)},status=status.HTTP_400_BAD_REQUEST)
        # except User.DoesNotExist:
        #     return Response({"Msg":"User Does Not Exist"},status=status.HTTP_204_NO_CONTENT)
              
        # try:
        #     data = request.data
        #     username = data['username']
        #     email = data['email']
        #     password = data['password']
        #     role = data['role']
        #     otp = generate_otp()

        #     if role == 'admin':
        #         user = User.objects.filter(email=email).create(username=username,email=email,password=password)
        #         user.is_admin=True
        #         user.is_staff=True

        #         user.otp = otp
        #         user.save()

        #         send_otp_mail(email,otp)
        #         return Response({"Msg":"Admin Register Successfully"},status=status.HTTP_200_OK)
        #     elif role != 'admin':
        #         user.delete()
        #         return Response({"Msg":"Only Admin can Register"},status=status.HTTP_404_NOT_FOUND)    
            
        # except Exception as e:
        #     return Response({"Error":str(e)},status=status.HTTP_400_BAD_REQUEST)
            # def verify_otp(self,data):
    #     try:
    #         email = data['email']
    #         otp = data['otp'] 
            
    #         email_otp = generate_otp()
    #         send_otp_mail(email, email_otp)
    #         if otp != email_otp:
    #             return Response({"Msg":"Enter Valid OTP"},status=status.HTTP_400_BAD_REQUEST)

    #         user = User.objects.get(email=email)
           
    #         if timezone.now() >= user.otp_created + datetime.timedelta(minutes=3):
    #             if not user.is_verified:
    #                 user.delete()
    #             return Response({"msg": "OTP has expired"}, status=status.HTTP_400_BAD_REQUEST)
    #         user.is_verified=True
            
    #         user.save()
            
    #         return Response({"msg": "OTP verified successfully"}, status=status.HTTP_200_OK)
    #     except Exception as e:
    #         return Response({"msg":str(e)}, status=status.HTTP_400_BAD_REQUEST)
# booking,created = Booking.objects.update_or_create(
#                 customer=user,
#                 defaults={
#                     "pickup_location":pickup_location,
#                     "drop_location" : drop_location,
#                     "vehicle" : vehicle,
#                     "status" :status,
#                     "price_per_km":price_per_km,
#                     "distance_km" : distance_km,
#                     "total_cost": total_cost,
#                     },)       
            