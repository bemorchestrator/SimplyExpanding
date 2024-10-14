# Generated by Django 5.1.1 on 2024-10-13 05:19

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0003_payrollrecord_other_payment_platform_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='payrollrecord',
            name='bonus',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Additional bonus for the employee.', max_digits=10),
        ),
        migrations.AddField(
            model_name='payrollrecord',
            name='deductions',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Any deductions (e.g., tax, insurance).', max_digits=10),
        ),
        migrations.AddField(
            model_name='payrollrecord',
            name='remarks',
            field=models.TextField(blank=True, help_text="Optional remarks or notes for the employee's payslip.", null=True),
        ),
        migrations.AlterField(
            model_name='payrollrecord',
            name='total_income',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='The base salary or income for the employee.', max_digits=10),
        ),
    ]