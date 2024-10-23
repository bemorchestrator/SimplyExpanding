import uuid
from django.db import models
from client.models import ClientOnboarding  # Assuming ClientOnboarding is the model for your clients

# Define the available report types
REPORT_TYPES = [
    ('google_analytics', 'Google Analytics'),
    ('keyword_research', 'Keyword Research'),
    ('website_audit', 'Website Audit'),
    ('google_search_console', 'Google Search Console'),  # Add this report type
]

class Report(models.Model):
    client = models.ForeignKey(ClientOnboarding, on_delete=models.CASCADE, related_name='reports')
    title = models.CharField(max_length=200)
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES, null=True, blank=True)  # Make nullable
    created_at = models.DateTimeField(auto_now_add=True)
    access_key = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)

    def __str__(self):
        return self.title


def generate_access_key():
    return str(uuid.uuid4())