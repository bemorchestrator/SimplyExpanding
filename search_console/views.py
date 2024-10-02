import logging
from urllib.parse import urlparse

from django.http import HttpResponseBadRequest, HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import redirect, render
from googleapiclient.discovery import build
from google_auth import authenticate_user, get_credentials, oauth2_callback  # Import from google_auth.py

# Configure logging
logger = logging.getLogger(__name__)

# Delegate to authenticate_user in google_auth.py
def authenticate_user_view(request):
    return authenticate_user(request)

# Delegate to oauth2_callback in google_auth.py
def oauth2_callback_view(request):
    return oauth2_callback(request)

# View to handle Search Console data retrieval
def search_console_data(request):
    try:
        logger.debug("Accessing search_console_data view.")

        # Get the credentials
        creds = get_credentials(request)

        # If creds is a redirect response, return it
        if isinstance(creds, HttpResponseRedirect):
            logger.debug("Credentials not available. Redirecting for authentication.")
            return creds  # Return the redirect response immediately

        if not creds:
            logger.warning("Credentials are missing. Redirecting to authenticate_user.")
            return redirect('authenticate_user')  # If credentials are missing, go to authentication

        # Build the Search Console service with the credentials
        service = build('webmasters', 'v3', credentials=creds)
        logger.debug("Search Console service built successfully.")

        if request.method == 'POST':
            input_url = request.POST.get('input_url')  # Single input field for URL
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            row_limit = request.POST.get('row_limit')

            # Add logging to capture submitted data
            logger.debug(f"Received POST data: input_url={input_url}, start_date={start_date}, end_date={end_date}, row_limit={row_limit}")

            # Validate inputs
            if not input_url or not start_date or not end_date or not row_limit:
                logger.warning("Invalid input received: one or more fields are missing.")
                return HttpResponseBadRequest("Please provide valid inputs.")

            # Parse the input URL
            parsed_input_url = urlparse(input_url)
            if not all([parsed_input_url.scheme, parsed_input_url.netloc]):
                logger.warning("Invalid input_url format.")
                return HttpResponseBadRequest("Please provide a valid URL.")

            # Normalize website_url (root domain)
            website_url = f"{parsed_input_url.scheme}://{parsed_input_url.netloc}/"
            logger.debug(f"Normalized website_url: {website_url}")

            # Determine if the input URL is the root domain or a specific page
            path = parsed_input_url.path
            if path in ['', '/']:
                # Input is the root domain; no page_url filter
                page_url = None
                logger.debug("Input URL is the root domain. No page_url filter will be applied.")
            else:
                # Input is a specific page; set page_url filter
                page_url = path if path.startswith('/') else f"/{path}"
                logger.debug(f"Input URL is a specific page. page_url set to: {page_url}")

            # Create request body
            request_body = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': ['query'],  # Include 'query' to get keyword data
                'rowLimit': int(row_limit)
            }

            # If page_url is specified, add a filter for it
            if page_url:
                request_body['dimensions'].append('page')  # Include 'page' dimension
                request_body['dimensionFilterGroups'] = [{
                    'filters': [{
                        'dimension': 'page',
                        'operator': 'equals',  # Use 'equals' for exact match
                        'expression': f"{website_url.rstrip('/')}{page_url}"  # Full URL of the page
                    }]
                }]
                logger.debug(f"Request body with page_url filter: {request_body}")
            else:
                logger.debug(f"Request body without page_url filter: {request_body}")

            try:
                # Fetch Search Analytics data
                response = service.searchanalytics().query(siteUrl=website_url, body=request_body).execute()
                logger.debug("Search Analytics data fetched successfully.")
                data = response.get('rows', [])
                return render(request, 'search_console/search_console_data.html', {
                    'data': data,
                    'input_url': input_url,
                    'start_date': start_date,
                    'end_date': end_date,
                    'row_limit': row_limit
                })
            except Exception as e:
                logger.error("Error fetching Search Console data:", exc_info=True)
                return HttpResponseServerError(f"Error fetching Search Console data: {str(e)}")

        # On GET request, show the form
        logger.debug("Rendering search_console_data form.")
        return render(request, 'search_console/search_console_data.html', {'data': None})

    except Exception as e:
        logger.error("Error in search_console_data view:", exc_info=True)
        return HttpResponseServerError(f"Error in search_console_data view: {str(e)}")
