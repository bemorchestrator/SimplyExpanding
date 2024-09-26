from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

app_name = 'employees'

urlpatterns = [
    path('profile/', views.employee_profile, name='employee_profile'),
    path('profile/settings/', views.profile_settings, name='profile_settings'),
    path('profile/disable-2fa/', views.disable_2fa, name='disable_2fa'),
    
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
