from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from .models import Employee

@login_required
def employee_profile(request):
    # Retrieve the employee instance linked to the current user
    employee = get_object_or_404(Employee, user=request.user)
    
    # Pass the employee object to the template
    return render(request, 'employees/profile.html', {'employee': employee})
