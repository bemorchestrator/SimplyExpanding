# analytics/views.py

import json
import logging
import datetime
import os
from django.shortcuts import render
from django.http import (
    HttpResponseBadRequest,
    HttpResponseServerError,
    JsonResponse,
)
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.admin_v1alpha import AnalyticsAdminServiceClient
from google.oauth2 import service_account

# Initialize logger
logger = logging.getLogger(__name__)

# Path to service account key JSON file for Analytics access
SERVICE_ACCOUNT_FILE = r'C:\Users\bem\Desktop\credentials\se_service_account.json'


def get_analytics_credentials():
    """Get Google Analytics credentials using service account."""
    SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        return credentials
    except Exception as e:
        logger.error(f"Failed to load service account credentials: {e}")
        return None


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


def format_duration(duration):
    try:
        duration = int(duration)
        if duration < 0:
            duration = 0
        minutes = duration // 60
        seconds = duration % 60
        return f'{minutes}:{seconds:02}'
    except (ValueError, TypeError):
        return '0:00'


# Fetch Google Analytics data view
def fetch_ga4_data(request):
    try:
        creds = get_analytics_credentials()
        if not creds:
            logger.error("Could not obtain Analytics credentials.")
            return HttpResponseServerError("Could not obtain Analytics credentials.")

        client = BetaAnalyticsDataClient(credentials=creds)

        report_data = []
        comparison_data = []
        start_date = None
        end_date = None
        row_limit = 10
        comparison_range = 'none'
        compare = False
        date_range = None
        property_id = None

        # Check if we have POST request for form data
        if request.method == 'POST':
            property_id = request.POST.get('property_id')
            date_range = request.POST.get('date_range', 'last_7_days')
            row_limit = int(request.POST.get('row_limit', 10))
            compare = request.POST.get('compare') == 'true'
            comparison_range = request.POST.get('comparison_range', 'none')

            # Custom date selection or handle preset date ranges
            if date_range == 'custom':
                start_date = request.POST.get('start_date')
                end_date = request.POST.get('end_date')
                if not start_date or not end_date:
                    logger.warning("Start date or end date not provided for custom date range.")
                    return HttpResponseBadRequest("Please provide valid start and end dates.")
            else:
                start_date_obj, end_date_obj = get_date_range(date_range)
                if not start_date_obj or not end_date_obj:
                    logger.warning(f"Invalid date range preset selected: {date_range}")
                    return HttpResponseBadRequest("Invalid date range selected.")
                start_date = start_date_obj.strftime('%Y-%m-%d')
                end_date = end_date_obj.strftime('%Y-%m-%d')

            # Validate inputs
            if not property_id or not start_date or not end_date or not row_limit:
                logger.warning("One or more required fields are missing.")
                return HttpResponseBadRequest("Please provide valid inputs.")

            # Remove 'properties/' prefix if present
            if property_id.startswith("properties/"):
                property_id = property_id.replace("properties/", "")

            # Request body for GA4 data
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
                'limit': int(row_limit),
            }

            logger.debug(f"Request body for GA4 data: {request_body}")

            # Fetching GA4 data
            try:
                response = client.run_report(request=request_body)
                for row in response.rows:
                    avg_session_duration = format_duration(
                        float(row.metric_values[3].value)
                    ) if row.metric_values[3].value else '0:00'

                    report_data.append({
                        "page_path": row.dimension_values[0].value,
                        "total_users": int(row.metric_values[0].value) if row.metric_values[0].value else 0,
                        "bounce_rate": float(row.metric_values[1].value) if row.metric_values[1].value else 0.0,
                        "sessions": int(row.metric_values[2].value) if row.metric_values[2].value else 0,
                        "avg_session_duration": avg_session_duration,
                    })
                logger.debug(f"Fetched {len(report_data)} rows of GA4 data.")
            except Exception as e:
                logger.error(f"Error fetching Google Analytics data: {str(e)}", exc_info=True)
                return HttpResponseBadRequest(f"Error fetching data: {str(e)}")

            # Handle comparison if requested
            if compare and comparison_range != 'none':
                comparison_start_date, comparison_end_date = None, None
                start_date_obj = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date_obj = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()

                if comparison_range == 'preceding_period':
                    delta = end_date_obj - start_date_obj
                    comparison_start_date = (start_date_obj - delta).strftime('%Y-%m-%d')
                    comparison_end_date = (end_date_obj - delta).strftime('%Y-%m-%d')
                elif comparison_range == 'preceding_period_match_day':
                    comparison_start_date = (start_date_obj - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
                    comparison_end_date = (end_date_obj - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
                elif comparison_range == 'same_period_last_year':
                    comparison_start_date = (start_date_obj - datetime.timedelta(days=365)).strftime('%Y-%m-%d')
                    comparison_end_date = (end_date_obj - datetime.timedelta(days=365)).strftime('%Y-%m-%d')
                else:
                    logger.warning(f"Invalid comparison range selected: {comparison_range}")
                    return HttpResponseBadRequest("Invalid comparison range selected.")

                # Prepare the comparison request body
                comparison_request_body = {
                    'property': f'properties/{property_id}',
                    'metrics': request_body['metrics'],
                    'dimensions': request_body['dimensions'],
                    'date_ranges': [{'start_date': comparison_start_date, 'end_date': comparison_end_date}],
                    'limit': int(row_limit),
                }

                logger.debug(f"Comparison request body: {comparison_request_body}")

                # Fetch comparison data
                try:
                    comparison_response = client.run_report(request=comparison_request_body)
                    for row in comparison_response.rows:
                        avg_session_duration = format_duration(
                            float(row.metric_values[3].value)
                        ) if row.metric_values[3].value else '0:00'

                        comparison_data.append({
                            "page_path": row.dimension_values[0].value,
                            "total_users": int(row.metric_values[0].value) if row.metric_values[0].value else 0,
                            "bounce_rate": float(row.metric_values[1].value) if row.metric_values[1].value else 0.0,
                            "sessions": int(row.metric_values[2].value) if row.metric_values[2].value else 0,
                            "avg_session_duration": avg_session_duration,
                        })
                    logger.debug(f"Fetched {len(comparison_data)} rows of comparison data.")
                except Exception as e:
                    logger.error(f"Error fetching comparison data: {str(e)}", exc_info=True)
                    return HttpResponseBadRequest(f"Error fetching comparison data: {str(e)}")

                # Calculate the differences
                comparison_dict = {data["page_path"]: data for data in comparison_data}
                for main_data in report_data:
                    comp_data = comparison_dict.get(main_data["page_path"], None)
                    if comp_data:
                        main_data["total_users_diff"] = main_data["total_users"] - comp_data["total_users"]
                        main_data["bounce_rate_diff"] = main_data["bounce_rate"] - comp_data["bounce_rate"]
                        main_data["sessions_diff"] = main_data["sessions"] - comp_data["sessions"]

                        # Calculate the avg_session_duration_diff in seconds
                        try:
                            main_minutes, main_seconds = map(int, main_data["avg_session_duration"].split(":"))
                            main_total_seconds = main_minutes * 60 + main_seconds
                        except (IndexError, ValueError):
                            main_total_seconds = 0

                        try:
                            comp_minutes, comp_seconds = map(int, comp_data["avg_session_duration"].split(":"))
                            comp_total_seconds = comp_minutes * 60 + comp_seconds
                        except (IndexError, ValueError):
                            comp_total_seconds = 0

                        diff_seconds = main_total_seconds - comp_total_seconds
                        main_data["avg_session_duration_diff"] = format_duration(diff_seconds)
                    else:
                        # If no comparison data exists for this page_path, set differences to None
                        main_data["total_users_diff"] = None
                        main_data["bounce_rate_diff"] = None
                        main_data["sessions_diff"] = None
                        main_data["avg_session_duration_diff"] = None

            else:
                # Ensure difference fields are None when not comparing
                for main_data in report_data:
                    main_data["total_users_diff"] = None
                    main_data["bounce_rate_diff"] = None
                    main_data["sessions_diff"] = None
                    main_data["avg_session_duration_diff"] = None

            # Render the results
            return render(request, 'analytics/ga4_data.html', {
                'report_data': report_data,
                'property_id': property_id,
                'start_date': start_date,
                'end_date': end_date,
                'row_limit': row_limit,
                'date_range': date_range,
                'comparison_range': comparison_range,
                'compare': compare,
            })

        else:
            # Handle GET request or empty form
            logger.debug("Rendering GA4 data form.")
            return render(request, 'analytics/ga4_data.html', {
                'report_data': None,
                'property_id': None,
                'compare': None,
                'comparison_range': 'none',
            })

    except Exception as e:
        logger.error("Error in fetch_ga4_data view:", exc_info=True)
        return HttpResponseServerError(f"Error in fetch_ga4_data view: {str(e)}")


def get_ga4_properties(request):
    try:
        # Get credentials
        creds = get_analytics_credentials()
        if not creds:
            logger.error("Could not obtain Analytics credentials.")
            return HttpResponseServerError("Could not obtain Analytics credentials.")

        # Create a client for Analytics Admin API
        admin_client = AnalyticsAdminServiceClient(credentials=creds)

        # Fetch the GA4 properties
        properties = []
        accounts = admin_client.list_account_summaries()
        for account in accounts:
            for property_summary in account.property_summaries:
                properties.append({
                    'property_id': property_summary.property,
                    'display_name': property_summary.display_name
                })

        logger.debug(f"Fetched {len(properties)} GA4 properties.")

        # Return the properties as JSON
        return JsonResponse({'properties': properties})

    except Exception as e:
        logger.error(f"Error fetching GA4 properties: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)
