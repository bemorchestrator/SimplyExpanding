# views.py

from django.shortcuts import render, redirect, get_object_or_404
from .forms import ClientOnboardingForm
from .models import ClientOnboarding
from django.contrib import messages
from django.db.models import Q
from .models import ClientOnboarding

# View to handle the client onboarding form (Create)
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

    # Render the form in the template with 'action' context for dynamic form behavior
    return render(request, 'client/client_onboarding.html', {'form': form, 'action': 'Create'})


# View to handle updating an existing client
def client_update_view(request, pk):
    # Retrieve the client instance or return 404 if not found
    client = get_object_or_404(ClientOnboarding, pk=pk)

    if request.method == 'POST':
        # Populate the form with POST data and the existing client instance
        form = ClientOnboardingForm(request.POST, instance=client)
        if form.is_valid():
            # Save the updated form data to the database
            form.save()
            # Optional: Add a success message
            messages.success(request, 'Client information updated successfully.')
            # Redirect to the client list page after successful update
            return redirect('client_list')  # Adjust the URL name to your client list page
    else:
        # Populate the form with the existing client data for GET requests
        form = ClientOnboardingForm(instance=client)

    # Render the form in the template with 'action' and 'client' context for dynamic form behavior
    return render(request, 'client/client_onboarding.html', {'form': form, 'action': 'Update', 'client': client})


# View to handle the success page after onboarding form submission
def onboarding_success_view(request):
    return render(request, 'client/onboarding_success.html')


# View to handle the client list with search and master-detail layout
def client_list_view(request):
    # Get the search query from the request
    query = request.GET.get('search')
    
    # Get the selected client ID from the request (optional)
    selected_client_id = request.GET.get('selected')
    
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
    
    # Preprocess competitor_urls by splitting them into lists
    for client in clients:
        if client.competitor_urls:
            # Split the competitor_urls by comma and strip any extra whitespace
            client.competitor_urls_list = [url.strip() for url in client.competitor_urls.split(',') if url.strip()]
        else:
            client.competitor_urls_list = []
    
    # Fetch the selected client if a valid ID is provided
    selected_client = None
    if selected_client_id:
        selected_client = get_object_or_404(ClientOnboarding, pk=selected_client_id)
    
    # Render the client list template with the clients, and the selected client
    context = {
        'clients': clients,
        'selected_client': selected_client,
    }

    return render(request, 'client/client_list.html', context)


