# urls.py

from django.urls import path
from . import views
from .views import populate_audit_dashboard_with_search_console_data

urlpatterns = [
    path('upload/', views.upload_file, name='upload_file'),  # For uploading files
    path('results/', views.audit_result, name='audit_result'),  # A placeholder for showing results
    path('crawl-sitemaps/', views.crawl_sitemaps, name='crawl_sitemaps'),  # For crawling sitemaps
    path('dashboard/', views.audit_dashboard, name='audit_dashboard'),
    path('delete-uploaded-files/', views.delete_uploaded_files, name='delete_uploaded_files'),
    path('update-action-choice/', views.update_action_choice, name='update_action_choice'),  # New URL for updating actions
    path('sitemaps/delete/<int:sitemap_id>/', views.delete_sitemap, name='delete_sitemap'),
    path('fetch-data/', populate_audit_dashboard_with_search_console_data, name='fetch_search_console_data'),

]
