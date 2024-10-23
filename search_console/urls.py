# search_console/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('data/', views.search_console_data, name='search_console_data'),
    
]
