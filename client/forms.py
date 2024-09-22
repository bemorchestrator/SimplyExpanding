from django import forms
from .models import ClientOnboarding

class ClientOnboardingForm(forms.ModelForm):
    class Meta:
        model = ClientOnboarding
        fields = [
            'business_name',
            'business_description',
            'website_url',
            'contact_person',
            'email',
            'phone_number',
            'business_goals',
            'target_keywords',
            'competitor_urls',
            'g4a_login',
            'google_search_console_login',
            'tag_manager_login',
            'website_login',
            'cms_type',
            'start_date',
            'end_date'
        ]
        # Define placeholders for each field
        widgets = {
            'business_name': forms.TextInput(attrs={
                'placeholder': 'Enter your business name *'
            }),
            'business_description': forms.Textarea(attrs={
                'placeholder': 'Brief description of your business'
            }),
            'website_url': forms.URLInput(attrs={
                'placeholder': 'Enter your website URL *'
            }),
            'contact_person': forms.TextInput(attrs={
                'placeholder': 'Name of the main contact person *'
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'Enter a valid email address *'
            }),
            'phone_number': forms.TextInput(attrs={
                'placeholder': 'Enter phone number'
            }),
            'business_goals': forms.Textarea(attrs={
                'placeholder': 'State the business goals for SEO *'
            }),
            'target_keywords': forms.Textarea(attrs={
                'placeholder': 'List target keywords, separated by commas'
            }),
            'competitor_urls': forms.Textarea(attrs={
                'placeholder': 'List competitor URLs, separated by commas'
            }),
            'g4a_login': forms.TextInput(attrs={
                'placeholder': 'G4A login details (if applicable)'
            }),
            'google_search_console_login': forms.TextInput(attrs={
                'placeholder': 'Google Search Console login details (if applicable)'
            }),
            'tag_manager_login': forms.TextInput(attrs={
                'placeholder': 'Tag Manager login details (if applicable)'
            }),
            'website_login': forms.TextInput(attrs={
                'placeholder': 'Website login details (if applicable)'
            }),
            'cms_type': forms.TextInput(attrs={
                'placeholder': 'CMS type (WordPress, Shopify, etc.)'
            }),
            'start_date': forms.DateInput(attrs={
                'placeholder': 'Project start date *',
                'type': 'date'  # HTML5 date picker
            }),
            'end_date': forms.DateInput(attrs={
                'placeholder': 'Project end date *',
                'type': 'date'  # HTML5 date picker
            }),
        }

    # Add custom labels with asterisk for required fields
    def __init__(self, *args, **kwargs):
        super(ClientOnboardingForm, self).__init__(*args, **kwargs)
        self.fields['business_name'].label = 'Business Name *'
        self.fields['website_url'].label = 'Website URL *'
        self.fields['contact_person'].label = 'Contact Person *'
        self.fields['email'].label = 'Email *'
        self.fields['business_goals'].label = 'Business Goals *'
        self.fields['start_date'].label = 'Start Date *'
        self.fields['end_date'].label = 'End Date *'

        # Make required fields explicitly required in the form
        for field in self.fields:
            if self.fields[field].required:
                self.fields[field].widget.attrs['class'] = 'required-field'  # Add a class for required fields if needed
