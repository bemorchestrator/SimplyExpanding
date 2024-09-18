# Generated by Django 5.1.1 on 2024-09-18 11:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employees', '0013_alter_employee_scheduled_start_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employee',
            name='scheduled_start_time',
            field=models.TimeField(blank=True, help_text='Specific scheduled start time for the employee. If not set, global scheduled start time is used. Example: 19:30 (24-hour format)', null=True),
        ),
    ]
