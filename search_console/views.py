# search_console/views.py

import logging
from urllib.parse import urlparse
from django.http import HttpResponseBadRequest, HttpResponseRedirect, HttpResponseServerError, HttpResponse
from django.shortcuts import redirect, render
from googleapiclient.discovery import build
from google_auth import get_credentials
from datetime import datetime, timedelta
import csv

# Configure logging
logger = logging.getLogger(__name__)


def find_matching_site_url(input_url, available_sites):
    """
    Find the site URL from available_sites that best matches the input_url.
    Handles both domain properties (e.g., 'sc-domain:example.com') and URL-prefix properties (e.g., 'https://www.example.com/').
    Returns the matched site URL or None if no match is found.
    """
    parsed_input_url = urlparse(input_url)
    input_scheme = parsed_input_url.scheme
    input_netloc = parsed_input_url.netloc.lower()
    input_path = parsed_input_url.path.rstrip('/') + '/'

    # If scheme is missing, set it to 'https'
    if not input_scheme:
        input_scheme = 'https'
        logger.debug(f"No scheme found in input URL. Normalized input URL to: {input_scheme}://{input_netloc}{parsed_input_url.path}")

    logger.debug(f"Parsed input URL: scheme={input_scheme}, netloc={input_netloc}, path={parsed_input_url.path}")

    # Reconstruct the normalized input URL
    normalized_input_url = f"{input_scheme}://{input_netloc}{input_path}"

    # First, check for exact matches with available_sites
    input_root_url = f"{input_scheme}://{input_netloc}/"
    if input_root_url in available_sites:
        logger.debug(f"Exact match found: {input_root_url}")
        return input_root_url

    # Prepare a list to store potential matches with their specificity
    potential_matches = []

    for site in available_sites:
        if site.startswith('sc-domain:'):
            # Handle domain properties
            domain = site.split(':', 1)[1].lower()
            if input_netloc == domain or input_netloc.endswith('.' + domain):
                logger.debug(f"Domain property match: {site} matches input domain {input_netloc}")
                # Assign higher specificity to exact domain matches
                potential_matches.append((site, 2))
        else:
            # Handle URL-prefix properties
            site_parsed = urlparse(site)
            site_scheme = site_parsed.scheme
            site_netloc = site_parsed.netloc.lower()
            site_path = site_parsed.path.rstrip('/') + '/'

            # Normalize paths for comparison
            normalized_site_url = f"{site_scheme}://{site_netloc}{site_path}"

            if normalized_input_url.startswith(normalized_site_url):
                logger.debug(f"URL-prefix property match: {site} is a prefix of input URL {input_url}")
                # Assign higher specificity to longer matching prefixes
                potential_matches.append((site, len(normalized_site_url)))

    if not potential_matches:
        logger.warning("No matching site URL found for the input URL.")
        return None

    # Select the most specific match (highest specificity value)
    potential_matches.sort(key=lambda x: x[1], reverse=True)
    best_match = potential_matches[0][0]
    logger.debug(f"Best match selected: {best_match}")
    return best_match


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
        creds = get_credentials(request, 'search_console')  # Pass 'search_console' as the service

        # If creds is a redirect response, return it
        if isinstance(creds, HttpResponseRedirect):
            logger.debug("Credentials not available. Redirecting for authentication.")
            return creds

        if not creds:
            logger.warning("Credentials are missing. Redirecting to authenticate_search_console.")
            return redirect('authenticate_search_console')  # Use the named URL for Search Console authentication

        # Build the Search Console service with the credentials
        service = build('webmasters', 'v3', credentials=creds)
        logger.debug("Search Console service built successfully.")

        # Fetch the list of sites available to the user
        site_list = service.sites().list().execute()
        site_entries = site_list.get('siteEntry', [])
        available_sites = [site['siteUrl'] for site in site_entries]
        logger.debug(f"Available sites: {available_sites}")

        data = None
        input_value = ''
        start_date = ''
        end_date = ''
        row_limit = 10
        sort = ''
        order = ''
        display_all = False  # Flag to control table display
        selected_site = ''
        tab = request.GET.get('tab', 'url')  # Default tab is 'url'

        # Prepare request_data based on request method and 'fetch_data' parameter
        if request.method == 'POST':
            request_data = request.POST
        elif request.method == 'GET' and 'fetch_data' in request.GET:
            request_data = request.GET
        else:
            request_data = {}

        if request_data:
            tab = request_data.get('tab', tab)
            input_value = request_data.get('input_value', '').strip()
            selected_site = request_data.get('selected_site', '')
            start_date = request_data.get('start_date')
            end_date = request_data.get('end_date')
            row_limit = request_data.get('row_limit')
            sort = request_data.get('sort', '')
            order = request_data.get('order', '')
            display_all = request_data.get('display_all') == 'on'

            # Add logging to capture submitted data
            logger.debug(f"Received data: tab={tab}, input_value={input_value}, selected_site={selected_site}, start_date={start_date}, end_date={end_date}, row_limit={row_limit}, sort={sort}, order={order}, display_all={display_all}")

            # Check if the form has been submitted to fetch data
            if 'fetch_data' in request_data:
                # Validate inputs
                if not input_value or not start_date or not end_date or not row_limit:
                    logger.warning("Invalid input received: one or more fields are missing.")
                    return HttpResponseBadRequest("Please provide valid inputs.")

                try:
                    row_limit_int = int(row_limit)
                except ValueError:
                    logger.warning("Row limit must be an integer.")
                    return HttpResponseBadRequest("Row limit must be an integer.")

                if tab == 'url':
                    # Process as URL
                    logger.debug("Processing as URL.")
                    # Normalize the input URL by adding scheme if missing
                    if not input_value.startswith(('http://', 'https://')):
                        input_value = 'https://' + input_value
                        logger.debug(f"No scheme found in input URL. Normalized input URL to: {input_value}")

                    # Find the matching site URL
                    matched_site_url = find_matching_site_url(input_value, available_sites)
                    if not matched_site_url:
                        logger.warning("Input URL does not match any sites in Search Console.")
                        return HttpResponseBadRequest("Input URL does not match any sites in your Search Console account.")
                    logger.debug(f"Matched site URL: {matched_site_url}")

                    # Determine if the input URL is the root domain or a specific page
                    parsed_input_url = urlparse(input_value)
                    parsed_matched_site = urlparse(matched_site_url)
                    matched_scheme = parsed_matched_site.scheme
                    matched_netloc = parsed_matched_site.netloc.lower()
                    matched_path = parsed_matched_site.path.rstrip('/') + '/'

                    # Reconstruct the matched site URL for comparison
                    reconstructed_matched_site_url = f"{matched_scheme}://{matched_netloc}{matched_path}"

                    # Normalize input URL for comparison
                    normalized_input_url = f"{parsed_input_url.scheme}://{parsed_input_url.netloc}{parsed_input_url.path.rstrip('/')}/"

                    if normalized_input_url == reconstructed_matched_site_url:
                        # Input is the root domain; no page_url filter
                        page_url = None
                        logger.debug("Input URL is the root domain. No page_url filter will be applied.")
                    else:
                        # Input URL is a specific page; set page_url filter
                        # Ensure the path starts with '/'
                        input_path = parsed_input_url.path
                        if not input_path.startswith('/'):
                            input_path = '/' + input_path
                        page_url = f"{reconstructed_matched_site_url.rstrip('/')}{input_path}"
                        logger.debug(f"Input URL is a specific page. page_url set to: {page_url}")

                    dimensions = ['query']
                    dimension_filter = None
                    if page_url:
                        dimension_filter = {
                            'dimension': 'page',
                            'operator': 'equals',
                            'expression': page_url
                        }
                    headers = [
                        {'name': '#', 'field': 'index'},
                        {'name': 'Query', 'field': 'query'},
                        {'name': 'Clicks', 'field': 'clicks'},
                        {'name': 'Clicks Δ', 'field': 'clicks_change'},
                        {'name': 'Impressions', 'field': 'impressions'},
                        {'name': 'Impressions Δ', 'field': 'impressions_change'},
                        {'name': 'CTR', 'field': 'ctr'},
                        {'name': 'CTR Δ', 'field': 'ctr_change'},
                        {'name': 'Position', 'field': 'position'},
                        {'name': 'Position Δ', 'field': 'position_change'},
                    ]

                    # Create request body
                    request_body = {
                        'startDate': start_date,
                        'endDate': end_date,
                        'dimensions': dimensions,
                        'rowLimit': row_limit_int
                    }

                    # If dimension filter is specified, add it
                    if dimension_filter:
                        request_body['dimensionFilterGroups'] = [{
                            'filters': [dimension_filter]
                        }]
                        logger.debug(f"Request body with dimension filter: {request_body}")
                    else:
                        logger.debug(f"Request body without dimension filter: {request_body}")

                    try:
                        # Fetch Search Analytics data for the selected period
                        response = service.searchanalytics().query(siteUrl=matched_site_url, body=request_body).execute()
                        logger.debug("Search Analytics data fetched successfully for the selected period.")
                        data = response.get('rows', [])

                        # Convert start_date and end_date to datetime.date objects
                        start_date_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
                        end_date_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

                        delta = end_date_dt - start_date_dt

                        # Compute previous period dates
                        prev_end_date_dt = start_date_dt - timedelta(days=1)
                        prev_start_date_dt = prev_end_date_dt - delta

                        prev_start_date = prev_start_date_dt.strftime('%Y-%m-%d')
                        prev_end_date = prev_end_date_dt.strftime('%Y-%m-%d')

                        # Create request body for previous period
                        prev_request_body = request_body.copy()
                        prev_request_body['startDate'] = prev_start_date
                        prev_request_body['endDate'] = prev_end_date

                        # Fetch Search Analytics data for the previous period
                        prev_response = service.searchanalytics().query(siteUrl=matched_site_url, body=prev_request_body).execute()
                        logger.debug("Search Analytics data fetched successfully for the previous period.")
                        prev_data = prev_response.get('rows', [])

                        # Create a mapping from key to previous data
                        prev_data_dict = {tuple(row['keys']): row for row in prev_data}

                        # Add index and compute deltas
                        for index, row in enumerate(data, start=1):
                            # Add 'query' field and index
                            row['query'] = row['keys'][0]
                            row['index'] = index
                            key = tuple(row['keys'])
                            prev_row = prev_data_dict.get(key)
                            if prev_row:
                                # Compute deltas
                                row['clicks_change'] = row['clicks'] - prev_row['clicks']
                                row['impressions_change'] = row['impressions'] - prev_row['impressions']
                                row['ctr_change'] = row['ctr'] - prev_row['ctr']
                                row['position_change'] = row['position'] - prev_row['position']
                            else:
                                # No data in previous period
                                row['clicks_change'] = 0
                                row['impressions_change'] = 0
                                row['ctr_change'] = 0
                                row['position_change'] = 0

                        # Apply sorting if necessary
                        if data and sort in [header['field'] for header in headers]:
                            reverse = True if order == 'desc' else False
                            if sort == 'query':
                                data.sort(key=lambda x: x.get(sort, ''), reverse=reverse)
                            elif sort == 'index':
                                data.sort(key=lambda x: x['index'], reverse=reverse)
                            else:
                                data.sort(key=lambda x: x.get(sort, 0) or 0, reverse=reverse)

                        # Handle CSV export
                        if 'export_csv' in request.GET:
                            response = HttpResponse(content_type='text/csv')
                            response['Content-Disposition'] = 'attachment; filename="search_console_data.csv"'

                            writer = csv.writer(response)
                            writer.writerow([header['name'] for header in headers])
                            for row in data:
                                writer.writerow([
                                    row.get('index', ''),
                                    row.get('query', ''),
                                    row.get('clicks', ''),
                                    row.get('clicks_change', ''),
                                    row.get('impressions', ''),
                                    row.get('impressions_change', ''),
                                    f"{row.get('ctr', 0)*100:.2f}%",
                                    f"{row.get('ctr_change', 0)*100:.2f}%",
                                    f"{row.get('position', 0):.2f}",
                                    f"{row.get('position_change', 0):.2f}",
                                ])
                            return response

                        return render(request, 'search_console/search_console_data.html', {
                            'data': data,
                            'input_value': input_value,
                            'start_date': start_date,
                            'end_date': end_date,
                            'row_limit': row_limit_int,
                            'headers': headers,
                            'sort': sort,
                            'order': order,
                            'display_all': display_all,
                            'available_sites': available_sites,
                            'selected_site': selected_site,
                            'tab': tab,
                        })
                    except Exception as e:
                        logger.error("Error fetching Search Console data:", exc_info=True)
                        return HttpResponseServerError(f"Error fetching Search Console data: {str(e)}")

                elif tab == 'keyword':
                    # Process as keyword
                    logger.debug("Processing as keyword.")

                    if not selected_site:
                        logger.warning("No site selected for keyword search.")
                        return HttpResponseBadRequest("Please select a site for keyword search.")

                    if selected_site not in available_sites:
                        logger.warning("Selected site is not in available sites.")
                        return HttpResponseBadRequest("Selected site is not available in your Search Console account.")

                    matched_site_url = selected_site

                    # Try both 'equals' and 'contains' operators
                    data_rows = None
                    operators = ['equals', 'contains']

                    for operator in operators:
                        dimensions = ['query', 'page']
                        dimension_filter = {
                            'dimension': 'query',
                            'operator': operator,
                            'expression': input_value
                        }
                        headers = [
                            {'name': '#', 'field': 'index'},
                            {'name': 'Page', 'field': 'page'},
                            {'name': 'Clicks', 'field': 'clicks'},
                            {'name': 'Clicks Δ', 'field': 'clicks_change'},
                            {'name': 'Impressions', 'field': 'impressions'},
                            {'name': 'Impressions Δ', 'field': 'impressions_change'},
                            {'name': 'CTR', 'field': 'ctr'},
                            {'name': 'CTR Δ', 'field': 'ctr_change'},
                            {'name': 'Position', 'field': 'position'},
                            {'name': 'Position Δ', 'field': 'position_change'},
                        ]

                        # Create request body
                        request_body = {
                            'startDate': start_date,
                            'endDate': end_date,
                            'dimensions': dimensions,
                            'dimensionFilterGroups': [{
                                'filters': [dimension_filter]
                            }],
                            'rowLimit': 25000  # Set high to get all data
                        }
                        logger.debug(f"Request body with dimension filter (operator: {operator}): {request_body}")

                        try:
                            # Fetch Search Analytics data for the selected period
                            response = service.searchanalytics().query(siteUrl=matched_site_url, body=request_body).execute()
                            logger.debug(f"Search Analytics data fetched successfully for the selected period with operator '{operator}'.")
                            data_rows = response.get('rows', [])
                            logger.debug(f"Number of rows returned: {len(data_rows)}")
                            if data_rows:
                                break  # Exit the loop if data is found
                        except Exception as e:
                            logger.error(f"Error fetching data with operator '{operator}': {e}", exc_info=True)
                            continue  # Try the next operator

                    if not data_rows:
                        logger.warning("No data returned from Search Console for the specified keyword.")
                        return render(request, 'search_console/search_console_data.html', {
                            'data': None,
                            'input_value': input_value,
                            'start_date': start_date,
                            'end_date': end_date,
                            'row_limit': row_limit,
                            'headers': headers,
                            'sort': sort,
                            'order': order,
                            'display_all': display_all,
                            'available_sites': available_sites,
                            'selected_site': selected_site,
                            'tab': tab,
                            'no_data_message': "No search data available for the specified input."
                        })

                    # Proceed with data processing
                    # Convert start_date and end_date to datetime.date objects
                    start_date_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
                    end_date_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

                    delta = end_date_dt - start_date_dt

                    # Compute previous period dates
                    prev_end_date_dt = start_date_dt - timedelta(days=1)
                    prev_start_date_dt = prev_end_date_dt - delta

                    prev_start_date = prev_start_date_dt.strftime('%Y-%m-%d')
                    prev_end_date = prev_end_date_dt.strftime('%Y-%m-%d')

                    # Create request body for previous period
                    prev_request_body = request_body.copy()
                    prev_request_body['startDate'] = prev_start_date
                    prev_request_body['endDate'] = prev_end_date

                    # Fetch Search Analytics data for the previous period
                    try:
                        prev_response = service.searchanalytics().query(siteUrl=matched_site_url, body=prev_request_body).execute()
                        logger.debug("Search Analytics data fetched successfully for the previous period.")
                        prev_data_rows = prev_response.get('rows', [])
                    except Exception as e:
                        logger.error(f"Error fetching previous period data: {e}", exc_info=True)
                        prev_data_rows = []

                    # Process data to aggregate metrics per page
                    page_data = {}
                    for row in data_rows:
                        keys = row['keys']  # keys[0] = 'query', keys[1] = 'page'
                        page = keys[1]
                        clicks = row.get('clicks', 0)
                        impressions = row.get('impressions', 0)
                        ctr = row.get('ctr', 0)
                        position = row.get('position', 0)
                        if page in page_data:
                            page_data[page]['clicks'] += clicks
                            page_data[page]['impressions'] += impressions
                            total_impressions = page_data[page]['impressions']
                            page_data[page]['ctr'] = page_data[page]['clicks'] / total_impressions if total_impressions else 0
                            page_data[page]['position'] = ((page_data[page]['position'] * (total_impressions - impressions)) + (position * impressions)) / total_impressions if total_impressions else 0
                        else:
                            page_data[page] = {
                                'clicks': clicks,
                                'impressions': impressions,
                                'ctr': ctr,
                                'position': position,
                            }

                    # Process previous data to aggregate metrics per page
                    prev_page_data = {}
                    for row in prev_data_rows:
                        keys = row['keys']  # keys[0] = 'query', keys[1] = 'page'
                        page = keys[1]
                        clicks = row.get('clicks', 0)
                        impressions = row.get('impressions', 0)
                        ctr = row.get('ctr', 0)
                        position = row.get('position', 0)
                        if page in prev_page_data:
                            prev_page_data[page]['clicks'] += clicks
                            prev_page_data[page]['impressions'] += impressions
                            total_impressions = prev_page_data[page]['impressions']
                            prev_page_data[page]['ctr'] = prev_page_data[page]['clicks'] / total_impressions if total_impressions else 0
                            prev_page_data[page]['position'] = ((prev_page_data[page]['position'] * (total_impressions - impressions)) + (position * impressions)) / total_impressions if total_impressions else 0
                        else:
                            prev_page_data[page] = {
                                'clicks': clicks,
                                'impressions': impressions,
                                'ctr': ctr,
                                'position': position,
                            }

                    # Prepare data for rendering
                    data = []
                    for index, (page, metrics) in enumerate(page_data.items(), start=1):
                        row = {
                            'index': index,
                            'page': page,
                            'clicks': metrics['clicks'],
                            'impressions': metrics['impressions'],
                            'ctr': metrics['ctr'],
                            'position': metrics['position'],
                        }
                        prev_metrics = prev_page_data.get(page)
                        if prev_metrics:
                            row['clicks_change'] = metrics['clicks'] - prev_metrics['clicks']
                            row['impressions_change'] = metrics['impressions'] - prev_metrics['impressions']
                            row['ctr_change'] = metrics['ctr'] - prev_metrics['ctr']
                            row['position_change'] = metrics['position'] - prev_metrics['position']
                        else:
                            row['clicks_change'] = 0
                            row['impressions_change'] = 0
                            row['ctr_change'] = 0
                            row['position_change'] = 0
                        data.append(row)

                    # Apply sorting if necessary
                    if data and sort in [header['field'] for header in headers]:
                        reverse = True if order == 'desc' else False
                        if sort == 'page':
                            data.sort(key=lambda x: x.get(sort, ''), reverse=reverse)
                        elif sort == 'index':
                            data.sort(key=lambda x: x['index'], reverse=reverse)
                        else:
                            data.sort(key=lambda x: x.get(sort, 0) or 0, reverse=reverse)

                    # Limit data to row_limit_int
                    data = data[:row_limit_int]

                    # Handle CSV export
                    if 'export_csv' in request.GET:
                        response = HttpResponse(content_type='text/csv')
                        response['Content-Disposition'] = 'attachment; filename="search_console_data.csv"'

                        writer = csv.writer(response)
                        writer.writerow([header['name'] for header in headers])
                        for row in data:
                            writer.writerow([
                                row.get('index', ''),
                                row.get('page', ''),
                                row.get('clicks', ''),
                                row.get('clicks_change', ''),
                                row.get('impressions', ''),
                                row.get('impressions_change', ''),
                                f"{row.get('ctr', 0)*100:.2f}%",
                                f"{row.get('ctr_change', 0)*100:.2f}%",
                                f"{row.get('position', 0):.2f}",
                                f"{row.get('position_change', 0):.2f}",
                            ])
                        return response

                    return render(request, 'search_console/search_console_data.html', {
                        'data': data,
                        'input_value': input_value,
                        'start_date': start_date,
                        'end_date': end_date,
                        'row_limit': row_limit_int,
                        'headers': headers,
                        'sort': sort,
                        'order': order,
                        'display_all': display_all,
                        'available_sites': available_sites,
                        'selected_site': selected_site,
                        'tab': tab,
                    })
                else:
                    logger.warning("Invalid tab selected.")
                    return HttpResponseBadRequest("Invalid tab selected.")
            else:
                # Form was submitted without 'fetch_data'; render the form
                logger.debug("Form submitted without 'fetch_data'; rendering form.")
                return render(request, 'search_console/search_console_data.html', {
                    'data': None,
                    'headers': [],
                    'input_value': input_value,
                    'start_date': start_date,
                    'end_date': end_date,
                    'row_limit': row_limit,
                    'sort': sort,
                    'order': order,
                    'display_all': display_all,
                    'available_sites': available_sites,
                    'selected_site': selected_site,
                    'tab': tab,
                })
        else:
            # On GET request without 'fetch_data', show the form
            logger.debug("Rendering search_console_data form.")
            return render(request, 'search_console/search_console_data.html', {
                'data': None,
                'headers': [],
                'input_value': input_value,
                'start_date': start_date,
                'end_date': end_date,
                'row_limit': row_limit,
                'sort': sort,
                'order': order,
                'display_all': display_all,
                'available_sites': available_sites,
                'selected_site': selected_site,
                'tab': tab,
            })

    except Exception as e:
        logger.error("Error in search_console_data view:", exc_info=True)
        return HttpResponseServerError(f"Error in search_console_data view: {str(e)}")
