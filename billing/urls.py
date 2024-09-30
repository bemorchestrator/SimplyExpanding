# billing/urls.py

from django.urls import path
from . import views
from .views import invoice_list
from .views import invoice_list, edit_invoice, create_invoice, mark_invoice_paid, share_invoice, generate_invoice_pdf, delete_invoice


urlpatterns = [
    path('dashboard/', views.billing_dashboard, name='billing_dashboard'),
    path('invoices/', invoice_list, name='invoice_list'),
    path('invoices/create/', create_invoice, name='create_client_invoice'),
    path('invoices/edit/<int:invoice_id>/', edit_invoice, name='edit_client_invoice'),
    path('invoices/<int:id>/mark-paid/', mark_invoice_paid, name='mark_invoice_paid'),
    path('invoices/<int:id>/share/', share_invoice, name='share_invoice'),
    path('invoices/<int:id>/generate-pdf/', generate_invoice_pdf, name='generate_invoice_pdf'),
    path('invoices/<int:id>/delete/', delete_invoice, name='delete_invoice'),
    path('email-invoice/<int:invoice_id>/', views.email_invoice, name='email_invoice'),

]
