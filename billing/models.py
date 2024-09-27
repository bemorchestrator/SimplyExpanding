# billing/models.py

from django.db import models
from employees.models import Employee
from client.models import ClientOnboarding
from django.utils import timezone

class BillingRecord(models.Model):
    PAYMENT_TYPE_CHOICES = [
        ('holiday', 'Holiday'),
        ('regular', 'Regular Work Day'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    total_income = models.DecimalField(max_digits=10, decimal_places=2)  # Reflects total income with deductions
    hours_worked = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # Field to track hours worked
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPE_CHOICES, default='regular')  # Defines whether income is from a regular day or holiday
    date = models.DateField(auto_now_add=True)  # Automatically sets the date for the billing record

    def __str__(self):
        return f"{self.employee} - {self.date} - {self.total_income} ({self.payment_type})"
    
    # Optional method to format total income display (for future use)
    def formatted_total_income(self):
        return f"Php {self.total_income:.2f}"


class Invoice(models.Model):
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('PHP', 'Philippine Peso'),
        # Add other currencies as needed
    ]

    client = models.ForeignKey(ClientOnboarding, on_delete=models.CASCADE)
    client_name = models.CharField(max_length=255)
    invoice_number = models.CharField(max_length=20, unique=True, blank=True, null=True)  # New field
    client_address = models.TextField(blank=True, null=True)  # New field
    invoice_date = models.DateField(default=timezone.now, editable=True)
    due_date = models.DateField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=10,
        choices=[
            ('pending', 'Pending'),
            ('paid', 'Paid'),
            ('overdue', 'Overdue'),
        ],
        default='pending'
    )
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='USD'
    )
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Invoice {self.id} - {self.client_name} - {self.total_amount} {self.currency}"