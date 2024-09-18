# Generated by Django 5.1.1 on 2024-09-18 07:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employees', '0006_alter_employee_profile_picture'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='per_day_rate',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
        ),
    ]
