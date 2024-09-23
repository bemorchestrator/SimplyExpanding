from django.db import models, transaction
from employees.models import Employee
from holidays.models import Holiday
from datetime import timedelta, datetime, time
from django.utils import timezone
from decimal import Decimal
import logging


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
        default=time(19, 30),
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
    lateness_calculated = models.BooleanField(
        default=False,
        help_text="Indicates if lateness has been calculated for the first clock-in of the day."
    )
    is_primary_clock_in = models.BooleanField(
        default=False,
        help_text="Indicates if this is the first clock-in of the day and eligible for lateness deductions."
    )
    holiday = models.ForeignKey(
        Holiday,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Holiday associated with this attendance record, if any."
    )
    total_income = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total income for the attendance record, including holiday adjustments."
    )

    def __str__(self):
        if self.clock_in_time:
            return f"{self.employee.user.username} - {self.get_status_display()} on {self.clock_in_time.date()}"
        else:
            return f"{self.employee.user.username} - {self.get_status_display()} on N/A"

    def is_clocked_in_method(self):
        return self.status == 'clocked_in'

    def is_on_break_method(self):
        return self.status == 'on_break'

    def is_clocked_out_method(self):
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

    def check_holiday(self):
        attendance_date = self.clock_in_time.date() if self.clock_in_time else None
        if attendance_date:
            fixed_holidays = Holiday.objects.filter(
                is_recurring=True,
                date__month=attendance_date.month,
                date__day=attendance_date.day
            )
            non_fixed_holidays = Holiday.objects.filter(
                is_recurring=False,
                date=attendance_date
            )
            holiday = fixed_holidays.first() or non_fixed_holidays.first()
            if holiday:
                self.holiday = holiday
            else:
                self.holiday = None

    def calculate_lateness_and_deduction(self):
        if self.clock_in_time and self.is_primary_clock_in and not self.lateness_calculated:
            employee = self.employee
            scheduled_time = self.get_scheduled_start_time()
            clock_in_time_local = timezone.localtime(self.clock_in_time)
            lateness = clock_in_time_local - scheduled_time
            if lateness > timedelta(0):
                self.lateness = lateness
                self.apply_lateness_deduction(lateness)
                self.lateness_calculated = True
                logger.debug(f"Lateness Calculated: {self.lateness}, Deduction: {self.lateness_deduction}")
            else:
                self.lateness = timedelta(0)
                self.lateness_deduction = Decimal('0.00')
                logger.debug("No lateness detected. No deduction applied.")
        elif not self.clock_in_time:
            self.lateness = None
            self.lateness_deduction = Decimal('0.00')
            logger.debug("Clock-in time is not set. Lateness and deduction are null.")

        self.check_holiday()

        if self.holiday:
            if self.holiday.holiday_type == 'non_working':
                self.apply_non_working_holiday_pay()
            elif self.holiday.holiday_type == 'special_non_working':
                self.apply_special_non_working_holiday_pay()

    def get_scheduled_start_time(self):
        if self.employee.scheduled_start_time:
            return timezone.make_aware(datetime.combine(self.clock_in_time.date(), self.employee.scheduled_start_time))
        global_settings = GlobalSettings.objects.first()
        if global_settings:
            return timezone.make_aware(datetime.combine(self.clock_in_time.date(), global_settings.scheduled_start_time))
        return timezone.make_aware(datetime.combine(self.clock_in_time.date(), time(19, 30)))

    def apply_lateness_deduction(self, lateness):
        total_deduction = Decimal('0.00')
        lateness_rules = self.employee.lateness_rules.all()
        logger.debug(f"Applying lateness deductions for employee {self.employee.id}. Lateness: {lateness}")

        if not lateness_rules.exists():
            logger.warning(f"No lateness rules found for employee {self.employee.id}.")
            return

        for rule in lateness_rules:
            logger.debug(f"Evaluating LatenessRule: {rule.name}")
            if lateness > rule.grace_period:
                deduction = rule.deductions.filter(min_lateness__lte=lateness).order_by('-min_lateness').first()
                if deduction:
                    logger.debug(f"Applying LatenessDeduction: {deduction.name}")
                    per_hour_rate = Decimal(self.employee.per_day_rate) / Decimal('8.00')  # Assuming 8-hour workday
                    deduction_hours = Decimal(deduction.deduction_duration.total_seconds()) / Decimal('3600')
                    deduction_amount = (per_hour_rate * deduction_hours).quantize(Decimal('0.01'))
                    logger.debug(f"Per Hour Rate: {per_hour_rate}, Deduction Hours: {deduction_hours}, Deduction Amount: {deduction_amount}")
                    total_deduction += deduction_amount
                    logger.debug(f"Accumulated Total Deduction: {total_deduction}")
                    break  # Apply only the highest applicable deduction
                else:
                    logger.debug(f"No applicable deductions found for rule {rule.name} with lateness {lateness}.")
        self.lateness_deduction = total_deduction
        logger.debug(f"Total Deduction Applied: {self.lateness_deduction}")



    def apply_non_working_holiday_pay(self):
        if self.is_primary_clock_in:
            if not self.clock_in_time:
                # Employee did not clock in, assign full day rate
                self.total_income = Decimal(self.employee.per_day_rate)
                logger.debug(f"Non-Working Holiday without clock-in: Total Income set to {self.total_income}")
            elif self.clock_in_time:
                # Employee clocked in, only add worked hours to the full day rate
                worked_pay = (Decimal(self.total_hours or 0) / Decimal('8.0')) * Decimal(self.employee.per_day_rate)
                self.total_income = Decimal(self.employee.per_day_rate) + worked_pay
                logger.debug(f"Non-Working Holiday with clock-in: Total Income set to {self.total_income}")


    def apply_special_non_working_holiday_pay(self):
        if self.is_primary_clock_in and self.clock_in_time:
            # Add 30% to hours worked
            worked_pay = (Decimal(self.total_hours or 0) / Decimal('8.0')) * Decimal(self.employee.per_day_rate) * Decimal('1.3')
            self.total_income = worked_pay
            logger.debug(f"Special Non-Working Holiday with clock-in: Total Income set to {self.total_income}")
        elif self.is_primary_clock_in and not self.clock_in_time:
            # No pay if not clocked in
            self.total_income = Decimal('0.00')
            logger.debug("Special Non-Working Holiday without clock-in: Total Income set to 0.00")

    def calculate_income(self):
        if self.holiday and self.is_primary_clock_in:
            if self.holiday.holiday_type == 'non_working':
                if not self.clock_in_time:
                    # Employee did not clock in, assign full day rate
                    self.total_income = Decimal(self.employee.per_day_rate)
                    logger.debug(f"Non-Working Holiday without clock-in: Total Income set to {self.total_income}")
                elif self.clock_in_time:
                    # Employee clocked in, only add worked hours to the full day rate
                    worked_pay = (Decimal(self.total_hours or 0) / Decimal('8.0')) * Decimal(self.employee.per_day_rate)
                    self.total_income = Decimal(self.employee.per_day_rate) + worked_pay
                    logger.debug(f"Non-Working Holiday with clock-in: Total Income set to {self.total_income}")
            elif self.holiday.holiday_type == 'special_non_working':
                if self.is_primary_clock_in and self.clock_in_time:
                    # Add 30% to hours worked
                    worked_pay = (Decimal(self.total_hours or 0) / Decimal('8.0')) * Decimal(self.employee.per_day_rate) * Decimal('1.3')
                    # Apply lateness deduction
                    worked_pay -= self.lateness_deduction
                    self.total_income = worked_pay.quantize(Decimal('0.01'))
                    logger.debug(f"Special Non-Working Holiday with clock-in: Total Income set to {self.total_income}")
                elif self.is_primary_clock_in and not self.clock_in_time:
                    # No pay if not clocked in
                    self.total_income = Decimal('0.00')
                    logger.debug("Special Non-Working Holiday without clock-in: Total Income set to 0.00")
        elif self.total_hours and self.employee.per_day_rate:
            standard_hours_per_day = Decimal('8.0')  # Assuming an 8-hour workday
            fraction_of_day = Decimal(str(self.total_hours)) / standard_hours_per_day
            income = Decimal(self.employee.per_day_rate) * fraction_of_day
            income -= self.lateness_deduction
            self.total_income = income.quantize(Decimal('0.01'))  # Ensure proper decimal formatting
            logger.debug(f"Regular Day Income calculated: {self.total_income}")
        else:
            self.total_income = Decimal('0.00')
            logger.debug("No income calculated: Total Income set to 0.00")


    def save(self, *args, **kwargs):
        with transaction.atomic():
            # Raise a ValueError if trying to clock out without clocking in
            if self.status == 'clocked_out' and not self.clock_in_time:
                raise ValueError("Cannot clock out without clocking in.")

            # Check if this is the primary clock-in for the day
            if self.clock_in_time:
                if not self.is_primary_clock_in:
                    existing_primary = Attendance.objects.filter(
                        employee=self.employee,
                        clock_in_time__date=self.clock_in_time.date(),
                        is_primary_clock_in=True
                    ).select_for_update().exists()
                    if not existing_primary:
                        self.is_primary_clock_in = True

            # Calculate lateness and deduction if clocking in as primary
            if self.status == 'clocked_in' and self.is_primary_clock_in and not self.lateness_calculated:
                self.calculate_lateness_and_deduction()

            # Calculate total hours worked if clock-in and clock-out times are set
            if self.clock_in_time and self.clock_out_time:
                total_duration = self.clock_out_time - self.clock_in_time
                if self.break_start_time and self.break_end_time:
                    break_duration = self.break_end_time - self.break_start_time
                    total_duration -= break_duration
                self.total_hours = total_duration.total_seconds() / 3600
            else:
                self.total_hours = None

            # Calculate the total income
            self.calculate_income()

            # Save the model
            super().save(*args, **kwargs)

