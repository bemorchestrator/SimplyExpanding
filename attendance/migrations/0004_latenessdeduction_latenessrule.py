# Generated by Django 5.1.1 on 2024-09-18 09:43

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0003_attendance_total_hours'),
    ]

    operations = [
        migrations.CreateModel(
            name='LatenessDeduction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('min_lateness', models.DurationField()),
                ('deduction', models.DecimalField(decimal_places=2, max_digits=5)),
            ],
        ),
        migrations.CreateModel(
            name='LatenessRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('grace_period', models.DurationField(default=datetime.timedelta(seconds=300))),
                ('deductions', models.ManyToManyField(to='attendance.latenessdeduction')),
            ],
        ),
    ]
