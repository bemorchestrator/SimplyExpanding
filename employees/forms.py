# employees/forms.py

from django import forms
from .models import Employee

class EmployeeProfileForm(forms.ModelForm):
    # Explicitly include User fields
    username = forms.CharField(max_length=100, required=True)
    first_name = forms.CharField(max_length=100, required=True)
    middle_name = forms.CharField(max_length=100, required=False)
    last_name = forms.CharField(max_length=100, required=True)
    email = forms.EmailField(required=True)
    address = forms.CharField(max_length=255, required=True)
    phone_number = forms.CharField(max_length=20, required=True)
    city = forms.CharField(max_length=100, required=True)
    country = forms.CharField(max_length=100, required=True)
    profile_picture = forms.ImageField(required=False)
    scheduled_start_time = forms.TimeField(required=False)
    # Removed per_day_rate and lateness_rules
    
    class Meta:
        model = Employee
        fields = [
            'username', 'first_name', 'middle_name', 'last_name', 'email', 
            'address', 'phone_number', 'city', 'country', 'profile_picture', 
            'scheduled_start_time'
        ]
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
            'scheduled_start_time': forms.TimeInput(attrs={'class': 'input-class', 'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        # Expecting 'employee' instance
        super(EmployeeProfileForm, self).__init__(*args, **kwargs)
        if self.instance:
            # Populate User fields from the Employee's User
            self.fields['username'].initial = self.instance.username
            self.fields['first_name'].initial = self.instance.first_name
            self.fields['last_name'].initial = self.instance.last_name
            self.fields['email'].initial = self.instance.email

    def save(self, commit=True):
        # Save Employee fields
        employee = super(EmployeeProfileForm, self).save(commit=False)
        
        # Update User fields via Employee's attributes
        employee.username = self.cleaned_data['username']
        employee.first_name = self.cleaned_data['first_name']
        employee.last_name = self.cleaned_data['last_name']
        employee.email = self.cleaned_data['email']
        employee.middle_name = self.cleaned_data.get('middle_name', '')
        employee.address = self.cleaned_data['address']
        employee.phone_number = self.cleaned_data['phone_number']
        employee.city = self.cleaned_data['city']
        employee.country = self.cleaned_data['country']
        employee.scheduled_start_time = self.cleaned_data.get('scheduled_start_time', None)
        
        if commit:
            employee.save()
            # If you had any ManyToMany fields previously, handle them here
            self.save_m2m()
        
        return employee
