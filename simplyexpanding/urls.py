from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    # Admin and home URLs
    path('admin/', admin.site.urls),
    path('', include('home.urls', namespace='home')),

    # Authentication URLs
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='home/password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='home/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='home/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='home/password_reset_complete.html'), name='password_reset_complete'),

    # App-specific URLs
    path('employees/', include('employees.urls', namespace='employees')),
    path('attendance/', include('attendance.urls')),
    path('billing/', include('billing.urls')),
    path('holidays/', include('holidays.urls')), 
    path('client/', include('client.urls')),
    path('search_console/', include('search_console.urls')),
    path('analytics/', include('analytics.urls')),
    path('payroll/', include('payroll.urls')),
    path('audit/', include('audit.urls')),
    path('keywords/', include('keywords.urls')),
    path('report/', include('report.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
