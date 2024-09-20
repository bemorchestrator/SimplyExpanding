# client/models.py

from django.db import models
from employees.models import Employee  # Ensure this import is correct and the Employee model exists

class Client(models.Model):
    # Basic Client Information
    name = models.CharField(
        max_length=255,
        help_text="Client's business name",
        blank=True,
        null=True,
        default=''
    )
    contact_info = models.CharField(
        max_length=255,
        help_text="Client's contact information",
        blank=True,
        null=True,
        default=''
    )
    email = models.EmailField(
        unique=True,
        help_text="Client's contact email",
        blank=True,
        null=True,
        default=''
    )
    phone_number = models.CharField(
        max_length=20,
        help_text="Client's contact phone number",
        blank=True,
        null=True,
        default=''
    )
    address = models.TextField(
        help_text="Client's business address",
        blank=True,
        null=True,
        default=''
    )

    # SEO Service Information
    SEO_TYPE_CHOICES = [
        ('Local', 'Local'),
        ('International', 'International'),
        # Add other SEO types as needed
    ]
    seo_type = models.CharField(
        max_length=20,
        choices=SEO_TYPE_CHOICES,
        help_text="Type of SEO service",
        blank=True,
        null=True,
        default='Local'
    )
    target_goals = models.TextField(
        help_text="Primary SEO goals",
        blank=True,
        null=True,
        default=''
    )
    primary_products_services = models.TextField(
        help_text="Main products or services",
        blank=True,
        null=True,
        default=''
    )
    target_audience = models.TextField(
        help_text="Description of the target audience",
        blank=True,
        null=True,
        default=''
    )
    target_locations = models.TextField(
        help_text="Target locations or regions",
        blank=True,
        null=True,
        default=''
    )
    top_competitors = models.TextField(
        help_text="Top competitors",
        blank=True,
        null=True,
        default=''
    )
    target_keywords = models.TextField(
        help_text="Target keywords for SEO",
        blank=True,
        null=True,
        default=''
    )

    # Competitor Analysis
    competitor_urls = models.TextField(
        help_text="List of competitor URLs",
        blank=True,
        null=True,
        default=''
    )

    # Technical SEO Details
    google_analytics_access = models.BooleanField(
        help_text="Google Analytics access",
        default=False
    )
    google_analytics_login = models.TextField(
        help_text="Google Analytics login details",
        blank=True,
        null=True,
        default=''
    )
    google_search_console_details = models.TextField(
        help_text="Google Search Console login details",
        blank=True,
        null=True,
        default=''
    )
    
    CMS_CHOICES = [
        ('WordPress', 'WordPress'),
        ('Joomla', 'Joomla'),
        ('Drupal', 'Drupal'),
        ('Other', 'Other'),
    ]
    current_cms = models.CharField(
        max_length=255,
        choices=CMS_CHOICES,
        help_text="Current CMS",
        blank=True,
        null=True,
        default=''
    )
    other_cms = models.CharField(
        max_length=255,
        help_text="Other CMS if selected",
        blank=True,
        null=True,
        default=''
    )
    google_my_business_url = models.URLField(
        help_text="Google My Business URL",
        blank=True,
        null=True,
        default=''
    )
    service_area = models.TextField(
        help_text="Service area",
        blank=True,
        null=True,
        default=''
    )
    business_hours = models.TextField(
        help_text="Business hours",
        blank=True,
        null=True,
        default=''
    )
    customer_reviews = models.TextField(
        help_text="Customer reviews",
        blank=True,
        null=True,
        default=''
    )

    # International SEO
    hreflang_implementation = models.BooleanField(
        help_text="Hreflang implemented for language targeting",
        default=False
    )
    international_competitor_websites = models.TextField(
        help_text="International competitor websites",
        blank=True,
        null=True,
        default=''
    )
    country_specific_urls = models.TextField(
        help_text="Country-specific URLs",
        blank=True,
        null=True,
        default=''
    )
    languages_supported = models.TextField(
        help_text="Languages supported on the website",
        blank=True,
        null=True,
        default=''
    )
    bulk_keywords = models.TextField(
        help_text="Bulk keywords",
        blank=True,
        null=True,
        default=''
    )

    # Additional Fields to Match the Form
    ga4_login_details = models.TextField(
        help_text="GA4 login details",
        blank=True,
        null=True,
        default=''
    )
    website_backend_login_details = models.TextField(
        help_text="Website backend login details",
        blank=True,
        null=True,
        default=''
    )
    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        # Add other billing cycles as needed
    ]
    billing_cycle = models.CharField(
        max_length=50,
        choices=BILLING_CYCLE_CHOICES,
        help_text="Billing cycle (e.g., monthly, yearly)",
        blank=True,
        null=True,
        default='monthly'
    )
    contract_start_date = models.DateField(
        help_text="Contract start date",
        blank=True,
        null=True
    )
    contract_duration = models.PositiveIntegerField(
        help_text="Contract duration in months",
        blank=True,
        null=True,
        default=0
    )

    # Team Assignment
    assigned_employees = models.ManyToManyField(
        Employee,
        related_name='clients',
        blank=True,
        help_text="Employees assigned to this client"
    )

    def __str__(self):
        return self.name if self.name else "Unnamed Client"
