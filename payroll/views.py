# views.py

import os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from attendance.models import Attendance
from employees.models import Employee
from billing.models import BillingRecord
from django.utils.timezone import now
from django.db.models import Sum
from datetime import datetime, timedelta, date

from payroll.forms import PayPeriodForm, PayrollRecordForm
from simplyexpanding import settings
from .models import PayrollRecord
from decimal import Decimal
from django.core.files.storage import FileSystemStorage
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from weasyprint import HTML
from django.http import Http404, HttpResponse, JsonResponse
import logging
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger



# Configure logging (you can adjust the logging level and handlers as needed)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)



@login_required
def payroll_dashboard(request):
    """
    Display the Payroll Dashboard with payroll records and preset/custom pay periods.
    """
    today = now().date()

    # Define preset date ranges
    preset_ranges = {
        '15_days': {
            'label': 'Last 15 Days',
            'start_delta': timedelta(days=15),
            'end_delta': timedelta(days=0),
        },
        '30_days': {
            'label': 'Last 30 Days',
            'start_delta': timedelta(days=30),
            'end_delta': timedelta(days=0),
        },
        '3_months': {
            'label': 'Last 3 Months',
            'start_delta': timedelta(days=90),
            'end_delta': timedelta(days=0),
        },
        '6_months': {
            'label': 'Last 6 Months',
            'start_delta': timedelta(days=180),
            'end_delta': timedelta(days=0),
        },
        '12_months': {
            'label': 'Last 12 Months',
            'start_delta': timedelta(days=365),
            'end_delta': timedelta(days=0),
        },
        'custom': {
            'label': 'Custom Range',
            'start_delta': None,
            'end_delta': None,
        },
    }

    # Get 'date_range' from GET parameters; default to '30_days'
    date_range_key = request.GET.get('date_range', '30_days')

    if date_range_key not in preset_ranges:
        date_range_key = '30_days'  # Fallback to default if invalid

    preset = preset_ranges[date_range_key]

    if date_range_key != 'custom':
        # Calculate pay_period_start and pay_period_end based on preset
        pay_period_start = today - preset['start_delta']
        pay_period_end = today - preset['end_delta']
        current_preset_label = preset['label']
    else:
        # Handle custom date range via GET parameters
        pay_period_start_str = request.GET.get('pay_period_start')
        pay_period_end_str = request.GET.get('pay_period_end')
        form = PayPeriodForm(request.GET)

        if form.is_valid():
            pay_period_start = form.cleaned_data['pay_period_start']
            pay_period_end = form.cleaned_data['pay_period_end']
            current_preset_label = 'Custom Range'
        else:
            # If form is invalid or not provided, fallback to default
            pay_period_start = today - timedelta(days=30)
            pay_period_end = today
            current_preset_label = 'Last 30 Days'

    # Ensure pay_period_start is not after pay_period_end
    if pay_period_start > pay_period_end:
        pay_period_start, pay_period_end = pay_period_end, pay_period_start

    payroll_data = []
    employees = Employee.objects.all()

    # Optimize database queries by fetching all relevant PayrollRecords and BillingRecords in bulk
    payroll_records = PayrollRecord.objects.filter(
        pay_period_start=pay_period_start,
        pay_period_end=pay_period_end,
        employee__in=employees
    ).select_related('employee')

    payroll_record_map = {record.employee_id: record for record in payroll_records}

    # Aggregate total_income from BillingRecords for each employee within the pay period
    billing_totals = BillingRecord.objects.filter(
        date__range=[pay_period_start, pay_period_end],
        employee__in=employees
    ).values('employee').annotate(total_income=Sum('total_income'))

    billing_map = {item['employee']: item['total_income'] for item in billing_totals}

    for employee in employees:
        payroll_record = payroll_record_map.get(employee.id)

        if payroll_record:
            status = payroll_record.status
            date_processed = payroll_record.date_processed
            total_income = payroll_record.total_income
            payroll_id = payroll_record.id
            payment_proof = payroll_record.payment_proof.url if payroll_record.payment_proof else None
        else:
            total_income = billing_map.get(employee.id, Decimal('0.00'))

            if total_income != Decimal('0.00'):
                status = 'pending'
                payroll_id = None
            else:
                status = 'no_income'
                payroll_id = None
            date_processed = None
            payment_proof = None

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
            'payment_proof': payment_proof
        })

    # Initialize the form for custom date range with existing GET parameters
    form = PayPeriodForm(initial={
        'pay_period_start': pay_period_start,
        'pay_period_end': pay_period_end
    }) if date_range_key == 'custom' else PayPeriodForm()

    context = {
        'payroll_data': payroll_data,
        'pay_period_start': pay_period_start,
        'pay_period_end': pay_period_end,
        'preset_ranges': preset_ranges,
        'current_range': date_range_key,
        'current_preset_label': current_preset_label,
        'form': form,
    }

    return render(request, 'payroll/payroll_dashboard.html', context)


@login_required
def initiate_payroll(request, employee_id, pay_period_start, pay_period_end):
    """
    Initiate a payroll record for an employee for a specific pay period.
    If the payroll record already exists, inform the user.
    Redirects to the edit payslip page after initiating the payroll.
    """
    employee = get_object_or_404(Employee, pk=employee_id)
    
    # Check if a PayrollRecord already exists or create a new one
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
    
    # Redirect to the edit payslip page
    return redirect('edit_payslip', payroll_id=payroll_record.id)



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
    

@login_required
def employee_payroll_dashboard(request):
    """
    Display all payroll records of the currently logged-in employee with pagination and rows per page control.
    """
    # Verify if the user has an associated Employee record
    try:
        employee = request.user.employee
    except Employee.DoesNotExist:
        raise Http404("You do not have access to payroll records.")

    # Retrieve all payroll records for the employee, sorted by most recent pay period
    payroll_records = PayrollRecord.objects.filter(employee=employee).order_by('-pay_period_end')

    # Get 'rows_per_page' from GET parameters, default to 10
    rows_per_page = request.GET.get('rows_per_page', '10')
    valid_rows = ['10', '20', '30', 'all']
    if rows_per_page not in valid_rows:
        rows_per_page = '10'

    # Get 'page' from GET parameters, default to 1
    page = request.GET.get('page', 1)

    # Determine the number of items per page
    if rows_per_page == 'all':
        per_page = payroll_records.count() if payroll_records.count() > 10 else 10  # Minimum display of 10
    else:
        per_page = int(rows_per_page) if int(rows_per_page) >=10 else 10  # Enforce minimum of 10

    # Initialize Paginator
    paginator = Paginator(payroll_records, per_page)

    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        page_obj = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results.
        page_obj = paginator.page(paginator.num_pages)

    # Preserve other GET parameters except 'page' and 'rows_per_page'
    get_params = request.GET.copy()
    if 'page' in get_params:
        del get_params['page']
    if 'rows_per_page' in get_params:
        del get_params['rows_per_page']
    current_get_parameters = get_params.urlencode()

    context = {
        'page_obj': page_obj,
        'paginator': paginator,
        'rows_per_page': rows_per_page,
        'current_get_parameters': get_params,  # For preserving other GET params
        'payroll_records': page_obj.object_list,  # Current page's payroll records
        'has_records': payroll_records.exists(),
    }
    return render(request, 'payroll/employee_dashboard.html', context)

@login_required
def download_payslip(request, payroll_id):
    """
    Allow the logged-in employee to download their designed payslip PDF.
    """
    payroll = get_object_or_404(PayrollRecord, pk=payroll_id, employee=request.user.employee)

    # Absolute path to the logo
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'se_logo.png')
    
    if not os.path.exists(logo_path):
        logger.error(f"Logo file does not exist at path: {logo_path}")
        # Optionally, handle the missing logo scenario
        raise Http404("Logo image not found.")

    # Convert to file URL with forward slashes
    logo_url = 'file:///' + logo_path.replace('\\', '/')

    # Ensure all monetary fields have default values
    average_daily_pay = payroll.average_daily_pay or Decimal('0.00')
    num_days = (payroll.pay_period_end - payroll.pay_period_start).days + 1
    basic_salary = average_daily_pay * Decimal(num_days)

    bonus = payroll.bonus or Decimal('0.00')
    deductions = payroll.deductions or Decimal('0.00')
    absence_deductions = payroll.absence_deductions or Decimal('0.00')
    other_deductions = payroll.other_deductions or Decimal('0.00')
    remarks = payroll.remarks or "N/A"

    # Net pay is stored in payroll.total_income
    net_pay = payroll.total_income or Decimal('0.00')

    # Render the payslip template
    html_string = render_to_string('payroll/payslip.html', {
        'employee_name': payroll.employee.user.get_full_name(),
        'pay_period_start': payroll.pay_period_start.strftime('%Y-%m-%d'),
        'pay_period_end': payroll.pay_period_end.strftime('%Y-%m-%d'),
        'date_processed': payroll.date_processed.strftime('%Y-%m-%d') if payroll.date_processed else 'N/A',
        'status': payroll.status,
        'logo_path': logo_url,
        'net_pay': net_pay,
        'basic_salary': basic_salary,
        'bonus': bonus,
        'deductions': deductions,
        'absence_deductions': absence_deductions,
        'other_deductions': other_deductions,
        'average_daily_pay': average_daily_pay,
        'remarks': remarks,
    })

    # Set base_url to the directory containing the logo
    base_url = 'file:///' + os.path.dirname(logo_path).replace('\\', '/') + '/'

    try:
        # Generate PDF
        pdf_file = HTML(string=html_string, base_url=base_url).write_pdf()
    except Exception as e:
        logger.error(f"Failed to generate PDF: {e}")
        raise Http404("Failed to generate PDF.")

    # Create HTTP response
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="payslip_{payroll_id}.pdf"'
    return response


@login_required
def edit_payslip(request, payroll_id):
    """
    Edit the payslip details, save it, and redirect to process payroll.
    """
    payroll = get_object_or_404(PayrollRecord, pk=payroll_id)

    # Fetch employee related to the payroll
    employee = payroll.employee

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.method == 'GET':
        # This is an AJAX request, process accordingly
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        try:
            pay_period_start = datetime.strptime(start_date, '%Y-%m-%d').date()
            pay_period_end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid dates provided'}, status=400)

        attendance_records = Attendance.objects.filter(
            employee=employee,
            clock_in_time__date__range=[pay_period_start, pay_period_end]
        )

        lateness_deduction = attendance_records.aggregate(
            total_lateness=Sum('lateness_deduction')
        )['total_lateness'] or Decimal('0.00')

        # Calculate the number of days in the pay period (inclusive)
        num_days = (pay_period_end - pay_period_start).days + 1

        # Get the per_day_rate from the employee model
        per_day_rate = employee.per_day_rate or Decimal('0.00')

        # Calculate Basic Salary
        basic_salary = per_day_rate * Decimal(num_days)

        return JsonResponse({
            'lateness_deduction': str(lateness_deduction),
            'basic_salary': str(basic_salary),
            'average_daily_pay': str(per_day_rate),
        })

    if request.method == 'POST':
        form = PayrollRecordForm(request.POST, instance=payroll)

        # Set fields to readonly in the form
        form.fields['total_income'].widget.attrs['readonly'] = True
        form.fields['average_daily_pay'].widget.attrs['readonly'] = True

        if form.is_valid():
            # Retrieve the form data for calculations
            basic_salary = form.cleaned_data.get('total_income', Decimal('0.00'))
            bonus = form.cleaned_data.get('bonus', Decimal('0.00'))
            deductions = form.cleaned_data.get('deductions', Decimal('0.00'))
            absence_deductions = form.cleaned_data.get('absence_deductions', Decimal('0.00'))
            other_deductions = form.cleaned_data.get('other_deductions', Decimal('0.00'))

            # Calculate net pay: Basic Salary + Bonus - (Deductions + Absence Deductions + Other Deductions)
            net_pay = basic_salary + bonus - (deductions + absence_deductions + other_deductions)

            # Save the updated payroll record with net pay
            payroll = form.save(commit=False)
            payroll.total_income = net_pay  # Update the net pay in the model
            payroll.status = 'pending'  # Ensure status is set to 'pending' after edits
            payroll.save()

            messages.success(request, 'Payslip updated successfully.')

            # Redirect to process payroll page after saving
            return redirect('process_payroll', payroll_id=payroll.id)
        else:
            # Log form errors for debugging
            logger.debug("Form is invalid. Errors: %s", form.errors)
            messages.error(request, 'There was an error updating the payslip. Please see the errors below.')
    else:
        # Pre-fill the "Other Deductions" field with the lateness deduction
        attendance_records = Attendance.objects.filter(
            employee=employee,
            clock_in_time__date__range=[payroll.pay_period_start, payroll.pay_period_end]
        )

        # Sum up the lateness deductions from all attendance records in the period
        lateness_deduction = attendance_records.aggregate(
            total_lateness=Sum('lateness_deduction')
        )['total_lateness'] or Decimal('0.00')

        # Calculate the number of days in the pay period (inclusive)
        num_days = (payroll.pay_period_end - payroll.pay_period_start).days + 1

        # Get the per_day_rate from the employee model
        per_day_rate = employee.per_day_rate or Decimal('0.00')

        # Calculate Basic Salary
        basic_salary = per_day_rate * Decimal(num_days)

        form = PayrollRecordForm(instance=payroll, initial={
            'other_deductions': lateness_deduction,
            'average_daily_pay': per_day_rate,
            'total_income': basic_salary,
            # Do not set 'absence_deductions' here; leave it for manual input
        })

        # Set fields to readonly in the form
        form.fields['total_income'].widget.attrs['readonly'] = True
        form.fields['average_daily_pay'].widget.attrs['readonly'] = True

    return render(request, 'payroll/edit_payslip.html', {'form': form, 'payroll': payroll})


@login_required
def preview_payslip(request, payroll_id):
    """
    Preview the payslip design before confirming payment.
    """
    payroll = get_object_or_404(PayrollRecord, pk=payroll_id)
    return render(request, 'payroll/preview_payslip.html', {'payroll': payroll})


@login_required
def confirm_payslip(request, payroll_id):
    """
    Confirm the payslip, marking it as 'paid'.
    """
    payroll = get_object_or_404(PayrollRecord, pk=payroll_id)
    payroll.status = 'paid'
    payroll.date_processed = now()
    payroll.save()
    return redirect('employee_dashboard')