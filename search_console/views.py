from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from googleapiclient.discovery import build
from google_auth import get_credentials  # Import the function from google_auth.py

# Define Google Search Console API scope
SEARCH_CONSOLE_SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']

# View to authenticate the user and redirect to search console data
def authenticate_user(request):
    try:
        # Get the credentials using the new google_auth function
        creds = get_credentials(SEARCH_CONSOLE_SCOPES)
        return redirect('search_console_data')
    except Exception as e:
        return HttpResponseBadRequest(f"Error during authentication: {str(e)}")

# View to handle Search Console data retrieval
def search_console_data(request):
    try:
        # Get credentials
        creds = get_credentials(SEARCH_CONSOLE_SCOPES)

        # Build the Search Console service
        service = build('webmasters', 'v3', credentials=creds)

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
    
    except Exception as e:
        return HttpResponseBadRequest(f"Error fetching data: {str(e)}")
