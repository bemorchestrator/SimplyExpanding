# employees/admin.py

from django.contrib import admin
from .models import Employee

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        'username', 'first_name', 'last_name', 'email',
        'per_day_rate', 'scheduled_start_time', 'lateness_rules_display',
        'city', 'country'
    )
    search_fields = (
        'username', 'first_name', 'last_name', 'email',
        'user__username', 'user__first_name', 'user__last_name', 'user__email'
    )
    list_filter = ('city', 'country', 'scheduled_start_time', 'lateness_rules')
    fieldsets = (
        (None, {
            'fields': (
                'user', 'username', 'first_name', 'middle_name', 'last_name', 'email',
                'address', 'phone_number', 'city', 'country', 'profile_picture',
                'per_day_rate', 'scheduled_start_time', 'lateness_rules'
            ),
            'description': 'Manage employee details, contact information, and scheduling.'
        }),
    )
    readonly_fields = ('user',)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('username', 'user')
        return self.readonly_fields

    def lateness_rules_display(self, obj):
        return ", ".join([rule.name for rule in obj.lateness_rules.all()])
    lateness_rules_display.short_description = 'Lateness Rules'
