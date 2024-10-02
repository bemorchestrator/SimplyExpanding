# views.py

import logging
from urllib.parse import urlparse

from django.http import HttpResponseBadRequest, HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import redirect, render
from googleapiclient.discovery import build
from google_auth import authenticate_user, get_credentials, oauth2_callback

# Configure logging
logger = logging.getLogger(__name__)

def find_matching_site_url(input_url, available_sites):
    """
    Find the site URL from available_sites that best matches the input_url.
    """
    parsed_input_url = urlparse(input_url)
    input_scheme = parsed_input_url.scheme
    input_netloc = parsed_input_url.netloc
    input_root_url = f"{input_scheme}://{input_netloc}/"

    if input_root_url in available_sites:
        return input_root_url

    # Try with 'www.' prefix
    if input_netloc.startswith('www.'):
        netloc_without_www = input_netloc[4:]
        alternative_url = f"{input_scheme}://{netloc_without_www}/"
    else:
        alternative_url = f"{input_scheme}://www.{input_netloc}/"

    if alternative_url in available_sites:
        return alternative_url

    # Try other schemes
    alternative_scheme = 'https' if input_scheme == 'http' else 'http'
    alternative_url = f"{alternative_scheme}://{input_netloc}/"
    if alternative_url in available_sites:
        return alternative_url

    # Try with 'www.' prefix and alternative scheme
    if input_netloc.startswith('www.'):
        netloc_without_www = input_netloc[4:]
        alternative_url = f"{alternative_scheme}://{netloc_without_www}/"
    else:
        alternative_url = f"{alternative_scheme}://www.{input_netloc}/"

    if alternative_url in available_sites:
        return alternative_url

    # If no match found, return None
    return None

def search_console_data(request):
    try:
        logger.debug("Accessing search_console_data view.")

        # Handle email selection
        select_email = request.GET.get('select_email')
        if select_email:
            if select_email in request.session.get('credentials', {}):
                request.session['active_email'] = select_email
                logger.debug(f"Active email set to {select_email}.")
            else:
                logger.warning(f"Selected email {select_email} not in session credentials.")
                return HttpResponseBadRequest("Selected email is not authenticated.")

        # Get the credentials
        creds = get_credentials(request)

        # If creds is a redirect response, return it
        if isinstance(creds, HttpResponseRedirect):
            logger.debug("Credentials not available. Redirecting for authentication.")
            return creds

        if not creds:
            logger.warning("Credentials are missing. Redirecting to authenticate_user.")
            return redirect('authenticate_user')

        # Build the Search Console service with the credentials
        service = build('webmasters', 'v3', credentials=creds)
        logger.debug("Search Console service built successfully.")

        # Fetch the list of sites available to the user
        site_list = service.sites().list().execute()
        site_entries = site_list.get('siteEntry', [])
        available_sites = [site['siteUrl'] for site in site_entries]
        logger.debug(f"Available sites: {available_sites}")

        # Define headers for the table
        headers = [
            {'name': 'Query', 'field': 'query'},
            {'name': 'Clicks', 'field': 'clicks'},
            {'name': 'Impressions', 'field': 'impressions'},
            {'name': 'CTR', 'field': 'ctr'},
            {'name': 'Position', 'field': 'position'},
        ]

        data = None
        input_url = ''
        start_date = ''
        end_date = ''
        row_limit = 10
        sort = ''
        order = ''

        if request.method == 'POST' or (request.method == 'GET' and 'input_url' in request.GET and 'start_date' in request.GET and 'end_date' in request.GET and 'row_limit' in request.GET):
            if request.method == 'POST':
                input_url = request.POST.get('input_url')
                start_date = request.POST.get('start_date')
                end_date = request.POST.get('end_date')
                row_limit = request.POST.get('row_limit')
                sort = request.POST.get('sort', '')
                order = request.POST.get('order', '')
            else:
                input_url = request.GET.get('input_url')
                start_date = request.GET.get('start_date')
                end_date = request.GET.get('end_date')
                row_limit = request.GET.get('row_limit')
                sort = request.GET.get('sort', '')
                order = request.GET.get('order', '')

            # Add logging to capture submitted data
            logger.debug(f"Received data: input_url={input_url}, start_date={start_date}, end_date={end_date}, row_limit={row_limit}, sort={sort}, order={order}")

            # Validate inputs
            if not input_url or not start_date or not end_date or not row_limit:
                logger.warning("Invalid input received: one or more fields are missing.")
                return HttpResponseBadRequest("Please provide valid inputs.")

            # Parse the input URL
            parsed_input_url = urlparse(input_url)
            if not all([parsed_input_url.scheme, parsed_input_url.netloc]):
                logger.warning("Invalid input_url format.")
                return HttpResponseBadRequest("Please provide a valid URL.")

            # Find the matching site URL
            matched_site_url = find_matching_site_url(input_url, available_sites)
            if not matched_site_url:
                logger.warning("Input URL does not match any sites in Search Console.")
                return HttpResponseBadRequest("Input URL does not match any sites in your Search Console account.")
            logger.debug(f"Matched site URL: {matched_site_url}")

            # Determine if the input URL is the root domain or a specific page
            input_path = parsed_input_url.path
            if input_path in ['', '/']:
                # Input is the root domain; no page_url filter
                page_url = None
                logger.debug("Input URL is the root domain. No page_url filter will be applied.")
            else:
                # Input URL is a specific page; set page_url filter
                page_url = f"{matched_site_url.rstrip('/')}{input_path}"
                logger.debug(f"Input URL is a specific page. page_url set to: {page_url}")

            # Create request body
            request_body = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': ['query'],
                'rowLimit': int(row_limit)
            }

            # If page_url is specified, add a filter for it
            if page_url:
                request_body['dimensionFilterGroups'] = [{
                    'filters': [{
                        'dimension': 'page',
                        'operator': 'equals',
                        'expression': page_url
                    }]
                }]
                logger.debug(f"Request body with page_url filter: {request_body}")
            else:
                logger.debug(f"Request body without page_url filter: {request_body}")

            try:
                # Fetch Search Analytics data
                response = service.searchanalytics().query(siteUrl=matched_site_url, body=request_body).execute()
                logger.debug("Search Analytics data fetched successfully.")
                data = response.get('rows', [])

                # Apply sorting if necessary
                if data and sort in ['query', 'clicks', 'impressions', 'ctr', 'position']:
                    reverse = True if order == 'desc' else False
                    if sort == 'query':
                        data.sort(key=lambda x: x['keys'][0], reverse=reverse)
                    else:
                        data.sort(key=lambda x: x.get(sort, 0), reverse=reverse)

                return render(request, 'search_console/search_console_data.html', {
                    'data': data,
                    'input_url': input_url,
                    'start_date': start_date,
                    'end_date': end_date,
                    'row_limit': row_limit,
                    'headers': headers,
                    'sort': sort,
                    'order': order,
                })
            except Exception as e:
                logger.error("Error fetching Search Console data:", exc_info=True)
                return HttpResponseServerError(f"Error fetching Search Console data: {str(e)}")

        # On GET request without parameters, show the form
        logger.debug("Rendering search_console_data form.")
        return render(request, 'search_console/search_console_data.html', {
            'data': None,
            'headers': headers,
            'input_url': input_url,
            'start_date': start_date,
            'end_date': end_date,
            'row_limit': row_limit,
            'sort': sort,
            'order': order,
        })

    except Exception as e:
        logger.error("Error in search_console_data view:", exc_info=True)
        return HttpResponseServerError(f"Error in search_console_data view: {str(e)}")
