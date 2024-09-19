# billing/views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from employees.models import Employee
from attendance.models import Attendance
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
import json
from decimal import Decimal

@login_required
def billing_dashboard(request):
    employee = Employee.objects.get(user=request.user)
    per_day_rate = employee.per_day_rate or Decimal('0.00')
    standard_hours_per_day = Decimal('8.0')

    # Annotate attendance records with income
    attendance_records = Attendance.objects.filter(employee=employee).annotate(
        income=ExpressionWrapper(
            F('total_income'),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )
    )

    # Total income including all closed attendances
    total_income = attendance_records.aggregate(
        total_income=Sum('income')
    )['total_income'] or Decimal('0.00')

    # Current session income
    open_attendance = Attendance.objects.filter(employee=employee, clock_out_time__isnull=True).first()
    is_clocked_in = open_attendance and open_attendance.status == 'clocked_in'
    clock_in_time = open_attendance.clock_in_time if is_clocked_in else None
    is_on_break = open_attendance.status == 'on_break' if open_attendance else False

    current_session_income = Decimal('0.00')
    if is_clocked_in and clock_in_time:
        elapsed_seconds = (timezone.now() - clock_in_time).total_seconds()
        elapsed_hours = Decimal(elapsed_seconds / 3600).quantize(Decimal('0.0001'))
        current_session_income = (per_day_rate / standard_hours_per_day) * elapsed_hours
        # No need to use max here; allow negative values
        current_session_income = current_session_income.quantize(Decimal('0.01'))

    # Income per day (last 30 days)
    today = timezone.now().date()
    one_month_ago = today - timedelta(days=30)
    recent_records = attendance_records.filter(clock_in_time__date__gte=one_month_ago)

    income_per_day = recent_records.annotate(
        date=TruncDate('clock_in_time')
    ).values('date').annotate(
        daily_income=Sum('income')
    ).order_by('date')

    # Income per week
    income_per_week = recent_records.annotate(
        week=TruncWeek('clock_in_time')
    ).values('week').annotate(
        weekly_income=Sum('income')
    ).order_by('week')

    # Income per month
    income_per_month = attendance_records.annotate(
        month=TruncMonth('clock_in_time')
    ).values('month').annotate(
        monthly_income=Sum('income')
    ).order_by('month')

    # Prepare data for JavaScript
    js_data = json.dumps({
        'clock_in_time': clock_in_time.isoformat() if clock_in_time else None,
        'per_day_rate': float(per_day_rate),
        'standard_hours_per_day': float(standard_hours_per_day),
        'is_on_break': is_on_break,
    })

    context = {
        'attendance_records': attendance_records,
        'total_income': total_income,
        'current_session_income': current_session_income,
        'income_per_day': income_per_day,
        'income_per_week': income_per_week,
        'income_per_month': income_per_month,
        'is_clocked_in': is_clocked_in,
        'clock_in_time': clock_in_time,
        'is_on_break': is_on_break,
        'per_day_rate': per_day_rate,
        'standard_hours_per_day': standard_hours_per_day,
        'js_data': js_data,
    }

    return render(request, 'billing/dashboard.html', context)
