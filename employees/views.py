from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Employee
from .forms import EmployeeProfileForm
from attendance.models import Attendance
from datetime import timedelta, date
from django.db.models import Sum

@login_required
def employee_profile(request):
    # Retrieve the employee instance linked to the current user
    employee = get_object_or_404(Employee, user=request.user)

    # Fetch attendance records for the employee
    attendance_logs = Attendance.objects.filter(employee=employee).order_by('-clock_in_time')

    # Calculate attendance stats
    total_attendance = attendance_logs.count()
    late_days = attendance_logs.filter(lateness__gt=timedelta(seconds=0)).count()
    absent_days = attendance_logs.filter(status='absent').count()

    # Calculate the total income for the current month
    current_month = date.today().month
    current_year = date.today().year
    total_income_month = attendance_logs.filter(
        clock_in_time__year=current_year, clock_in_time__month=current_month
    ).aggregate(Sum('total_income'))['total_income__sum'] or 0  # Handle None case with 'or 0'

    # Pass the employee object and attendance data to the template
    context = {
        'employee': employee,
        'attendance_logs': attendance_logs,
        'total_attendance': total_attendance,
        'late_days': late_days,
        'absent_days': absent_days,
        'total_income_month': total_income_month,  # Pass total income to the template
    }
    return render(request, 'employees/profile.html', context)


@login_required
def profile_settings(request):
    # Retrieve the employee instance linked to the current user
    employee = get_object_or_404(Employee, user=request.user)

    if request.method == 'POST':
        # Populate the form with POST data and files (for profile picture)
        form = EmployeeProfileForm(request.POST, request.FILES, instance=employee)
        
        if form.is_valid():
            # Save the form and update employee details
            form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('profile_settings')  # Redirect to avoid resubmission issues
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        # For GET requests, prepopulate the form with the employee data
        form = EmployeeProfileForm(instance=employee)
    
    # Render the profile settings template
    return render(request, 'employees/profile_settings.html', {'form': form, 'employee': employee})
