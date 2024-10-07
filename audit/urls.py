from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_file, name='upload_file'),  # For uploading files
    path('results/', views.audit_result, name='audit_result'),  # A placeholder for showing results
    path('crawl-sitemaps/', views.crawl_sitemaps, name='crawl_sitemaps'),  # For crawling sitemaps
    path('dashboard/', views.audit_dashboard, name='audit_dashboard'),
    path('delete-uploaded-files/', views.delete_uploaded_files, name='delete_uploaded_files'),
]
