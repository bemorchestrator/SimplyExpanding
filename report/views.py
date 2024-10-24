# report/views.py

from datetime import datetime, timedelta
import logging
from django.core.exceptions import PermissionDenied
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseRedirect,
    HttpResponseServerError,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from analytics.views import fetch_ga4_data
from audit.models import AuditDashboard
from client.models import ClientOnboarding
from keywords.models import KeywordResearchDashboard
from report.models import Report
from django.contrib import messages
from google.oauth2 import service_account
from google.analytics.admin_v1beta import AnalyticsAdminServiceClient
from google.analytics.data_v1beta.types import RunReportRequest
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from urllib.parse import urlparse
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Path to your service account key JSON file for Google Search Console access
SERVICE_ACCOUNT_SEARCH_CONSOLE_FILE = '/var/www/credentials/se_service_account.json'  # Update with your actual path


def get_analytics_credentials():
    """Get Google Analytics credentials using service account."""
    SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_SEARCH_CONSOLE_FILE, scopes=SCOPES
        )
        return credentials
    except Exception as e:
        logger.error(f"Failed to load service account credentials: {e}")
        return None


def get_search_console_credentials():
    """Get Google Search Console credentials using service account."""
    SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_SEARCH_CONSOLE_FILE, scopes=SCOPES
        )
        return credentials
    except Exception as e:
        logger.error(f"Failed to load Search Console service account credentials: {e}")
        return None


# Function to fetch Google Search Console data
def fetch_search_console_data(
    request, site_url, start_date, end_date, dimensions=['query'], row_limit=10
):
    try:
        # Use the service account to authenticate for Google Search Console
        creds = get_search_console_credentials()

        if not creds:
            logger.error("Failed to obtain credentials for Google Search Console.")
            return HttpResponseBadRequest(
                "Failed to get credentials for Google Search Console"
            )

        # Build the Search Console API service
        service = build('webmasters', 'v3', credentials=creds)

        # Prepare the request body for Search Analytics query
        request_body = {
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': dimensions,
            'rowLimit': row_limit,
        }

        logger.debug(
            f"Fetching Search Console data for site: {site_url} with request body: {request_body}"
        )

        # Execute the query and get the response
        response = (
            service.searchanalytics()
            .query(siteUrl=site_url, body=request_body)
            .execute()
        )

        # Extract rows from the response
        data = response.get('rows', [])
        logger.debug(
            f"Fetched {len(data)} rows from Search Console for the period {start_date} to {end_date}"
        )

        # Handle 'keys' if they are in bytes and ensure proper handling of the data
        for row in data:
            if 'keys' in row and row['keys']:
                key = row['keys'][0]
                if isinstance(key, bytes):
                    key = key.decode('utf-8')  # Decode bytes to string
                row['keys'][0] = key

        return data  # You can further process or pass this data to a template

    except Exception as e:
        logger.error(
            f"Error fetching Google Search Console data: {str(e)}", exc_info=True
        )
        return HttpResponseServerError(f"Error fetching Search Console data: {str(e)}")


# Landing page for reports via client_id (for internal use)
def client_portal(request, client_id):
    # Fetch the client by ID
    client = get_object_or_404(ClientOnboarding, id=client_id)

    # Fetch or create a report for the client
    report, created = Report.objects.get_or_create(
        client=client, defaults={'title': f"{client.business_name} Report"}
    )

    # Fetch the audit dashboard associated with the client
    audit_dashboard = AuditDashboard.objects.filter(client=client).first()

    # Fetch the keyword research dashboard associated with the audit dashboard
    keyword_dashboard = KeywordResearchDashboard.objects.filter(audit_dashboard=audit_dashboard).first()

    # Define the available report types for the client
    report_types = [
        {
            'name': 'Google Search Console',
            'report_type': 'google_search_console',
            'url': reverse('google_search_console_report', kwargs={'client_id': client.id}),
            'available': True,  # Assume always available for now
        },
        {
            'name': 'Google Analytics',
            'report_type': 'google_analytics',
            'url': reverse('google_analytics_report', kwargs={'client_id': client.id}),
            'available': True,  # Assume available if Google Analytics data can be fetched
        },
        {
            'name': 'Keyword Research',
            'report_type': 'keyword_research',
            'url': reverse('load_keyword_dashboard', kwargs={'id': keyword_dashboard.id}) if keyword_dashboard else '#',
            'available': bool(keyword_dashboard),  # Only available if the dashboard exists
        },
        {
            'name': 'Website Audit',
            'report_type': 'website_audit',
            'url': reverse('load_dashboard', kwargs={'id': audit_dashboard.id}) if audit_dashboard else '#',
            'available': bool(audit_dashboard),  # Only available if the dashboard exists
        },
    ]

    # If neither audit nor keyword dashboard exists, show an error message
    if not audit_dashboard and not keyword_dashboard:
        messages.error(request, "No audit or keyword research dashboard available for this client.")

    # Pass the client, report, and report types to the template
    return render(
        request,
        'report/landing.html',
        {
            'client': client,
            'report': report,
            'report_types': report_types,
        }
    )




def client_list(request):
    # Fetch all clients
    clients = ClientOnboarding.objects.all()

    # Render a template that lists the clients
    return render(request, 'report/client_list.html', {'clients': clients})


# View for Google Search Console Report
def google_search_console_report(request, client_id):
    try:
        # Fetch the client from the database
        client = get_object_or_404(ClientOnboarding, id=client_id)

        # Get the selected date range and compare flag from the request
        date_range = request.GET.get('date_range', '30')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        compare = request.GET.get('compare', 'false') == 'true'

        # Calculate the start and end dates based on the selected range
        if date_range == 'custom' and start_date and end_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError as ve:
                logger.error(f"Invalid date format: {ve}")
                return HttpResponseBadRequest("Invalid date format. Please use YYYY-MM-DD.")
            start_date = start_date_obj.strftime('%Y-%m-%d')
            end_date = end_date_obj.strftime('%Y-%m-%d')
        else:
            days_map = {
                '7': 7,
                '14': 14,
                '28': 28,
                '30': 30,
                '90': 90,
                '180': 180,
                '365': 365,
            }
            days = days_map.get(date_range, 30)  # Default to 30 days if no valid option is selected
            start_date_obj = datetime.now() - timedelta(days=days)
            end_date_obj = datetime.now()
            start_date = start_date_obj.strftime('%Y-%m-%d')
            end_date = end_date_obj.strftime('%Y-%m-%d')

        # Calculate the start and end dates for the previous period
        prev_start_date_obj = start_date_obj - timedelta(days=days)
        prev_end_date_obj = end_date_obj - timedelta(days=days)
        prev_start_date = prev_start_date_obj.strftime('%Y-%m-%d')
        prev_end_date = prev_end_date_obj.strftime('%Y-%m-%d')

        site_url = client.website_url  # Assuming website_url is part of ClientOnboarding

        logger.debug(
            f"Client ID: {client_id}, Site URL: {site_url}, Date Range: {date_range}, Start Date: {start_date}, End Date: {end_date}, Compare: {compare}"
        )

        # Fetch data for the current period
        current_page_data = fetch_search_console_data(
            request, site_url, start_date, end_date, dimensions=['page']
        )
        if isinstance(current_page_data, HttpResponse):
            return current_page_data

        current_query_data = fetch_search_console_data(
            request, site_url, start_date, end_date, dimensions=['query'], row_limit=10
        )
        if isinstance(current_query_data, HttpResponse):
            return current_query_data

        # Fetch data for the previous period
        previous_page_data = fetch_search_console_data(
            request, site_url, prev_start_date, prev_end_date, dimensions=['page']
        )
        if isinstance(previous_page_data, HttpResponse):
            return previous_page_data

        previous_query_data = fetch_search_console_data(
            request, site_url, prev_start_date, prev_end_date, dimensions=['query'], row_limit=10
        )
        if isinstance(previous_query_data, HttpResponse):
            return previous_query_data

        # Map previous data by key for easy comparison
        prev_page_map = {
            row['keys'][0]: row for row in previous_page_data if 'keys' in row and row['keys']
        }
        prev_query_map = {
            row['keys'][0]: row for row in previous_query_data if 'keys' in row
        }

        # Calculate traffic loss for each page
        traffic_loss_data = []
        for row in current_page_data:
            url = row['keys'][0] if 'keys' in row else ''
            current_clicks = row.get('clicks', 0)
            prev_clicks = prev_page_map.get(url, {}).get('clicks', 0)
            traffic_loss = prev_clicks - current_clicks  # Positive if there was traffic loss
            if traffic_loss > 0:
                traffic_loss_data.append(
                    {
                        'url': url,
                        'clicks_loss': traffic_loss,
                        'current_clicks': current_clicks,
                        'prev_clicks': prev_clicks,
                        'impressions': row.get('impressions', 0),
                        'ctr': row.get('ctr', 0),
                        'position': row.get('position', 0),
                    }
                )

        # Sort by the largest traffic loss and limit to top 10
        traffic_loss_data = sorted(
            traffic_loss_data, key=lambda x: x['clicks_loss'], reverse=True
        )[:10]

        # Calculate total metrics for the current period
        total_clicks = sum(row.get('clicks', 0) for row in current_page_data)
        total_impressions = sum(row.get('impressions', 0) for row in current_page_data)
        total_ctr = (
            (total_clicks / total_impressions) * 100 if total_impressions > 0 else 0
        )
        avg_position = (
            sum(row.get('position', 0) for row in current_page_data) / len(current_page_data)
            if current_page_data
            else 0
        )

        # Calculate total metrics for the previous period
        previous_total_clicks = sum(row.get('clicks', 0) for row in previous_page_data)
        previous_total_impressions = sum(
            row.get('impressions', 0) for row in previous_page_data
        )
        previous_total_ctr = (
            (previous_total_clicks / previous_total_impressions) * 100
            if previous_total_impressions > 0
            else 0
        )
        previous_avg_position = (
            sum(row.get('position', 0) for row in previous_page_data)
            / len(previous_page_data)
            if previous_page_data
            else 0
        )

        # Calculate deltas if compare is enabled
        if compare:
            delta_total_clicks = total_clicks - previous_total_clicks
            delta_total_impressions = total_impressions - previous_total_impressions
            delta_total_ctr = total_ctr - previous_total_ctr
            delta_avg_position = avg_position - previous_avg_position
        else:
            delta_total_clicks = 0
            delta_total_impressions = 0
            delta_total_ctr = 0
            delta_avg_position = 0

        # Get top 10 performing pages for the current period
        top_pages = sorted(
            current_page_data, key=lambda x: x.get('clicks', 0), reverse=True
        )[:10]

        # Add 'url' key to each row in top_pages
        for row in top_pages:
            row['url'] = row['keys'][0] if 'keys' in row else ''

        # Get top 10 queries for the current period
        top_queries = sorted(
            current_query_data, key=lambda x: x.get('clicks', 0), reverse=True
        )[:10]

        # Add 'query' key to each row in top_queries
        for row in top_queries:
            row['query'] = row['keys'][0] if 'keys' in row else ''

        # If compare is enabled, calculate deltas for top_pages and top_queries
        if compare:
            top_pages_with_delta = []
            for row in top_pages:
                url = row['url']
                prev_row = prev_page_map.get(url, {})
                prev_clicks = prev_row.get('clicks', 0)
                prev_impressions = prev_row.get('impressions', 0)
                prev_ctr = prev_row.get('ctr', 0)
                prev_position = prev_row.get('position', 0)

                delta_clicks = row.get('clicks', 0) - prev_clicks
                delta_impressions = row.get('impressions', 0) - prev_impressions
                delta_ctr = row.get('ctr', 0) - prev_ctr
                delta_position = row.get('position', 0) - prev_position

                top_pages_with_delta.append(
                    {
                        'url': url,
                        'clicks': row.get('clicks', 0),
                        'impressions': row.get('impressions', 0),
                        'ctr': row.get('ctr', 0),
                        'position': row.get('position', 0),
                        'delta_clicks': delta_clicks,
                        'delta_impressions': delta_impressions,
                        'delta_ctr': delta_ctr,
                        'delta_position': delta_position,
                    }
                )

            # Get top 10 queries for the previous period to calculate deltas
            top_queries_with_delta = []
            for row in top_queries:
                query = row['query']
                prev_row = prev_query_map.get(query, {})
                prev_clicks = prev_row.get('clicks', 0)
                prev_impressions = prev_row.get('impressions', 0)
                prev_ctr = prev_row.get('ctr', 0)
                prev_position = prev_row.get('position', 0)

                delta_clicks = row.get('clicks', 0) - prev_clicks
                delta_impressions = row.get('impressions', 0) - prev_impressions
                delta_ctr = row.get('ctr', 0) - prev_ctr
                delta_position = row.get('position', 0) - prev_position

                top_queries_with_delta.append(
                    {
                        'query': query,
                        'clicks': row.get('clicks', 0),
                        'impressions': row.get('impressions', 0),
                        'ctr': row.get('ctr', 0),
                        'position': row.get('position', 0),
                        'delta_clicks': delta_clicks,
                        'delta_impressions': delta_impressions,
                        'delta_ctr': delta_ctr,
                        'delta_position': delta_position,
                    }
                )

            # Update top_pages and top_queries with delta data
            top_pages = top_pages_with_delta
            top_queries = top_queries_with_delta

        # Render the template with all necessary data
        context = {
            'client': client,
            'total_clicks': total_clicks,
            'total_impressions': total_impressions,
            'total_ctr': total_ctr,
            'avg_position': avg_position,
            'previous_total_clicks': previous_total_clicks,
            'previous_total_impressions': previous_total_impressions,
            'previous_total_ctr': previous_total_ctr,
            'previous_avg_position': previous_avg_position,
            'top_pages': top_pages,
            'traffic_loss_data': traffic_loss_data,
            'top_queries': top_queries,
            'date_range': date_range,
            'start_date': start_date,
            'end_date': end_date,
            'compare': compare,
            'delta_total_clicks': delta_total_clicks,
            'delta_total_impressions': delta_total_impressions,
            'delta_total_ctr': delta_total_ctr,
            'delta_avg_position': delta_avg_position,
        }

        return render(request, 'report/search_console_detail.html', context)

    except Exception as e:
        logger.error(
            f"Error in google_search_console_report for client_id {client_id}: {str(e)}",
            exc_info=True,
        )
        return HttpResponseServerError(
            "An internal server error occurred while processing the report."
        )




# View for Keyword Research Report
def keyword_research_report(request, client_id):
    client = get_object_or_404(ClientOnboarding, id=client_id)

    # Fetch Keyword Research data (replace with actual logic)
    # Placeholder data
    keyword_data = [
        {'keyword': 'SEO', 'volume': 5000, 'ranking': 1},
        {'keyword': 'digital marketing', 'volume': 3000, 'ranking': 3},
    ]

    return render(
        request, 'report/keyword_research_detail.html', {'client': client, 'data': keyword_data}
    )


# View for Website Audit Report
def website_audit_report(request, client_id):
    client = get_object_or_404(ClientOnboarding, id=client_id)

    # Fetch Website Audit data (replace with actual logic)
    # Placeholder data
    audit_data = {
        'total_pages': 100,
        'errors': 5,
        'warnings': 10,
        'notices': 50,
    }

    return render(
        request, 'report/website_audit_detail.html', {'client': client, 'data': audit_data}
    )


def get_property_id_for_website(website_url):
    # Try to get property ID from cache
    cache_key = f'property_id_{website_url}'
    property_id = cache.get(cache_key)
    if property_id:
        logger.debug(f"Cache hit for website {website_url}: Property ID {property_id}")
        return property_id

    logger.debug(f"Cache miss for website {website_url}. Looking up property ID.")
    
    creds = get_analytics_credentials()
    if not creds:
        logger.error("Could not obtain Analytics credentials.")
        return None

    admin_client = AnalyticsAdminServiceClient(credentials=creds)

    try:
        # Parse the website_url to get the domain
        website_domain = urlparse(website_url).netloc.lower().replace('www.', '').strip('/')
        logger.debug(f"Website domain to match: {website_domain}")

        # Fetch all account summaries accessible by the service account
        account_summaries = admin_client.list_account_summaries()
        for account_summary in account_summaries:
            for property_summary in account_summary.property_summaries:
                property_name = property_summary.property  # e.g., 'properties/123456789'
                property_id = property_name.split('/')[-1]

                # Now, list data streams for this property
                data_streams = admin_client.list_data_streams(parent=property_name)
                for data_stream in data_streams:
                    if data_stream.type_ == data_stream.DataStreamType.WEB_DATA_STREAM:
                        default_uri = data_stream.web_stream_data.default_uri
                        # Parse default_uri to get the domain
                        default_domain = urlparse(default_uri).netloc.lower().replace('www.', '').strip('/')
                        logger.debug(f"Checking default_domain: {default_domain} against website_domain: {website_domain}")
                        if default_domain == website_domain:
                            logger.info(f"Found property ID {property_id} for website {website_url}")
                            # Cache the property ID
                            cache.set(cache_key, property_id, timeout=86400)  # Cache for 1 day (86400 seconds)
                            return property_id

        logger.warning(f"No property found for website URL: {website_url}")
        return None

    except Exception as e:
        logger.error(f"Error fetching property ID for website {website_url}: {str(e)}", exc_info=True)
        return None


def format_duration(duration):
    """Format duration from seconds to 'minutes:seconds'."""
    try:
        duration = float(duration)
        if duration < 0:
            duration = 0
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        return f'{minutes}:{seconds:02}'
    except (ValueError, TypeError):
        return '0:00'



def fetch_ga4_data(property_id, start_date='30daysAgo', end_date='today'):
    """Fetch GA4 data for the given property ID using service account credentials."""
    creds = get_analytics_credentials()
    if not creds:
        logger.error("Could not obtain Analytics credentials.")
        return None

    client = BetaAnalyticsDataClient(credentials=creds)

    try:
        # Fetch overview metrics
        request_metrics = RunReportRequest(
            property=f'properties/{property_id}',
            date_ranges=[{"start_date": start_date, "end_date": end_date}],
            metrics=[
                {"name": "totalUsers"},
                {"name": "newUsers"},
                {"name": "sessions"},
                {"name": "bounceRate"},
            ],
        )

        metrics_response = client.run_report(request_metrics)
        data = {}
        if metrics_response.rows:
            row = metrics_response.rows[0]
            for i, metric in enumerate(request_metrics.metrics):
                if metric.name in ['totalUsers', 'newUsers', 'sessions']:
                    data[metric.name] = int(row.metric_values[i].value)
                elif metric.name == 'bounceRate':
                    data[metric.name] = float(row.metric_values[i].value)
                else:
                    data[metric.name] = row.metric_values[i].value

        # Fetch top pages
        request_pages = RunReportRequest(
            property=f'properties/{property_id}',
            date_ranges=[{"start_date": start_date, "end_date": end_date}],
            dimensions=[{"name": "pagePath"}],
            metrics=[
                {"name": "screenPageViews"},
                {"name": "activeUsers"},
                {"name": "sessions"},
                {"name": "bounceRate"},
                {"name": "averageSessionDuration"},
            ],
            order_bys=[
                {"metric": {"metric_name": "screenPageViews"}, "desc": True}
            ],
            limit=10,
        )

        pages_response = client.run_report(request_pages)
        top_pages = []
        for row in pages_response.rows:
            page_data = {}
            for i, dimension in enumerate(request_pages.dimensions):
                page_data[dimension.name] = row.dimension_values[i].value
            for i, metric in enumerate(request_pages.metrics):
                value = row.metric_values[i].value
                if metric.name == 'averageSessionDuration':
                    value = format_duration(value)  # Converts to "MM:SS"
                elif metric.name in ['activeUsers', 'sessions', 'screenPageViews']:
                    value = int(value)
                elif metric.name == 'bounceRate':
                    value = float(value)
                else:
                    value = value
                page_data[metric.name] = value
            top_pages.append(page_data)

        data['top_pages'] = top_pages

        return data

    except Exception as e:
        logger.error(f"Error fetching GA4 data: {str(e)}", exc_info=True)
        return None




def google_analytics_report(request, client_id):
    client = get_object_or_404(ClientOnboarding, id=client_id)

    # Get the property ID for the client's website URL
    property_id = get_property_id_for_website(client.website_url)
    if not property_id:
        return render(request, 'report/google_analytics_detail.html', {
            'error_message': f"No GA4 property found for website URL: {client.website_url}"
        })

    # Get the selected date range and compare flag from the request
    date_range = request.GET.get('date_range', '30')
    compare = request.GET.get('compare', 'false') == 'true'
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Calculate the start and end dates based on the selected range
    if date_range == 'custom' and start_date and end_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError as ve:
            logger.error(f"Invalid date format: {ve}")
            return HttpResponseBadRequest("Invalid date format. Please use YYYY-MM-DD.")
        start_date_str = start_date_obj.strftime('%Y-%m-%d')
        end_date_str = end_date_obj.strftime('%Y-%m-%d')
    else:
        days_map = {
            '7': 7,
            '14': 14,
            '28': 28,
            '30': 30,
            '90': 90,
            '180': 180,
            '365': 365,
        }
        days = days_map.get(date_range, 30)  # Default to 30 days
        end_date_obj = datetime.now().date()
        start_date_obj = end_date_obj - timedelta(days=days)
        start_date_str = start_date_obj.strftime('%Y-%m-%d')
        end_date_str = end_date_obj.strftime('%Y-%m-%d')

    # Calculate comparison dates if compare is True
    if compare:
        delta = end_date_obj - start_date_obj
        prev_end_date_obj = start_date_obj - timedelta(days=1)
        prev_start_date_obj = prev_end_date_obj - delta
        prev_start_date_str = prev_start_date_obj.strftime('%Y-%m-%d')
        prev_end_date_str = prev_end_date_obj.strftime('%Y-%m-%d')
    else:
        prev_start_date_str = prev_end_date_str = None

    # Fetch data for the current period
    analytics_data = fetch_ga4_data(property_id, start_date_str, end_date_str)
    if not analytics_data:
        return render(request, 'report/google_analytics_detail.html', {
            'error_message': "No analytics data fetched for the current period."
        })

    # Extract metrics
    active_users = analytics_data.get('totalUsers', 0)
    new_users = analytics_data.get('newUsers', 0)
    sessions = analytics_data.get('sessions', 0)
    bounce_rate = analytics_data.get('bounceRate', 0.0)
    top_pages = analytics_data.get('top_pages', [])

    # Prepare data for the graph (e.g., daily sessions)
    graph_dates = []      # e.g., ["2024-10-01", "2024-10-02", ...]
    graph_sessions = []   # e.g., [120, 150, 130, ...]

    # Fetch time-series data for the graph
    try:
        client_ts = BetaAnalyticsDataClient(credentials=get_analytics_credentials())
        request_ts = RunReportRequest(
            property=f'properties/{property_id}',
            date_ranges=[{"start_date": start_date_str, "end_date": end_date_str}],
            dimensions=[{"name": "date"}],
            metrics=[{"name": "sessions"}],
            order_bys=[{"dimension": {"dimension_name": "date"}}],
        )
        response_ts = client_ts.run_report(request_ts)
        for row in response_ts.rows:
            graph_dates.append(row.dimension_values[0].value)
            graph_sessions.append(int(row.metric_values[0].value))
    except Exception as e:
        logger.error(f"Error fetching time-series data: {str(e)}", exc_info=True)

    # Initialize delta variables with default values
    delta_active_users = delta_new_users = delta_sessions = delta_bounce_rate = None
    delta_active_users_sign = delta_new_users_sign = delta_sessions_sign = delta_bounce_rate_sign = None
    delta_active_users_value = delta_new_users_value = delta_sessions_value = delta_bounce_rate_value = None

    # If compare is True, fetch data for the previous period and calculate deltas
    if compare:
        prev_analytics_data = fetch_ga4_data(property_id, prev_start_date_str, prev_end_date_str)
        if not prev_analytics_data:
            return render(request, 'report/google_analytics_detail.html', {
                'error_message': "No analytics data fetched for the comparison period."
            })

        # Extract previous period metrics
        prev_active_users = prev_analytics_data.get('totalUsers', 0)
        prev_new_users = prev_analytics_data.get('newUsers', 0)
        prev_sessions = prev_analytics_data.get('sessions', 0)
        prev_bounce_rate = prev_analytics_data.get('bounceRate', 0.0)
        prev_top_pages = prev_analytics_data.get('top_pages', [])

        # Calculate differences
        delta_active_users = active_users - prev_active_users
        delta_new_users = new_users - prev_new_users
        delta_sessions = sessions - prev_sessions
        delta_bounce_rate = bounce_rate - prev_bounce_rate

        # Determine the sign for each delta and calculate absolute values
        if delta_active_users > 0:
            delta_active_users_sign = 'positive'
            delta_active_users_value = delta_active_users
        elif delta_active_users < 0:
            delta_active_users_sign = 'negative'
            delta_active_users_value = abs(delta_active_users)
        else:
            delta_active_users_sign = 'no_change'
            delta_active_users_value = 0

        if delta_new_users > 0:
            delta_new_users_sign = 'positive'
            delta_new_users_value = delta_new_users
        elif delta_new_users < 0:
            delta_new_users_sign = 'negative'
            delta_new_users_value = abs(delta_new_users)
        else:
            delta_new_users_sign = 'no_change'
            delta_new_users_value = 0

        if delta_sessions > 0:
            delta_sessions_sign = 'positive'
            delta_sessions_value = delta_sessions
        elif delta_sessions < 0:
            delta_sessions_sign = 'negative'
            delta_sessions_value = abs(delta_sessions)
        else:
            delta_sessions_sign = 'no_change'
            delta_sessions_value = 0

        if delta_bounce_rate > 0:
            delta_bounce_rate_sign = 'positive'
            delta_bounce_rate_value = delta_bounce_rate
        elif delta_bounce_rate < 0:
            delta_bounce_rate_sign = 'negative'
            delta_bounce_rate_value = abs(delta_bounce_rate)
        else:
            delta_bounce_rate_sign = 'no_change'
            delta_bounce_rate_value = 0.0

        # Merge top pages data
        prev_pages_dict = {page['pagePath']: page for page in prev_top_pages}
        for page in top_pages:
            page_path = page['pagePath']
            prev_page = prev_pages_dict.get(page_path)
            if prev_page:
                # Calculate delta_activeUsers
                page['delta_activeUsers'] = page['activeUsers'] - prev_page['activeUsers']
                if page['delta_activeUsers'] > 0:
                    page['delta_activeUsers_sign'] = 'positive'
                    page['delta_activeUsers_value'] = page['delta_activeUsers']
                elif page['delta_activeUsers'] < 0:
                    page['delta_activeUsers_sign'] = 'negative'
                    page['delta_activeUsers_value'] = abs(page['delta_activeUsers'])
                else:
                    page['delta_activeUsers_sign'] = 'no_change'
                    page['delta_activeUsers_value'] = 0

                # Calculate delta_sessions
                page['delta_sessions'] = page['sessions'] - prev_page['sessions']
                if page['delta_sessions'] > 0:
                    page['delta_sessions_sign'] = 'positive'
                    page['delta_sessions_value'] = page['delta_sessions']
                elif page['delta_sessions'] < 0:
                    page['delta_sessions_sign'] = 'negative'
                    page['delta_sessions_value'] = abs(page['delta_sessions'])
                else:
                    page['delta_sessions_sign'] = 'no_change'
                    page['delta_sessions_value'] = 0

                # Calculate delta_bounceRate
                page['delta_bounceRate'] = page['bounceRate'] - prev_page['bounceRate']
                if page['delta_bounceRate'] > 0:
                    page['delta_bounce_rate_sign'] = 'positive'
                    page['delta_bounce_rate_value'] = page['delta_bounceRate']
                elif page['delta_bounceRate'] < 0:
                    page['delta_bounce_rate_sign'] = 'negative'
                    page['delta_bounce_rate_value'] = abs(page['delta_bounceRate'])
                else:
                    page['delta_bounce_rate_sign'] = 'no_change'
                    page['delta_bounce_rate_value'] = 0.0

                # Calculate delta_averageSessionDuration
                main_duration = parse_duration(page['averageSessionDuration'])  # in seconds
                prev_duration = parse_duration(prev_page['averageSessionDuration'])  # in seconds
                delta_duration_seconds = main_duration - prev_duration
                page['delta_averageSessionDuration'] = format_duration_seconds(delta_duration_seconds)

                if delta_duration_seconds > 0:
                    page['delta_averageSessionDuration_sign'] = 'positive'
                    page['delta_averageSessionDuration_value'] = format_duration_seconds(delta_duration_seconds)
                elif delta_duration_seconds < 0:
                    page['delta_averageSessionDuration_sign'] = 'negative'
                    page['delta_averageSessionDuration_value'] = format_duration_seconds(delta_duration_seconds)
                else:
                    page['delta_averageSessionDuration_sign'] = 'no_change'
                    page['delta_averageSessionDuration_value'] = '0:00'

            else:
                # If no comparison data exists for this page_path, set differences to default
                page['delta_activeUsers_sign'] = 'no_change'
                page['delta_activeUsers_value'] = 0
                page['delta_sessions_sign'] = 'no_change'
                page['delta_sessions_value'] = 0
                page['delta_bounce_rate_sign'] = 'no_change'
                page['delta_bounce_rate_value'] = 0.0
                page['delta_averageSessionDuration_sign'] = 'no_change'
                page['delta_averageSessionDuration_value'] = '0:00'

    # If compare is False, ensure delta variables are set to default
    else:
        delta_active_users_sign = 'no_change'
        delta_active_users_value = 0
        delta_new_users_sign = 'no_change'
        delta_new_users_value = 0
        delta_sessions_sign = 'no_change'
        delta_sessions_value = 0
        delta_bounce_rate_sign = 'no_change'
        delta_bounce_rate_value = 0.0

    # Pass all data to the template
    context = {
        'client': client,
        'active_users': active_users,
        'new_users': new_users,
        'sessions': sessions,
        'bounce_rate': bounce_rate,
        'top_pages': top_pages,
        'delta_active_users': delta_active_users,
        'delta_new_users': delta_new_users,
        'delta_sessions': delta_sessions,
        'delta_bounce_rate': delta_bounce_rate,
        'delta_active_users_sign': delta_active_users_sign,
        'delta_active_users_value': delta_active_users_value,
        'delta_new_users_sign': delta_new_users_sign,
        'delta_new_users_value': delta_new_users_value,
        'delta_sessions_sign': delta_sessions_sign,
        'delta_sessions_value': delta_sessions_value,
        'delta_bounce_rate_sign': delta_bounce_rate_sign,
        'delta_bounce_rate_value': delta_bounce_rate_value,
        'date_range': date_range,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'compare': compare,
        'graph_dates': graph_dates,
        'graph_sessions': graph_sessions,
    }

    return render(request, 'report/google_analytics_detail.html', context)




def parse_duration(duration_str):
    """Convert 'minutes:seconds' string to total seconds."""
    try:
        minutes, seconds = map(int, duration_str.split(':'))
        return minutes * 60 + seconds
    except (ValueError, TypeError):
        return 0

def format_duration_seconds(total_seconds):
    """Convert total seconds to 'minutes:seconds' format, handling negative durations."""
    try:
        is_negative = total_seconds < 0
        total_seconds = abs(int(total_seconds))
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        duration_str = f"{minutes}:{seconds:02}"
        return f"-{duration_str}" if is_negative else duration_str
    except (ValueError, TypeError):
        return '0:00'


