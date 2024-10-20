# keywords/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_keyword_dashboard, name='create_keyword_dashboard'),
    path('save/<int:dashboard_id>/', views.save_keyword_dashboard, name='save_keyword_dashboard'),
    path('load/<int:id>/', views.load_keyword_dashboard, name='load_keyword_dashboard'),
    path('delete/<int:id>/', views.delete_keyword_dashboard, name='delete_keyword_dashboard'),
    path('list/', views.list_keyword_dashboards, name='list_keyword_dashboard'),
    path('update-field/', views.update_field, name='update_field'),  # AJAX URL
]
