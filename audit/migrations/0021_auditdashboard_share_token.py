# Generated by Django 5.1.1 on 2024-10-14 06:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0020_auditdashboard_uploadedfile_dashboard'),
    ]

    operations = [
        migrations.AddField(
            model_name='auditdashboard',
            name='share_token',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
    ]
