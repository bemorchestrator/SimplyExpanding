# Generated by Django 5.1.1 on 2024-10-16 00:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0023_uploadedfile_secondary_keywords'),
    ]

    operations = [
        migrations.AddField(
            model_name='uploadedfile',
            name='customer_journey',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]