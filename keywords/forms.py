from django import forms
from .models import KeywordResearchDashboard

class KeywordDashboardForm(forms.ModelForm):
    class Meta:
        model = KeywordResearchDashboard
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter dashboard name',
                'style': 'width: 300px;'
            })
        }
        labels = {
            'name': 'Dashboard Name',
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if KeywordResearchDashboard.objects.filter(name=name).exists():
            raise forms.ValidationError(f"A dashboard with the name '{name}' already exists.")
        return name
