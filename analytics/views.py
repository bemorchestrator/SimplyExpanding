import json
import logging
import datetime
from django.shortcuts import redirect, render
from django.http import HttpResponseBadRequest, HttpResponseServerError
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.admin_v1alpha import AnalyticsAdminServiceClient
from google_auth import get_credentials, authenticate_user, oauth2_callback  # Import from google_auth
from django.urls import reverse

# Initialize logger
logger = logging.getLogger(__name__)

# Utility function to handle preset date ranges
def get_date_range(preset):
    today = datetime.date.today()
    if preset == 'last_7_days':
        return today - datetime.timedelta(days=7), today
    elif preset == 'last_14_days':
        return today - datetime.timedelta(days=14), today
    elif preset == 'last_28_days':
        return today - datetime.timedelta(days=28), today
    elif preset == 'last_90_days':
        return today - datetime.timedelta(days=90), today
    elif preset == 'last_12_months':
        return today - datetime.timedelta(days=365), today
    else:
        return None, None

# Google Analytics authentication view
def authenticate_ga4(request):
    return authenticate_user(request, 'ga')

# Callback view for OAuth2
def google_oauth2_callback(request):
    return oauth2_callback(request, 'ga')



def format_duration(duration):
    try:
        minutes = int(duration) // 60
        seconds = int(duration) % 60
        return f'{minutes}:{seconds:02}'
    except (ValueError, TypeError):
        return 'N/A'


# Fetch Google Analytics data view
def get_date_range(preset):
    today = datetime.date.today()
    if preset == 'last_7_days':
        return today - datetime.timedelta(days=7), today
    elif preset == 'last_14_days':
        return today - datetime.timedelta(days=14), today
    elif preset == 'last_28_days':
        return today - datetime.timedelta(days=28), today
    elif preset == 'last_90_days':
        return today - datetime.timedelta(days=90), today
    elif preset == 'last_12_months':
        return today - datetime.timedelta(days=365), today
    else:
        return None, None

# Google Analytics authentication view
def authenticate_ga4(request):
    return authenticate_user(request, 'ga')

# Callback view for OAuth2
def google_oauth2_callback(request):
    return oauth2_callback(request, 'ga')

def format_duration(duration):
    try:
        minutes = int(duration) // 60
        seconds = int(duration) % 60
        return f'{minutes}:{seconds:02}'
    except (ValueError, TypeError):
        return '0:00'  # Changed from 'N/A' to '0:00'

# Fetch Google Analytics data view
def fetch_ga4_data(request):
    try:
        creds = get_credentials(request, 'ga')
        if not creds:
            return redirect('authenticate_ga4')

        client = BetaAnalyticsDataClient(credentials=creds)
        admin_client = AnalyticsAdminServiceClient(credentials=creds)

        # Fetch all properties associated with the authenticated user
        accounts = admin_client.list_account_summaries()
        properties = [
            {
                'property_id': property_summary.property.split('/')[-1],
                'display_name': property_summary.display_name
            }
            for account in accounts
            for property_summary in account.property_summaries
        ]

        if request.method == 'POST':
            property_id = request.POST.get('property_id')
            date_range = request.POST.get('date_range')
            row_limit = request.POST.get('row_limit', 10)
            compare = request.POST.get('compare')
            comparison_range = request.POST.get('comparison_range')

            # Handle custom date selection or preset date ranges
            if date_range == 'custom':
                start_date = request.POST.get('start_date')
                end_date = request.POST.get('end_date')
                if not start_date or not end_date:
                    return HttpResponseBadRequest("Please provide valid start and end dates.")
            else:
                start_date, end_date = get_date_range(date_range)

            if not property_id or not start_date or not end_date or not row_limit:
                return HttpResponseBadRequest("Please provide valid inputs.")

            # Construct the main request body
            request_body = {
                'property': f'properties/{property_id}',
                'metrics': [
                    {'name': 'totalUsers'},
                    {'name': 'bounceRate'},
                    {'name': 'sessions'},
                    {'name': 'averageSessionDuration'},
                ],
                'dimensions': [{'name': 'pagePath'}],
                'date_ranges': [{'start_date': str(start_date), 'end_date': str(end_date)}],
                'limit': int(row_limit)
            }

            report_data = []
            comparison_data = []

            # Fetch the main report data
            try:
                response = client.run_report(request=request_body)
                for row in response.rows:
                    try:
                        avg_session_duration = format_duration(float(row.metric_values[3].value))
                    except (ValueError, TypeError):
                        avg_session_duration = '0:00'  # Ensure zero duration

                    report_data.append({
                        "page_path": row.dimension_values[0].value,
                        "total_users": int(row.metric_values[0].value) if row.metric_values[0].value else 0,
                        "bounce_rate": float(row.metric_values[1].value) if row.metric_values[1].value else 0.0,
                        "sessions": int(row.metric_values[2].value) if row.metric_values[2].value else 0,
                        "avg_session_duration": avg_session_duration,
                    })
            except Exception as e:
                logger.error(f"Error fetching Google Analytics data: {str(e)}", exc_info=True)
                return HttpResponseBadRequest(f"Error fetching data: {str(e)}")

            # Handle comparison logic based on user input
            if compare and comparison_range != 'none':
                # Get comparison date ranges based on the selected option
                comparison_start_date, comparison_end_date = None, None
                if comparison_range == 'preceding_period':
                    delta = end_date - start_date
                    comparison_start_date = (start_date - delta).strftime('%Y-%m-%d')
                    comparison_end_date = (end_date - delta).strftime('%Y-%m-%d')
                elif comparison_range == 'preceding_period_match_day':
                    comparison_start_date = (start_date - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
                    comparison_end_date = (end_date - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
                elif comparison_range == 'same_period_last_year':
                    comparison_start_date = (start_date - datetime.timedelta(days=365)).strftime('%Y-%m-%d')
                    comparison_end_date = (end_date - datetime.timedelta(days=365)).strftime('%Y-%m-%d')

                comparison_request_body = {
                    'property': f'properties/{property_id}',
                    'metrics': request_body['metrics'],
                    'dimensions': request_body['dimensions'],
                    'date_ranges': [{'start_date': comparison_start_date, 'end_date': comparison_end_date}],
                    'limit': int(row_limit)
                }

                # Fetch comparison data
                try:
                    comparison_response = client.run_report(request=comparison_request_body)
                    for row in comparison_response.rows:
                        try:
                            avg_session_duration = format_duration(float(row.metric_values[3].value))
                        except (ValueError, TypeError):
                            avg_session_duration = '0:00'  # Ensure zero duration

                        comparison_data.append({
                            "page_path": row.dimension_values[0].value,
                            "total_users": int(row.metric_values[0].value) if row.metric_values[0].value else 0,
                            "bounce_rate": float(row.metric_values[1].value) if row.metric_values[1].value else 0.0,
                            "sessions": int(row.metric_values[2].value) if row.metric_values[2].value else 0,
                            "avg_session_duration": avg_session_duration,
                        })
                except Exception as e:
                    logger.error(f"Error fetching comparison data: {str(e)}", exc_info=True)
                    return HttpResponseBadRequest(f"Error fetching comparison data: {str(e)}")

                # Create a dictionary for quick lookup of comparison data by page_path
                comparison_dict = {data["page_path"]: data for data in comparison_data}

                # Calculate differences
                for main_data in report_data:
                    comp_data = comparison_dict.get(main_data["page_path"], None)
                    if comp_data:
                        main_data["total_users_diff"] = main_data["total_users"] - comp_data["total_users"]
                        main_data["bounce_rate_diff"] = main_data["bounce_rate"] - comp_data["bounce_rate"]
                        main_data["sessions_diff"] = main_data["sessions"] - comp_data["sessions"]

                        # Calculate avg_session_duration_diff in seconds
                        try:
                            main_seconds = int(main_data["avg_session_duration"].split(":")[0]) * 60 + int(main_data["avg_session_duration"].split(":")[1])
                        except (IndexError, ValueError):
                            main_seconds = 0

                        try:
                            comp_seconds = int(comp_data["avg_session_duration"].split(":")[0]) * 60 + int(comp_data["avg_session_duration"].split(":")[1])
                        except (IndexError, ValueError):
                            comp_seconds = 0

                        diff_seconds = main_seconds - comp_seconds
                        if diff_seconds < 0:
                            diff_seconds = 0  # Prevent negative durations if needed
                        main_data["avg_session_duration_diff"] = format_duration(diff_seconds)
                    else:
                        # If no comparison data exists for this page_path, set differences to zero
                        main_data["total_users_diff"] = 0
                        main_data["bounce_rate_diff"] = 0.0
                        main_data["sessions_diff"] = 0
                        main_data["avg_session_duration_diff"] = '0:00'

            return render(request, 'analytics/ga4_data.html', {
                'report_data': report_data,
                'properties': properties,
                'property_id': property_id,
                'start_date': start_date,
                'end_date': end_date,
                'row_limit': row_limit,
                'date_range': date_range,  # Pass the selected date range to the template
                'comparison_range': comparison_range,  # Pass the selected comparison range to the template
            })

        return render(request, 'analytics/ga4_data.html', {
            'report_data': None,
            'properties': properties,
        })

    except Exception as e:
        logger.error("Error in fetch_ga4_data view:", exc_info=True)
        return HttpResponseServerError(f"Error in fetch_ga4_data view: {str(e)}")
