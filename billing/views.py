# billing/views.py

from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.forms import inlineformset_factory
from django.template.loader import get_template, render_to_string
from weasyprint import HTML
from django.core.mail import send_mail, EmailMessage
from django.utils.html import strip_tags
from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from decimal import Decimal
import json
from datetime import timedelta

from employees.models import Employee
from attendance.models import Attendance
from holidays.models import Holiday
from .models import BillingRecord, Invoice, InvoiceItem
from .forms import InvoiceForm





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

            # Set the total_amount before saving
            invoice.total_amount = amount if amount > 0 else Decimal('0.00')
            invoice.save()  # Now save the invoice with the total_amount

            # Create the InvoiceItem only if there's a valid quantity and rate
            if quantity > 0 and rate > 0:
                InvoiceItem.objects.create(
                    invoice=invoice,
                    description=description,
                    quantity=quantity,
                    rate=rate,
                    amount=amount
                )

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

    # Use the existing template path for generating the PDF
    template_path = 'billing/shareable_invoice.html'
    context = {'invoice': invoice}

    # Render the HTML template with context
    template = get_template(template_path)
    html = template.render(context)

    # Remove the '{% extends 'base.html' %}' dynamically, if needed
    html = html.replace("{% extends 'base.html' %}", "")

    # Create a HttpResponse object with PDF headers
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="invoice_{invoice.id}.pdf"'

    # Convert HTML to PDF using WeasyPrint
    HTML(string=html).write_pdf(response)

    return response



def email_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id) 
    subject = f'Invoice #{invoice.invoice_number} from {settings.DEFAULT_FROM_EMAIL}' 
    html_message = render_to_string('billing/shareable_invoice.html', {'invoice': invoice})
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = [invoice.client.email]  # Assuming 'client' is a field in the Invoice model
    email = EmailMessage(
        subject,            
        html_message,       
        from_email,         
        to_email            
    )
    
    email.content_subtype = "html"
    
    try:
        email.send()
        messages.success(request, f"Invoice #{invoice.invoice_number} has been sent to {invoice.client.email}")
    except Exception as e:
        messages.error(request, f"Error sending invoice: {str(e)}")
    
    return redirect('invoice_list')



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