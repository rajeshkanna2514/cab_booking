from rest_framework import serializers
from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['booking', 'payment_method', 'paid', 'razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature']
        
