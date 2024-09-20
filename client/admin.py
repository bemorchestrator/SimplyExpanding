# client/admin.py

from django.contrib import admin
from .models import Client

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone_number', 'seo_type', 'billing_cycle')
    search_fields = ('name', 'email', 'contact_info', 'phone_number')
    list_filter = ('seo_type', 'billing_cycle', 'contract_start_date', 'google_analytics_access', 'hreflang_implementation')
    filter_horizontal = ('assigned_employees',)
    ordering = ('name',)
    readonly_fields = ('contract_start_date',)  # Example: Make 'contract_start_date' readonly if desired

    fieldsets = (
        (None, {
            'fields': ('name', 'contact_info', 'email', 'phone_number', 'address')
        }),
        ('SEO Service Information', {
            'fields': (
                'seo_type', 'target_goals', 'primary_products_services', 'target_audience',
                'target_locations', 'top_competitors', 'target_keywords', 'competitor_urls'
            )
        }),
        ('Technical SEO Details', {
            'fields': (
                'google_analytics_access', 'google_analytics_login', 'google_search_console_details',
                'current_cms', 'google_my_business_url', 'service_area', 'business_hours',
                'customer_reviews'
            )
        }),
        ('International SEO', {
            'fields': (
                'hreflang_implementation', 'international_competitor_websites',
                'country_specific_urls', 'languages_supported', 'bulk_keywords'
            )
        }),
        ('Additional Information', {
            'fields': (
                'ga4_login_details', 'website_backend_login_details', 'billing_cycle',
                'contract_start_date', 'contract_duration', 'assigned_employees'
            )
        }),
    )
