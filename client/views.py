# client/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Client
from .forms import ClientForm

def client_onboarding(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save()
            messages.success(request, 'Client onboarded successfully!')
            return redirect('client_onboarding_success')  # Redirect to the success page
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ClientForm()

    return render(request, 'client/client_onboarding.html', {'form': form})

def onboarding_success(request):
    return render(request, 'client/onboarding_success.html')
