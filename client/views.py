from django.shortcuts import render, redirect
from .forms import ClientOnboardingForm
from .models import ClientOnboarding
from django.contrib import messages
from django.db.models import Q  # For search queries


# View to handle the client onboarding form
def client_onboarding_view(request):
    if request.method == 'POST':
        # If the form is submitted, populate the form with POST data
        form = ClientOnboardingForm(request.POST)
        if form.is_valid():
            # Save the form data to the database
            form.save()
            # Optional: Add a success message
            messages.success(request, 'Client onboarding information submitted successfully.')
            # Redirect to a success page or another page after form submission
            return redirect('onboarding_success')  # Adjust the URL name to your success page
    else:
        # Display an empty form if the request is GET
        form = ClientOnboardingForm()

    # Render the form in the template
    return render(request, 'client/client_onboarding.html', {'form': form})


# View to handle the success page after onboarding form submission
def onboarding_success_view(request):
    return render(request, 'client/onboarding_success.html')


from django.db.models import Q
from django.shortcuts import render
from .models import ClientOnboarding

def client_list_view(request):
    # Get the search query from the request
    query = request.GET.get('search')
    
    # Get the view mode from the request (either 'table' or 'grid')
    view_mode = request.GET.get('view', 'grid')

    # If a search query exists, filter the clients based on the query
    if query:
        clients = ClientOnboarding.objects.filter(
            Q(business_name__icontains=query) |
            Q(business_description__icontains=query) |
            Q(contact_person__icontains=query) |
            Q(email__icontains=query) |
            Q(phone_number__icontains=query)
        )
    else:
        # If no search query, display all clients
        clients = ClientOnboarding.objects.all()

    # Define the headers list
    headers = [
        'Business Name', 'Business Description', 'Website URL', 'Contact Person',
        'Email', 'Phone Number', 'Business Goals', 'Target Keywords',
        'Competitor URLs', 'G4A Login', 'Google Search Console Login',
        'Tag Manager Login', 'Website Login', 'CMS Type', 'Start Date', 'End Date'
    ]

    # Render the client list template with the clients, headers, and the current view mode
    context = {
        'clients': clients,
        'headers': headers,
        'view_mode': view_mode,  # Pass the view mode to the template
    }

    return render(request, 'client/client_list.html', context)

