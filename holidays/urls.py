# holidays/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.holiday_list, name='holiday_list'),                    # List all holidays
    path('add/', views.add_holiday, name='add_holiday'),                  # Form to add a new holiday
    path('delete/<int:holiday_id>/', views.delete_holiday, name='delete_holiday'),  # Delete a holiday
]
