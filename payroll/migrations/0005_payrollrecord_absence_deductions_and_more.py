# Generated by Django 5.1.1 on 2024-10-13 08:50

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0004_payrollrecord_bonus_payrollrecord_deductions_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='payrollrecord',
            name='absence_deductions',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Deductions for employee absences.', max_digits=10),
        ),
        migrations.AddField(
            model_name='payrollrecord',
            name='average_daily_pay',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text="The employee's average daily pay.", max_digits=10),
        ),
        migrations.AddField(
            model_name='payrollrecord',
            name='other_deductions',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Additional deductions (e.g., loans, penalties).', max_digits=10),
        ),
    ]
