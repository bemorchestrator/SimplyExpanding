# Generated by Django 5.1.1 on 2024-10-08 14:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0007_alter_sitemapurl_url'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sitemap',
            name='url',
            field=models.URLField(default='http://example.com/sitemap.xml', max_length=1000),
        ),
        migrations.AlterField(
            model_name='sitemapurl',
            name='status',
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='uploadedfile',
            name='action_choice',
            field=models.CharField(choices=[('leave', 'Leave As Is'), ('update_on_page', 'Update On Page'), ('target_with_links', 'Target w/ Links'), ('301', '301'), ('canonicalize', 'Canonicalize'), ('block_crawl', 'Block Crawl'), ('no_index', 'No Index'), ('content_audit', 'Content Audit'), ('merge', 'Merge')], default='leave', max_length=1000),
        ),
        migrations.AlterField(
            model_name='uploadedfile',
            name='best_kw',
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='uploadedfile',
            name='canonical_link',
            field=models.URLField(blank=True, max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='uploadedfile',
            name='category',
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='uploadedfile',
            name='current_title',
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='uploadedfile',
            name='drive_file_id',
            field=models.CharField(default='unknown_id', max_length=1000),
        ),
        migrations.AlterField(
            model_name='uploadedfile',
            name='drive_file_link',
            field=models.URLField(blank=True, max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='uploadedfile',
            name='file_name',
            field=models.CharField(default='unknown_file', max_length=1000),
        ),
        migrations.AlterField(
            model_name='uploadedfile',
            name='h1',
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='uploadedfile',
            name='index_status',
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='uploadedfile',
            name='last_modified',
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='uploadedfile',
            name='main_kw',
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='uploadedfile',
            name='meta',
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='uploadedfile',
            name='page_path',
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='uploadedfile',
            name='status_code',
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='uploadedfile',
            name='type',
            field=models.CharField(default='text/html; charset=UTF-8', max_length=1000),
        ),
        migrations.AlterField(
            model_name='uploadedfile',
            name='url',
            field=models.URLField(default='http://example.com', max_length=1000),
        ),
    ]
