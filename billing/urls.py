from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.billing_dashboard, name='billing_dashboard'),
]
