# views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from employees.models import Employee
from billing.models import BillingRecord
from django.utils.timezone import now
from django.db.models import Sum
from datetime import timedelta
from .models import PayrollRecord
from decimal import Decimal
from django.core.files.storage import FileSystemStorage
from django.core.exceptions import ValidationError

@login_required
def payroll_dashboard(request):
    """
    Display the Payroll Dashboard with all payroll records.
    Includes a column for Proof of Payment with clickable thumbnails.
    """
    today = now().date()
    pay_period_start = today - timedelta(days=30)
    pay_period_end = today

    payroll_data = []

    employees = Employee.objects.all()

    for employee in employees:
        payroll_record = PayrollRecord.objects.filter(
            employee=employee,
            pay_period_start=pay_period_start,
            pay_period_end=pay_period_end
        ).first()

        if payroll_record:
            status = payroll_record.status
            date_processed = payroll_record.date_processed
            total_income = payroll_record.total_income
            payroll_id = payroll_record.id
            payment_proof = payroll_record.payment_proof.url if payroll_record.payment_proof else None
        else:
            total_income = BillingRecord.objects.filter(
                employee=employee,
                date__range=[pay_period_start, pay_period_end]
            ).aggregate(total_income=Sum('total_income'))['total_income'] or Decimal('0.00')

            if total_income != Decimal('0.00'):
                status = 'pending'
                payroll_id = None
            else:
                status = 'no_income'
                payroll_id = None
            date_processed = None
            payment_proof = None  # No proof if no payroll record exists

        status_display = status.title() if status not in ['pending', 'paid', 'no_income'] else status.capitalize()

        payroll_data.append({
            'id': payroll_id,
            'employee': employee,
            'pay_period_start': pay_period_start,
            'pay_period_end': pay_period_end,
            'total_income': total_income,
            'status': status,
            'status_display': status_display,
            'date_processed': date_processed,
            'payment_proof': payment_proof  # Added payment_proof to context
        })

    context = {
        'payroll_data': payroll_data
    }

    return render(request, 'payroll/payroll_dashboard.html', context)


@login_required
def initiate_payroll(request, employee_id, pay_period_start, pay_period_end):
    """
    Initiate a payroll record for an employee for a specific pay period.
    If the payroll record already exists, inform the user.
    """
    employee = get_object_or_404(Employee, pk=employee_id)
    
    # Check if a PayrollRecord already exists
    payroll_record, created = PayrollRecord.objects.get_or_create(
        employee=employee,
        pay_period_start=pay_period_start,
        pay_period_end=pay_period_end,
        defaults={
            'total_income': BillingRecord.objects.filter(
                employee=employee,
                date__range=[pay_period_start, pay_period_end]
            ).aggregate(total_income=Sum('total_income'))['total_income'] or Decimal('0.00'),
            'status': 'pending'
        }
    )
    
    if created:
        messages.success(request, f'Payroll record created for {employee.user.username}.')
    else:
        messages.info(request, f'Payroll record already exists for {employee.user.username}.')
    
    return redirect('process_payroll', payroll_record.id)


@login_required
def process_payroll(request, payroll_id=None, employee_id=None, pay_period_start=None, pay_period_end=None):
    """
    Process a payroll record by updating its status to 'paid' and attaching proof of payment.
    Handles both existing payroll records and initiates new ones if necessary.
    """
    if payroll_id:
        payroll_record = get_object_or_404(PayrollRecord, pk=payroll_id)
    elif employee_id and pay_period_start and pay_period_end:
        employee = get_object_or_404(Employee, pk=employee_id)
        payroll_record, created = PayrollRecord.objects.get_or_create(
            employee=employee,
            pay_period_start=pay_period_start,
            pay_period_end=pay_period_end,
            defaults={
                'total_income': BillingRecord.objects.filter(
                    employee=employee,
                    date__range=[pay_period_start, pay_period_end]
                ).aggregate(total_income=Sum('total_income'))['total_income'] or Decimal('0.00'),
                'status': 'pending'
            }
        )
    else:
        messages.error(request, 'Invalid parameters for processing payroll.')
        return redirect('payroll_dashboard')

    if request.method == 'POST':
        referral_code = request.POST.get('referral_code')
        payment_platform = request.POST.get('payment_platform')
        other_payment_platform = request.POST.get('other_payment_platform') if payment_platform == 'other' else None
        payment_proof = request.FILES.get('payment_proof')

        payroll_record.referral_code = referral_code
        payroll_record.payment_platform = payment_platform
        payroll_record.other_payment_platform = other_payment_platform
        payroll_record.status = 'paid'
        payroll_record.date_processed = now()

        # Handle payment proof upload with server-side validation
        if payment_proof:
            try:
                validate_payment_proof(payment_proof)
            except ValidationError as e:
                messages.error(request, e.message)
                return redirect('process_payroll', payroll_record.id)
            
            payroll_record.payment_proof = payment_proof

        payroll_record.save()

        messages.success(request, f'Payroll for {payroll_record.employee.user.username} has been processed.')
        return redirect('payroll_dashboard')

    context = {
        'employee': payroll_record.employee,
        'pay_period_start': payroll_record.pay_period_start,
        'pay_period_end': payroll_record.pay_period_end,
        'total_income': payroll_record.total_income,
        'payment_platform': payroll_record.payment_platform,
        'payroll_record': payroll_record,  # Added to access payment_proof in template
    }

    return render(request, 'payroll/process_payroll.html', context)


def validate_payment_proof(payment_proof):
    """
    Validates the uploaded payment proof file.
    Ensures that the file is an image and does not exceed size limits.
    Raises ValidationError if validation fails.
    """
    valid_mime_types = ['image/jpeg', 'image/png', 'image/gif']
    if payment_proof.content_type not in valid_mime_types:
        raise ValidationError('Unsupported file type. Please upload an image file (JPEG, PNG, GIF).')
    
    max_file_size = 5 * 1024 * 1024  # 5MB
    if payment_proof.size > max_file_size:
        raise ValidationError('File size exceeds the 5MB limit.')
