# home/views.py

from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from employees.models import Employee
import pyotp
import qrcode
from io import BytesIO
import base64

def home_view(request):
    """
    Handles user login and redirects based on 2FA status.
    """
    if request.user.is_authenticated:
        # If user is already TOTP-verified, redirect to profile
        if request.session.get('totp_verified', False):
            return redirect('employees:employee_profile')  # Namespaced URL

        # If user is authenticated but not TOTP-verified, redirect to TOTP verification
        return redirect('home:totp_verification')

    # Handle normal username and password login
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            request.session['totp_verified'] = False  # Require TOTP after login

            # Check if the user has 2FA enabled
            try:
                employee = Employee.objects.get(user=user)
                if employee.totp_secret:
                    return redirect('home:totp_verification')  # Redirect to TOTP verification
                else:
                    messages.success(request, 'Logged in successfully.')
                    return redirect('employees:employee_profile')  # Redirect directly to profile
            except Employee.DoesNotExist:
                messages.error(request, 'Employee profile not found.')
                logout(request)
                return redirect('home:home')  # Redirect back to login
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()

    return render(request, 'home/home.html', {'form': form})


def logout_view(request):
    """
    Handles user logout.
    """
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('home:home')  # Redirect to your home or login page after logout


@login_required
def totp_verification(request):
    """
    Handles TOTP code verification after user login.
    """
    if request.method == 'POST':
        totp_code = request.POST.get('totp_code')
        try:
            employee = Employee.objects.get(user=request.user)
            totp = pyotp.TOTP(employee.totp_secret)
            if totp.verify(totp_code):
                request.session['totp_verified'] = True  # Mark as verified
                messages.success(request, 'Two-Factor Authentication verified successfully.')
                return redirect('employees:employee_profile')  # Redirect to the existing profile view
            else:
                messages.error(request, 'Invalid TOTP code. Please try again.')
        except Employee.DoesNotExist:
            messages.error(request, 'Employee profile not found.')
            logout(request)
            return redirect('home:home')  # Redirect back to login if profile not found

    return render(request, 'home/totp_verification.html')


@login_required
def enable_2fa(request):
    """
    Enables Two-Factor Authentication for the authenticated user.
    Generates a temporary TOTP secret, displays a QR code, and verifies the TOTP code entered by the user.
    Only after successful verification is the TOTP secret saved to the Employee model.
    """
    user = request.user
    employee, created = Employee.objects.get_or_create(user=user)

    if request.method == 'POST':
        # User has submitted the TOTP code for verification
        totp_code = request.POST.get('totp_code')
        temp_secret = request.session.get('temp_totp_secret')

        if not temp_secret:
            messages.error(request, 'Temporary TOTP secret not found. Please try enabling 2FA again.')
            return redirect('home:enable_2fa')

        totp = pyotp.TOTP(temp_secret)
        if totp.verify(totp_code):
            # Verification successful; save the TOTP secret
            employee.totp_secret = temp_secret
            employee.save()
            # Remove the temporary secret from the session
            del request.session['temp_totp_secret']
            messages.success(request, 'Two-Factor Authentication has been enabled successfully.')
            return redirect('employees:employee_profile')
        else:
            messages.error(request, 'Invalid TOTP code. Please try again.')

    else:
        # GET request; generate a temporary TOTP secret and QR code
        if not employee.totp_secret:
            # Generate a new temporary TOTP secret
            temp_secret = pyotp.random_base32()
            request.session['temp_totp_secret'] = temp_secret

            # Generate the provisioning URI for the authenticator app
            totp = pyotp.TOTP(temp_secret)
            provisioning_uri = totp.provisioning_uri(name=user.email, issuer_name="YourAppName")

            # Generate QR code in PNG format
            img = qrcode.make(provisioning_uri)
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            qr_png = base64.b64encode(buffer.getvalue()).decode()

            # Create data URI for embedding the image
            qr_data_uri = f"data:image/png;base64,{qr_png}"

            context = {
                'qr_data_uri': qr_data_uri,
            }

            return render(request, 'home/enable_2fa.html', context)
        else:
            messages.info(request, 'Two-Factor Authentication is already enabled.')
            return redirect('employees:employee_profile')


@login_required
def test_svg(request):
    """
    A test view for rendering SVG content.
    """
    svg_content = '<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">' \
                  '<circle cx="50" cy="50" r="40" stroke="green" stroke-width="4" fill="yellow" /></svg>'
    return render(request, 'home/test_svg.html', {'svg_content': svg_content})
