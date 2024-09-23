from django.urls import path
from . import views

urlpatterns = [
    path('ga4/authenticate/', views.authenticate_ga4, name='authenticate_ga4'),
    path('ga4/data/', views.fetch_ga4_data, name='fetch_ga4_data'),
]
