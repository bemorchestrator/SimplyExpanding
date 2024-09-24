from django import forms
from .models import Employee

class EmployeeProfileForm(forms.ModelForm):
    class Meta:
        model = Employee
        # List of fields from Employee model to include in the form
        fields = [
            'username', 'first_name', 'middle_name', 'last_name', 'email', 
            'address', 'phone_number', 'city', 'country', 'profile_picture', 
            'per_day_rate', 'scheduled_start_time', 'lateness_rules'
        ]
        # Widgets for the fields, including customized classes for styling
        widgets = {
            'username': forms.TextInput(attrs={'class': 'input-class'}),
            'first_name': forms.TextInput(attrs={'class': 'input-class'}),
            'middle_name': forms.TextInput(attrs={'class': 'input-class'}),
            'last_name': forms.TextInput(attrs={'class': 'input-class'}),
            'email': forms.EmailInput(attrs={'class': 'input-class'}),
            'address': forms.TextInput(attrs={'class': 'input-class'}),
            'phone_number': forms.TextInput(attrs={'class': 'input-class'}),
            'city': forms.TextInput(attrs={'class': 'input-class'}),
            'country': forms.TextInput(attrs={'class': 'input-class'}),
            'profile_picture': forms.FileInput(attrs={'class': 'input-class'}),
            'per_day_rate': forms.NumberInput(attrs={'class': 'input-class', 'step': '0.01'}),
            'scheduled_start_time': forms.TimeInput(attrs={'class': 'input-class', 'type': 'time'}),
            'lateness_rules': forms.SelectMultiple(attrs={'class': 'input-class'}),
        }
