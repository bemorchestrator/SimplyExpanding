# attendance/admin.py

from django.contrib import admin
from django import forms
from .models import Attendance, LatenessRule, LatenessDeduction, GlobalSettings

# Custom form for Attendance model with enhanced help texts
class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = '__all__'
        help_texts = {
            'employee': 'Select the employee for this attendance record.',
            'clock_in_time': 'Date and time when the employee clocked in. Example: 2023-01-01 19:47:19',
            'clock_out_time': 'Date and time when the employee clocked out. Example: 2023-01-01 17:00:00',
            'break_start_time': 'Date and time when the employee started their break.',
            'break_end_time': 'Date and time when the employee ended their break.',
            'status': 'Current status of the employee: Clocked In, On Break, or Clocked Out.',
            'total_hours': 'Total hours worked, calculated automatically.',
            'lateness': 'Duration the employee was late, calculated based on scheduled start time.',
            'lateness_deduction': 'Total monetary deduction due to lateness, calculated based on lateness rules.',
        }

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    form = AttendanceForm
    list_display = ('employee', 'clock_in_time', 'clock_out_time', 'status', 'lateness_formatted', 'lateness_deduction_amount')
    search_fields = ('employee__username', 'employee__first_name', 'employee__last_name')
    list_filter = ('status', 'employee')
    readonly_fields = ('lateness', 'lateness_deduction', 'total_hours', 'lateness_formatted', 'lateness_deduction_amount')
    fieldsets = (
        (None, {
            'fields': ('employee', 'status'),
        }),
        ('Time Information', {
            'fields': ('clock_in_time', 'clock_out_time', 'break_start_time', 'break_end_time'),
            'description': 'Manage clock-in/out and break times.',
        }),
        ('Lateness and Deductions', {
            'fields': ('lateness', 'lateness_deduction', 'lateness_formatted', 'lateness_deduction_amount', 'total_hours'),
            'description': 'These fields are calculated automatically based on clock-in time and lateness rules.',
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('employee',)
        return self.readonly_fields

# Custom form for LatenessRule model with enhanced help texts
class LatenessRuleForm(forms.ModelForm):
    class Meta:
        model = LatenessRule
        fields = '__all__'
        help_texts = {
            'name': 'Name of the lateness rule set. Example: Standard Lateness Policy',
            'description': 'Detailed description of the lateness rule. Explain when and how deductions are applied.',
            'grace_period': 'Duration allowed before lateness deductions apply. Example: 0:05:00 for 5 minutes',
            'deductions': 'Select the deductions that apply for this rule based on lateness duration.',
        }

@admin.register(LatenessRule)
class LatenessRuleAdmin(admin.ModelAdmin):
    form = LatenessRuleForm
    list_display = ('name', 'grace_period', 'description')
    filter_horizontal = ('deductions',)
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'grace_period', 'deductions'),
            'description': 'Define lateness rules and associate deductions based on lateness duration.',
        }),
    )

# Custom form for LatenessDeduction model with enhanced help texts
class LatenessDeductionForm(forms.ModelForm):
    class Meta:
        model = LatenessDeduction
        fields = '__all__'
        help_texts = {
            'name': 'Name of the lateness deduction. Example: Minor Lateness Deduction',
            'description': 'Detailed description of the deduction. Explain how the deduction is calculated and applied.',
            'min_lateness': 'Minimum lateness duration to trigger this deduction. Example: 0:05:01 for 5 minutes and 1 second',
            'deduction_duration': 'Duration to deduct from income due to lateness. Example: 0:02:00 for 2 hours',
        }

@admin.register(LatenessDeduction)
class LatenessDeductionAdmin(admin.ModelAdmin):
    form = LatenessDeductionForm
    list_display = ('name', 'min_lateness', 'deduction_duration', 'description')
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'min_lateness', 'deduction_duration'),
            'description': 'Specify the minimum lateness duration and the deduction duration.',
        }),
    )

# Custom form for GlobalSettings model with enhanced help texts
class GlobalSettingsForm(forms.ModelForm):
    class Meta:
        model = GlobalSettings
        fields = '__all__'
        help_texts = {
            'scheduled_start_time': 'Global scheduled start time for all employees. Example: 19:30 (24-hour format)',
        }

@admin.register(GlobalSettings)
class GlobalSettingsAdmin(admin.ModelAdmin):
    form = GlobalSettingsForm
    list_display = ('scheduled_start_time',)
    fieldsets = (
        (None, {
            'fields': ('scheduled_start_time',),
            'description': 'Set the global scheduled start time for all employees. Employees can override this with their specific scheduled start time.',
        }),
    )

    def has_add_permission(self, request):
        # Allow only one GlobalSettings instance
        if GlobalSettings.objects.exists():
            return False
        return True
