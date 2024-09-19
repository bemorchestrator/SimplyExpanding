# holidays/admin.py

from django.contrib import admin
from django import forms
from .models import Holiday

# Custom form for Holiday model with enhanced help texts
class HolidayFormAdmin(forms.ModelForm):
    class Meta:
        model = Holiday
        fields = '__all__'
        help_texts = {
            'name': 'Name of the holiday, e.g., New Year, Christmas.',
            'date': 'Date of the holiday. Required if the holiday is not recurring.',
            'is_recurring': 'Indicates if the holiday recurs annually.',
            'holiday_type': 'Type of the holiday. "Non-Working" are paid even if not clocked in. "Special Non-Working" require clock-in for pay.',
            'description': 'Optional description of the holiday.',
        }

@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    form = HolidayFormAdmin
    list_display = ('name', 'holiday_type', 'date', 'is_recurring', 'description')
    list_filter = ('is_recurring', 'holiday_type')
    search_fields = ('name',)
    ordering = ('date',)
    fieldsets = (
        (None, {
            'fields': ('name', 'holiday_type', 'is_recurring', 'date'),
            'description': 'Define the holiday details. Specify if it is recurring and its type.'
        }),
        ('Additional Information', {
            'fields': ('description',),
            'description': 'Provide an optional description for the holiday.',
        }),
    )
    actions = ['make_recurring', 'make_non_recurring', 'set_non_working', 'set_special_non_working']

    def make_recurring(self, request, queryset):
        """Mark selected holidays as recurring."""
        updated = queryset.update(is_recurring=True)
        self.message_user(request, f"{updated} holiday(s) marked as recurring.")
    make_recurring.short_description = "Mark selected holidays as recurring"

    def make_non_recurring(self, request, queryset):
        """Mark selected holidays as non-recurring."""
        updated = queryset.update(is_recurring=False)
        self.message_user(request, f"{updated} holiday(s) marked as non-recurring.")
    make_non_recurring.short_description = "Mark selected holidays as non-recurring"

    def set_non_working(self, request, queryset):
        """Set selected holidays as Non-Working Holidays."""
        updated = queryset.update(holiday_type='non_working')
        self.message_user(request, f"{updated} holiday(s) set as Non-Working Holidays.")
    set_non_working.short_description = "Set selected holidays as Non-Working Holidays"

    def set_special_non_working(self, request, queryset):
        """Set selected holidays as Special Non-Working Holidays."""
        updated = queryset.update(holiday_type='special_non_working')
        self.message_user(request, f"{updated} holiday(s) set as Special Non-Working Holidays.")
    set_special_non_working.short_description = "Set selected holidays as Special Non-Working Holidays"

    def get_queryset(self, request):
        """Optimize queryset by selecting related fields."""
        qs = super().get_queryset(request)
        return qs.select_related()
