from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Employee
from .forms import EmployeeProfileForm

@login_required
def employee_profile(request):
    # Retrieve the employee instance linked to the current user
    employee = get_object_or_404(Employee, user=request.user)
    
    # Pass the employee object to the template
    return render(request, 'employees/profile.html', {'employee': employee})

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
