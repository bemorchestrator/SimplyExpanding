import os
from django.http import HttpResponseBadRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from django.shortcuts import redirect, render
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Google Search Console API scope
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']

# Path to credentials and token
CREDENTIALS_PATH = r'C:\Users\bem\Desktop\credentials\client_secret_520578449641-vldnvlmflegmd5nar6qvjehaojthhpde.apps.googleusercontent.com.json'
TOKEN_PATH = r'C:\Users\bem\Desktop\credentials\token.json'


def authenticate_user(request):
    creds = None
    
    # Check if the token.json file exists
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # If no valid credentials, go through OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Create a flow to get user credentials and use port 8080
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=8080)

        # Save the new credentials for future use
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    # After authentication, redirect to fetch the Search Console data
    return redirect('search_console_data')


def search_console_data(request):
    # Check if the token exists
    if not os.path.exists(TOKEN_PATH):
        return HttpResponseBadRequest("Authentication required. Please authenticate first.")

    # Load the credentials from token.json
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    
    # Build the Search Console service
    service = build('webmasters', 'v3', credentials=creds)

    # Handle POST request to fetch Search Console data
    if request.method == 'POST':
        website_url = request.POST.get('website_url')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        row_limit = request.POST.get('row_limit')

        # Validate the inputs
        if not website_url or not start_date or not end_date or not row_limit:
            return HttpResponseBadRequest("Please provide valid inputs for website URL, start date, end date, and row limit.")

        # Prepare the request body for Search Analytics
        request_body = {
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': ['query'],
            'rowLimit': int(row_limit)
        }

        # Fetch the Search Analytics data
        response = service.searchanalytics().query(siteUrl=website_url, body=request_body).execute()

        # Extract the rows from the response
        data = response.get('rows', [])

        # Render the results to the template
        return render(request, 'search_console/search_console_data.html', {
            'data': data,
            'website_url': website_url,
            'start_date': start_date,
            'end_date': end_date,
            'row_limit': row_limit
        })

    # On GET request, show the form
    return render(request, 'search_console/search_console_data.html', {'data': None})
