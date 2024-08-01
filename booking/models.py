from datetime import datetime
from django.db import models
from .manager import BaseUser
from django.contrib.auth.models import AbstractBaseUser,PermissionsMixin
from django.core.validators import RegexValidator,MaxValueValidator,MinValueValidator


class User(AbstractBaseUser,PermissionsMixin):

    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('customer', 'Customer'),
        ('driver', 'Driver'),
    )
    DRIVER_CHOICES = (
        ('requested','Requested'),
        ('accepted','Accepted')
    )

    username = models.CharField(max_length=100,null=True)
    email = models.EmailField(max_length=50,null=True,blank=True,unique=True)
    is_verified = models.BooleanField(default=False)
    otp = models.CharField(max_length=6,null=True,blank=True)
    otp_created = models.DateTimeField(null=True,blank=True)
    role = models.CharField(max_length=8, choices=ROLE_CHOICES,default='customer')
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_customer = models.BooleanField(default=False)
    is_driver = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    phone_no = models.CharField(max_length=10,null=True,validators=[RegexValidator(regex=r'^\d{10}$',
                message='Phone number must be exactly 10 digits.')])
    license_no = models.CharField(max_length=50,null=True,unique=True,blank=True)
    vehicle = models.CharField(max_length=50,null=True,blank=True)
    vehicle_no = models.CharField(max_length=50,null=True,unique=True,blank=True)
    wallet = models.FloatField(default=0,null=True,blank=True)
    cancellation_count = models.PositiveIntegerField(default=0)
    driver_status = models.CharField(choices=DRIVER_CHOICES,max_length=9,default='requested')
    

    USERNAME_FIELD = ('email')
    REQUIRED_FIELDS= ('username',)

    objects = BaseUser()

    def __str__(self):
        return self.email if self.email else 'No Email'


def generate_id():
    return f"ID{datetime.now().strftime('%Y%m%d%H%M%S')}"

  
class Booking(models.Model):
    Vehicle_Choices = [
        ('bike','Bike'),
        ('auto','Auto'),
        ('car','Car')
    ]

    Status_Choices = [
        ('requested','Requested'),
        ('accepted','Accepted'),
        ('half_pickup','Half_pickup'),
        ('pickuppoint','PickupPoint'),
        ('pickup','Pickup'),
        ('drop','Drop'),
        ('completed','Completed'),
        ('cancelled','Cancelled')
    ]
 
    id = models.CharField(primary_key=True,unique=True,default=generate_id,editable=False,max_length=50)
    customer = models.ForeignKey(User,on_delete=models.CASCADE,null=True,blank=True,related_name='bookings')
    drivers = models.ForeignKey(User,on_delete=models.CASCADE,null=True,blank=True,related_name='driver_booking')
    pickup_location = models.CharField(max_length=200,null=True)
    drop_location = models.CharField(max_length=200,null=True)
    pickup_on = models.DateTimeField(auto_now_add=True)
    drop_on = models.DateTimeField(auto_now=True)
    vehicle = models.CharField(choices=Vehicle_Choices,max_length=15,default='bike')
    status = models.CharField(choices=Status_Choices,max_length=15,default='requested')
    price_per_km = models.FloatField(null=True,blank=True)
    distance_km = models.FloatField(null=True,blank=True,default=0)
    cancellation_fee = models.FloatField(default=0)
    total_cost = models.FloatField(null=True,blank=True)

    def __str__(self):
        return self.id


class Payment(models.Model):
    Payment_Choice = [   
    ('cash_on','Cash_on'),
    ('wallet','wallet'),
    ('creditordebit','CreditOrDebit'),
    ('upi','Upi')
    ]

    booking = models.ForeignKey(Booking,on_delete=models.CASCADE,related_name='customer_payment')    
    payment_method = models.CharField(choices=Payment_Choice,max_length=15,default='cash_on')
    paid = models.BooleanField(default=False)
    razorpay_signature = models.CharField(max_length=100,null=True,blank=True)
    razorpay_order_id = models.CharField(max_length=100,null=True,blank=True)
    razorpay_payment_id = models.CharField(max_length=100,null=True,blank=True)

    def __str__(self):
        return self.booking.id

class Rating(models.Model):
    booking= models.ForeignKey(Booking,on_delete=models.CASCADE,related_name='rate_customer')
    comment = models.CharField(max_length=100,null=True)
    rating = models.IntegerField(default=0,
    validators = [
        MaxValueValidator(5),
        MinValueValidator(1),
    ]
) 
    
    def __str__(self):
        return self.booking.id
   
   