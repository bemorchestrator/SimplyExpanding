# models.py

from django.db import models

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
    file_name = models.CharField(max_length=2000, default='unknown_file')  # Increased from 255
    drive_file_id = models.CharField(max_length=2000, default='unknown_id')  # Increased from 255
    drive_file_link = models.URLField(max_length=2000, null=True, blank=True)  # Increased from 500
    uploaded_at = models.DateTimeField(auto_now_add=True)
    url = models.URLField(default='http://example.com', max_length=2000, unique=False)  # Ensure enough space for long URLs and enforce uniqueness
    type = models.CharField(max_length=2000, default='text/html; charset=UTF-8')  # Increased from 100
    current_title = models.CharField(max_length=2000, null=True, blank=True)  # Increased from 255
    meta = models.CharField(max_length=2000, null=True, blank=True)  # Increased from 255
    h1 = models.CharField(max_length=2000, null=True, blank=True)  # Increased from 255
    word_count = models.IntegerField(null=True, blank=True)
    canonical_link = models.URLField(null=True, blank=True, max_length=2000)  # Increased from the default length
    status_code = models.CharField(max_length=2000, null=True, blank=True)  # Increased from 10
    index_status = models.CharField(max_length=2000, null=True, blank=True)  # Increased from 50
    last_modified = models.CharField(max_length=2000, null=True, blank=True)  # Increased from 100
    inlinks = models.IntegerField(null=True, blank=True)
    outlinks = models.IntegerField(null=True, blank=True)
    page_path = models.CharField(max_length=2000, null=True, blank=True)  # Increased from 255
    crawl_depth = models.IntegerField(null=True, blank=True)
    action_choice = models.CharField(max_length=2000, choices=ACTION_CHOICES, default='leave')  # Increased from 50

    # New fields based on your tables.py
    main_kw = models.CharField(max_length=2000, null=True, blank=True)  # Increased from 255
    kw_volume = models.IntegerField(null=True, blank=True)
    kw_ranking = models.IntegerField(null=True, blank=True)
    best_kw = models.CharField(max_length=2000, null=True, blank=True)  # Increased from 255
    best_kw_volume = models.IntegerField(null=True, blank=True)
    best_kw_ranking = models.IntegerField(null=True, blank=True)
    impressions = models.IntegerField(null=True, blank=True)
    sessions = models.IntegerField(null=True, blank=True)
    percent_change_sessions = models.FloatField(null=True, blank=True)
    bounce_rate = models.FloatField(null=True, blank=True)
    avg_time_on_page = models.FloatField(null=True, blank=True)
    losing_traffic = models.BooleanField(default=False)
    links = models.IntegerField(null=True, blank=True)
    serp_ctr = models.FloatField(null=True, blank=True)
    in_sitemap = models.BooleanField(default=False)

    def __str__(self):
        return self.file_name

class Sitemap(models.Model):
    url = models.URLField(default='http://example.com/sitemap.xml', max_length=2000)  # Increased from default length
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.url

class SitemapURL(models.Model):
    sitemap = models.ForeignKey(Sitemap, on_delete=models.CASCADE, related_name='urls')
    url = models.URLField(max_length=2000, default='http://example.com/page')  # Increased from 2000
    status = models.CharField(max_length=2000, null=True, blank=True)  # Increased from 50
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.url
