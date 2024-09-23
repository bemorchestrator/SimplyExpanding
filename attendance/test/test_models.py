# attendance/tests/test_models.py

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from employees.models import Employee
from attendance.models import Attendance, LatenessRule, LatenessDeduction, GlobalSettings
from holidays.models import Holiday
from django.db.utils import IntegrityError
from django.db import transaction
from datetime import timedelta, datetime, time
from decimal import Decimal

User = get_user_model()


class AttendanceModelTest(TestCase):
    def setUp(self):
        """
        Set up common objects for all tests.
        """
        # Create a unique test user
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpassword'
        )
        
        # Retrieve the Employee created by the signal
        self.employee = Employee.objects.get(user=self.user)
        self.employee.per_day_rate = 1000
        self.employee.save()
        
        # Create Lateness Deduction
        self.lateness_deduction = LatenessDeduction.objects.create(
            name="Minor Lateness Deduction",
            description="Deduction for minor lateness",
            min_lateness=timedelta(minutes=5, seconds=1),
            deduction_duration=timedelta(minutes=15)  # 15 minutes deduction
        )
        
        # Create Lateness Rule and associate deductions
        self.lateness_rule = LatenessRule.objects.create(
            name="Standard Lateness Policy",
            description="Standard policy for handling lateness",
            grace_period=timedelta(minutes=5)
        )
        self.lateness_rule.deductions.add(self.lateness_deduction)
        
        # Create Global Settings
        self.global_settings = GlobalSettings.objects.create(
            scheduled_start_time=time(9, 0)  # 9:00 AM
        )
        
        # Create a recurring holiday with both recurring_month and recurring_day
        self.recurring_holiday = Holiday.objects.create(
            name="Recurring Holiday",
            recurring_month=1,  # January
            recurring_day=1,    # 1st day
            is_recurring=True,
            holiday_type='non_working'
        )
        
        # Create a non-recurring holiday with a specific date
        self.non_recurring_holiday = Holiday.objects.create(
            name="Non-Recurring Holiday",
            date=datetime.now().date(),
            is_recurring=False,
            holiday_type='special_non_working'
        )

    # -------------------------------
    # 1. Model Constraints and Relationships
    # -------------------------------
    
    def test_employee_creation_via_signal(self):
        """
        Test that an Employee instance is automatically created via signals when a User is created.
        """
        # Verify that the Employee was created by the signal
        employee = Employee.objects.get(user=self.user)
        self.assertIsNotNone(employee)
        self.assertEqual(employee.per_day_rate, 1000)

    def test_unique_employee_per_user(self):
        """
        Test that creating a second Employee for the same User raises an IntegrityError.
        """
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Employee.objects.create(user=self.user, per_day_rate=1500)

    # -------------------------------
    # 2. Business Logic and Model Methods
    # -------------------------------
    
    def test_attendance_status_transitions(self):
        """
        Test valid status transitions for Attendance.
        """
        now = timezone.now()
        attendance = Attendance.objects.create(
            employee=self.employee,
            clock_in_time=now,
            status='clocked_in',
            is_primary_clock_in=True
        )
        
        # Transition to on_break
        attendance.status = 'on_break'
        attendance.save()
        self.assertEqual(attendance.status, 'on_break')
        
        # Transition back to clocked_in
        attendance.status = 'clocked_in'
        attendance.save()
        self.assertEqual(attendance.status, 'clocked_in')
        
        # Transition to clocked_out
        attendance.status = 'clocked_out'
        attendance.save()
        self.assertEqual(attendance.status, 'clocked_out')

    def test_invalid_status_transition(self):
        """
        Test that invalid status transitions are handled gracefully.
        For example, transitioning from 'clocked_out' to 'on_break' without clocking in.
        """
        now = timezone.now()
        attendance = Attendance.objects.create(
            employee=self.employee,
            status='clocked_out',
            is_primary_clock_in=True
        )
        
        # Attempt to transition to 'on_break' without clocking in
        attendance.status = 'on_break'
        with self.assertRaises(ValueError):
            attendance.save()

    def test_lateness_calculation_within_grace_period(self):
        """
        Test that no lateness is recorded if clock-in is within the grace period.
        """
        scheduled_datetime = timezone.make_aware(datetime.combine(timezone.now().date(), self.global_settings.scheduled_start_time))
        clock_in_time = scheduled_datetime + timedelta(minutes=4)  # Within 5-minute grace period
        
        attendance = Attendance.objects.create(
            employee=self.employee,
            clock_in_time=clock_in_time,
            status='clocked_in',
            is_primary_clock_in=True
        )
        attendance.save()
        
        self.assertEqual(attendance.lateness, timedelta(0))
        self.assertEqual(attendance.lateness_deduction, Decimal('0.00'))
        self.assertTrue(attendance.lateness_calculated)

    def test_lateness_calculation_exceeds_grace_period(self):
        """
        Test that lateness and deductions are correctly calculated when clock-in exceeds the grace period.
        """
        scheduled_datetime = timezone.make_aware(datetime.combine(timezone.now().date(), self.global_settings.scheduled_start_time))
        clock_in_time = scheduled_datetime + timedelta(minutes=10)  # Exceeds 5-minute grace period
        
        attendance = Attendance.objects.create(
            employee=self.employee,
            clock_in_time=clock_in_time,
            status='clocked_in',
            is_primary_clock_in=True
        )
        attendance.save()
        
        expected_lateness = timedelta(minutes=10)
        expected_deduction = (Decimal(self.employee.per_day_rate) / Decimal('8.00') * 
                              (Decimal(self.lateness_deduction.deduction_duration.total_seconds()) / Decimal('3600'))).quantize(Decimal('0.01'))
        
        self.assertEqual(attendance.lateness, expected_lateness)
        self.assertEqual(attendance.lateness_deduction, expected_deduction)
        self.assertTrue(attendance.lateness_calculated)

    def test_holiday_handling_non_working(self):
        """
        Test that attendance on a non-recurring holiday is handled correctly.
        """
        # Assume today is the non-recurring holiday
        attendance_date = self.non_recurring_holiday.date
        clock_in_time = timezone.make_aware(datetime.combine(attendance_date, time(9, 0)))
        
        attendance = Attendance.objects.create(
            employee=self.employee,
            clock_in_time=clock_in_time,
            status='clocked_in',
            is_primary_clock_in=True
        )
        attendance.save()
        
        # Check that the holiday is correctly associated
        self.assertEqual(attendance.holiday, self.non_recurring_holiday)
        
        # Check total income calculation for special non-working holiday
        expected_income = (Decimal(self.employee.per_day_rate) / Decimal('8.00') * 
                           Decimal('8.00') * Decimal('1.3')).quantize(Decimal('0.01'))  # Assuming 8 hours worked
        self.assertEqual(attendance.total_income, expected_income)

    def test_holiday_handling_recurring_non_working(self):
        """
        Test that attendance on a recurring non-working holiday is handled correctly.
        """
        # Create attendance on a recurring holiday date
        holiday_date = datetime(2024, self.recurring_holiday.recurring_month, self.recurring_holiday.recurring_day).date()
        clock_in_time = timezone.make_aware(datetime.combine(holiday_date, time(9, 0)))
        
        attendance = Attendance.objects.create(
            employee=self.employee,
            clock_in_time=clock_in_time,
            status='clocked_in',
            is_primary_clock_in=True
        )
        attendance.save()
        
        # Check that the holiday is correctly associated
        self.assertEqual(attendance.holiday, self.recurring_holiday)
        
        # Check total income calculation for non-working holiday
        expected_income = Decimal(self.employee.per_day_rate)
        self.assertEqual(attendance.total_income, expected_income)

    def test_timezone_handling(self):
        """
        Test that timezone-aware times are handled correctly in attendance calculations.
        """
        # Assuming the application uses UTC
        scheduled_datetime = timezone.make_aware(datetime.combine(timezone.now().date(), self.global_settings.scheduled_start_time), timezone.utc)
        clock_in_time = scheduled_datetime + timedelta(minutes=6)  # Exceeds grace period
        
        attendance = Attendance.objects.create(
            employee=self.employee,
            clock_in_time=clock_in_time,
            status='clocked_in',
            is_primary_clock_in=True
        )
        attendance.save()
        
        expected_lateness = timedelta(minutes=6)
        expected_deduction = (Decimal(self.employee.per_day_rate) / Decimal('8.00') * 
                              (Decimal(self.lateness_deduction.deduction_duration.total_seconds()) / Decimal('3600'))).quantize(Decimal('0.01'))
        
        self.assertEqual(attendance.lateness, expected_lateness)
        self.assertEqual(attendance.lateness_deduction, expected_deduction)

    # -------------------------------
    # 3. Data Validation and Integrity
    # -------------------------------
    
    def test_negative_per_day_rate_validation(self):
        """
        Test that setting a negative per_day_rate raises a ValidationError.
        """
        self.employee.per_day_rate = -500
        with self.assertRaises(ValueError):
            self.employee.save()

    def test_default_values_on_attendance_creation(self):
        """
        Test that default values are correctly set when creating an Attendance record.
        """
        attendance = Attendance.objects.create(
            employee=self.employee
        )
        self.assertEqual(attendance.status, 'clocked_out')
        self.assertIsNone(attendance.clock_in_time)
        self.assertIsNone(attendance.clock_out_time)
        self.assertIsNone(attendance.break_start_time)
        self.assertIsNone(attendance.break_end_time)
        self.assertFalse(attendance.is_primary_clock_in)
        self.assertFalse(attendance.lateness_calculated)
        self.assertEqual(attendance.lateness_deduction, Decimal('0.00'))
        self.assertEqual(attendance.total_income, Decimal('0.00'))

    # -------------------------------
    # 4. Signal Handling and Automatic Actions
    # -------------------------------
    
    def test_signal_idempotency_on_user_save(self):
        """
        Test that saving a User multiple times does not create multiple Employee instances.
        """
        # Initial Employee creation via signal
        initial_employee_count = Employee.objects.filter(user=self.user).count()
        self.assertEqual(initial_employee_count, 1)
        
        # Save the user again
        self.user.save()
        
        # Ensure only one Employee exists
        employee_count_after_save = Employee.objects.filter(user=self.user).count()
        self.assertEqual(employee_count_after_save, 1)

    def test_signal_side_effects_on_user_creation(self):
        """
        Test that creating a User triggers the signal to create an Employee.
        """
        new_user = User.objects.create_user(
            username='anotheruser',
            email='anotheruser@example.com',
            password='anotherpassword'
        )
        employee = Employee.objects.get(user=new_user)
        self.assertIsNotNone(employee)
        self.assertEqual(employee.per_day_rate, 0)  # Assuming default per_day_rate is 0

    # -------------------------------
    # 5. Edge Cases and Unusual Scenarios
    # -------------------------------
    
    def test_overlapping_breaks(self):
        """
        Test that starting a new break while already on a break is handled appropriately.
        """
        now = timezone.now()
        attendance = Attendance.objects.create(
            employee=self.employee,
            clock_in_time=now,
            status='clocked_in',
            is_primary_clock_in=True
        )
        attendance.save()
        
        # Start first break
        attendance.break_start_time = now + timedelta(hours=1)
        attendance.status = 'on_break'
        attendance.save()
        self.assertEqual(attendance.status, 'on_break')
        
        # Attempt to start a second break without ending the first
        attendance.break_start_time = now + timedelta(hours=2)
        with self.assertRaises(ValueError):
            attendance.save()

    def test_clock_out_without_clock_in(self):
        """
        Test that clocking out without a prior clock-in raises an error or handles gracefully.
        """
        attendance = Attendance.objects.create(
            employee=self.employee,
            status='clocked_out',
            is_primary_clock_in=True
        )
        
        with self.assertRaises(ValueError):
            attendance.save()

    def test_missing_clock_out_time(self):
        """
        Test that total_hours is None if clock_out_time is missing.
        """
        now = timezone.now()
        attendance = Attendance.objects.create(
            employee=self.employee,
            clock_in_time=now,
            status='clocked_in',
            is_primary_clock_in=True
        )
        attendance.save()
        self.assertIsNone(attendance.total_hours)
    
    def test_missing_clock_in_time(self):
        """
        Test that total_hours is None if clock_in_time is missing.
        """
        attendance = Attendance.objects.create(
            employee=self.employee,
            clock_out_time=timezone.now(),
            status='clocked_out',
            is_primary_clock_in=True
        )
        attendance.save()
        self.assertIsNone(attendance.total_hours)

    def test_attendance_on_leap_day(self):
        """
        Test attendance handling on a leap day.
        """
        leap_day = datetime(2024, 2, 29).date()
        Holiday.objects.create(
            name="Leap Day",
            recurring_month=2,
            recurring_day=29,
            is_recurring=True,
            holiday_type='non_working'
        )
        
        clock_in_time = timezone.make_aware(datetime.combine(leap_day, time(9, 0)))
        
        attendance = Attendance.objects.create(
            employee=self.employee,
            clock_in_time=clock_in_time,
            status='clocked_in',
            is_primary_clock_in=True
        )
        attendance.save()
        
        # Check that the holiday is correctly associated
        associated_holiday = Holiday.objects.get(name="Leap Day")
        self.assertEqual(attendance.holiday, associated_holiday)
        self.assertEqual(attendance.total_income, Decimal('1000.00'))

    def test_attendance_on_end_of_month(self):
        """
        Test attendance handling on the last day of the month.
        """
        last_day = datetime(2023, 4, 30).date()
        clock_in_time = timezone.make_aware(datetime.combine(last_day, time(9, 0)))
        
        attendance = Attendance.objects.create(
            employee=self.employee,
            clock_in_time=clock_in_time,
            status='clocked_in',
            is_primary_clock_in=True
        )
        attendance.save()
        
        # No holiday set for this date
        self.assertIsNone(attendance.holiday)
        self.assertEqual(attendance.total_income, Decimal('0.00'))  # Assuming no work done

    # -------------------------------
    # 6. Performance and Scalability
    # -------------------------------
    
    def test_bulk_attendance_creation(self):
        """
        Test the performance and integrity when creating a large number of Attendance records.
        """
        num_records = 1000
        now = timezone.now()
        for i in range(num_records):
            Attendance.objects.create(
                employee=self.employee,
                clock_in_time=now + timedelta(minutes=i),
                status='clocked_in',
                is_primary_clock_in=(i == 0)  # Only the first record is primary
            )
        
        self.assertEqual(Attendance.objects.filter(employee=self.employee).count(), num_records)
        # Verify that only one primary clock-in exists
        primary_count = Attendance.objects.filter(employee=self.employee, is_primary_clock_in=True).count()
        self.assertEqual(primary_count, 1)

    # -------------------------------
    # 7. Security Considerations
    # -------------------------------
    
    def test_employee_data_access_permissions(self):
        """
        While comprehensive permission tests typically involve integration tests,
        here's a basic test to ensure that only authenticated users can access Employee data.
        """
        # This test would normally involve testing views or APIs.
        # Placeholder for actual permission tests.
        pass

    def test_attendance_data_integrity_after_exception(self):
        """
        Ensure that partial data changes are rolled back in case of an exception.
        """
        try:
            with transaction.atomic():
                Attendance.objects.create(
                    employee=self.employee,
                    clock_in_time=timezone.now(),
                    status='clocked_in',
                    is_primary_clock_in=True
                )
                # Force an exception
                raise ValueError("Forced exception to test rollback.")
        except ValueError:
            pass
        
        # Ensure that the Attendance record was not created
        self.assertEqual(Attendance.objects.filter(employee=self.employee).count(), 0)

    # -------------------------------
    # 8. Logging and Monitoring Tests
    # -------------------------------
    
    def test_logging_on_lateness_calculation(self):
        """
        Test that appropriate logging occurs during lateness calculation.
        Note: Requires configuring Django's logging to capture logs for testing.
        """
        import logging
        from unittest.mock import patch
        
        with patch('attendance.models.logger') as mock_logger:
            scheduled_datetime = timezone.make_aware(datetime.combine(timezone.now().date(), self.global_settings.scheduled_start_time))
            clock_in_time = scheduled_datetime + timedelta(minutes=10)
            
            attendance = Attendance.objects.create(
                employee=self.employee,
                clock_in_time=clock_in_time,
                status='clocked_in',
                is_primary_clock_in=True
            )
            attendance.save()
            
            # Check that a debug log was called for lateness calculation
            mock_logger.debug.assert_any_call(
                f"Lateness Calculated: {attendance.lateness}, Deduction: {attendance.lateness_deduction}"
            )

    # -------------------------------
    # 9. Utility Tests
    # -------------------------------
    
    def test_total_time_calculation_with_breaks(self):
        """
        Test that total_time is correctly calculated when there are break periods.
        """
        now = timezone.now()
        clock_in = now
        clock_out = now + timedelta(hours=8, minutes=30)  # 8.5 hours
        break_start = now + timedelta(hours=4)
        break_end = break_start + timedelta(minutes=30)
        
        attendance = Attendance.objects.create(
            employee=self.employee,
            clock_in_time=clock_in,
            break_start_time=break_start,
            break_end_time=break_end,
            clock_out_time=clock_out,
            status='clocked_out',
            is_primary_clock_in=True
        )
        attendance.save()
        
        expected_total_time = (clock_out - clock_in) - (break_end - break_start)
        self.assertEqual(attendance.total_time, expected_total_time)
        self.assertEqual(attendance.total_time_formatted, "08:00:00")

    def test_total_income_calculation_regular_day(self):
        """
        Test that total_income is correctly calculated on a regular working day.
        """
        now = timezone.now()
        clock_in = now
        clock_out = now + timedelta(hours=8)
        
        attendance = Attendance.objects.create(
            employee=self.employee,
            clock_in_time=clock_in,
            clock_out_time=clock_out,
            status='clocked_out',
            is_primary_clock_in=True
        )
        attendance.save()
        
        expected_income = Decimal('1000.00')  # 8 hours * 125 per hour
        self.assertEqual(attendance.total_income, expected_income)

    def test_total_income_with_lateness_deduction(self):
        """
        Test that total_income accounts for lateness deductions.
        """
        scheduled_datetime = timezone.make_aware(datetime.combine(timezone.now().date(), self.global_settings.scheduled_start_time))
        clock_in_time = scheduled_datetime + timedelta(minutes=10)  # 10 minutes late
        
        attendance = Attendance.objects.create(
            employee=self.employee,
            clock_in_time=clock_in_time,
            status='clocked_in',
            is_primary_clock_in=True
        )
        attendance.save()
        
        # Assuming per_day_rate is 1000, 8-hour workday, 15 minutes deduction
        per_hour_rate = Decimal('1000.00') / Decimal('8.00')  # 125.00
        deduction = per_hour_rate * (Decimal('15') / Decimal('60'))  # 125 * 0.25 = 31.25
        expected_income = Decimal('1000.00') - deduction
        self.assertEqual(attendance.lateness_deduction, deduction)
        self.assertEqual(attendance.total_income, expected_income)

    def test_attendance_on_non_working_holiday_without_clock_in(self):
        """
        Test income calculation when an employee does not clock in on a non-working holiday.
        """
        # Create attendance record without clock_in_time on a non-working holiday
        attendance_date = self.recurring_holiday.recurring_month, self.recurring_holiday.recurring_day
        attendance = Attendance.objects.create(
            employee=self.employee,
            status='clocked_out',
            is_primary_clock_in=True
        )
        attendance.save()
        
        # Check that total_income is set to per_day_rate
        self.assertEqual(attendance.total_income, Decimal('1000.00'))

    def test_total_time_formatted_property(self):
        """
        Test the total_time_formatted property for correct formatting.
        """
        now = timezone.now()
        clock_in = now
        clock_out = now + timedelta(hours=8, minutes=30)  # 8.5 hours
        break_start = now + timedelta(hours=4)
        break_end = break_start + timedelta(minutes=30)
        
        attendance = Attendance.objects.create(
            employee=self.employee,
            clock_in_time=clock_in,
            break_start_time=break_start,
            break_end_time=break_end,
            clock_out_time=clock_out,
            status='clocked_out',
            is_primary_clock_in=True
        )
        attendance.save()
        
        expected_total_time = timedelta(hours=8, minutes=0)  # 8.5 - 0.5 = 8 hours
        self.assertEqual(attendance.total_time, expected_total_time)
        self.assertEqual(attendance.total_time_formatted, "08:00:00")

    def test_lateness_formatted_property(self):
        """
        Test the lateness_formatted property for correct formatting.
        """
        now = timezone.now()
        scheduled_datetime = timezone.make_aware(datetime.combine(now.date(), self.global_settings.scheduled_start_time))
        clock_in_time = scheduled_datetime + timedelta(minutes=7)
        
        attendance = Attendance.objects.create(
            employee=self.employee,
            clock_in_time=clock_in_time,
            status='clocked_in',
            is_primary_clock_in=True
        )
        attendance.save()
        
        self.assertEqual(attendance.lateness_formatted, "00:07:00")

    def test_lateness_deduction_amount_property(self):
        """
        Test the lateness_deduction_amount property for correct formatting.
        """
        now = timezone.now()
        scheduled_datetime = timezone.make_aware(datetime.combine(now.date(), self.global_settings.scheduled_start_time))
        clock_in_time = scheduled_datetime + timedelta(minutes=10)
        
        attendance = Attendance.objects.create(
            employee=self.employee,
            clock_in_time=clock_in_time,
            status='clocked_in',
            is_primary_clock_in=True
        )
        attendance.save()
        
        expected_deduction = Decimal('31.25')  # 1000/8 * 0.25
        self.assertEqual(attendance.lateness_deduction, expected_deduction)
        self.assertEqual(attendance.lateness_deduction_amount, "Php 31.25")


# -------------------------------
# 10. Additional Test Cases (Optional)
# -------------------------------

# Depending on your application's complexity, you might want to add more tests such as:
# - Testing form validations if you have forms for Attendance.
# - Testing API endpoints using Django REST Framework's APITestCase.
# - Testing frontend interactions using Selenium or similar tools.
# - Testing batch processing or management commands if any.
# - Testing permissions and access controls in views or APIs.

# These are typically covered in separate test files or classes.
