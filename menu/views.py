from django.shortcuts import render
from .models import Menu
from django.contrib.auth.decorators import user_passes_test

# Function to check if the user belongs to a specific group
def is_in_group(user, group_name):
    return user.groups.filter(name=group_name).exists()

# Menu loading with role-based filtering
def load_menu(request):
    # Get all menus and their items
    menus = Menu.objects.prefetch_related('items').all()

    # Filter the menu items based on the user's role
    filtered_menus = []
    for menu in menus:
        filtered_items = []
        for item in menu.items.all():
            # Only display menu items if the user is in the allowed group
            if (is_in_group(request.user, 'Admin') or 
                is_in_group(request.user, 'Accountant') or 
                is_in_group(request.user, 'Employee')):
                filtered_items.append(item)
        
        # Add the menu with filtered items
        if filtered_items:
            menu.items = filtered_items
            filtered_menus.append(menu)

    return {'menus': filtered_menus}

# Function to check if the user is an Admin
def is_admin(user):
    return is_in_group(user, 'Admin')

# Function to check if the user is an Accountant
def is_accountant(user):
    return is_in_group(user, 'Accountant')

# Function to check if the user is an Employee
def is_employee(user):
    return is_in_group(user, 'Employee')

# View for Admin users
@user_passes_test(is_admin)
def admin_dashboard(request):
    # Logic for admin dashboard
    return render(request, 'admin_dashboard.html')

# View for Accountant users
@user_passes_test(is_accountant)
def financial_reports(request):
    # Logic for financial reports
    return render(request, 'financial_reports.html')

# View for Employee users
@user_passes_test(is_employee)
def employee_tasks(request):
    # Logic for employee tasks
    return render(request, 'employee_tasks.html')
