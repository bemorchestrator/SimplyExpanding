from django.urls import path
from . import views

urlpatterns = [
    # Route for listing clients
    path('clients/', views.client_list, name='client_list'),
    
    # Client portal, accessible using client_id
    path('portal/<int:client_id>/', views.client_portal, name='client_portal'),

    # URLs for individual reports
    path('google-search-console/<int:client_id>/', views.google_search_console_report, name='google_search_console_report'),
    path('google-analytics/<int:client_id>/', views.google_analytics_report, name='google_analytics_report'),
    path('keyword-research/<int:client_id>/', views.keyword_research_report, name='keyword_research_report'),
    path('website-audit/<int:client_id>/', views.website_audit_report, name='website_audit_report'),
]
