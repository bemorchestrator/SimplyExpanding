from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from employees.models import Employee
from attendance.models import Attendance
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
import json  # Import json module

@login_required
def billing_dashboard(request):
    employee = Employee.objects.get(user=request.user)
    per_day_rate = employee.per_day_rate or 0.00
    standard_hours_per_day = 8.0

    # Annotate attendance records with income
    attendance_records = Attendance.objects.filter(employee=employee).annotate(
        income=ExpressionWrapper(
            (F('total_hours') / standard_hours_per_day) * per_day_rate,
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )
    )

    # Total income
    total_income = attendance_records.aggregate(
        total_income=Sum('income')
    )['total_income'] or 0.00

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

    # Check if employee is clocked in
    open_attendance = Attendance.objects.filter(employee=employee, clock_out_time__isnull=True).first()
    is_clocked_in = open_attendance and open_attendance.status == 'clocked_in'
    clock_in_time = open_attendance.clock_in_time if is_clocked_in else None
    is_on_break = open_attendance.status == 'on_break' if open_attendance else False

    # Prepare data for JavaScript
    js_data = json.dumps({
        'clock_in_time': clock_in_time.isoformat() if clock_in_time else None,
        'per_day_rate': float(per_day_rate),
        'standard_hours_per_day': standard_hours_per_day,
        'is_on_break': is_on_break,
    })

    context = {
        'attendance_records': attendance_records,
        'total_income': total_income,
        'income_per_day': income_per_day,
        'income_per_week': income_per_week,
        'income_per_month': income_per_month,
        'is_clocked_in': is_clocked_in,
        'clock_in_time': clock_in_time,
        'is_on_break': is_on_break,
        'per_day_rate': per_day_rate,
        'standard_hours_per_day': standard_hours_per_day,
        'js_data': js_data,  # Pass the serialized data to the template
    }

    return render(request, 'billing/dashboard.html', context)
