import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# Set your verify token and access token
VERIFY_TOKEN = 'Set_your_verify_token_value_here'
WHATSAPP_TOKEN = 'Paste_whatsapp_access_token_here'

# In-memory storage for activities (not persistent)
stored_activities = []

@csrf_exempt
def whatsapp_webhook(request):
    if request.method == 'GET':
    
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            return JsonResponse({'hub.challenge': int(challenge)}, status=200)
        else:
            return JsonResponse({'error': 'Token verification failed'}, status=403)

    elif request.method == 'POST':
       
        try:
            body = json.loads(request.body)
            entries = body.get('entry', [])
            for entry in entries:
                changes = entry.get('changes', [])
                for change in changes:
                    value = change.get('value', {})
                    if value:
                      
                        phone_number_id = value.get('metadata', {}).get('phone_number_id')
                        timestamp = value.get('timestamp')

                     
                        messages = value.get('messages', [])
                        for message in messages:
                            if message.get('type') == 'text':
                                from_number = message.get('from')
                                message_id = message.get('id')
                                message_body = message.get('text', {}).get('body')
                                reply_message = "Ack from Django: " + message_body

                              
                                activity = {
                                    "type": "message",
                                    "from": from_number,
                                    "message_id":message_id,
                                    "message_body": message_body,
                                    "timestamp": timestamp,
                                    "metadata": value.get('metadata', {}),
                                }
                                stored_activities.append(activity)

                                
                                mark_message_as_read(message_id, WHATSAPP_TOKEN)

                   
                        interactive = value.get('interactive', {})
                        if interactive.get('type') == 'button_reply':
                            button_reply = interactive.get('button_reply', {})
                            from_number = button_reply.get('from')
                            message_id = button_reply.get('id')
                            activity = {
                                "type": "order",
                                "from": from_number,
                                "product_id": button_reply.get('id'),
                                "catalog_id": button_reply.get('catalog_id'),
                                "title": button_reply.get('title'),
                                "timestamp": timestamp,
                                "metadata": value.get('metadata', {}),
                            }
                            stored_activities.append(activity)

                      
                            mark_message_as_read(message_id, WHATSAPP_TOKEN)

                        statuses = value.get('statuses', [])
                        for status in statuses:
                            activity = {
                                "type": "status",
                                "id": status.get('id'),
                                "status": status.get('status'),
                                "timestamp": timestamp,
                                "metadata": value.get('metadata', {}),
                            }
                            stored_activities.append(activity)

            return JsonResponse({'status': 'Event received'}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid payload'}, status=400)

    return JsonResponse({'error': 'Unsupported method'}, status=405)

@csrf_exempt
def get_activities(request):
    return JsonResponse({'activities': stored_activities}, status=200)

import requests

def mark_message_as_read(message_id, WHATSAPP_TOKEN):
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
