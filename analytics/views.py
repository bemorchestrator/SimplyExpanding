import os
import json  # Import json module
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.admin_v1alpha import AnalyticsAdminServiceClient
from google.auth.transport.requests import Request

# GA4 SCOPES
SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']

# Paths to credentials and token
CREDENTIALS_PATH = r'C:\Users\bem\Desktop\credentials\client_secret_ga4.json'
TOKEN_PATH = r'C:\Users\bem\Desktop\credentials\token_ga4.json'

def authenticate_ga4(request):
    creds = None

    # Load credentials if they exist
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # Authenticate the user if there are no valid credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=8081)

        # Save the credentials for future use
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    return redirect('fetch_ga4_data')


def fetch_ga4_data(request):
    if not os.path.exists(TOKEN_PATH):
        return HttpResponseBadRequest("Authentication required. Please authenticate first.")

    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    client = BetaAnalyticsDataClient(credentials=creds)
    admin_client = AnalyticsAdminServiceClient(credentials=creds)

    # Fetch all properties associated with the authenticated user
    accounts = admin_client.list_account_summaries()

    properties = []
    for account in accounts:
        for property_summary in account.property_summaries:
            # Extract only the numeric property ID
            numeric_property_id = property_summary.property.split('/')[-1]
            properties.append({
                'property_id': numeric_property_id,  # Numeric Property ID
                'display_name': property_summary.display_name  # Human-readable property name
            })

    if request.method == 'POST':
        property_id = request.POST.get('property_id')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        row_limit = request.POST.get('row_limit')

        if not property_id or not start_date or not end_date or not row_limit:
            return HttpResponseBadRequest("Please provide valid inputs.")

        # Define the report request
        request_body = {
            'property': property_id,  # Use only the numeric property ID
            'metrics': [
                {'name': 'totalUsers'},               # Total Users
                {'name': 'bounceRate'},               # Bounce Rate
                {'name': 'sessions'},                 # Total Sessions
                {'name': 'averageSessionDuration'},   # Average Session Duration
            ],
            'date_ranges': [{'start_date': start_date, 'end_date': end_date}],
            'limit': int(row_limit)  # Optional: You can set this to 1 if you expect only one row
        }

        # Fetch the report data
        try:
            response = client.run_report(request=request_body)
        except Exception as e:
            return HttpResponseBadRequest(f"Error fetching data: {str(e)}")

        # Extract data from the response
        report_data = []
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
            'report_data_json': report_data_json,  # Add serialized data
            'properties': properties,  # Ensure properties are passed back to the template
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
