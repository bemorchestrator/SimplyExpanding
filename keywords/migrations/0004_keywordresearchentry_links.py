# Generated by Django 5.1.1 on 2024-10-21 03:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keywords', '0003_keywordresearchentry_avg_backlinks_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='keywordresearchentry',
            name='links',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]