from django.shortcuts import render
from .models import Menu
from django.contrib.auth.decorators import user_passes_test

# Function to check if the user belongs to a specific group
def is_in_group(user, group_name):
    return user.groups.filter(name=group_name).exists()

# Recursive function to filter menu items based on visibility
def filter_items(items, user_groups):
    filtered_items = []
    for item in items:
        if item.visibility.exists():
            if item.visibility.filter(id__in=user_groups).exists():
                # Filter children recursively
                item.filtered_children = filter_items(item.children.all(), user_groups)
                filtered_items.append(item)
        else:
            # No visibility restrictions, include item
            item.filtered_children = filter_items(item.children.all(), user_groups)
            filtered_items.append(item)
    return filtered_items

# Menu loading with role-based filtering
def load_menu(request):
    user_groups = request.user.groups.values_list('id', flat=True)
    menus = Menu.objects.prefetch_related('items__children').all()
    filtered_menus = []
    for menu in menus:
        filtered_items = filter_items(menu.items.all(), user_groups)
        if filtered_items:
            menu.filtered_items = filtered_items
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
