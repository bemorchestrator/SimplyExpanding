# attendance/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('clock_in_out/', views.clock_in_out_page, name='clock_in_out_page'),
    path('clock_in/', views.clock_in, name='clock_in'),
    path('clock_out/', views.clock_out, name='clock_out'),
    path('start_break/', views.start_break, name='start_break'),
    path('end_break/', views.end_break, name='end_break'),
    path('', views.attendance_dashboard, name='attendance_dashboard'),
]
