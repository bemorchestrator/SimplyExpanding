from django.db import models

# Create your models here.
from django.db import models

class ClientOnboarding(models.Model):
    # Business Information
    business_name = models.CharField(max_length=255)
    business_description = models.TextField(null=True, blank=True)  # New field for business description
    website_url = models.URLField(max_length=200)
    contact_person = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    phone_number = models.CharField(max_length=15)

    
    # SEO Information
    business_goals = models.TextField(null=True, blank=True)
    target_keywords = models.TextField(null=True, blank=True)  # Can be stored as comma-separated values
    competitor_urls = models.TextField(null=True, blank=True)  # Can be stored as comma-separated values

    # Login Details
    g4a_login = models.CharField(max_length=255, null=True, blank=True)
    google_search_console_login = models.CharField(max_length=255, null=True, blank=True)
    tag_manager_login = models.CharField(max_length=255, null=True, blank=True)
    website_login = models.CharField(max_length=255, null=True, blank=True)

    # CMS Information
    cms_type = models.CharField(max_length=255, null=True, blank=True)  # E.g., WordPress, Shopify, etc.

    # Project Dates
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.business_name
    

    
