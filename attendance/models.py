# attendance/models.py

from django.db import models
from employees.models import Employee
from datetime import timedelta, datetime, time
from django.utils import timezone
from decimal import Decimal
import logging  # Import logging module

# Initialize logger
logger = logging.getLogger('attendance')

class LatenessRule(models.Model):
    name = models.CharField(
        max_length=100,
        help_text="Name of the lateness rule set. Example: Standard Lateness Policy"
    )
    description = models.TextField(
        help_text="Detailed description of the lateness rule. Explain when and how deductions are applied."
    )
    grace_period = models.DurationField(
        default=timedelta(minutes=5),
        help_text="Duration allowed before lateness deductions apply. Example: 0:05:00 for 5 minutes"
    )
    deductions = models.ManyToManyField(
        'LatenessDeduction',
        help_text="Select the deductions that apply for this rule based on lateness duration."
    )

    def __str__(self):
        return self.name

class LatenessDeduction(models.Model):
    name = models.CharField(
        max_length=100,
        help_text="Name of the lateness deduction. Example: Minor Lateness Deduction"
    )
    description = models.TextField(
        help_text="Detailed description of the deduction. Explain how the deduction is calculated and applied."
    )
    min_lateness = models.DurationField(
        help_text="Minimum lateness duration to trigger this deduction. Example: 0:05:01 for 5 minutes and 1 second"
    )
    deduction_duration = models.DurationField(
        help_text="Duration to deduct from income due to lateness. Example: 0:02:00 for 2 hours"
    )

    def __str__(self):
        hours, remainder = divmod(self.deduction_duration.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{self.name} | Lateness >= {self.min_lateness} | Deduct {int(hours)}h {int(minutes)}m"

class GlobalSettings(models.Model):
    scheduled_start_time = models.TimeField(
        default=time(19, 30),  # Set default to 19:30 (7:30 PM)
        help_text="Global scheduled start time for all employees. Example: 19:30 (24-hour format)"
    )

    def __str__(self):
        return "Global Settings"

    class Meta:
        verbose_name = "Global Setting"
        verbose_name_plural = "Global Settings"

class Attendance(models.Model):
    STATUS_CHOICES = [
        ('clocked_in', 'Clocked In'),
        ('on_break', 'On Break'),
        ('clocked_out', 'Clocked Out'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    clock_in_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time when the employee clocked in. Example: 2023-01-01 19:56:19"
    )
    clock_out_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time when the employee clocked out. Example: 2023-01-01 17:00:00"
    )
    break_start_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time when the employee started their break."
    )
    break_end_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time when the employee ended their break."
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='clocked_out',
        help_text="Current status of the employee: Clocked In, On Break, or Clocked Out."
    )
    total_hours = models.FloatField(
        null=True,
        blank=True,
        help_text="Total hours worked, calculated automatically."
    )
    lateness = models.DurationField(
        null=True,
        blank=True,
        help_text="Duration the employee was late, calculated based on scheduled start time."
    )
    lateness_deduction = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total monetary deduction due to lateness, calculated based on lateness rules."
    )

    def __str__(self):
        if self.clock_in_time:
            return f"{self.employee.user.username} - {self.get_status_display()} on {self.clock_in_time.date()}"
        else:
            return f"{self.employee.user.username} - {self.get_status_display()} on N/A"

    def is_clocked_in(self):
        return self.status == 'clocked_in'

    def is_on_break(self):
        return self.status == 'on_break'

    def is_clocked_out(self):
        return self.status == 'clocked_out'

    @property
    def total_time(self):
        if self.clock_in_time and self.clock_out_time:
            total_duration = self.clock_out_time - self.clock_in_time
            if self.break_start_time and self.break_end_time:
                break_duration = self.break_end_time - self.break_start_time
                total_duration -= break_duration
            return total_duration
        return None

    @property
    def total_time_formatted(self):
        total_duration = self.total_time
        if total_duration:
            total_seconds = int(total_duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return "N/A"

    @property
    def lateness_formatted(self):
        if self.lateness:
            total_seconds = int(self.lateness.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return "00:00:00"

    @property
    def lateness_deduction_amount(self):
        if self.lateness_deduction > 0:
            return f"Php {self.lateness_deduction}"
        return "Php 0.00"

    def calculate_lateness_and_deduction(self):
        if self.clock_in_time:
            employee = self.employee
            # Get the scheduled start time: employee's or global
            if employee.scheduled_start_time:
                scheduled_time = datetime.combine(self.clock_in_time.date(), employee.scheduled_start_time)
            else:
                global_settings = GlobalSettings.objects.first()
                if global_settings:
                    scheduled_time = datetime.combine(self.clock_in_time.date(), global_settings.scheduled_start_time)
                else:
                    # Default to 19:30 (7:30 PM) if global settings are not set
                    scheduled_time = datetime.combine(self.clock_in_time.date(), time(19, 30))

            # Ensure timezone-aware datetime
            if timezone.is_naive(scheduled_time):
                scheduled_time = timezone.make_aware(scheduled_time, timezone.get_current_timezone())
            else:
                scheduled_time = scheduled_time.astimezone(timezone.get_current_timezone())

            # Ensure clock_in_time is in local timezone
            clock_in_time_local = timezone.localtime(self.clock_in_time)

            # Log times for debugging
            logger.debug(f"Scheduled Time: {scheduled_time} | Clock In Time (Local): {clock_in_time_local}")

            lateness = clock_in_time_local - scheduled_time

            logger.debug(f"Lateness Calculated: {lateness}")

            if lateness > timedelta(0):
                self.lateness = lateness
                # Get all assigned lateness rules
                lateness_rules = employee.lateness_rules.all()
                total_deduction = Decimal('0.00')
                for rule in lateness_rules:
                    if lateness > rule.grace_period:
                        # Find applicable deductions for this rule
                        deductions = rule.deductions.filter(min_lateness__lte=lateness).order_by('-min_lateness')
                        for deduction in deductions:
                            per_hour_rate = employee.per_day_rate / Decimal('8.00')  # Assuming 8-hour workday
                            deduction_hours = Decimal(deduction.deduction_duration.total_seconds()) / Decimal('3600')
                            total_deduction += (per_hour_rate * deduction_hours).quantize(Decimal('0.01'))
                self.lateness_deduction = total_deduction
                logger.debug(f"Total Deduction Calculated: {self.lateness_deduction}")
            else:
                self.lateness = timedelta(0)
                self.lateness_deduction = Decimal('0.00')
                logger.debug("No lateness detected. No deduction applied.")
        else:
            self.lateness = None
            self.lateness_deduction = Decimal('0.00')
            logger.debug("Clock-in time is not set. Lateness and deduction are null.")

    def save(self, *args, **kwargs):
        # Calculate lateness and deductions before saving
        self.calculate_lateness_and_deduction()

        # Calculate total_hours
        if self.clock_in_time and self.clock_out_time:
            total_duration = self.clock_out_time - self.clock_in_time
            if self.break_start_time and self.break_end_time:
                break_duration = self.break_end_time - self.break_start_time
                total_duration -= break_duration
            self.total_hours = total_duration.total_seconds() / 3600
        else:
            self.total_hours = None

        super().save(*args, **kwargs)

    def calculate_income(self):
        if self.total_hours and self.employee.per_day_rate:
            standard_hours_per_day = Decimal('8.0')  # Assuming an 8-hour workday
            fraction_of_day = Decimal(str(self.total_hours)) / standard_hours_per_day
            income = self.employee.per_day_rate * fraction_of_day
            # Apply lateness deduction
            income -= self.lateness_deduction
            return max(income, Decimal('0.00'))  # Ensure income doesn't go negative
        return Decimal('0.00')
