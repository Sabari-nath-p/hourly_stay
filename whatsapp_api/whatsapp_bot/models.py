from django.db import models

class WhatsAppAdmin(models.Model):
    ROLES = [
        ('super', 'Super Admin'),
        ('hotel', 'Hotel Admin'),
        ('user', 'Regular User')
    ]
    
    phone_number = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=10, choices=ROLES, default='user')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.role})"

class Hotel(models.Model):
    name = models.CharField(max_length=200)
    district = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    locality = models.CharField(max_length=100)
    admin_phone = models.CharField(max_length=20)
    description = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class RoomType(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    total_rooms = models.IntegerField()
    available_rooms = models.IntegerField()
    amenities = models.TextField()

    def __str__(self):
        return f"{self.hotel.name} - {self.name}"

class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed')
    ]
    
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE)
    check_in = models.DateTimeField()
    check_out = models.DateTimeField()
    guest_name = models.CharField(max_length=100)
    guest_phone = models.CharField(max_length=20)
    number_of_rooms = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

class WhatsAppState(models.Model):
    phone_number = models.CharField(max_length=20, unique=True)
    current_state = models.CharField(max_length=50, default='initial')
    temp_data = models.JSONField(default=dict)
    last_updated = models.DateTimeField(auto_now=True)