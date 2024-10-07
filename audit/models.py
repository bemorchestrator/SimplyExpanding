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

    file_name = models.CharField(max_length=255, default='unknown_file')
    drive_file_id = models.CharField(max_length=255, default='unknown_id')
    drive_file_link = models.URLField(max_length=500, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    url = models.URLField(default='http://example.com')
    type = models.CharField(max_length=100, default='text/html; charset=UTF-8')
    current_title = models.CharField(max_length=255, null=True, blank=True)
    meta = models.CharField(max_length=255, null=True, blank=True)
    h1 = models.CharField(max_length=255, null=True, blank=True)
    word_count = models.IntegerField(null=True, blank=True)
    canonical_link = models.URLField(null=True, blank=True)
    status_code = models.CharField(max_length=10, null=True, blank=True)
    index_status = models.CharField(max_length=50, null=True, blank=True)
    last_modified = models.CharField(max_length=100, null=True, blank=True)
    inlinks = models.IntegerField(null=True, blank=True)
    outlinks = models.IntegerField(null=True, blank=True)
    page_path = models.CharField(max_length=255, null=True, blank=True)  
    crawl_depth = models.IntegerField(null=True, blank=True)
    action_choice = models.CharField(max_length=50, choices=ACTION_CHOICES, default='leave')

    def __str__(self):
        return self.file_name

class Sitemap(models.Model):
    url = models.URLField(default='http://example.com/sitemap.xml')
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.url

class SitemapURL(models.Model):
    sitemap = models.ForeignKey(Sitemap, on_delete=models.CASCADE, related_name='urls')
    url = models.URLField(default='http://example.com/page')
    status = models.CharField(max_length=50, null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.url
