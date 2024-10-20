from django.db import models, transaction
from employees.models import Employee
from holidays.models import Holiday
from datetime import timedelta, datetime, time
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
import logging
from django.utils.timezone import make_aware, now

# Configure logging for the attendance app
logger = logging.getLogger('attendance')

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
        LatenessDeduction,
        help_text="Select the deductions that apply for this rule based on lateness duration."
    )

    def __str__(self):
        return self.name

class GlobalSettings(models.Model):
    scheduled_start_time = models.TimeField(
        default=time(9, 0),
        help_text="Global scheduled start time for all employees. Example: 09:00 (24-hour format)"
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
        help_text="Date and time when the employee clocked in. Example: 2023-01-01 09:00:00"
    )
    clock_out_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time when the employee clocked out. Example: 2023-01-01 17:00:00"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='clocked_out',
        help_text="Current status of the employee: Clocked In, On Break, or Clocked Out."
    )
    total_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
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

    @property
    def break_duration(self):
        """Calculate the total break duration from all breaks."""
        total_duration = timedelta(0)
        for brk in self.breaks.all():
            if brk.break_start_time and brk.break_end_time:
                total_duration += brk.break_end_time - brk.break_start_time
        return total_duration

    @property
    def break_duration_formatted(self):
        """Return break duration in HH:MM:SS format."""
        duration = self.break_duration
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if duration > timedelta(0) else "00:00:00"

    @property
    def total_time(self):
        """
        Calculate total working time excluding break duration.
        If breaks were taken, deduct total break duration.
        """
        if self.clock_in_time and self.clock_out_time:
            total_duration = self.clock_out_time - self.clock_in_time

            # Get total break duration
            total_break_duration = self.break_duration

            # Deduct total break time
            total_duration -= total_break_duration

            # Ensure that total duration does not go negative
            if total_duration < timedelta(0):
                total_duration = timedelta(0)

            return total_duration
        return None

    @property
    def total_time_formatted(self):
        """Return total working time in HH:MM:SS format."""
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
        """Return lateness duration in HH:MM:SS format."""
        if self.lateness:
            total_seconds = int(self.lateness.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return "00:00:00"

    @property
    def lateness_deduction_amount_formatted(self):
        """Return formatted lateness deduction amount."""
        if self.lateness_deduction > 0:
            return f"Php {self.lateness_deduction}"
        return "Php 0.00"

    def check_holiday(self):
        """Check if the attendance date is a holiday."""
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
                logger.debug(f"Holiday found: {self.holiday.name}")
            else:
                self.holiday = None
                logger.debug("No holiday found for this date.")

    def calculate_lateness_and_deduction(self):
        """
        Calculate lateness and apply deductions based on lateness rules.
        """
        if self.clock_in_time and self.is_primary_clock_in and not self.lateness_calculated:
            employee = self.employee
            scheduled_time = self.get_scheduled_start_time()
            clock_in_time_local = timezone.localtime(self.clock_in_time)
            
            # Apply grace period from lateness rules or default to 5 minutes
            grace_period = (
                employee.lateness_rules.first().grace_period 
                if employee.lateness_rules.exists() 
                else timedelta(minutes=5)
            )
            
            # Calculate lateness (difference between clock-in time and scheduled start time)
            lateness = clock_in_time_local - scheduled_time
            
            # Adjust the logic: lateness is only calculated if it's beyond the grace period
            if lateness > grace_period:  # Employee is late if beyond the grace period
                self.lateness = lateness
                self.apply_lateness_deduction(lateness)
                self.lateness_calculated = True
                logger.debug(f"Lateness Calculated: {self.lateness}, Deduction: {self.lateness_deduction}")
            else:  # Clocked in on time or within the grace period
                self.lateness = timedelta(0)
                self.lateness_deduction = Decimal('0.00')
                self.lateness_calculated = False
                logger.debug("No lateness detected within grace period. No deduction applied.")
        elif not self.clock_in_time:
            self.lateness = None
            self.lateness_deduction = Decimal('0.00')
            self.lateness_calculated = False
            logger.debug("Clock-in time is not set. Lateness and deduction are null.")

        # Check if the clock-in date falls on a holiday and adjust pay accordingly
        self.check_holiday()

        if self.holiday:
            if self.holiday.holiday_type == 'non_working':
                self.apply_non_working_holiday_pay()
            elif self.holiday.holiday_type == 'special_non_working':
                self.apply_special_non_working_holiday_pay()


    def get_scheduled_start_time(self):
        """Retrieve the scheduled start time for the employee."""
        # Get today's date or the clock-in date if available
        current_date = self.clock_in_time.date() if self.clock_in_time else now().date()

        # Check if the employee has a specific scheduled start time
        if hasattr(self.employee, 'scheduled_start_time') and self.employee.scheduled_start_time:
            scheduled_time = self.employee.scheduled_start_time
        else:
            # Retrieve the global scheduled start time from settings
            global_settings = GlobalSettings.objects.first()
            if global_settings and global_settings.scheduled_start_time:
                scheduled_time = global_settings.scheduled_start_time
            else:
                # Default to 9:00 AM if no global or employee-specific time is set
                scheduled_time = time(9, 0)

        # Combine the date and time, ensuring the datetime is timezone-aware
        scheduled_datetime = datetime.combine(current_date, scheduled_time)
        return make_aware(scheduled_datetime)

    def apply_lateness_deduction(self, lateness):
        """
        Apply the appropriate lateness deduction based on lateness duration.
        """
        total_deduction = Decimal('0.00')
        lateness_rules = self.employee.lateness_rules.all()
        logger.debug(f"Applying lateness deductions for employee {self.employee.id}. Lateness: {lateness}")

        if not lateness_rules.exists():
            logger.warning(f"No lateness rules found for employee {self.employee.id}.")
            return

        # Apply deductions based on rules
        for rule in lateness_rules:
            logger.debug(f"Evaluating LatenessRule: {rule.name}")
            if lateness > rule.grace_period:
                # Find the applicable deduction with the highest min_lateness <= lateness
                deduction = rule.deductions.filter(min_lateness__lte=lateness).order_by('-min_lateness').first()
                if deduction:
                    logger.debug(f"Applying LatenessDeduction: {deduction.name}")
                    per_hour_rate = Decimal(str(self.employee.per_day_rate)) / Decimal('8.00')  # Assuming 8-hour workday
                    deduction_hours = Decimal(str(deduction.deduction_duration.total_seconds())) / Decimal('3600')
                    deduction_amount = (per_hour_rate * deduction_hours).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    logger.debug(f"Per Hour Rate: {per_hour_rate}, Deduction Hours: {deduction_hours}, Deduction Amount: {deduction_amount}")
                    total_deduction += deduction_amount
                    logger.debug(f"Accumulated Total Deduction: {total_deduction}")
                    break  # Apply only the highest applicable deduction
                else:
                    logger.debug(f"No applicable deductions found for rule {rule.name} with lateness {lateness}.")
        self.lateness_deduction = total_deduction
        logger.debug(f"Total Deduction Applied: {self.lateness_deduction}")

    def apply_non_working_holiday_pay(self):
        """
        Apply pay adjustments for non-working holidays.
        """
        if self.is_primary_clock_in:
            if not self.clock_in_time:
                # Employee did not clock in, assign full day rate
                self.total_income = Decimal(str(self.employee.per_day_rate))
                logger.debug(f"Non-Working Holiday without clock-in: Total Income set to {self.total_income}")
            elif self.clock_in_time:
                # Employee clocked in, only add worked hours to the full day rate
                if self.total_hours:
                    worked_pay = (self.total_hours / Decimal('8.0')) * Decimal(str(self.employee.per_day_rate))
                    self.total_income = Decimal(str(self.employee.per_day_rate)) + worked_pay
                    logger.debug(f"Non-Working Holiday with clock-in: Total Income set to {self.total_income}")
                else:
                    self.total_income = Decimal('0.00')
                    logger.debug("Non-Working Holiday with clock-in but no total hours: Total Income set to 0.00")

    def apply_special_non_working_holiday_pay(self):
        """
        Apply pay adjustments for special non-working holidays.
        """
        if self.is_primary_clock_in and self.clock_in_time:
            if self.total_hours:
                # Add 30% to hours worked
                worked_pay = (self.total_hours / Decimal('8.0')) * Decimal(str(self.employee.per_day_rate)) * Decimal('1.3')
                # Apply lateness deduction
                worked_pay -= self.lateness_deduction
                # Allow total_income to be negative
                self.total_income = worked_pay.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                logger.debug(f"Special Non-Working Holiday with clock-in: Total Income set to {self.total_income}")
            else:
                self.total_income = Decimal('0.00')
                logger.debug("Special Non-Working Holiday with clock-in but no total hours: Total Income set to 0.00")
        elif self.is_primary_clock_in and not self.clock_in_time:
            # No pay if not clocked in
            self.total_income = Decimal('0.00')
            logger.debug("Special Non-Working Holiday without clock-in: Total Income set to 0.00")

    def calculate_income(self):
        """
        Calculate the total income based on attendance details.
        """
        logger.debug(f"Calculating income for Attendance ID={self.id}")
        if self.holiday and self.is_primary_clock_in:
            logger.debug("Holiday detected. Applying holiday pay rules.")
            # Holiday pay logic
            if self.holiday.holiday_type == 'non_working':
                if not self.clock_in_time:
                    self.total_income = Decimal(str(self.employee.per_day_rate))
                    logger.debug(f"Non-Working Holiday without clock-in: Total Income = {self.total_income}")
                elif self.clock_in_time and self.total_hours:
                    worked_pay = (self.total_hours / Decimal('8.0')) * Decimal(str(self.employee.per_day_rate))
                    self.total_income = Decimal(str(self.employee.per_day_rate)) + worked_pay
                    logger.debug(f"Non-Working Holiday with clock-in: Total Income = {self.total_income}")
                else:
                    self.total_income = Decimal('0.00')
                    logger.debug("Non-Working Holiday with clock-in but no total hours: Total Income set to 0.00")
            elif self.holiday.holiday_type == 'special_non_working':
                self.apply_special_non_working_holiday_pay()
        elif self.total_hours and self.employee.per_day_rate:
            logger.debug("Regular day detected. Calculating income based on hours worked.")
            standard_hours_per_day = Decimal('8.0')
            fraction_of_day = Decimal(str(self.total_hours)) / standard_hours_per_day
            income = Decimal(str(self.employee.per_day_rate)) * fraction_of_day
            income -= self.lateness_deduction
            # Allow total_income to be negative
            self.total_income = income.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            logger.debug(f"Calculated Total Income: {self.total_income}")
        else:
            self.total_income = Decimal('0.00')
            logger.debug("No income conditions met. Setting Total Income = 0.00")

    def calculate_total_hours(self):
        """
        Calculate total hours worked excluding break durations.
        If the employee clocked in earlier than the scheduled start time,
        working hours start from the scheduled start time.
        """
        if self.clock_in_time and self.clock_out_time:
            # Ensure clock-in and clock-out times are timezone-aware
            actual_clock_in = timezone.localtime(self.clock_in_time)
            actual_clock_out = timezone.localtime(self.clock_out_time)

            # Get the scheduled start time
            try:
                scheduled_start = timezone.localtime(self.get_scheduled_start_time())
            except Exception as e:
                logger.error(f"Error getting scheduled start time: {e}")
                self.total_hours = Decimal('0.00')
                return

            # Determine the effective start time (whichever is later)
            start_time = max(scheduled_start, actual_clock_in)

            # Calculate total working duration from start to clock-out
            total_duration = actual_clock_out - start_time

            # Subtract break durations if any
            total_duration -= self.break_duration

            # Ensure the total duration is not negative
            if total_duration < timedelta(0):
                total_duration = timedelta(0)

            # Convert total duration to decimal hours
            self.total_hours = Decimal(total_duration.total_seconds() / 3600).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            logger.debug(f"Total hours worked: {self.total_hours}")
        else:
            # If either clock-in or clock-out time is missing, set total hours to 0
            self.total_hours = Decimal('0.00')
            logger.debug("Clock-in or clock-out time missing. Total hours set to 0.")

    def save(self, *args, **kwargs):
        """
        Override the save method to perform calculations before saving.
        """
        with transaction.atomic():
            # Determine if this attendance is the primary clock-in for the day
            if self.clock_in_time:
                if not self.is_primary_clock_in:
                    existing_primary = Attendance.objects.filter(
                        employee=self.employee,
                        clock_in_time__date=self.clock_in_time.date(),
                        is_primary_clock_in=True
                    ).select_for_update().exists()
                    if not existing_primary:
                        self.is_primary_clock_in = True
                        logger.debug(f"Setting this attendance as primary clock-in for the day: {self.clock_in_time.date()}")

            # Calculate lateness and deductions if applicable
            if self.status == 'clocked_in' and self.is_primary_clock_in and not self.lateness_calculated:
                self.calculate_lateness_and_deduction()

            # Calculate total hours worked
            self.calculate_total_hours()

            # Calculate the total income
            self.calculate_income()
            logger.debug(f"Total income calculated: {self.total_income}")  # Log total income

            # Save the model
            super().save(*args, **kwargs)

class Break(models.Model):
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name='breaks')
    break_start_time = models.DateTimeField()
    break_end_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Break from {self.break_start_time} to {self.break_end_time}"
