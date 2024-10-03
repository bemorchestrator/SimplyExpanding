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

        # Log available sites for debugging
        logger.info(f"User has access to the following sites in Search Console: {available_sites}")

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

        if request.method == 'POST' or (
            request.method == 'GET' and 
            all(param in request.GET for param in ['input_url', 'start_date', 'end_date', 'row_limit'])
        ):
            if request.method == 'POST':
                input_url = request.POST.get('input_url').strip()
                start_date = request.POST.get('start_date')
                end_date = request.POST.get('end_date')
                row_limit = request.POST.get('row_limit')
                sort = request.POST.get('sort', '')
                order = request.POST.get('order', '')
            else:
                input_url = request.GET.get('input_url').strip()
                start_date = request.GET.get('start_date')
                end_date = request.GET.get('end_date')
                row_limit = request.GET.get('row_limit')
                sort = request.GET.get('sort', '')
                order = request.GET.get('order', '')

            # Normalize the input URL by adding scheme if missing
            if not input_url.startswith(('http://', 'https://')):
                input_url = 'https://' + input_url
                logger.debug(f"No scheme found in input URL. Normalized input URL to: {input_url}")

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

            # Create request body
            try:
                row_limit_int = int(row_limit)
            except ValueError:
                logger.warning("Row limit must be an integer.")
                return HttpResponseBadRequest("Row limit must be an integer.")

            request_body = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': ['query'],
                'rowLimit': row_limit_int
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
                    'row_limit': row_limit_int,
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
