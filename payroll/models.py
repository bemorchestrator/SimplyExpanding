from django.db import models
from employees.models import Employee
from decimal import Decimal

class PayrollRecord(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ]
    
    PAYMENT_PLATFORM_CHOICES = [
        ('gcash', 'GCash'),
        ('bank_transfer', 'Bank Transfer'),
        ('maya', 'Maya'),
        ('other', 'Other'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    total_income = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    pay_period_start = models.DateField(help_text="The start date of the pay period.")
    pay_period_end = models.DateField(help_text="The end date of the pay period.")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    date_processed = models.DateField(null=True, blank=True, help_text="Date when the payment was processed.")
    
    # New fields for referral code, payment platform, other platform, and payment proof
    referral_code = models.CharField(max_length=255, null=True, blank=True, help_text="The payment transaction referral code.")
    payment_platform = models.CharField(max_length=50, choices=PAYMENT_PLATFORM_CHOICES, null=True, blank=True, help_text="The payment platform used (e.g., GCash, Bank Transfer, Maya, Other).")
    other_payment_platform = models.CharField(max_length=100, null=True, blank=True, help_text="Custom payment platform if 'Other' is selected.")
    payment_proof = models.FileField(upload_to='payment_proofs/', null=True, blank=True, help_text="Upload proof of payment (receipt or screenshot).")
    
    def __str__(self):
        return f"Payroll Record: {self.employee} | {self.pay_period_start} to {self.pay_period_end} | {self.status}"

    @property
    def is_paid(self):
        return self.status == 'paid'
