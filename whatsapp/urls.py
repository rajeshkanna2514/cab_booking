from django.urls import path
from .views import ActivitiesView

urlpatterns = [
    path('get-activities/',ActivitiesView.as_view(),name='activities')
]