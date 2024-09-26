# home/urls.py

from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.home_view, name='home'),  # Login view at the root URL
    path('logout/', views.logout_view, name='logout'),
    path('totp-verification/', views.totp_verification, name='totp_verification'),
    path('enable-2fa/', views.enable_2fa, name='enable_2fa'),
    path('test-svg/', views.test_svg, name='test_svg'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
