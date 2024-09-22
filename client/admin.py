from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import ClientOnboarding

@admin.register(ClientOnboarding)
class ClientOnboardingAdmin(admin.ModelAdmin):
    list_display = (
        'business_name',
        'business_description',
        'website_url',
        'contact_person',
        'email',
        'phone_number',
        'business_goals',
        'cms_type',
        'start_date',
        'end_date'
    )
    search_fields = ('business_name', 'contact_person', 'email', 'website_url', 'cms_type')
    list_filter = ('start_date', 'end_date')
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'business_name', 
                'business_description', 
                'website_url', 
                'contact_person', 
                'email', 
                'phone_number',
            )
        }),
        ('Project Details', {
            'fields': (
                'business_goals',
                'target_keywords',
                'competitor_urls',
                'start_date',
                'end_date'
            )
        }),
        ('Login Credentials', {
            'fields': (
                'g4a_login', 
                'google_search_console_login', 
                'tag_manager_login', 
                'website_login', 
                'cms_type',
            )
        }),
    )
