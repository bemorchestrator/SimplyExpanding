from django import forms

from client.models import ClientOnboarding
from .models import AuditDashboard, UploadedFile


class UploadedFileForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ['category', 'action_choice']
        widgets = {
            'category': forms.Select(attrs={'class': 'category-dropdown form-control'}),
            'action_choice': forms.Select(attrs={'class': 'action-dropdown form-control'}),
            'customer_journey': forms.Select(attrs={'class': 'customer-journey-dropdown form-control'}),
            'serp_content_type': forms.Select(attrs={'class': 'serp-content-type-dropdown form-control'}),
        }

class FileUploadForm(forms.Form):
    file = forms.FileField(label='Select a file')


class SitemapForm(forms.Form):
    sitemap_urls = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Enter one or more sitemap URLs, each on a new line'}),
        label='Sitemap URLs',
        help_text='Enter one or more sitemap URLs, each on a new line.'
    )

class AuditDashboardForm(forms.ModelForm):
    overwrite_existing = forms.BooleanField(required=False)

    class Meta:
        model = AuditDashboard
        fields = ['name', 'description', 'client']
        widgets = {
            'client': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Select a client (optional)'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].queryset = ClientOnboarding.objects.all()  # Load all clients
        self.fields['client'].required = False  # Make the client optional
