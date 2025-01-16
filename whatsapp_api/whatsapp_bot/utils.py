from django.conf import settings  # Add this import
import json
import requests
from datetime import datetime
from .models import *

def handle_admin_commands(phone_number, message_text, state):
    """Handle administrative commands"""
    try:
        admin = WhatsAppAdmin.objects.get(phone_number=phone_number, is_active=True)
    except WhatsAppAdmin.DoesNotExist:
        return "Unauthorized access. Please contact system administrator."

    parts = message_text.lower().split()
    command = parts[0] if parts else ""

    if admin.role == 'super':
        return handle_super_admin_commands(admin, parts, state)
    elif admin.role == 'hotel':
        return handle_hotel_admin_commands(admin, parts, state)
    else:
        return "Unknown command. Type 'help' for available commands."

def handle_super_admin_commands(admin, parts, state):
    """Handle super admin specific commands"""
    command = parts[0] if parts else ""
    
    if command == 'addadmin':
        state.current_state = 'adding_admin_name'
        state.save()
        return "Enter admin name:"
        
    elif command == 'addhotel':
        state.current_state = 'adding_hotel_name'
        state.save()
        return "Enter hotel name:"
        
    elif command == 'listadmins':
        admins = WhatsAppAdmin.objects.all()
        response = "Registered Admins:\n"
        for admin in admins:
            response += f"{admin.name} ({admin.role}) - {admin.phone_number}\n"
        return response
        
    elif command == 'listhotels':
        hotels = Hotel.objects.all()
        response = "Registered Hotels:\n"
        for hotel in hotels:
            response += f"{hotel.name} - {hotel.city}, {hotel.district}\n"
        return response

    return handle_super_admin_state(admin, parts, state)

def handle_super_admin_state(admin, parts, state):
    """Handle super admin state machine"""
    current_state = state.current_state
    temp_data = state.temp_data
    message = ' '.join(parts)

    if current_state == 'adding_admin_name':
        temp_data['admin_name'] = message
        state.current_state = 'adding_admin_phone'
        state.temp_data = temp_data
        state.save()
        return "Enter admin phone number:"

    elif current_state == 'adding_admin_phone':
        temp_data['admin_phone'] = message
        state.current_state = 'adding_admin_role'
        state.temp_data = temp_data
        state.save()
        return "Enter admin role (hotel/super):"

    elif current_state == 'adding_admin_role':
        if message not in ['hotel', 'super']:
            return "Invalid role. Please enter 'hotel' or 'super':"

        try:
            WhatsAppAdmin.objects.create(
                name=temp_data['admin_name'],
                phone_number=temp_data['admin_phone'],
                role=message
            )
            state.current_state = 'initial'
            state.temp_data = {}
            state.save()
            return "Admin added successfully!"
        except Exception as e:
            return f"Error adding admin: {str(e)}"

    elif current_state == 'adding_hotel_name':
        temp_data['hotel_name'] = message
        state.current_state = 'adding_hotel_district'
        state.temp_data = temp_data
        state.save()
        return "Enter hotel district:"

    # Continue hotel addition flow
    elif current_state == 'adding_hotel_district':
        temp_data['district'] = message
        state.current_state = 'adding_hotel_city'
        state.temp_data = temp_data
        state.save()
        return "Enter hotel city:"

    elif current_state == 'adding_hotel_city':
        temp_data['city'] = message
        state.current_state = 'adding_hotel_locality'
        state.temp_data = temp_data
        state.save()
        return "Enter hotel locality:"

    elif current_state == 'adding_hotel_locality':
        temp_data['locality'] = message
        state.current_state = 'adding_hotel_admin'
        state.temp_data = temp_data
        state.save()
        return "Enter hotel admin phone number:"

    elif current_state == 'adding_hotel_admin':
        try:
            hotel = Hotel.objects.create(
                name=temp_data['hotel_name'],
                district=temp_data['district'],
                city=temp_data['city'],
                locality=temp_data['locality'],
                admin_phone=message
            )
            
            # Create hotel admin if doesn't exist
            WhatsAppAdmin.objects.get_or_create(
                phone_number=message,
                defaults={
                    'name': f"Admin for {hotel.name}",
                    'role': 'hotel'
                }
            )
            
            state.current_state = 'initial'
            state.temp_data = {}
            state.save()
            return "Hotel added successfully!"
        except Exception as e:
            return f"Error adding hotel: {str(e)}"

    return "Unknown state. Type 'help' for commands."

def handle_hotel_admin_commands(admin, parts, state):
    """Handle hotel admin specific commands"""
    command = parts[0] if parts else ""
    
    try:
        hotel = Hotel.objects.get(admin_phone=admin.phone_number)
    except Hotel.DoesNotExist:
        return "No hotel associated with this admin."

    if command == 'addroom':
        state.current_state = 'adding_room_type'
        state.save()
        return "Enter room type name:"
        
    elif command == 'updateroom':
        room_types = RoomType.objects.filter(hotel=hotel)
        response = "Available Room Types:\n"
        for i, room in enumerate(room_types, 1):
            response += f"{i}. {room.name} - Available: {room.available_rooms}/{room.total_rooms}\n"
        response += "\nEnter room number to update:"
        
        state.temp_data['room_types'] = list(room_types.values())
        state.current_state = 'updating_room_selection'
        state.save()
        return response
        
    elif command == 'status':
        bookings = Booking.objects.filter(
            room_type__hotel=hotel,
            status__in=['pending', 'confirmed']
        ).order_by('check_in')
        
        response = "Current Bookings:\n"
        for booking in bookings:
            response += f"ID: {booking.id}\n"
            response += f"Guest: {booking.guest_name}\n"
            response += f"Room: {booking.room_type.name}\n"
            response += f"Check-in: {booking.check_in.strftime('%d-%m-%Y')}\n"
            response += f"Status: {booking.status}\n\n"
        
        return response

    return handle_hotel_admin_state(admin, parts, state, hotel)

def handle_hotel_admin_state(admin, parts, state, hotel):
    """Handle hotel admin state machine"""
    current_state = state.current_state
    temp_data = state.temp_data
    message = ' '.join(parts)

    if current_state == 'adding_room_type':
        temp_data['room_name'] = message
        state.current_state = 'adding_room_price'
        state.temp_data = temp_data
        state.save()
        return "Enter price per day:"

    elif current_state == 'adding_room_price':
        try:
            temp_data['price'] = float(message)
            state.current_state = 'adding_room_total'
            state.temp_data = temp_data
            state.save()
            return "Enter total number of rooms:"
        except ValueError:
            return "Invalid price. Please enter a number:"

    elif current_state == 'adding_room_total':
        try:
            temp_data['total_rooms'] = int(message)
            state.current_state = 'adding_room_amenities'
            state.temp_data = temp_data
            state.save()
            return "Enter room amenities (comma separated):"
        except ValueError:
            return "Invalid number. Please enter a whole number:"

    elif current_state == 'adding_room_amenities':
        try:
            RoomType.objects.create(
                hotel=hotel,
                name=temp_data['room_name'],
                price_per_day=temp_data['price'],
                total_rooms=temp_data['total_rooms'],
                available_rooms=temp_data['total_rooms'],
                amenities=message
            )
            state.current_state = 'initial'
            state.temp_data = {}
            state.save()
            return "Room type added successfully!"
        except Exception as e:
            return f"Error adding room type: {str(e)}"

    elif current_state == 'updating_room_selection':
        try:
            room_index = int(message) - 1
            room_data = temp_data['room_types'][room_index]
            temp_data['selected_room_id'] = room_data['id']
            state.current_state = 'updating_room_available'
            state.temp_data = temp_data
            state.save()
            return "Enter number of available rooms:"
        except (ValueError, IndexError):
            return "Invalid selection. Please enter a valid number:"

    elif current_state == 'updating_room_available':
        try:
            available_rooms = int(message)
            room_type = RoomType.objects.get(id=temp_data['selected_room_id'])
            
            if available_rooms <= room_type.total_rooms:
                room_type.available_rooms = available_rooms
                room_type.save()
                state.current_state = 'initial'
                state.temp_data = {}
                state.save()
                return "Room availability updated successfully!"
            else:
                return f"Available rooms cannot exceed total rooms ({room_type.total_rooms}). Try again:"
        except ValueError:
            return "Invalid number. Please enter a whole number:"

    return "Unknown state. Type 'help' for commands."

def handle_user_commands(phone_number, message_text, state):
    """Handle regular user commands and booking flow"""
    if message_text == 'book':
        state.current_state = 'booking_district'
        state.save()
        return "Please enter district for hotel search:"
        
    elif message_text == 'status':
        bookings = Booking.objects.filter(guest_phone=phone_number).order_by('-created_at')[:5]
        if not bookings:
            return "No recent bookings found. Type 'book' to make a reservation."
            
        response = "Your Recent Bookings:\n"
        for booking in bookings:
            response += f"ID: {booking.id}\n"
            response += f"Hotel: {booking.room_type.hotel.name}\n"
            response += f"Check-in: {booking.check_in.strftime('%d-%m-%Y')}\n"
            response += f"Status: {booking.status}\n\n"
        return response
        
    elif message_text == 'cancel':
        state.current_state = 'cancelling_booking'
        state.save()
        return "Enter booking ID to cancel:"
        
    elif message_text == 'help':
        return get_help_message(phone_number)
        
    return handle_user_state(phone_number, message_text, state)

        
def handle_user_state(phone_number, message_text, state):
    """Handle user booking state machine"""
    current_state = state.current_state
    temp_data = state.temp_data

    if current_state == 'booking_locality':
        hotels = Hotel.objects.filter(
            district__iexact=temp_data['district'],
            city__iexact=temp_data['city'],
            locality__iexact=message_text,
            is_active=True
        )
        
        if hotels.exists():
            response = "Available Hotels:\n"
            for i, hotel in enumerate(hotels, 1):
                response += f"{i}. {hotel.name}\n"
            
            temp_data['hotels'] = list(hotels.values())
            state.current_state = 'selecting_hotel'
            state.temp_data = temp_data
            state.save()
            return response + "\nEnter hotel number to select:"
        else:
            return "No hotels found in this location. Type 'book' to try again."

    elif current_state == 'selecting_hotel':
        try:
            hotel_index = int(message_text) - 1
            hotel_data = temp_data['hotels'][hotel_index]
            temp_data['selected_hotel_id'] = hotel_data['id']
            
            room_types = RoomType.objects.filter(
                hotel_id=hotel_data['id'],
                available_rooms__gt=0
            )
            
            response = "Available Room Types:\n"
            for i, room in enumerate(room_types, 1):
                response += f"{i}. {room.name}\n"
                response += f"   Price: ₹{room.price_per_day}/day\n"
                response += f"   Amenities: {room.amenities}\n\n"
            
            temp_data['room_types'] = list(room_types.values())
            state.current_state = 'selecting_room'
            state.temp_data = temp_data
            state.save()
            return response + "Enter room number to select:"
        except (ValueError, IndexError):
            return "Invalid selection. Please enter a valid number:"

    elif current_state == 'selecting_room':
        try:
            room_index = int(message_text) - 1
            room_data = temp_data['room_types'][room_index]
            temp_data['selected_room_id'] = room_data['id']
            
            state.current_state = 'entering_checkin'
            state.temp_data = temp_data
            state.save()
            return "Enter check-in date (DD-MM-YYYY):"
        except (ValueError, IndexError):
            return "Invalid selection. Please enter a valid number:"

    elif current_state == 'entering_checkin':
        try:
            check_in = datetime.strptime(message_text, '%d-%m-%Y')
            if check_in.date() < datetime.now().date():
                return "Check-in date cannot be in the past. Please enter a valid date (DD-MM-YYYY):"
            
            temp_data['check_in'] = check_in.strftime('%Y-%m-%d')
            state.current_state = 'entering_checkout'
            state.temp_data = temp_data
            state.save()
            return "Enter check-out date (DD-MM-YYYY):"
        except ValueError:
            return "Invalid date format. Please use DD-MM-YYYY:"

    elif current_state == 'entering_checkout':
        try:
            check_out = datetime.strptime(message_text, '%d-%m-%Y')
            check_in = datetime.strptime(temp_data['check_in'], '%Y-%m-%d')
            
            if check_out <= check_in:
                return "Check-out must be after check-in. Please enter check-out date (DD-MM-YYYY):"
            
            temp_data['check_out'] = check_out.strftime('%Y-%m-%d')
            state.current_state = 'entering_rooms'
            state.temp_data = temp_data
            state.save()
            return "Enter number of rooms required:"
        except ValueError:
            return "Invalid date format. Please use DD-MM-YYYY:"

    elif current_state == 'entering_rooms':
        try:
            num_rooms = int(message_text)
            room_type = RoomType.objects.get(id=temp_data['selected_room_id'])
            
            if num_rooms <= 0:
                return "Please enter a valid number of rooms (greater than 0):"
            elif num_rooms > room_type.available_rooms:
                return f"Only {room_type.available_rooms} rooms available. Please enter a smaller number:"
            
            temp_data['num_rooms'] = num_rooms
            state.current_state = 'entering_name'
            state.temp_data = temp_data
            state.save()
            return "Enter guest name:"
        except ValueError:
            return "Invalid number. Please enter a whole number:"

    elif current_state == 'entering_name':
        # Calculate total price and create booking
        room_type = RoomType.objects.get(id=temp_data['selected_room_id'])
        check_in = datetime.strptime(temp_data['check_in'], '%Y-%m-%d')
        check_out = datetime.strptime(temp_data['check_out'], '%Y-%m-%d')
        days = (check_out - check_in).days
        total_price = room_type.price_per_day * days * temp_data['num_rooms']

        # Create booking
        booking = Booking.objects.create(
            room_type=room_type,
            check_in=check_in,
            check_out=check_out,
            guest_name=message_text,
            guest_phone=phone_number,
            number_of_rooms=temp_data['num_rooms'],
            total_price=total_price,
            status='confirmed'
        )

        # Update room availability
        room_type.available_rooms -= temp_data['num_rooms']
        room_type.save()

        # Notify hotel admin
        admin_message = f"New Booking!\n"
        admin_message += f"Booking ID: {booking.id}\n"
        admin_message += f"Guest: {booking.guest_name}\n"
        admin_message += f"Phone: {booking.guest_phone}\n"
        admin_message += f"Check-in: {check_in.strftime('%d-%m-%Y')}\n"
        admin_message += f"Rooms: {booking.number_of_rooms} {room_type.name}"
        
        send_whatsapp_message(room_type.hotel.admin_phone, admin_message)

        # Reset state
        state.current_state = 'initial'
        state.temp_data = {}
        state.save()

        # Send confirmation to user
        return (f"Booking confirmed!\n"
                f"Booking ID: {booking.id}\n"
                f"Hotel: {room_type.hotel.name}\n"
                f"Room Type: {room_type.name}\n"
                f"Check-in: {check_in.strftime('%d-%m-%Y')}\n"
                f"Check-out: {check_out.strftime('%d-%m-%Y')}\n"
                f"Total Price: ₹{total_price}\n\n"
                f"Type 'status' to view your bookings")

    elif current_state == 'cancelling_booking':
        try:
            booking = Booking.objects.get(
                id=int(message_text),
                guest_phone=phone_number,
                status='confirmed'
            )
            
            booking.status = 'cancelled'
            booking.save()

            # Return rooms to inventory
            room_type = booking.room_type
            room_type.available_rooms += booking.number_of_rooms
            room_type.save()

            # Notify hotel admin
            admin_message = f"Booking Cancelled!\n"
            admin_message += f"Booking ID: {booking.id}\n"
            admin_message += f"Guest: {booking.guest_name}"
            
            send_whatsapp_message(room_type.hotel.admin_phone, admin_message)

            state.current_state = 'initial'
            state.save()
            return "Booking cancelled successfully."
        except (ValueError, Booking.DoesNotExist):
            return "Invalid booking ID. Please check your booking ID and try again:"

    return "Unexpected state. Type 'help' for available commands."

def get_help_message(phone_number):
    """Get help message based on user role"""
    try:
        admin = WhatsAppAdmin.objects.get(phone_number=phone_number)
        if admin.role == 'super':
            return ("Super Admin Commands:\n"
                   "- addadmin: Add new admin\n"
                   "- addhotel: Add new hotel\n"
                   "- listadmins: List all admins\n"
                   "- listhotels: List all hotels\n"
                   "- help: Show this message")
        elif admin.role == 'hotel':
            return ("Hotel Admin Commands:\n"
                   "- addroom: Add new room type\n"
                   "- updateroom: Update room availability\n"
                   "- status: View current bookings\n"
                   "- help: Show this message")
    except WhatsAppAdmin.DoesNotExist:
        return ("User Commands:\n"
                "- book: Make a new booking\n"
                "- status: Check your bookings\n"
                "- cancel: Cancel a booking\n"
                "- help: Show this message")

def send_whatsapp_message(phone_number, message):
    """Send WhatsApp message using Meta's API"""
    headers = {
        'Authorization': f'Bearer {settings.WHATSAPP_TOKEN}',
        'Content-Type': 'application/json',
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {"body": message}
    }

    url = f"https://graph.facebook.com/v21.0/{settings.PHONE_NUMBER_ID}/messages"
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error sending message: {e}")
        return None
