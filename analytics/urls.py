# analytics/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('ga4/data/', views.fetch_ga4_data, name='fetch_ga4_data'),
    path('ga4/properties/', views.get_ga4_properties, name='get_ga4_properties'),
    path('ga4/search_properties/', views.search_properties, name='search_properties'),

]
