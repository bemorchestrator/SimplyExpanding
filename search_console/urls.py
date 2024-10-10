# search_console/urls.py

from django.urls import path
from . import views
from google_auth import authenticate_user, oauth2_callback

urlpatterns = [
    path('authenticate/', authenticate_user, {'service': 'search_console'}, name='authenticate_search_console'),
    path('oauth2/callback/', oauth2_callback, {'service': 'search_console'}, name='search_console_oauth2_callback'),
    path('data/', views.search_console_data, name='search_console_data'),
]
