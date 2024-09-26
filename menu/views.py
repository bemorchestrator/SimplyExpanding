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
            # Only display menu items if the user is in the allowed group or if no restrictions
            if item.visibility.exists():  # If visibility is set
                if item.visibility.filter(id__in=request.user.groups.values_list('id', flat=True)).exists():
                    filtered_items.append(item)
            else:  # If no visibility is set, show to everyone
                filtered_items.append(item)

        # Add the menu with filtered items
        if filtered_items:
            menu.items = filtered_items
            filtered_menus.append(menu)

    return {'menus': filtered_menus}

# View for Admin users
@user_passes_test(lambda u: is_in_group(u, 'Admin'))
def admin_dashboard(request):
    # Logic for admin dashboard
    return render(request, 'admin_dashboard.html')

# View for Accountant users
@user_passes_test(lambda u: is_in_group(u, 'Accountant'))
def financial_reports(request):
    # Logic for financial reports
    return render(request, 'financial_reports.html')

# View for Employee users
@user_passes_test(lambda u: is_in_group(u, 'Employee'))
def employee_tasks(request):
    # Logic for employee tasks
    return render(request, 'employee_tasks.html')
