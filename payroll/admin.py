from django.contrib import admin
from .models import PayrollRecord
from django.utils.timezone import now

@admin.register(PayrollRecord)
class PayrollRecordAdmin(admin.ModelAdmin):
    list_display = ('employee', 'pay_period_start', 'pay_period_end', 'total_income', 'status', 'date_processed')
    list_filter = ('status', 'pay_period_start', 'pay_period_end')
    search_fields = ('employee__username', 'employee__first_name', 'employee__last_name')

    # Add the ability to bulk process payrolls via admin actions
    actions = ['mark_as_paid', 'mark_as_pending', 'mark_as_no_income']

    # Custom action to mark selected payroll records as 'paid'
    def mark_as_paid(self, request, queryset):
        updated = queryset.update(status='paid', date_processed=now())
        self.message_user(request, f'{updated} payroll records were successfully marked as paid.')

    mark_as_paid.short_description = 'Mark selected payrolls as Paid'

    # Custom action to mark selected payroll records as 'pending'
    def mark_as_pending(self, request, queryset):
        updated = queryset.update(status='pending', date_processed=None)
        self.message_user(request, f'{updated} payroll records were successfully marked as pending.')

    mark_as_pending.short_description = 'Mark selected payrolls as Pending'

    # Custom action to mark selected payroll records as 'no_income'
    def mark_as_no_income(self, request, queryset):
        updated = queryset.update(status='no_income', date_processed=None)
        self.message_user(request, f'{updated} payroll records were successfully marked as No Income.')

    mark_as_no_income.short_description = 'Mark selected payrolls as No Income'

    # Ensure that changes to total income are recalculated and saved properly
    def save_model(self, request, obj, form, change):
        if change:  # If updating an existing record
            if obj.status == 'pending' and obj.total_income > 0:
                obj.status = 'pending'
            elif obj.total_income == 0:
                obj.status = 'no_income'
            super().save_model(request, obj, form, change)
