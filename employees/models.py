# employees/models.py

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from decimal import Decimal
import pyotp
import threading

# Initialize thread-local storage
_thread_locals = threading.local()

def is_updating_employee():
    return getattr(_thread_locals, 'updating_employee', False)

def set_updating_employee(value):
    _thread_locals.updating_employee = value

class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    username = models.CharField(
        max_length=100,
        unique=True,
        default="default_username",
        help_text="Unique username for the employee. Example: jdoe"
    )
    first_name = models.CharField(
        max_length=100,
        default="Juan",
        help_text="First name of the employee. Example: Juan"
    )
    middle_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Middle name of the employee. Optional."
    )
    last_name = models.CharField(
        max_length=100,
        default="Dela Cruz",
        help_text="Last name of the employee. Example: Dela Cruz"
    )
    email = models.EmailField(
        unique=True,
        default="default@example.com",
        help_text="Email address of the employee. Example: jdoe@example.com"
    )
    address = models.CharField(
        max_length=255,
        default="123 Default St",
        help_text="Home address of the employee. Example: 123 Main St, City, Country"
    )
    phone_number = models.CharField(
        max_length=20,
        default="0000000000",
        help_text="Contact phone number of the employee. Example: 09123456789"
    )
    city = models.CharField(
        max_length=100,
        default="Default City",
        help_text="City where the employee resides. Example: Manila"
    )
    country = models.CharField(
        max_length=100,
        default="Default Country",
        help_text="Country where the employee resides. Example: Philippines"
    )
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True,
        default='profile_pictures/default-profile.png',
        help_text="Upload a profile picture for the employee."
    )
    per_day_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Daily rate for the employee. Example: 100.00"
    )
    scheduled_start_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Specific scheduled start time for the employee. If not set, global scheduled start time is used. Example: 19:30 (24-hour format)"
    )
    lateness_rules = models.ManyToManyField(
        'attendance.LatenessRule',
        blank=True,
        help_text="Assign one or more lateness rules to the employee. If not set, the global default rule is applied."
    )

    # Add TOTP secret field for 2FA (Google Authenticator)
    totp_secret = models.CharField(
        max_length=32,
        default=pyotp.random_base32,
        help_text="TOTP secret for two-factor authentication"
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"

# Signal to create or update Employee whenever a User is created or updated
@receiver(post_save, sender=User)
def create_or_update_employee(sender, instance, created, **kwargs):
    if is_updating_employee():
        return  # Avoid recursion

    if created:
        Employee.objects.create(
            user=instance,
            username=instance.username,
            first_name=instance.first_name or "Juan",
            last_name=instance.last_name or "Dela Cruz",
            email=instance.email or "default@example.com"
        )
    else:
        try:
            employee = instance.employee
            set_updating_employee(True)
            # Update Employee fields based on User fields
            employee.username = instance.username
            employee.first_name = instance.first_name or "Juan"
            employee.last_name = instance.last_name or "Dela Cruz"
            employee.email = instance.email or "default@example.com"
            employee.save(update_fields=['username', 'first_name', 'last_name', 'email'])
        except Employee.DoesNotExist:
            Employee.objects.create(
                user=instance,
                username=instance.username,
                first_name=instance.first_name or "Juan",
                last_name=instance.last_name or "Dela Cruz",
                email=instance.email or "default@example.com"
            )
        finally:
            set_updating_employee(False)

# Signal to update User when Employee is updated
@receiver(post_save, sender=Employee)
def update_user_from_employee(sender, instance, **kwargs):
    if is_updating_employee():
        return  # Avoid recursion

    try:
        user = instance.user
        if user:
            set_updating_employee(True)
            # Update User fields based on Employee fields
            user.username = instance.username
            user.first_name = instance.first_name
            user.last_name = instance.last_name
            user.email = instance.email
            user.save(update_fields=['username', 'first_name', 'last_name', 'email'])
    finally:
        set_updating_employee(False)

# Signal to delete User when Employee is deleted
@receiver(post_delete, sender=Employee)
def delete_user_with_employee(sender, instance, **kwargs):
    if instance.user:
        instance.user.delete()
