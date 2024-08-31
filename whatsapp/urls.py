from django.urls import path
from .views import get_activities

urlpatterns = [
    path('webhook/',get_activities,name='webhook')
]