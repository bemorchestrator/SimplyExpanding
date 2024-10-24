# Generated by Django 5.1.1 on 2024-09-19 04:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0010_alter_attendance_clock_in_time_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendance',
            name='lateness_calculated',
            field=models.BooleanField(default=False, help_text='Indicates if lateness has been calculated for the day.'),
        ),
    ]
