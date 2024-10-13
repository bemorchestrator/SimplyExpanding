from django.urls import path
from . import views

urlpatterns = [
    path('', views.payroll_dashboard, name='payroll_dashboard'),
    path('process/<int:payroll_id>/', views.process_payroll, name='process_payroll'),
    path('initiate/<int:employee_id>/<str:pay_period_start>/<str:pay_period_end>/', 
         views.initiate_payroll, name='initiate_payroll'),
    path('employee-dashboard/', views.employee_payroll_dashboard, name='employee_dashboard'),
    path('download-payslip/<int:payroll_id>/', views.download_payslip, name='download_payslip'),
    path('edit-payslip/<int:payroll_id>/', views.edit_payslip, name='edit_payslip'),
    path('preview-payslip/<int:payroll_id>/', views.preview_payslip, name='preview_payslip'),
    path('confirm-payslip/<int:payroll_id>/', views.confirm_payslip, name='confirm_payslip'),
]
