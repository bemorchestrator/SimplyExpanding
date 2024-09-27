# Generated by Django 5.1.1 on 2024-09-27 07:49

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0007_remove_clientbillingrecord_company_address_and_more'),
        ('client', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='clientbillingrecord',
            name='client_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='clientbillingrecord',
            name='client',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='client.clientonboarding'),
        ),
    ]
