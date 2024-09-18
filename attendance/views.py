# attendance/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from employees.models import Employee  # Import the Employee model
from .models import Attendance
from django.utils import timezone
from django.db import transaction
from django.contrib import messages

@login_required
def clock_in(request):
    # Get the Employee instance for the logged-in user
    employee = get_object_or_404(Employee, user=request.user)
    
    # Check if the employee has already clocked in without clocking out
    if Attendance.objects.filter(employee=employee, clock_out_time__isnull=True).exists():
        messages.warning(request, 'You have already clocked in.')
        return redirect('clock_in_out_page')

    # Create an attendance record with clock-in time and set status to 'clocked_in'
    with transaction.atomic():
        Attendance.objects.create(employee=employee, clock_in_time=timezone.now(), status='clocked_in')
        messages.success(request, 'Successfully clocked in.')
    
    return redirect('clock_in_out_page')

@login_required
def clock_out(request):
    # Get the Employee instance for the logged-in user
    employee = get_object_or_404(Employee, user=request.user)

    # Find the employee's open attendance record (not clocked out)
    attendance = Attendance.objects.filter(employee=employee, clock_out_time__isnull=True).first()

    if not attendance:
        messages.warning(request, 'You have not clocked in yet.')
        return redirect('clock_in_out_page')

    # Clock out by setting the clock-out time and updating status
    with transaction.atomic():
        attendance.clock_out_time = timezone.now()
        attendance.status = 'clocked_out'
        attendance.save()
        messages.success(request, 'Successfully clocked out.')
    
    return redirect('clock_in_out_page')

@login_required
def start_break(request):
    # Get the Employee instance for the logged-in user
    employee = get_object_or_404(Employee, user=request.user)
    
    # Find the employee's open attendance record (not clocked out and not on break)
    attendance = Attendance.objects.filter(
        employee=employee,
        clock_out_time__isnull=True,
        break_start_time__isnull=True
    ).first()

    if not attendance or attendance.is_on_break():
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

    # Find the employee's open attendance record (on break)
    attendance = Attendance.objects.filter(
        employee=employee,
        clock_out_time__isnull=True,
        break_end_time__isnull=True
    ).first()

    if not attendance or not attendance.is_on_break():
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

    return render(request, 'attendance/dashboard.html', {
        'attendance_records': attendance_records,
        'current_status': current_status
    })

@login_required
def clock_in_out_page(request):
    # Get the Employee instance for the logged-in user
    employee = get_object_or_404(Employee, user=request.user)

    # If it's a POST request, process the form submission (clock in/out/start/end break)
    if request.method == 'POST':
        with transaction.atomic():
            # Clock in action
            if 'clock_in' in request.POST:
                if not Attendance.objects.filter(employee=employee, clock_out_time__isnull=True).exists():
                    Attendance.objects.create(employee=employee, clock_in_time=timezone.now(), status='clocked_in')
                    messages.success(request, 'Successfully clocked in.')
                else:
                    messages.warning(request, 'You are already clocked in.')

            # Clock out action
            elif 'clock_out' in request.POST:
                attendance = Attendance.objects.filter(employee=employee, clock_out_time__isnull=True).first()
                if attendance:
                    attendance.clock_out_time = timezone.now()
                    attendance.status = 'clocked_out'
                    attendance.save()
                    messages.success(request, 'Successfully clocked out.')
                else:
                    messages.warning(request, 'No active clock-in record found.')

            # Start break action
            elif 'start_break' in request.POST:
                attendance = Attendance.objects.filter(
                    employee=employee,
                    clock_out_time__isnull=True,
                    break_start_time__isnull=True
                ).first()
                if attendance and attendance.status == 'clocked_in':
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
                ).first()
                if attendance and attendance.status == 'on_break':
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
