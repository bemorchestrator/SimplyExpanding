from django.urls import path
from . import views
from .views import client_list_view

urlpatterns = [
    path('onboarding/', views.client_onboarding_view, name='client_onboarding'),
    path('onboarding/success/', views.onboarding_success_view, name='onboarding_success'),
    path('clients/', client_list_view, name='client_list'),
    path('clients/update/<int:pk>/', views.client_update_view, name='client_update'),
]
