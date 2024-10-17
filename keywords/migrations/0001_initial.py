# Generated by Django 5.1.1 on 2024-10-17 03:55

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('audit', '0021_auditdashboard_share_token'),
    ]

    operations = [
        migrations.CreateModel(
            name='KeywordResearchDashboard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Dashboard Name')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('audit_dashboard', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='keyword_research_dashboards', to='audit.auditdashboard')),
            ],
        ),
        migrations.CreateModel(
            name='KeywordResearchEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField(max_length=500, verbose_name='URL')),
                ('category', models.CharField(blank=True, max_length=255, verbose_name='Category')),
                ('main_kw', models.CharField(max_length=255, verbose_name='Main Keyword')),
                ('kw_volume', models.IntegerField(blank=True, null=True, verbose_name='KW Volume')),
                ('kw_ranking', models.IntegerField(blank=True, null=True, verbose_name='KW Ranking')),
                ('best_kw', models.CharField(blank=True, max_length=255, verbose_name='Best KW')),
                ('best_kw_volume', models.IntegerField(blank=True, null=True, verbose_name='Best KW Volume')),
                ('best_kw_ranking', models.IntegerField(blank=True, null=True, verbose_name='Best KW Ranking')),
                ('primary_keyword', models.CharField(blank=True, max_length=255, verbose_name='Primary Keyword')),
                ('pk_volume', models.IntegerField(blank=True, null=True, verbose_name='PK Volume')),
                ('pk_ranking', models.IntegerField(blank=True, null=True, verbose_name='PK Ranking')),
                ('secondary_keywords', models.TextField(blank=True, verbose_name='Secondary Keywords')),
                ('action_choice', models.CharField(choices=[('Leave As Is', 'Leave As Is'), ('Update On Page', 'Update On Page'), ('Target w/ Links', 'Target w/ Links'), ('301', '301'), ('Canonicalize', 'Canonicalize'), ('Block Crawl', 'Block Crawl'), ('No Index', 'No Index'), ('Content Audit', 'Content Audit'), ('Merge', 'Merge')], max_length=50, verbose_name='Action Choice')),
                ('customer_journey', models.CharField(choices=[('Awareness', 'Awareness'), ('Consideration', 'Consideration'), ('Decision', 'Decision'), ('Retention', 'Retention')], max_length=50, verbose_name='Customer Journey')),
                ('serp_content_type', models.CharField(choices=[('Amazon Product Page', 'Amazon Product Page'), ('Blog Category', 'Blog Category'), ('Blog Post', 'Blog Post'), ('Citation Site', 'Citation Site'), ('Homepage', 'Homepage'), ('Lead Generation', 'Lead Generation'), ('Local Lander', 'Local Lander'), ('Product Category', 'Product Category'), ('Product Page', 'Product Page'), ('Resource Guide', 'Resource Guide'), ('Review Site', 'Review Site'), ('Site Info', 'Site Info'), ('YouTube Video', 'YouTube Video'), ('Pinterest Page', 'Pinterest Page'), ('Wikipedia', 'Wikipedia'), ('Facebook Page', 'Facebook Page'), ('Instagram Page', 'Instagram Page'), ('Video Page', 'Video Page')], max_length=50, verbose_name='SERP Content Type')),
                ('keyword_dashboard', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entries', to='keywords.keywordresearchdashboard')),
            ],
        ),
    ]