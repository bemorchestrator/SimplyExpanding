from django.db import models
from django.contrib.auth.models import User  # If you want to track which user created the dashboard

class AuditDashboard(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Optional, to track who created the dashboard
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)  # Optional description of the dashboard
    created_at = models.DateTimeField(auto_now_add=True)
    share_token = models.CharField(max_length=64, unique=True, null=True, blank=True)

    def __str__(self):
        return self.name


class UploadedFile(models.Model):
    ACTION_CHOICES = [
        ('leave', 'Leave As Is'),
        ('update_on_page', 'Update On Page'),
        ('target_with_links', 'Target w/ Links'),
        ('301', '301'),
        ('canonicalize', 'Canonicalize'),
        ('block_crawl', 'Block Crawl'),
        ('no_index', 'No Index'),
        ('content_audit', 'Content Audit'),
        ('merge', 'Merge'),
    ]

    CATEGORY_CHOICES = [
        ('Product Page', 'Product Page'),
        ('Product Category', 'Product Category'),
        ('Local Lander', 'Local Lander'),
        ('Lead Generation', 'Lead Generation'),
        ('Blog Post', 'Blog Post'),
        ('Resource / Guide', 'Resource / Guide'),
        ('Blog Category', 'Blog Category'),
        ('Site Info', 'Site Info'),
        ('Images', 'Images'),
        ('Assets', 'Assets'),
    ]
    
    category = models.CharField(max_length=255, choices=CATEGORY_CHOICES, blank=True, null=True)
    file_name = models.CharField(max_length=2000, default='unknown_file')
    drive_file_id = models.CharField(max_length=2000, default='unknown_id')
    drive_file_link = models.URLField(max_length=2000, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    url = models.URLField(default='http://example.com', max_length=2000, unique=False)
    type = models.CharField(max_length=2000, default='text/html; charset=UTF-8')
    current_title = models.CharField(max_length=2000, null=True, blank=True)
    meta = models.CharField(max_length=2000, null=True, blank=True)
    h1 = models.CharField(max_length=2000, null=True, blank=True)
    word_count = models.IntegerField(null=True, blank=True)
    canonical_link = models.URLField(null=True, blank=True, max_length=2000)
    status_code = models.CharField(max_length=2000, null=True, blank=True)
    index_status = models.CharField(max_length=2000, null=True, blank=True)
    last_modified = models.CharField(max_length=2000, null=True, blank=True)
    inlinks = models.IntegerField(null=True, blank=True)
    outlinks = models.IntegerField(null=True, blank=True)
    page_path = models.CharField(max_length=2000, null=True, blank=True)
    crawl_depth = models.IntegerField(null=True, blank=True)
    action_choice = models.CharField(max_length=2000, choices=ACTION_CHOICES, default='leave')

    # New fields based on your tables.py
    main_kw = models.CharField(max_length=2000, null=True, blank=True)
    kw_volume = models.IntegerField(null=True, blank=True)
    kw_ranking = models.IntegerField(null=True, blank=True)
    best_kw = models.CharField(max_length=2000, null=True, blank=True)
    best_kw_volume = models.IntegerField(null=True, blank=True)
    best_kw_ranking = models.IntegerField(null=True, blank=True)
    impressions = models.IntegerField(null=True, blank=True)
    sessions = models.IntegerField(null=True, blank=True)
    percent_change_sessions = models.FloatField(null=True, blank=True)
    bounce_rate = models.FloatField(null=True, blank=True)
    avg_time_on_page = models.CharField(max_length=20, null=True, blank=True)
    losing_traffic = models.CharField(
        max_length=10, 
        choices=[('up', 'Up'), ('down', 'Down'), ('none', 'None')], 
        default='none'
    )
    links = models.IntegerField(null=True, blank=True)
    serp_ctr = models.FloatField(null=True, blank=True)
    in_sitemap = models.BooleanField(default=False)

    # New ForeignKey linking this file to an AuditDashboard instance
    dashboard = models.ForeignKey(AuditDashboard, on_delete=models.CASCADE, related_name="audit_data", null=True, blank=True)
    primary_keyword = models.CharField(max_length=255, null=True, blank=True)
    pk_volume = models.IntegerField(null=True, blank=True)
    pk_ranking = models.IntegerField(null=True, blank=True)
    secondary_keywords = models.TextField(null=True, blank=True)
    customer_journey = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.file_name


class Sitemap(models.Model):
    url = models.URLField(default='http://example.com/sitemap.xml', max_length=2000)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.url


class SitemapURL(models.Model):
    sitemap = models.ForeignKey(Sitemap, on_delete=models.CASCADE, related_name='urls')
    url = models.URLField(max_length=2000, default='http://example.com/page')
    status = models.CharField(max_length=2000, null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.url
