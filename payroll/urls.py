# urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.payroll_dashboard, name='payroll_dashboard'),
    path('process/<int:payroll_id>/', views.process_payroll, name='process_payroll'),
    path('initiate/<int:employee_id>/<str:pay_period_start>/<str:pay_period_end>/', views.initiate_payroll, name='initiate_payroll'),
]
