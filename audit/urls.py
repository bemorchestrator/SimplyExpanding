# urls.py
from django.urls import path
from . import views
from .views import populate_audit_dashboard_with_search_console_data

urlpatterns = [
    path('upload/', views.upload_file, name='upload_file'),  # For uploading files
    path('results/', views.audit_result, name='audit_result'),  # A placeholder for showing results
    path('crawl-sitemaps/', views.crawl_sitemaps, name='crawl_sitemaps'),  # For crawling sitemaps
    path('dashboard/', views.audit_dashboard, name='audit_dashboard'),
    
    # Delete Uploaded Files
    path('delete-uploaded-files/', views.delete_uploaded_files, name='delete_uploaded_files'),  # Delete all unsaved files
    path('delete-uploaded-files/<int:dashboard_id>/', views.delete_uploaded_files, name='delete_uploaded_files_with_id'),  # Delete files for specific dashboard
    
    path('update-action-choice/', views.update_action_choice, name='update_action_choice'),  # New URL for updating actions
    path('update-category/', views.update_category, name='update_category'),
    path('sitemaps/delete/<int:sitemap_id>/', views.delete_sitemap, name='delete_sitemap'),
    path('fetch-data/', populate_audit_dashboard_with_search_console_data, name='fetch_search_console_data'),
    path('save-audit-dashboard/', views.save_audit_dashboard, name='save_audit_dashboard'),
    
    path('list-dashboard/', views.list_dashboard, name='list_dashboard'),  # Removed duplicate
    
    path('load-dashboard/<int:id>/', views.load_dashboard, name='load_dashboard'),
    path('delete-dashboard/<int:id>/', views.delete_dashboard, name='delete_dashboard'),
    path('generate-share-link/<int:id>/', views.generate_shareable_link, name='generate_shareable_link'),
    path('shared-dashboard/<str:share_token>/', views.shared_dashboard, name='shared_dashboard'),
]
