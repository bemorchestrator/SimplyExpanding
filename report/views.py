# report/views.py

from datetime import datetime, timedelta
import logging
from pyexpat.errors import messages

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

from audit.models import AuditDashboard
from client.models import ClientOnboarding
from report.models import Report

logger = logging.getLogger(__name__)

# Path to your service account key JSON file for Google Search Console access
SERVICE_ACCOUNT_SEARCH_CONSOLE_FILE = r'C:\Users\bem\Desktop\credentials\se_service_account.json'  # Update with your actual path


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

    # Fetch the audit dashboard for this specific client using the model, not the view
    audit_dashboard = AuditDashboard.objects.filter(user=client.user).first()

    # Handle case where no audit dashboard exists for this client
    if not audit_dashboard:
        messages.error(request, "No audit dashboard available for this client.")
        return redirect('some_default_view')  # Redirect to a default page or handle error

    # Define the available report types for the client
    report_types = [
        {
            'name': 'Google Search Console',
            'report_type': 'google_search_console',
            'url': reverse('google_search_console_report', kwargs={'client_id': client.id}),
        },
        {
            'name': 'Google Analytics',
            'report_type': 'google_analytics',
            'url': reverse('google_analytics_report', kwargs={'client_id': client.id}),
        },
        {
            'name': 'Keyword Research',
            'report_type': 'keyword_research',
            'url': reverse('keyword_research_report', kwargs={'client_id': client.id}),
        },
        {
            'name': 'Website Audit',
            'report_type': 'website_audit',
            'url': reverse('load_dashboard', kwargs={'id': audit_dashboard.id}),  # Corrected here
        },
    ]

    # Pass the client, report, and report types to the template
    return render(
        request,
        'report/landing.html',
        {'client': client, 'report': report, 'report_types': report_types},
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


# View for Google Analytics Report
def google_analytics_report(request, client_id):
    client = get_object_or_404(ClientOnboarding, id=client_id)

    # Fetch Google Analytics data (replace with actual logic)
    # Placeholder data
    analytics_data = {
        'sessions': 1000,
        'bounce_rate': '50%',
        'avg_session_duration': '2 minutes',
    }

    return render(
        request, 'report/google_analytics_detail.html', {'client': client, 'data': analytics_data}
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
