# Generated by Django 5.1.1 on 2024-09-26 05:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='payrollrecord',
            name='payment_platform',
            field=models.CharField(blank=True, help_text='The payment platform used (e.g., GCash, Bank Transfer).', max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='payrollrecord',
            name='referral_code',
            field=models.CharField(blank=True, help_text='The payment transaction referral code.', max_length=255, null=True),
        ),
    ]
