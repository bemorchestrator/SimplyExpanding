# billing/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from employees.models import Employee
from attendance.models import Attendance
from holidays.models import Holiday
from .models import BillingRecord
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
import json
from decimal import Decimal
from django.shortcuts import render
from .models import Invoice
from .forms import InvoiceForm
from django.contrib import messages
from django.shortcuts import get_object_or_404, HttpResponse
from .models import Invoice
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.forms import inlineformset_factory
from .models import Invoice, InvoiceItem




@login_required
def billing_dashboard(request):
    # Get the Employee instance for the logged-in user
    employee = Employee.objects.get(user=request.user)
    per_day_rate = employee.per_day_rate or Decimal('0.00')
    standard_hours_per_day = Decimal('8.0')  # Standard 8-hour workday assumption

    # Fetch and annotate attendance records with the calculated income
    attendance_records = Attendance.objects.filter(employee=employee).annotate(
        income=ExpressionWrapper(
            F('total_income'),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )
    )

    # Total income from closed (clocked out) attendance records
    total_income = attendance_records.aggregate(
        total_income=Sum('income')
    )['total_income'] or Decimal('0.00')

    # Check if today is a non-working holiday and if the employee has not clocked in
    today = timezone.now().date()
    holiday = Holiday.objects.filter(
        date=today,
        holiday_type='non_working'
    ).first()

    if holiday:
        # Check if the employee has clocked in for today
        attendance_today = Attendance.objects.filter(
            employee=employee,
            clock_in_time__date=today
        ).exists()

        if not attendance_today:
            # Automatically add holiday compensation if no attendance record exists for today
            total_income += per_day_rate
            # Create a billing record for this holiday compensation
            BillingRecord.objects.create(
                employee=employee,
                total_income=per_day_rate
            )

    # Handle current session income if the employee is clocked in
    open_attendance = Attendance.objects.filter(employee=employee, clock_out_time__isnull=True).first()
    is_clocked_in = open_attendance and open_attendance.status == 'clocked_in'
    clock_in_time = open_attendance.clock_in_time if is_clocked_in else None
    is_on_break = open_attendance.status == 'on_break' if open_attendance else False

    current_session_income = Decimal('0.00')
    if is_clocked_in and clock_in_time:
        # Calculate the income for the current session
        elapsed_seconds = (timezone.now() - clock_in_time).total_seconds()
        elapsed_hours = Decimal(elapsed_seconds / 3600).quantize(Decimal('0.0001'))
        current_session_income = (per_day_rate / standard_hours_per_day) * elapsed_hours
        current_session_income = current_session_income.quantize(Decimal('0.01'))

    # Income per day for the last 30 days
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

    # Prepare JavaScript data
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




def invoice_list(request):
    invoices = Invoice.objects.all().order_by('-invoice_date')
    context = {
        'invoices': invoices,
    }
    return render(request, 'billing/invoice_list.html', context)


def create_invoice(request):
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.save()  # Save the invoice to get an ID

            # Retrieve Invoice Item data from POST request
            description = request.POST.get('description')
            quantity = request.POST.get('quantity')
            rate = request.POST.get('rate')

            # Convert quantity and rate to appropriate types
            try:
                quantity = int(quantity)
            except (TypeError, ValueError):
                quantity = 0

            try:
                rate = float(rate)
            except (TypeError, ValueError):
                rate = 0.0

            amount = quantity * rate

            # Create an InvoiceItem instance
            InvoiceItem.objects.create(
                invoice=invoice,
                description=description,
                quantity=quantity,
                rate=rate,
                amount=amount
            )

            # Update the total amount of the invoice
            invoice.total_amount = amount
            invoice.save()

            messages.success(request, 'Invoice created successfully.')
            return redirect('invoice_list')  # Adjust the redirect URL as needed
        else:
            messages.error(request, 'There were errors in the form submission.')
    else:
        form = InvoiceForm()

    return render(request, 'billing/invoice_form.html', {
        'form': form,
        'is_edit': False,
        'invoice_item_data': {}  # Empty dict for consistency
    })
# Create an inline formset for handling Invoice Items
InvoiceItemFormSet = inlineformset_factory(Invoice, InvoiceItem, fields=('description', 'quantity', 'rate'), extra=1, can_delete=True)

def edit_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)

    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.save()

            # Retrieve Invoice Item data from POST request
            description = request.POST.get('description')
            quantity = request.POST.get('quantity')
            rate = request.POST.get('rate')

            # Convert quantity and rate to appropriate types
            try:
                quantity = int(quantity)
            except (TypeError, ValueError):
                quantity = 0

            try:
                rate = float(rate)
            except (TypeError, ValueError):
                rate = 0.0

            amount = quantity * rate

            # Update or create the InvoiceItem
            invoice_item, created = InvoiceItem.objects.update_or_create(
                invoice=invoice,
                defaults={
                    'description': description,
                    'quantity': quantity,
                    'rate': rate,
                    'amount': amount
                }
            )

            # Update the total amount of the invoice
            invoice.total_amount = amount
            invoice.save()

            messages.success(request, 'Invoice updated successfully.')
            return redirect('invoice_list')
        else:
            messages.error(request, 'There were errors in the form submission.')
    else:
        form = InvoiceForm(instance=invoice)
        # Load existing InvoiceItem data to pre-fill the form
        invoice_item = InvoiceItem.objects.filter(invoice=invoice).first()
        if invoice_item:
            invoice_item_data = {
                'description': invoice_item.description,
                'quantity': invoice_item.quantity,
                'rate': invoice_item.rate,
                'amount': invoice_item.amount
            }
        else:
            invoice_item_data = {}

    return render(request, 'billing/invoice_form.html', {
        'form': form,
        'is_edit': True,
        'invoice': invoice,
        'invoice_item_data': invoice_item_data
    })



def mark_invoice_paid(request, id):
    # Retrieve the invoice object
    invoice = get_object_or_404(Invoice, id=id)

    # Update the invoice status
    invoice.status = 'paid'
    invoice.save()

    # Provide feedback to the user
    messages.success(request, 'Invoice marked as paid successfully.')
    return redirect('invoice_list')  # Adjust the redirect as needed


def share_invoice(request, id):
    # Retrieve the invoice object
    invoice = get_object_or_404(Invoice, id=id)

    # Pass the invoice object to the template context
    context = {
        'invoice': invoice
    }

    # Render the 'shareable_invoice.html' template
    return render(request, 'billing/shareable_invoice.html', context)



def generate_invoice_pdf(request, id):
    # Retrieve the invoice object
    invoice = get_object_or_404(Invoice, id=id)

    # Create a HttpResponse object with PDF headers
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="invoice_{invoice.id}.pdf"'

    # Create the PDF object using ReportLab
    pdf = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    # Set up the basic structure of the PDF
    pdf.setTitle(f"Invoice {invoice.id}")
    pdf.drawString(100, height - 50, f"Invoice #{invoice.invoice_number}")
    pdf.drawString(100, height - 70, f"Client: {invoice.client_name or invoice.client.business_name}")
    pdf.drawString(100, height - 90, f"Date: {invoice.invoice_date.strftime('%B %d, %Y')}")
    pdf.drawString(100, height - 110, f"Due Date: {invoice.due_date.strftime('%B %d, %Y')}")

    # Draw items header
    pdf.drawString(100, height - 150, "Description")
    pdf.drawString(300, height - 150, "Quantity")
    pdf.drawString(400, height - 150, "Rate")
    pdf.drawString(500, height - 150, "Amount")

    # Draw each item line by line
    y_position = height - 170
    for item in invoice.items.all():
        pdf.drawString(100, y_position, item.description)
        pdf.drawString(300, y_position, str(item.quantity))
        pdf.drawString(400, y_position, f"{item.rate:.2f}")
        pdf.drawString(500, y_position, f"{item.amount:.2f}")
        y_position -= 20

    # Draw the total amount
    pdf.drawString(400, y_position - 20, "Total:")
    pdf.drawString(500, y_position - 20, f"{invoice.total_amount:.2f}")

    # Finalize the PDF
    pdf.showPage()
    pdf.save()

    return response



def delete_invoice(request, id):
    # Retrieve the invoice object by its ID
    invoice = get_object_or_404(Invoice, id=id)

    # Store the invoice number before deletion
    invoice_number = invoice.invoice_number

    # Delete the invoice
    invoice.delete()

    # Display a success message
    messages.success(request, f'Invoice #{invoice_number} has been deleted successfully.')

    # Redirect to the invoice list view (adjust the redirect URL as needed)
    return redirect('invoice_list')