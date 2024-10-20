from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from employees.models import Employee
from .models import Attendance, Break
from django.utils import timezone
from django.db import transaction
from django.contrib import messages
from decimal import Decimal
from billing.models import BillingRecord
import logging
from django.core.paginator import Paginator
import json

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
            # Adjust timezone consistency
            scheduled_time = timezone.localtime(attendance.get_scheduled_start_time())
            clock_in_time_local = timezone.localtime(attendance.clock_in_time)

            # Apply grace period
            grace_period = (
                employee.lateness_rules.first().grace_period 
                if employee.lateness_rules.exists() 
                else timedelta(minutes=5)
            )

            lateness = clock_in_time_local - scheduled_time

            # Check if lateness exceeds the grace period
            if lateness > grace_period:
                attendance.lateness = lateness
                attendance.apply_lateness_deduction(lateness)
                attendance.lateness_calculated = True
                messages.success(request, 'Successfully clocked in with lateness calculation applied.')
            else:
                attendance.lateness = timedelta(0)
                attendance.lateness_deduction = Decimal('0.00')
                attendance.lateness_calculated = False
                messages.success(request, 'Successfully clocked in on time.')

            attendance.save()  # Ensure changes are saved
        else:
            messages.success(request, 'Successfully clocked in without lateness calculation.')

    return redirect('clock_in_out_page')


@login_required
def clock_out(request):
    # Get the Employee instance for the logged-in user
    employee = get_object_or_404(Employee, user=request.user)

    # Automatically clock out if it's past 5 PM
    check_for_auto_clock_out(employee)

    # Find the most recent open attendance record where clock_out_time is null
    attendance = Attendance.objects.filter(
        employee=employee,
        clock_out_time__isnull=True
    ).order_by('-clock_in_time').first()

    if not attendance:
        messages.error(request, 'Cannot clock out without clocking in first.')
        return redirect('clock_in_out_page')

    with transaction.atomic():
        # Set clock_out_time to the current time
        attendance.clock_out_time = timezone.now()
        attendance.status = 'clocked_out'

        # Ensure calculations are done correctly by triggering the save method
        try:
            # Trigger save to calculate total hours and income
            attendance.save()

            # Log calculated values for debugging
            logger.debug(f"Employee: {employee}, Total Hours Worked: {attendance.total_hours}, Total Income: {attendance.total_income}")

            worked_income = attendance.total_income
            worked_hours = attendance.total_hours  # This is a DecimalField

            payment_type = 'holiday' if attendance.holiday else 'regular'

            # Create a billing record for the worked income and hours
            BillingRecord.objects.create(
                employee=employee,
                total_income=worked_income,
                hours_worked=worked_hours if worked_hours else None,
                payment_type=payment_type
            )
            logger.debug(f"Billing record created for employee {employee} with income {worked_income}, hours worked {worked_hours}, and payment type {payment_type}")

            # Display success message
            messages.success(request, 'Successfully clocked out and billing record updated.')

        except Exception as e:
            # Log error for troubleshooting
            logger.error(f"Error during clock out: {e}")
            messages.error(request, 'An error occurred during the clock-out process.')

    return redirect('clock_in_out_page')

@login_required
def start_break(request):
    # Get the Employee instance for the logged-in user
    employee = get_object_or_404(Employee, user=request.user)

    # Automatically clock out if it's past 5 PM
    check_for_auto_clock_out(employee)

    # Find the most recent attendance record that is currently clocked in
    attendance = Attendance.objects.filter(
        employee=employee,
        clock_out_time__isnull=True,
    ).order_by('-clock_in_time').first()

    if not attendance or attendance.status != 'clocked_in':
        messages.warning(request, 'You cannot start a break at this time.')
        return redirect('clock_in_out_page')

    with transaction.atomic():
        # Create a new Break record
        Break.objects.create(
            attendance=attendance,
            break_start_time=timezone.now()
        )
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
        clock_out_time__isnull=True,
    ).order_by('-clock_in_time').first()

    if not attendance or attendance.status != 'on_break':
        messages.warning(request, 'You are not on a break.')
        return redirect('clock_in_out_page')

    with transaction.atomic():
        # Find the most recent Break record without an end time
        current_break = Break.objects.filter(
            attendance=attendance,
            break_end_time__isnull=True
        ).order_by('-break_start_time').first()

        if not current_break:
            messages.warning(request, 'No active break found.')
            return redirect('clock_in_out_page')

        current_break.break_end_time = timezone.now()
        current_break.save()

        attendance.status = 'clocked_in'
        attendance.calculate_total_hours()
        attendance.calculate_income()
        attendance.save()
        messages.success(request, 'Break ended.')

    return redirect('clock_in_out_page')

@login_required
def attendance_dashboard(request):
    # Redirect to the main clock in/out page
    return redirect('clock_in_out_page')




@login_required
def clock_in_out_page(request):
    # Helper function to format timedelta as hh:mm:ss
    def format_timedelta(td):
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}:{minutes:02}:{seconds:02}"

    # Get the logged-in user's employee record
    current_employee = get_object_or_404(Employee, user=request.user)

    # Admin can select an employee, or regular users will view their own records
    if request.user.is_superuser:
        employees = Employee.objects.all()  # Fetch all employees for the dropdown menu
        if 'employee_id' in request.GET:
            # Admin viewing selected employee's attendance
            employee = get_object_or_404(Employee, pk=request.GET.get('employee_id'))
        else:
            # Default to viewing admin's own attendance
            employee = current_employee
    else:
        # Regular user
        employee = current_employee
        employees = None  # No dropdown for regular users

    # Automatically clock out if it's past 5 PM
    check_for_auto_clock_out(employee)

    # Handle POST request (Clock in/out/start/end break)
    if request.method == 'POST':
        # Only allow the current user to perform clock in/out actions for themselves
        if employee != current_employee:
            messages.error(request, 'You cannot perform actions on behalf of other employees.')
            return redirect('clock_in_out_page')

        action = None
        if 'clock_in' in request.POST:
            action = 'clock_in'
        elif 'clock_out' in request.POST:
            action = 'clock_out'
        elif 'start_break' in request.POST:
            action = 'start_break'
        elif 'end_break' in request.POST:
            action = 'end_break'

        with transaction.atomic():
            if action == 'clock_in':
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
                    attendance.calculate_total_hours()
                    attendance.calculate_income()
                    attendance.save()
                    messages.success(request, 'Successfully clocked in with lateness calculation applied.')
                else:
                    attendance.save()
                    messages.success(request, 'Successfully clocked in without lateness calculation.')

            elif action == 'clock_out':
                attendance = Attendance.objects.filter(
                    employee=employee,
                    clock_out_time__isnull=True
                ).order_by('-clock_in_time').first()

                if attendance:
                    attendance.clock_out_time = timezone.now()
                    attendance.status = 'clocked_out'
                    attendance.save()  # Trigger calculations via the overridden save method

                    # Create a billing record for the worked income and hours
                    try:
                        BillingRecord.objects.create(
                            employee=employee,
                            total_income=attendance.total_income,
                            hours_worked=attendance.total_hours if attendance.total_hours else Decimal('0.00'),
                            payment_type='holiday' if attendance.holiday else 'regular'
                        )
                        logger.debug(f"Billing record created for employee {employee} with income {attendance.total_income}, hours worked {attendance.total_hours}, and payment type {attendance.holiday.holiday_type if attendance.holiday else 'regular'}")
                        messages.success(request, 'Successfully clocked out and billing record updated.')
                    except Exception as e:
                        logger.error(f"Error creating billing record: {e}")
                        messages.error(request, 'Successfully clocked out, but failed to create billing record.')

                else:
                    messages.warning(request, 'No active clock-in record found.')

            elif action == 'start_break':
                attendance = Attendance.objects.filter(
                    employee=employee,
                    clock_out_time__isnull=True,
                ).order_by('-clock_in_time').first()

                if attendance and attendance.status == 'clocked_in':
                    # Create a new Break record
                    Break.objects.create(
                        attendance=attendance,
                        break_start_time=timezone.now()
                    )
                    attendance.status = 'on_break'
                    attendance.save()
                    messages.success(request, 'Break started.')
                else:
                    messages.warning(request, 'Cannot start break at this time.')

            elif action == 'end_break':
                attendance = Attendance.objects.filter(
                    employee=employee,
                    clock_out_time__isnull=True,
                ).order_by('-clock_in_time').first()

                if attendance and attendance.status == 'on_break':
                    # Find the most recent Break record without an end time
                    current_break = Break.objects.filter(
                        attendance=attendance,
                        break_end_time__isnull=True
                    ).order_by('-break_start_time').first()

                    if current_break:
                        current_break.break_end_time = timezone.now()
                        current_break.save()
                        attendance.status = 'clocked_in'
                        attendance.calculate_total_hours()
                        attendance.calculate_income()
                        attendance.save()
                        messages.success(request, 'Break ended.')
                    else:
                        messages.warning(request, 'No active break found.')
                else:
                    messages.warning(request, 'Cannot end break at this time.')

        return redirect('clock_in_out_page')

    # Fetch attendance records for the employee
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

    # Pagination: handle rows per page selection
    rows_per_page = request.GET.get('rows_per_page', 10)  # Default to 10 rows per page
    if rows_per_page == 'all':
        paginator = None  # No pagination if 'all' is selected
        page_obj = attendance_records
    else:
        try:
            rows_per_page = int(rows_per_page)
        except ValueError:
            rows_per_page = 10  # Fallback to default if invalid
        paginator = Paginator(attendance_records, rows_per_page)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

    # Grand totals calculation over displayed records
    grand_total_break_duration_td = sum([record.break_duration for record in page_obj], timedelta(0))
    grand_total_time_td = sum([record.total_time for record in page_obj if record.total_time], timedelta(0))
    grand_total_hours_worked = sum([record.total_hours for record in page_obj if record.total_hours], Decimal('0.00'))
    grand_total_time_late_td = sum([record.lateness for record in page_obj if record.lateness], timedelta(0))
    grand_total_deductions = sum([record.lateness_deduction for record in page_obj if record.lateness_deduction], Decimal('0.00'))
    grand_total_income = sum([record.total_income for record in page_obj if record.total_income], Decimal('0.00'))

    # Format the timedelta objects
    grand_total_break_duration = format_timedelta(grand_total_break_duration_td)
    grand_total_time = format_timedelta(grand_total_time_td)
    grand_total_time_late = format_timedelta(grand_total_time_late_td)

    # Build the current GET parameters, excluding 'page'
    current_get_parameters = request.GET.copy()
    if 'page' in current_get_parameters:
        del current_get_parameters['page']

    # Determine current status
    current_status = 'clocked_out'
    open_attendance = Attendance.objects.filter(employee=employee, clock_out_time__isnull=True).first()

    if open_attendance:
        if open_attendance.status == 'on_break':
            current_status = 'on_break'
        elif open_attendance.status == 'clocked_in':
            current_status = 'clocked_in'

        # Prepare data for JavaScript
        standard_hours_per_day = 8.0
        js_data = {
            'clock_in_time': open_attendance.clock_in_time.isoformat() if open_attendance.clock_in_time else None,
            'per_day_rate': float(open_attendance.employee.per_day_rate),
            'standard_hours_per_day': standard_hours_per_day,
            'is_on_break': current_status == 'on_break',
            'deductions_applied': float(open_attendance.lateness_deduction) if open_attendance.lateness_deduction else 0
        }
    else:
        js_data = {}

    return render(request, 'attendance/clock_in_out.html', {
        'current_status': current_status,
        'attendance_records': attendance_records,
        'selected_start_date': selected_start_date,
        'selected_end_date': selected_end_date,
        'page_obj': page_obj,
        'paginator': paginator,
        'rows_per_page': rows_per_page,
        'js_data': json.dumps(js_data),
        'employees': employees,  # Pass employee list for the admin dropdown
        'employee': employee,    # Pass the selected employee
        'grand_total_break_duration': grand_total_break_duration,
        'grand_total_time': grand_total_time,
        'grand_total_hours_worked': grand_total_hours_worked,
        'grand_total_time_late': grand_total_time_late,
        'grand_total_deductions': grand_total_deductions,
        'grand_total_income': grand_total_income,
        'current_get_parameters': current_get_parameters,
    })





def check_for_auto_clock_out(employee):
    """
    Automatically clock out the employee if it's 5 PM or later.
    """
    now = timezone.now()

    # Check if it's past 5 PM and before midnight
    if now.hour >= 17 and now.hour < 24:
        # Find the most recent open attendance record
        attendance = Attendance.objects.filter(
            employee=employee,
            clock_out_time__isnull=True
        ).order_by('-clock_in_time').first()

        # If the employee is still clocked in or on break, clock them out
        if attendance:
            with transaction.atomic():
                attendance.clock_out_time = now
                attendance.status = 'clocked_out'
                attendance.save()

                # Create a billing record for the worked income and hours
                try:
                    BillingRecord.objects.create(
                        employee=employee,
                        total_income=attendance.total_income,
                        hours_worked=attendance.total_hours if attendance.total_hours else Decimal('0.00'),
                        payment_type='holiday' if attendance.holiday else 'regular'
                    )
                    logger.debug(f"Auto clock-out applied for employee {employee} at 5 PM.")
                except Exception as e:
                    logger.error(f"Error creating billing record during auto clock-out: {e}")
