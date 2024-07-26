from django.contrib import admin
from .models import Booking, Payment, User,Rating

class UserAdmin(admin.ModelAdmin):

    list_display = ('username','email','phone_no','license_no','wallet','driver_status','cancellation_count','vehicle','vehicle_no','otp','role','is_active','is_admin','is_staff','is_superuser','is_customer','is_driver','is_verified','password')
    search_fields = ('username','email',)
    list_filter = ('is_admin','is_superuser','is_customer','is_driver')

admin.site.register(User,UserAdmin)

class BookingAdmin(admin.ModelAdmin):
    
    list_display = ('id','customer','drivers','pickup_location','drop_location','pickup_on','cancellation_fee','drop_on','vehicle','status','price_per_km','distance_km','total_cost')
    search_fields = ('customer',)
    list_filter = ('customer',)

admin.site.register(Booking,BookingAdmin)

class PaymentAdmin(admin.ModelAdmin):

    list_display = ('booking','payment_method','paid')
    list_filter = ('payment_method',)

admin.site.register(Payment,PaymentAdmin)    

class RatingAdmin(admin.ModelAdmin):

    list_display = ('booking','rating','comment')
    list_filter = ('rating',)

admin.site.register(Rating,RatingAdmin)    

