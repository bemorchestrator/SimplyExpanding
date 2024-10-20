# Generated by Django 5.1.1 on 2024-10-20 08:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('keywords', '0002_keywordresearchentry_audit_entry'),
    ]

    operations = [
        migrations.AddField(
            model_name='keywordresearchentry',
            name='avg_backlinks',
            field=models.IntegerField(blank=True, null=True, verbose_name='Average Backlinks'),
        ),
        migrations.AddField(
            model_name='keywordresearchentry',
            name='avg_da',
            field=models.FloatField(blank=True, null=True, verbose_name='Average DA'),
        ),
        migrations.AddField(
            model_name='keywordresearchentry',
            name='avg_pa',
            field=models.FloatField(blank=True, null=True, verbose_name='Average PA'),
        ),
        migrations.AddField(
            model_name='keywordresearchentry',
            name='avg_rd',
            field=models.FloatField(blank=True, null=True, verbose_name='Average RD'),
        ),
    ]
