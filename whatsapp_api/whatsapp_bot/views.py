
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
from datetime import datetime
from .models import *
from .utils import *
import requests
@csrf_exempt
def webhook(request):
    if request.method == 'GET':
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        if mode and token:
            if mode == 'subscribe' and token == settings.VERIFY_TOKEN:
                return HttpResponse(challenge, content_type='text/plain')
            return HttpResponse('Forbidden', status=403)

    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            
            if 'entry' in data and data['entry']:
                entry = data['entry'][0]
                if 'changes' in entry and entry['changes']:
                    change = entry['changes'][0]
                    if 'value' in change and 'messages' in change['value']:
                        message = change['value']['messages'][0]
                        
                        phone_number = message['from']
                        message_text = message['text']['body'].strip()

                        # Get or create user state
                        state, _ = WhatsAppState.objects.get_or_create(phone_number=phone_number)

                        # Process message based on user role
                        try:
                            admin = WhatsAppAdmin.objects.get(phone_number=phone_number)
                            print(admin)
                            if admin.role == 'super':
                                response = handle_super_admin_commands(admin, message_text.split(), state)
                            elif admin.role == 'hotel':
                                response = handle_hotel_admin_commands(admin, message_text.split(), state)
                        except WhatsAppAdmin.DoesNotExist:
                            response = handle_user_commands(phone_number, message_text.lower(), state)

                        # Send response
                        send_whatsapp_message(phone_number, response)
            
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            print(f"Error processing webhook: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return HttpResponse('Method not allowed', status=405)