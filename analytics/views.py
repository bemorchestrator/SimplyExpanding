import json
import logging
from django.shortcuts import redirect, render
from django.http import HttpResponseBadRequest, HttpResponseServerError
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.admin_v1alpha import AnalyticsAdminServiceClient
from audit.utils import identify_csv_type
from google_auth import get_credentials, authenticate_user, oauth2_callback  # Import from google_auth
from django.urls import reverse

# Initialize logger
logger = logging.getLogger(__name__)

# Google Analytics authentication view
def authenticate_ga4(request):
    # Call authenticate_user from google_auth.py to initiate the Google Analytics OAuth2 flow
    return authenticate_user(request, 'ga')

# Callback view for OAuth2
def google_oauth2_callback(request):
    # Delegate the callback handling to google_auth.py's handle_oauth2_callback function
    return oauth2_callback(request, 'ga')

# Fetch Google Analytics data view
def fetch_ga4_data(request):
    try:
        # Fetch credentials using google_auth
        creds = get_credentials(request, 'ga')
        if not creds:
            # If credentials are missing, redirect to the authentication flow
            return redirect('authenticate_ga4')

        # Initialize Google Analytics client
        client = BetaAnalyticsDataClient(credentials=creds)
        admin_client = AnalyticsAdminServiceClient(credentials=creds)

        # Fetch all properties associated with the authenticated user
        accounts = admin_client.list_account_summaries()

        properties = []
        for account in accounts:
            for property_summary in account.property_summaries:
                # Extract the numeric property ID and display name
                numeric_property_id = property_summary.property.split('/')[-1]
                properties.append({
                    'property_id': numeric_property_id,
                    'display_name': property_summary.display_name
                })

        if request.method == 'POST':
            # Handle form submission and input validation
            property_id = request.POST.get('property_id')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            row_limit = request.POST.get('row_limit')

            # Validate input fields
            if not property_id or not start_date or not end_date or not row_limit:
                return HttpResponseBadRequest("Please provide valid inputs.")

            # Define the report request with the correct property format
            request_body = {
                'property': f'properties/{property_id}',
                'metrics': [
                    {'name': 'totalUsers'},  # Total Users
                    {'name': 'bounceRate'},  # Bounce Rate
                    {'name': 'sessions'},  # Total Sessions
                    {'name': 'averageSessionDuration'},  # Average Session Duration
                ],
                'date_ranges': [{'start_date': start_date, 'end_date': end_date}],
                'limit': int(row_limit)  # Limit the number of rows
            }

            # Fetch the report data
            try:
                response = client.run_report(request=request_body)
            except Exception as e:
                logger.error(f"Error fetching Google Analytics data: {str(e)}", exc_info=True)
                return HttpResponseBadRequest(f"Error fetching data: {str(e)}")

            # Extract data from the response and process using identify_csv_type
            report_data = []
            headers = ['page_path', 'sessions', 'bounce_rate', 'avg_session_duration']  # Example headers
            csv_type = identify_csv_type(headers)  # Identify CSV type
            logger.debug(f"Identified CSV type: {csv_type}")

            for row in response.rows:
                report_data.append({
                    "total_users": row.metric_values[0].value,
                    "bounce_rate": row.metric_values[1].value,
                    "sessions": row.metric_values[2].value,
                    "avg_session_duration": row.metric_values[3].value,
                })

            # Serialize report_data to JSON
            report_data_json = json.dumps(report_data)

            # Render the template with the report data
            return render(request, 'analytics/ga4_data.html', {
                'report_data': report_data,
                'report_data_json': report_data_json,
                'properties': properties,
                'property_id': property_id,
                'start_date': start_date,
                'end_date': end_date,
                'row_limit': row_limit
            })

        # On GET request, show the form with available properties
        return render(request, 'analytics/ga4_data.html', {
            'report_data': None,
            'properties': properties,  # Ensure properties are passed to the template
        })

    except Exception as e:
        logger.error("Error in fetch_ga4_data view:", exc_info=True)
        return HttpResponseServerError(f"Error in fetch_ga4_data view: {str(e)}")
