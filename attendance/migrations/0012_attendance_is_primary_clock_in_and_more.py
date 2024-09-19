# Generated by Django 5.1.1 on 2024-09-19 04:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0011_attendance_lateness_calculated'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendance',
            name='is_primary_clock_in',
            field=models.BooleanField(default=False, help_text='Indicates if this is the first clock-in of the day and eligible for lateness deductions.'),
        ),
        migrations.AlterField(
            model_name='attendance',
            name='lateness_calculated',
            field=models.BooleanField(default=False, help_text='Indicates if lateness has been calculated for the first clock-in of the day.'),
        ),
    ]
