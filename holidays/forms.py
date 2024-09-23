from django import forms
from .models import Holiday
import calendar
from datetime import date

class HolidayForm(forms.ModelForm):
    RECURRENCE_CHOICES = (
        (True, 'Yes'),
        (False, 'No'),
    )

    is_recurring = forms.TypedChoiceField(
        choices=RECURRENCE_CHOICES,
        coerce=lambda x: x == 'True',
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_is_recurring'}),
        help_text='Indicates if the holiday recurs annually.'
    )

    recurring_month = forms.ChoiceField(
        choices=[(str(i), calendar.month_name[i]) for i in range(1, 13)],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'recurring_month'}),
        help_text='Month when the holiday recurs.',
    )

    recurring_day = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'id': 'recurring_day',
            'min': 1,
            'max': 31,
        }),
        help_text='Day of the month when the holiday recurs.',
    )

    class Meta:
        model = Holiday
        fields = ['name', 'holiday_type', 'is_recurring', 'date', 'recurring_month', 'recurring_day', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter holiday name'
            }),
            'holiday_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'id': 'fixed_date'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter description (optional)',
                'rows': 3
            }),
        }
        help_texts = {
            'name': 'Name of the holiday, e.g., New Year, Christmas.',
            'holiday_type': 'Type of the holiday.',
            'is_recurring': 'Indicates if the holiday recurs annually.',
            'date': 'Date of the holiday.',
            'description': 'Optional description of the holiday.',
        }

    def clean(self):
        cleaned_data = super().clean()
        is_recurring = cleaned_data.get('is_recurring')
        date = cleaned_data.get('date')
        recurring_month = cleaned_data.get('recurring_month')
        recurring_day = cleaned_data.get('recurring_day')

        # Non-recurring holiday must have a date
        if not is_recurring and not date:
            self.add_error('date', 'Date is required for non-recurring holidays.')

        # Recurring holiday must not have a date
        if is_recurring and date:
            self.add_error('date', 'Date should not be set for recurring holidays.')

        # Recurring holidays must have a month and a day
        if is_recurring and (not recurring_month or not recurring_day):
            self.add_error('recurring_month', 'Month is required for recurring holidays.')
            self.add_error('recurring_day', 'Day is required for recurring holidays.')

        # Special handling for leap day (February 29)
        if is_recurring and recurring_month == '2' and recurring_day == 29:
            current_year = date.today().year
            if not calendar.isleap(current_year):
                self.add_error('recurring_day', 'February 29 is only valid in leap years.')

        return cleaned_data
