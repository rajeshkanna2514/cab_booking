from logging import config
from django.core.mail import send_mail
from django.conf import settings

import random



def generate_otp(length=6):
    otp_chars = "0123456789" 
    otp = ''.join(random.choice(otp_chars) for _ in range(length))
    return otp

def format_phone_number(phone_number, country_code="+91"):
    # Check if phone number already has a country code
    if not phone_number.startswith("+"):
        # Prepend the provided country code
        phone_number = country_code + phone_number
    return phone_number

def send_otp_mail(email, otp):
    send_mail(
        'Email Verification',
        f'Hello,\n\nYour OTP code is {otp}.',
        settings.EMAIL_HOST_USER,
        [email],
        fail_silently=False,
    )
 