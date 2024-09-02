import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

VERIFY_TOKEN = 'HAPPY'
WHATSAPP_TOKEN = 'EAAOiVl18euoBO1jO9zmuKMfX9cuc5QJJ4EONnlwdaHi4B8uTvOnwSqZBYdDjSjOovngqaxDDPJK4EZAFFMszHWLNhfpxZCupnen6ZCU7SztYDGnFe3COza3EP0yYVGXff71uZCmCuyqVdnZB0Av3BXKWSGkTDj8SZBE1oyuvmFQMWVZChQZB0pIXa5HtIViqdmJk3hjscoxmMtzarqD96RlT0ah1p8Nub0h8jFwMZD'

stored_activities = []

def mark_message_as_read(message_id):
    url = f"https://graph.facebook.com/v16.0/{message_id}"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "status": "read"
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        print(f"Message {message_id} marked as read.")
    else:
        print(f"Failed to mark message as read: {response.status_code} {response.text}")

@csrf_exempt
def whatsapp_webhook(request):
    if request.method == 'GET':

        mode = "subscribe"
        token = "HAPPY"
        challenge = "challenge"
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            return JsonResponse({'hub.challenge': challenge}, status=200)
        else:
            return JsonResponse({'error': 'Token verification failed'}, status=403)
    
    elif request.method == 'POST':
        try:
            body = json.loads(request.body.decode('utf-8'))
            entries = body.get('entry', [])
            for entry in entries:
                changes = entry.get('changes', [])
                for change in changes:
                    value = change.get('value', {})
                    messages = value.get('messages', [])
                    for message in messages:
                        message_type = message.get('type')
                        message_id = message.get('id')
                        from_number = message.get('from')
                        timestamp = message.get('timestamp')
                        metadata = value.get('metadata', {})
                        contacts = value.get('contacts', [{}])[0]
                        customer_name = contacts.get('profile', {}).get('name', 'Unknown')
                        
                        if message_type == 'order':
                            order = message.get('order', {})
                            catalog_id = order.get('catalog_id')
                            product_items = order.get('product_items', [])
                            order_text = order.get('text', '')
                            
                            activity = {
                                "type": "order",
                                "message_id": message_id,
                                "from": from_number,
                                "customer_name": customer_name,
                                "timestamp": timestamp,
                                "catalog_id": catalog_id,
                                "product_items": product_items,
                                "order_text": order_text,
                                "metadata": metadata,
                            }
                            stored_activities.append(activity)
                        
                            mark_message_as_read(message_id)
                        
                        elif message_type == 'text':
                            text_body = message.get('text', {}).get('body', '')
                            activity = {
                                "type": "text",
                                "message_id": message_id,
                                "from": from_number,
                                "customer_name": customer_name,
                                "timestamp": timestamp,
                                "message_body": text_body,
                                "metadata": metadata,
                            }
                            stored_activities.append(activity)
                            
                            mark_message_as_read(message_id)
                       
            return JsonResponse({'status': 'Event received'}, status=200)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON payload'}, status=400)
        except Exception as e:
            print(f"Error processing webhook: {e}")
            return JsonResponse({'error': 'Internal server error'}, status=500)
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)
class ActivitiesView(APIView):
    def get(self, request):
        return Response({"activities": stored_activities}, status=status.HTTP_200_OK)
