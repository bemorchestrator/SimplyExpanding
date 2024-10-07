# Generated by Django 5.1.1 on 2024-10-07 10:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0004_uploadedfile_crawl_depth_uploadedfile_page_path'),
    ]

    operations = [
        migrations.AddField(
            model_name='uploadedfile',
            name='action_choice',
            field=models.CharField(choices=[('leave', 'Leave As Is'), ('update_on_page', 'Update On Page'), ('target_with_links', 'Target w/ Links'), ('301', '301'), ('canonicalize', 'Canonicalize'), ('block_crawl', 'Block Crawl'), ('no_index', 'No Index'), ('content_audit', 'Content Audit'), ('merge', 'Merge')], default='leave', max_length=50),
        ),
    ]
