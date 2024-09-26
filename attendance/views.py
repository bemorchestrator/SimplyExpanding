from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from employees.models import Employee
from .models import Attendance
from django.utils import timezone
from django.db import transaction
from django.contrib import messages
from decimal import Decimal
from billing.models import BillingRecord
import logging

logger = logging.getLogger(__name__)

@login_required
def clock_in(request):
    employee = get_object_or_404(Employee, user=request.user)
    now = timezone.now()

    # Automatically clock out if it's past 5 PM
    check_for_auto_clock_out(employee)

    with transaction.atomic():
        is_primary = not Attendance.objects.filter(
            employee=employee,
            clock_in_time__date=now.date(),
            is_primary_clock_in=True
        ).exists()

        attendance = Attendance.objects.create(
            employee=employee,
            clock_in_time=now,
            status='clocked_in',
            is_primary_clock_in=is_primary
        )

        if is_primary:
            attendance.calculate_lateness_and_deduction()
            attendance.save()  # Ensure changes are saved
            messages.success(request, 'Successfully clocked in with lateness calculation applied.')
        else:
            messages.success(request, 'Successfully clocked in without lateness calculation.')

    return redirect('clock_in_out_page')


@login_required
def clock_out(request):
    # Get the Employee instance for the logged-in user
    employee = get_object_or_404(Employee, user=request.user)

    # Automatically clock out if it's past 5 PM
    check_for_auto_clock_out(employee)

    # Find the most recent open attendance record
    attendance = Attendance.objects.filter(
        employee=employee,
        clock_out_time__isnull=True
    ).order_by('-clock_in_time').first()

    # Raise a ValueError if no clock-in was found
    if not attendance:
        raise ValueError('Cannot clock out without clocking in first.')

    # Clock out by setting the clock-out time and updating status
    with transaction.atomic():
        attendance.clock_out_time = timezone.now()
        attendance.status = 'clocked_out'
        attendance.save()

        # Use the total_income from Attendance instead of recalculating
        worked_income = attendance.total_income
        worked_hours = attendance.total_hours  # Get the hours worked from Attendance

        # Determine the payment type based on whether there is a holiday in the attendance record
        payment_type = 'holiday' if attendance.holiday else 'regular'

        # Create a billing record for this clock-out
        BillingRecord.objects.create(
            employee=employee,
            total_income=worked_income,
            hours_worked=Decimal(worked_hours) if worked_hours else None,  # Pass hours worked to the billing record
            payment_type=payment_type  # Set payment_type based on holiday
        )
        logger.debug(f"Billing record created for employee {employee} with income {worked_income}, hours worked {worked_hours}, and payment type {payment_type}")

        messages.success(request, 'Successfully clocked out and billing record updated.')

    return redirect('clock_in_out_page')


@login_required
def start_break(request):
    # Get the Employee instance for the logged-in user
    employee = get_object_or_404(Employee, user=request.user)

    # Automatically clock out if it's past 5 PM
    check_for_auto_clock_out(employee)

    # Find the most recent attendance record not already on break
    attendance = Attendance.objects.filter(
        employee=employee,
        clock_out_time__isnull=True,
        break_start_time__isnull=True
    ).order_by('-clock_in_time').first()

    if not attendance or attendance.is_on_break_method():
        messages.warning(request, 'You cannot start a break at this time.')
        return redirect('clock_in_out_page')

    # Start the break by setting break_start_time and updating status
    with transaction.atomic():
        attendance.break_start_time = timezone.now()
        attendance.status = 'on_break'
        attendance.save()
        messages.success(request, 'Break started.')

    return redirect('clock_in_out_page')


@login_required
def end_break(request):
    # Get the Employee instance for the logged-in user
    employee = get_object_or_404(Employee, user=request.user)

    # Automatically clock out if it's past 5 PM
    check_for_auto_clock_out(employee)

    # Find the most recent attendance record that is currently on break
    attendance = Attendance.objects.filter(
        employee=employee,
        break_start_time__isnull=False,
        break_end_time__isnull=True
    ).order_by('-clock_in_time').first()

    if not attendance or not attendance.is_on_break_method():
        messages.warning(request, 'You are not on a break.')
        return redirect('clock_in_out_page')

    # End the break by setting break_end_time and updating status
    with transaction.atomic():
        attendance.break_end_time = timezone.now()
        attendance.status = 'clocked_in'
        attendance.save()
        messages.success(request, 'Break ended.')

    return redirect('clock_in_out_page')


@login_required
def attendance_dashboard(request):
    # Get the Employee instance for the logged-in user
    employee = get_object_or_404(Employee, user=request.user)

    # Automatically clock out if it's past 5 PM
    check_for_auto_clock_out(employee)

    # Display all attendance records for the logged-in employee
    attendance_records = Attendance.objects.filter(employee=employee).order_by('-clock_in_time')

    # Determine current status
    current_status = 'clocked_out'
    open_attendance = Attendance.objects.filter(employee=employee, clock_out_time__isnull=True).first()

    if open_attendance:
        if open_attendance.break_start_time and not open_attendance.break_end_time:
            current_status = 'on_break'
        else:
            current_status = 'clocked_in'

    return render(request, 'attendance/clock_in_out.html', {
        'attendance_records': attendance_records,
        'current_status': current_status
    })


@login_required
def clock_in_out_page(request):
    # Get the Employee instance for the logged-in user
    employee = get_object_or_404(Employee, user=request.user)

    # Automatically clock out if it's past 5 PM
    check_for_auto_clock_out(employee)

    # If it's a POST request, process the form submission (clock in/out/start/end break)
    if request.method == 'POST':
        with transaction.atomic():
            # Clock in action
            if 'clock_in' in request.POST:
                now = timezone.now()
                is_primary = not Attendance.objects.filter(
                    employee=employee,
                    clock_in_time__date=now.date(),
                    is_primary_clock_in=True
                ).exists()

                attendance = Attendance.objects.create(
                    employee=employee,
                    clock_in_time=now,
                    status='clocked_in',
                    is_primary_clock_in=is_primary
                )

                if is_primary:
                    attendance.calculate_lateness_and_deduction()
                    messages.success(request, 'Successfully clocked in with lateness calculation applied.')
                else:
                    messages.success(request, 'Successfully clocked in without lateness calculation.')

            # Clock out action
            elif 'clock_out' in request.POST:
                attendance = Attendance.objects.filter(
                    employee=employee,
                    clock_out_time__isnull=True
                ).order_by('-clock_in_time').first()

                if attendance:
                    attendance.clock_out_time = timezone.now()
                    attendance.status = 'clocked_out'
                    attendance.save()

                    # Use the total_income from Attendance instead of recalculating
                    worked_income = attendance.total_income

                    # Create a billing record for this clock-out
                    BillingRecord.objects.create(
                        employee=employee,
                        total_income=worked_income
                    )
                    logger.debug(f"Billing record created for employee {employee} with income {worked_income}")

                    messages.success(request, 'Successfully clocked out and billing record updated.')
                else:
                    messages.warning(request, 'No active clock-in record found.')

            # Start break action
            elif 'start_break' in request.POST:
                attendance = Attendance.objects.filter(
                    employee=employee,
                    clock_out_time__isnull=True,
                    break_start_time__isnull=True
                ).order_by('-clock_in_time').first()

                if attendance and attendance.is_clocked_in_method():
                    attendance.break_start_time = timezone.now()
                    attendance.status = 'on_break'
                    attendance.save()
                    messages.success(request, 'Break started.')
                else:
                    messages.warning(request, 'Cannot start break at this time.')

            # End break action
            elif 'end_break' in request.POST:
                attendance = Attendance.objects.filter(
                    employee=employee,
                    break_start_time__isnull=False,
                    break_end_time__isnull=True
                ).order_by('-clock_in_time').first()

                if attendance and attendance.is_on_break_method():
                    attendance.break_end_time = timezone.now()
                    attendance.status = 'clocked_in'
                    attendance.save()
                    messages.success(request, 'Break ended.')
                else:
                    messages.warning(request, 'Cannot end break at this time.')

        return redirect('clock_in_out_page')

    # Fetch attendance records for the employee, possibly filtered by date range
    attendance_records = Attendance.objects.filter(employee=employee).order_by('-clock_in_time')

    # Handle date range filtering
    date_range = request.GET.get('date_range')
    if date_range:
        dates = date_range.split(' to ')
        if len(dates) == 2:
            selected_start_date = dates[0]
            selected_end_date = dates[1]
            attendance_records = attendance_records.filter(
                clock_in_time__date__range=[selected_start_date, selected_end_date]
            )
        else:
            selected_start_date = selected_end_date = None
    elif 'today' in request.GET:
        today = timezone.now().date()
        attendance_records = attendance_records.filter(clock_in_time__date=today)
        selected_start_date = selected_end_date = str(today)
    else:
        selected_start_date = selected_end_date = None

    # Determine current status
    current_status = 'clocked_out'
    open_attendance = Attendance.objects.filter(employee=employee, clock_out_time__isnull=True).first()

    if open_attendance:
        if open_attendance.break_start_time and not open_attendance.break_end_time:
            current_status = 'on_break'
        else:
            current_status = 'clocked_in'

    return render(request, 'attendance/clock_in_out.html', {
        'current_status': current_status,
        'attendance_records': attendance_records,
        'selected_start_date': selected_start_date,
        'selected_end_date': selected_end_date,
    })


def check_for_auto_clock_out(employee):
    """
    Automatically clock out the employee if it's 5 PM or later.
    """
    now = timezone.now()

    # Check if it's past 5 PM
    if now.hour >= 17:  # 5 PM
        # Find the most recent open attendance record
        attendance = Attendance.objects.filter(
            employee=employee,
            clock_out_time__isnull=True
        ).order_by('-clock_in_time').first()

        # If the employee is still clocked in, clock them out
        if attendance:
            with transaction.atomic():
                attendance.clock_out_time = now
                attendance.status = 'clocked_out'
                attendance.save()

                # Create a billing record
                worked_income = attendance.total_income
                BillingRecord.objects.create(
                    employee=employee,
                    total_income=worked_income
                )
                logger.debug(f"Auto clock-out applied for employee {employee} at 5 PM.")
