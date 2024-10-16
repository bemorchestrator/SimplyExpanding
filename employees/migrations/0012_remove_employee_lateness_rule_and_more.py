# Generated by Django 5.1.1 on 2024-09-18 11:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0007_globalsettings_latenessdeduction_description_and_more'),
        ('employees', '0011_alter_employee_address_alter_employee_city_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='employee',
            name='lateness_rule',
        ),
        migrations.AddField(
            model_name='employee',
            name='lateness_rules',
            field=models.ManyToManyField(blank=True, help_text='Assign one or more lateness rules to the employee. If not set, the global default rule is applied.', to='attendance.latenessrule'),
        ),
    ]
