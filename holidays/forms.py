# holidays/forms.py

from django import forms
from .models import Holiday

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

    class Meta:
        model = Holiday
        fields = ['name', 'holiday_type', 'is_recurring', 'date', 'description']
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
            'holiday_type': 'Type of the holiday. "Non-Working" are paid even if not clocked in. "Special Non-Working" require clock-in for pay.',
            'is_recurring': 'Indicates if the holiday recurs annually.',
            'date': 'Date of the holiday.',
            'description': 'Optional description of the holiday.',
        }

    def clean(self):
        cleaned_data = super().clean()
        is_recurring = cleaned_data.get('is_recurring')
        date = cleaned_data.get('date')

        # Validation logic: Date required if not recurring
        if not is_recurring and not date:
            self.add_error('date', 'Date is required for non-recurring holidays.')
        if is_recurring and date:
            self.add_error('date', 'Date should not be set for recurring holidays.')
        
        return cleaned_data
