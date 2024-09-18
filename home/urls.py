from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),  # Home is also the login page
    path('logout/', views.logout_view, name='logout'),
]
