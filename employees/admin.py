# employees/admin.py

from django.contrib import admin
from .models import Employee

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    # Fields to display in the admin list view
    list_display = (
        'username', 'first_name', 'last_name', 'email',
        'per_day_rate', 'scheduled_start_time', 'lateness_rules_display',
        'city', 'country', 'is_2fa_enabled'
    )
    
    # Fields to enable searching in the admin list view
    search_fields = (
        'username', 'first_name', 'last_name', 'email',
        'user__username', 'user__first_name', 'user__last_name', 'user__email'
    )
    
    # Filters to enable filtering in the admin list view
    list_filter = ('city', 'country', 'scheduled_start_time', 'lateness_rules')
    
    # Organizing fields into sections in the admin detail view
    fieldsets = (
        (None, {
            'fields': (
                'user', 'username', 'first_name', 'middle_name', 'last_name', 'email',
                'address', 'phone_number', 'city', 'country', 'profile_picture',
                'per_day_rate', 'scheduled_start_time', 'lateness_rules',
            ),
            'description': 'Manage employee details, contact information, and scheduling.'
        }),
        ('Two-Factor Authentication', {
            'fields': ('is_2fa_enabled',),
            'description': 'Manage Two-Factor Authentication settings.'
        }),
    )
    
    # Fields that are read-only in the admin detail view
    readonly_fields = ('user', 'is_2fa_enabled',)
    
    # Additional read-only fields based on object existence
    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('username', 'user')
        return self.readonly_fields
    
    # Custom method to display lateness rules
    def lateness_rules_display(self, obj):
        return ", ".join([rule.name for rule in obj.lateness_rules.all()])
    lateness_rules_display.short_description = 'Lateness Rules'

    # Method to determine if 2FA is enabled
    def is_2fa_enabled(self, obj):
        return bool(obj.totp_secret)
    is_2fa_enabled.boolean = True  # Displays as a boolean icon (checkmark or cross)
    is_2fa_enabled.short_description = '2FA Enabled'

    # Define custom admin actions
    actions = ['disable_two_factor_authentication']

    # Custom admin action to disable 2FA for selected employees
    def disable_two_factor_authentication(self, request, queryset):
        """
        Admin action to disable 2FA for selected employees by clearing their totp_secret.
        """
        updated = queryset.update(totp_secret='')
        self.message_user(request, f"Successfully disabled Two-Factor Authentication for {updated} employee(s).")
    disable_two_factor_authentication.short_description = "Disable Two-Factor Authentication for selected employees"
