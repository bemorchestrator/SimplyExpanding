from django.urls import path
from . import views

urlpatterns = [
    path('authenticate/', views.authenticate_user, name='authenticate_user'),
    path('data/', views.search_console_data, name='search_console_data'),
]
