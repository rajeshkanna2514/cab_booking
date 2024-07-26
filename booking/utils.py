from django.conf import settings
import googlemaps


def get_google_maps_client():
    return googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)