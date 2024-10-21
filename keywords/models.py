from django.db import models
from audit.models import AuditDashboard, UploadedFile  # Import the AuditDashboard model from the audit app

class KeywordResearchDashboard(models.Model):
    # Container for multiple keyword research entries
    name = models.CharField(max_length=255, verbose_name='Dashboard Name')
    audit_dashboard = models.ForeignKey(AuditDashboard, on_delete=models.CASCADE, related_name='keyword_research_dashboards')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class KeywordResearchEntry(models.Model):
    ACTION_CHOICES = [
        ('Leave As Is', 'Leave As Is'),
        ('Update On Page', 'Update On Page'),
        ('Target w/ Links', 'Target w/ Links'),
        ('301', '301'),
        ('Canonicalize', 'Canonicalize'),
        ('Block Crawl', 'Block Crawl'),
        ('No Index', 'No Index'),
        ('Content Audit', 'Content Audit'),
        ('Merge', 'Merge'),
    ]

    CUSTOMER_JOURNEY_CHOICES = [
        ('Awareness', 'Awareness'),
        ('Consideration', 'Consideration'),
        ('Decision', 'Decision'),
        ('Retention', 'Retention'),
    ]

    SERP_CONTENT_TYPE_CHOICES = [
        ('Amazon Product Page', 'Amazon Product Page'),
        ('Blog Category', 'Blog Category'),
        ('Blog Post', 'Blog Post'),
        ('Citation Site', 'Citation Site'),
        ('Homepage', 'Homepage'),
        ('Lead Generation', 'Lead Generation'),
        ('Local Lander', 'Local Lander'),
        ('Product Category', 'Product Category'),
        ('Product Page', 'Product Page'),
        ('Resource Guide', 'Resource Guide'),
        ('Review Site', 'Review Site'),
        ('Site Info', 'Site Info'),
        ('YouTube Video', 'YouTube Video'),
        ('Pinterest Page', 'Pinterest Page'),
        ('Wikipedia', 'Wikipedia'),
        ('Facebook Page', 'Facebook Page'),
        ('Instagram Page', 'Instagram Page'),
        ('Video Page', 'Video Page')
    ]

    keyword_dashboard = models.ForeignKey(KeywordResearchDashboard, on_delete=models.CASCADE, related_name='entries')
    url = models.URLField(verbose_name='URL', max_length=500)
    category = models.CharField(max_length=255, verbose_name='Category', blank=True)
    main_kw = models.CharField(max_length=255, verbose_name='Main Keyword')
    kw_volume = models.IntegerField(verbose_name='KW Volume', null=True, blank=True)
    kw_ranking = models.IntegerField(verbose_name='KW Ranking', null=True, blank=True)
    best_kw = models.CharField(max_length=255, verbose_name='Best KW', blank=True)
    best_kw_volume = models.IntegerField(verbose_name='Best KW Volume', null=True, blank=True)
    best_kw_ranking = models.IntegerField(verbose_name='Best KW Ranking', null=True, blank=True)
    primary_keyword = models.CharField(max_length=255, verbose_name="Primary Keyword", blank=True)
    pk_volume = models.IntegerField(verbose_name="PK Volume", null=True, blank=True)
    pk_ranking = models.IntegerField(verbose_name="PK Ranking", null=True, blank=True)
    secondary_keywords = models.TextField(verbose_name="Secondary Keywords", blank=True)
    action_choice = models.CharField(max_length=50, choices=ACTION_CHOICES, verbose_name='Action Choice')
    customer_journey = models.CharField(max_length=50, choices=CUSTOMER_JOURNEY_CHOICES, verbose_name='Customer Journey')
    serp_content_type = models.CharField(max_length=50, choices=SERP_CONTENT_TYPE_CHOICES, verbose_name='SERP Content Type')
    audit_entry = models.ForeignKey(UploadedFile, on_delete=models.CASCADE, related_name='keyword_entries', null=True, blank=True)
    avg_rd = models.FloatField(verbose_name='Average RD', null=True, blank=True)
    avg_da = models.FloatField(verbose_name='Average DA', null=True, blank=True)
    avg_pa = models.FloatField(verbose_name='Average PA', null=True, blank=True)
    avg_backlinks = models.IntegerField(verbose_name='Average Backlinks', null=True, blank=True)
    links = models.IntegerField(null=True, blank=True)
    

    def __str__(self):
        return self.url
