# employees/views.py

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Employee
from attendance.models import Attendance
from datetime import date
from django.db.models import Sum
from .forms import EmployeeProfileForm
from datetime import timedelta
from django.conf import settings

@login_required
def employee_profile(request):
    """
    Displays the employee's profile, including attendance statistics and 2FA status.
    """
    user = request.user
    employee = get_object_or_404(Employee, user=user)

    # Attendance calculations
    total_attendance = Attendance.objects.filter(employee=employee).count()
    total_income_month = Attendance.objects.filter(
        employee=employee,
        clock_in_time__month=date.today().month
    ).aggregate(Sum('total_income'))['total_income__sum'] or 0
    absent_days = Attendance.objects.filter(employee=employee, status='absent').count()

    # Fetch attendance logs
    attendance_logs = Attendance.objects.filter(employee=employee).order_by('-clock_in_time')[:10]

    # Note: lateness calculation is already handled by the Attendance model,
    # so you just need to pass the logs with lateness already computed.
    
    context = {
        'user': user,
        'employee': employee,
        'total_attendance': total_attendance,
        'total_income_month': total_income_month,
        'absent_days': absent_days,
        'attendance_logs': attendance_logs,
    }

    return render(request, 'employees/profile.html', context)


@login_required
def profile_settings(request):
    """
    Handles profile settings for the employee.
    Allows the employee to update their profile information.
    """
    employee = get_object_or_404(Employee, user=request.user)

    if request.method == 'POST':
        form = EmployeeProfileForm(request.POST, request.FILES, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('employees:employee_profile')  # Redirect to profile after saving
        else:
            messages.error(request, 'There was an error updating your profile. Please correct the errors below.')
    else:
        form = EmployeeProfileForm(instance=employee)

    return render(request, 'employees/profile_settings.html', {'form': form, 'employee': employee})


@login_required
def disable_2fa(request):
    """
    Disables Two-Factor Authentication for the authenticated user.
    """
    employee = get_object_or_404(Employee, user=request.user)

    if not employee.totp_secret:
        messages.info(request, 'Two-Factor Authentication is not enabled.')
        return redirect('employees:employee_profile')

    if request.method == 'POST':
        employee.totp_secret = ''
        employee.save()
        messages.success(request, 'Two-Factor Authentication has been disabled successfully.')
        return redirect('employees:employee_profile')

    return render(request, 'employees/disable_2fa.html')
