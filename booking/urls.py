from django.urls import path
from .views import BookingView, RatingView, RegisterView,LoginView,LogoutView,Driver_AcceptBooking,PaymentView, WalletView,DistanceView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,TokenBlacklistView
)

urlpatterns = [

    path('login/', LoginView.as_view()),
    path('logout/', LogoutView.as_view()),
    
    path('distance/',DistanceView.as_view()), 
     
    path('register/', RegisterView.as_view()),
    path('accept-driver/', Driver_AcceptBooking.as_view()),
    path('booking-cab/', BookingView.as_view()),
    
    path('wallet/',WalletView.as_view()),
    path('payment/',PaymentView.as_view()),
    path('rating/',RatingView.as_view()),

    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),

]