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

    # Employee relation
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)

    # Payroll-related fields
    total_income = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'), 
        help_text="The base salary or income for the employee."
    )
    bonus = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'), 
        help_text="Additional bonus for the employee."
    )
    deductions = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'), 
        help_text="Any deductions (e.g., tax, insurance)."
    )
    absence_deductions = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'), 
        help_text="Deductions for employee absences."
    )
    other_deductions = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'), 
        help_text="Additional deductions (e.g., loans, penalties)."
    )
    average_daily_pay = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'), 
        help_text="The employee's average daily pay."
    )

    remarks = models.TextField(
        null=True, blank=True, 
        help_text="Optional remarks or notes for the employee's payslip."
    )

    # Pay period fields
    pay_period_start = models.DateField(help_text="The start date of the pay period.")
    pay_period_end = models.DateField(help_text="The end date of the pay period.")
    
    # Status and payment tracking
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='pending'
    )
    date_processed = models.DateField(
        null=True, blank=True, help_text="Date when the payment was processed."
    )

    # Payment details
    referral_code = models.CharField(
        max_length=255, null=True, blank=True, 
        help_text="The payment transaction referral code."
    )
    payment_platform = models.CharField(
        max_length=50, choices=PAYMENT_PLATFORM_CHOICES, null=True, blank=True, 
        help_text="The payment platform used (e.g., GCash, Bank Transfer, Maya, Other)."
    )
    other_payment_platform = models.CharField(
        max_length=100, null=True, blank=True, 
        help_text="Custom payment platform if 'Other' is selected."
    )
    payment_proof = models.FileField(
        upload_to='payment_proofs/', null=True, blank=True, 
        help_text="Upload proof of payment (receipt or screenshot)."
    )

    def __str__(self):
        return f"Payroll Record: {self.employee} | {self.pay_period_start} to {self.pay_period_end} | {self.status}"

    @property
    def net_pay(self):
        """
        Calculate the net pay after adding bonuses and subtracting deductions.
        """
        total_deductions = self.deductions + self.absence_deductions + self.other_deductions
        return self.total_income + self.bonus - total_deductions

    @property
    def is_paid(self):
        """
        Check if the payroll status is marked as 'paid'.
        """
        return self.status == 'paid'
