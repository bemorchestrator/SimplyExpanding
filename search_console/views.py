import logging
from django.http import HttpResponseBadRequest, HttpResponseServerError
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
        creds = get_credentials(request)
        if not creds:
            return redirect('authenticate_user_view')

        # Build the Search Console service
        service = build('webmasters', 'v3', credentials=creds)
        logger.debug("Search Console service built successfully.")

        if request.method == 'POST':
            website_url = request.POST.get('website_url')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            row_limit = request.POST.get('row_limit')

            # Validate inputs
            if not website_url or not start_date or not end_date or not row_limit:
                logger.warning("Invalid input received.")
                return HttpResponseBadRequest("Please provide valid inputs.")

            request_body = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': ['query'],
                'rowLimit': int(row_limit)
            }
            logger.debug(f"Request body prepared: {request_body}")

            try:
                response = service.searchanalytics().query(siteUrl=website_url, body=request_body).execute()
                logger.debug("Search Analytics data fetched successfully.")
                data = response.get('rows', [])
                return render(request, 'search_console/search_console_data.html', {
                    'data': data,
                    'website_url': website_url,
                    'start_date': start_date,
                    'end_date': end_date,
                    'row_limit': row_limit
                })
            except Exception as e:
                logger.error(f"Error fetching Search Console data: {str(e)}")
                return HttpResponseServerError(f"Error fetching Search Console data: {str(e)}")

        # On GET request, show the form
        logger.debug("Rendering search_console_data form.")
        return render(request, 'search_console/search_console_data.html', {'data': None})

    except Exception as e:
        logger.error(f"Error in search_console_data view: {str(e)}")
        return HttpResponseServerError(f"Error in search_console_data view: {str(e)}")
