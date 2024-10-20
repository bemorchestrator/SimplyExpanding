# Generated by Django 5.1.1 on 2024-09-18 09:56

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0005_attendance_lateness_attendance_lateness_deduction'),
        ('employees', '0008_employee_scheduled_start_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='lateness_rule',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='attendance.latenessrule'),
        ),
    ]
