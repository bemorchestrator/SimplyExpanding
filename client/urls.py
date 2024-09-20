# client/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('onboarding/', views.client_onboarding, name='client_onboarding'),
    path('onboarding/success/', views.onboarding_success, name='client_onboarding_success'),
]
