from django.contrib import admin
from .models import BillingRecord
from attendance.models import Attendance  # Import the related Attendance model
from .models import Invoice

@admin.register(BillingRecord)
class BillingRecordAdmin(admin.ModelAdmin):
    # Display relevant fields including hours worked and holiday
    list_display = ('employee', 'total_income', 'get_hours_worked', 'get_holiday', 'payment_type', 'date')

    # Allow searching by employee username and date
    search_fields = ['employee__user__username', 'employee__first_name', 'employee__last_name', 'date']
    
    # Add filters for date and payment type
    list_filter = ['date', 'payment_type']

    # Read-only fields for total_income to prevent accidental editing
    readonly_fields = ('total_income', 'date')

    # Custom method to pull hours worked from the related Attendance record
    def get_hours_worked(self, obj):
        # Assuming BillingRecord has a foreign key or relation to Attendance
        attendance_record = Attendance.objects.filter(employee=obj.employee, clock_out_time__date=obj.date).first()
        if attendance_record:
            total_seconds = (attendance_record.clock_out_time - attendance_record.clock_in_time).total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int(total_seconds % 60)
            return f'{hours:02d}:{minutes:02d}:{seconds:02d}'  # Return formatted in HH:MM:SS
        return 'N/A'
    
    # Change column name to "Hours Worked"
    get_hours_worked.short_description = 'Hours Worked'

    # Custom method to pull holiday from the related Attendance record
    def get_holiday(self, obj):
        attendance_record = Attendance.objects.filter(employee=obj.employee, clock_in_time__date=obj.date).first()
        if attendance_record and attendance_record.holiday:
            return attendance_record.holiday.name  # Return the holiday name
        return 'N/A'

    # Change column name to "Holiday"
    get_holiday.short_description = 'Holiday'



@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'client_name', 'total_amount', 'currency', 'status', 'invoice_date', 'due_date')
    search_fields = ('client_name', 'client__name')
    list_filter = ('status', 'currency', 'invoice_date', 'due_date')
    ordering = ('-invoice_date',)
    readonly_fields = ('total_amount', 'invoice_date')

    def client_name_display(self, obj):
        return obj.client_name
    client_name_display.short_description = 'Client Name'