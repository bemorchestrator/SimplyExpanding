# client/forms.py

from django import forms
from .models import Client

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            'name',
            'contact_info',
            'email',
            'phone_number',
            'address',
            'seo_type',
            'target_goals',
            'primary_products_services',
            'target_audience',
            'target_locations',
            'target_keywords',
            'competitor_urls',
            'google_analytics_access',
            'google_analytics_login',
            'google_search_console_details',
            'current_cms',
            'other_cms',
            'google_my_business_url',
            'service_area',
            'business_hours',
            'customer_reviews',
            'hreflang_implementation',
            'international_competitor_websites',
            'country_specific_urls',
            'languages_supported',
            'bulk_keywords',
            'ga4_login_details',
            'website_backend_login_details',
            'billing_cycle',
            'contract_start_date',
            'contract_duration',
            'assigned_employees'
        ]
        widgets = {
            'contract_start_date': forms.DateInput(attrs={'type': 'date'}),
            'contract_duration': forms.NumberInput(attrs={'min': 1}),
            'billing_cycle': forms.Select(choices=Client.BILLING_CYCLE_CHOICES),
            'seo_type': forms.Select(choices=Client.SEO_TYPE_CHOICES),
            'current_cms': forms.Select(choices=Client.CMS_CHOICES),
            'assigned_employees': forms.CheckboxSelectMultiple(),
            'google_analytics_access': forms.CheckboxInput(),
            'hreflang_implementation': forms.CheckboxInput(),
        }
        labels = {
            'name': 'Business Name',
            'contact_info': 'Primary Contact Name',
            'seo_type': 'SEO Type',
            'ga4_login_details': 'GA4 Login Details',
            'google_search_console_details': 'Google Search Console Details',
            'website_backend_login_details': 'Website Backend Login Details',
            'billing_cycle': 'Billing Cycle',
            'contract_start_date': 'Contract Start Date',
            'contract_duration': 'Contract Duration (months)',
            'assigned_employees': 'Assigned Employees',
            'current_cms': 'Current CMS',
            'other_cms': 'Other CMS',
            'google_my_business_url': 'Google My Business URL',
            'google_analytics_access': 'Google Analytics Access',
            'hreflang_implementation': 'Hreflang Implementation',
        }
        help_texts = {
            'contract_start_date': 'Select the start date of the contract.',
            'contract_duration': 'Enter the duration of the contract in months.',
            'billing_cycle': 'Select the billing cycle.',
            'seo_type': 'Choose the type of SEO service.',
            'current_cms': 'Select the current CMS. Choose "Other" if not listed.',
            # Add other help texts as needed
        }

    def clean_contract_duration(self):
        duration = self.cleaned_data.get('contract_duration')
        if duration is not None and duration <= 0:
            raise forms.ValidationError("Contract duration must be a positive number.")
        return duration
