# Generated by Django 5.1.1 on 2024-10-07 04:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0003_uploadedfile_canonical_link_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='uploadedfile',
            name='crawl_depth',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='uploadedfile',
            name='page_path',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
