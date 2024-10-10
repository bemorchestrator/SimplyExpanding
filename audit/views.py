# views.py
import os
import csv
import re
import requests
import logging
import tempfile
import json
import xml.etree.ElementTree as ET
import cloudscraper
import certifi
import ssl

from requests.exceptions import SSLError, ConnectionError, Timeout, RequestException
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_protect

from .filters import UploadedFileFilter 
from .forms import FileUploadForm, SitemapForm, UploadedFileForm
from .models import UploadedFile, SitemapURL, Sitemap
from .google_drive_utils import upload_file_to_drive
from google_auth import get_credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from django_tables2 import RequestConfig
from django.views.decorators.csrf import csrf_exempt
from .tables import UploadedFileTable 
from .utils import identify_csv_type
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
from django.shortcuts import redirect
from django.contrib import messages
import logging
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google_auth import get_credentials


logger = logging.getLogger(__name__)

# Configure logging: log DEBUG and above messages to a file, and only ERROR messages to the console
file_handler = logging.FileHandler('audit_log.log', mode='a')
file_handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.ERROR)  # Only show top-level errors in the terminal

# Set the logging format
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Get the root logger and configure it
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)  # Log all levels to the file
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# Define the fixed folder ID for Google Drive
GOOGLE_DRIVE_FIXED_FOLDER_ID = '1yEieevdY2PQgJH4eV4QIcdLO5kJ-w1nB'



def audit_result(request):
    # Order the audit_data queryset by 'id' to ensure consistent ordering across pages
    audit_data = UploadedFile.objects.all().order_by('id')  # You can replace 'id' with any other field if needed
    logging.info(f"Audit data retrieved for dashboard: {len(audit_data)} files.")

    # Pagination Logic
    page_number = request.GET.get('page', 1)
    rows_per_page = request.GET.get('rows', 15)  # Default to 25 rows per page

    # Ensure rows_per_page is an integer
    try:
        rows_per_page = int(rows_per_page)
        if rows_per_page <= 0:
            rows_per_page = 15
    except ValueError:
        rows_per_page = 15

    paginator = Paginator(audit_data, rows_per_page)

    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver the first page
        page_obj = paginator.get_page(1)
    except EmptyPage:
        # If page is out of range, deliver the last page of results
        page_obj = paginator.get_page(paginator.num_pages)

    return render(request, 'audit/audit_dashboard.html', {
        'audit_data': page_obj,
        'paginator': paginator,
        'page_obj': page_obj,
        'rows_per_page': rows_per_page,  # Pass rows_per_page to the template
    })


def normalize_url(url):
    url = url.strip().lower()  # Convert to lowercase and strip spaces
    if url.endswith('/'):
        url = url[:-1]  # Remove trailing slash if present
    return url


def upload_file(request):
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            logging.info(f"File upload initiated: {file.name}, size: {file.size} bytes")

            if file.size > 10485760:  # Limit file size to 10MB
                messages.error(request, "File too large. The maximum file size is 10MB.")
                logging.warning(f"File too large: {file.name}, size: {file.size} bytes")
                return render(request, 'audit/upload.html', {'form': form})

            temp_file_path = None
            try:
                # Create a temporary file for uploading
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_file_path = temp_file.name
                    for chunk in file.chunks():
                        temp_file.write(chunk)
                    temp_file.flush()
                    logging.info(f"Temporary file created: {temp_file_path}")

                # Step 1: Get Google Drive credentials
                creds = get_credentials(request, 'drive')
                if not creds:
                    messages.error(request, "Google Drive authentication failed.")
                    logging.error("Google Drive authentication failed.")
                    return redirect('authenticate_user')

                # Step 2: Upload the file to Google Drive
                try:
                    service = build('drive', 'v3', credentials=creds)
                    file_metadata = {
                        'name': file.name,
                        'parents': [GOOGLE_DRIVE_FIXED_FOLDER_ID],
                        'mimeType': 'text/csv'
                    }
                    media = MediaFileUpload(temp_file_path, mimetype='text/csv')

                    uploaded_file_drive = service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id, webViewLink'
                    ).execute()

                    drive_file_id = uploaded_file_drive.get('id')
                    drive_file_link = uploaded_file_drive.get('webViewLink')

                    logging.info(f"File uploaded to Google Drive: {drive_file_id}, link: {drive_file_link}")

                    if not drive_file_id or not drive_file_link:
                        raise Exception("Failed to upload file to Google Drive")

                    # Step 3: Process CSV data before storing in the database
                    file.seek(0)  # Reset file pointer to process CSV
                    audit_data = process_csv_file(file)  # Use the updated function

                    if audit_data:
                        for data in audit_data:
                            url = data.get('url')
                            if not url:
                                continue
                            url = normalize_url(url)  # Normalize the URL before processing
                            try:
                                # Try to get existing UploadedFile with matching URL
                                uploaded_file = UploadedFile.objects.filter(url=url).first()
                                if uploaded_file:
                                    # Update fields
                                    uploaded_file.file_name = file.name
                                    uploaded_file.drive_file_id = drive_file_id
                                    uploaded_file.drive_file_link = drive_file_link
                                    # Update all fields from data
                                    for key, value in data.items():
                                        if value is not None:
                                            setattr(uploaded_file, key, value)
                                    uploaded_file.save()
                                    logging.info(f"Updated UploadedFile for URL: {url}")
                                else:
                                    # Create new UploadedFile
                                    data['file_name'] = file.name
                                    data['drive_file_id'] = drive_file_id
                                    data['drive_file_link'] = drive_file_link
                                    data['url'] = url  # Ensure the URL is included
                                    uploaded_file = UploadedFile(**data)
                                    uploaded_file.save()
                                    logging.info(f"Created new UploadedFile for URL: {url}")
                            except Exception as e:
                                logging.error(f"Error processing URL {url}: {e}")

                        messages.success(request, "File uploaded successfully and audit data processed.")

                        # Step 4: Update the 'In Sitemap' status after saving the uploaded data
                        update_in_sitemap_status()  # Call the function to update 'in_sitemap' field
                    else:
                        logging.warning("The CSV file is empty or could not be processed.")
                        messages.error(request, "The CSV file is empty or could not be processed.")

                except Exception as e:
                    logging.error(f"Google Drive upload error: {e}")
                    messages.error(request, f"An error occurred while uploading the file to Google Drive: {e}")
                    return redirect('audit_dashboard')

            except Exception as e:
                logging.error(f"An error occurred during file processing: {e}")
                messages.error(request, f"An error occurred while processing the file: {e}")

            finally:
                # Ensure the file is closed before removing it
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.remove(temp_file_path)
                        logging.info(f"Temporary file deleted: {temp_file_path}")
                    except PermissionError:
                        logging.debug(f"Retry failed to delete temp file. File may still be in use: {temp_file_path}")

            return redirect('audit_dashboard')
    else:
        form = FileUploadForm()

    return render(request, 'audit/upload.html', {'form': form})




def fetch_search_console_data(creds, site_url, start_date, end_date):
    try:
        service = build('searchconsole', 'v1', credentials=creds)
        
        # Define the query for search analytics
        request = {
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': ['page'],
            'rowLimit': 1000  # Adjust the row limit as needed
        }
        
        # Make the API request to get the search analytics data
        response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
        return response.get('rows', [])
    
    except Exception as e:
        logging.error(f"Error fetching data from Google Search Console: {e}")
        return []



def populate_audit_dashboard_with_search_console_data(request):
    site_url = 'https://www.example.com'
    
    # Calculate 6 months ago from today
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=180)).strftime('%Y-%m-%d')  # Approx. 6 months (180 days)

    # Fetch Google Search Console credentials
    creds = get_credentials(request)
    if not creds:
        messages.error(request, "Google Search Console authentication failed.")
        logging.error("Google Search Console authentication failed.")
        return redirect('authenticate_user')

    try:
        # Fetch data using 6-month date range
        rows = fetch_search_console_data(creds, site_url, start_date, end_date)
    except Exception as e:
        logging.error(f"Error fetching data from Google Search Console: {e}")
        messages.error(request, "An error occurred while fetching data from Google Search Console.")
        return redirect('audit_dashboard')
    
    if not rows:
        logging.info(f"No data returned for {site_url} between {start_date} and {end_date}.")
        messages.error(request, "No data found in the last 6 months.")
        return redirect('audit_dashboard')

    # Process and update the audit dashboard with the fetched data
    for row in rows:
        try:
            page_url = row['keys'][0]  # The 'page' dimension (URL)
            impressions = row.get('impressions', 0)
            ctr = row.get('ctr', 0) * 100  # Convert to percentage

            # Update or create the UploadedFile record
            uploaded_file, created = UploadedFile.objects.update_or_create(
                url=page_url,
                defaults={
                    'impressions': impressions,
                    'serp_ctr': ctr,
                }
            )
            if created:
                logging.info(f"Created new record for {page_url} with impressions: {impressions}, CTR: {ctr}%.")
            else:
                logging.info(f"Updated record for {page_url} with impressions: {impressions}, CTR: {ctr}%.")
        except KeyError as e:
            logging.error(f"KeyError while processing row {row}: {e}")
        except Exception as e:
            logging.error(f"Error updating audit data for {page_url}: {e}")

    # Notify the user about the successful update
    messages.success(request, "Audit data updated with the last 6 months of Search Console data.")
    return redirect('audit_dashboard')


def scrape_sitemap(sitemap_url):
    """
    Scrapes the sitemap from the given URL.
    Tries using cloudscraper first, falls back to requests if necessary.
    """
    # Define headers to mimic a real browser
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/91.0.4472.124 Safari/537.36'
        )
    }

    # First attempt with cloudscraper, using TLS 1.2 and certifi for SSL certificates
    scraper = cloudscraper.create_scraper(ssl_context=ssl.SSLContext(ssl.PROTOCOL_TLSv1_2))
    try:
        logging.debug(f"Attempting to fetch sitemap with cloudscraper: {sitemap_url}")
        response = scraper.get(sitemap_url, headers=headers, timeout=10, verify=certifi.where())  # Using certifi certificates
        response.raise_for_status()
        logging.debug(f"Response Status Code with cloudscraper: {response.status_code}")
        logging.debug(f"Response Content (first 500 characters): {response.text[:500]}")

        # Parse the sitemap XML
        return parse_sitemap(response.content, sitemap_url)

    except (SSLError, ConnectionError, Timeout) as e:
        logging.error(f"cloudscraper failed for {sitemap_url}. Error: {e}")
    except RequestException as e:
        logging.error(f"RequestException with cloudscraper for {sitemap_url}. Error: {e}")

    # Fallback attempt with requests, disabling SSL verification
    try:
        logging.debug(f"Attempting to fetch sitemap with requests: {sitemap_url}")
        response = requests.get(sitemap_url, headers=headers, timeout=10, verify=False)  # Disable SSL verification
        response.raise_for_status()
        logging.debug(f"Response Status Code with requests: {response.status_code}")
        logging.debug(f"Response Content (first 500 characters): {response.text[:500]}")

        # Parse the sitemap XML
        return parse_sitemap(response.content, sitemap_url)

    except (SSLError, ConnectionError, Timeout) as e:
        logging.error(f"requests failed for {sitemap_url}. Error: {e}")
    except RequestException as e:
        logging.error(f"RequestException with requests for {sitemap_url}. Error: {e}")

    # If both attempts fail, return None
    logging.warning(f"Both cloudscraper and requests failed to fetch the sitemap: {sitemap_url}")
    return None



def parse_sitemap(content, sitemap_url):
    """
    Parses the sitemap XML content and returns a list of URLs.
    """
    try:
        root = ET.fromstring(content)
        urls = []
        namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

        if root.tag.endswith('sitemapindex'):
            # Sitemap index file
            for sitemap in root.findall('ns:sitemap', namespace):
                loc = sitemap.find('ns:loc', namespace).text
                urls.append(loc)
            logging.info(f"Sitemap index scraped successfully: {sitemap_url}")

        elif root.tag.endswith('urlset'):
            # Regular sitemap file
            for url in root.findall('ns:url', namespace):
                loc = url.find('ns:loc', namespace).text
                urls.append(loc)
            logging.info(f"Sitemap scraped successfully: {sitemap_url}")

        else:
            logging.warning(f"Unknown sitemap type for URL: {sitemap_url}")
            return None

        return urls

    except ET.ParseError as parse_err:
        logging.error(f"XML parsing error for sitemap: {sitemap_url}. Error: {parse_err}")
        return None


@csrf_protect
def crawl_sitemaps(request):
    crawled_results = {}
    form = SitemapForm()

    if request.method == 'POST':
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # Handle AJAX POST request
            form = SitemapForm(request.POST)
            if form.is_valid():
                sitemap_urls = form.cleaned_data['sitemap_urls'].splitlines()
                new_sitemaps = []
                failed_sitemaps = []

                for sitemap_url in sitemap_urls:
                    sitemap_url = sitemap_url.strip()
                    if sitemap_url:
                        urls = scrape_sitemap(sitemap_url)
                        if urls:
                            # Normalize the sitemap URLs before saving them
                            normalized_urls = [normalize_url(url) for url in urls]

                            # Create Sitemap entry
                            sitemap = Sitemap.objects.create(url=sitemap_url)
                            
                            # Save the normalized sitemap URLs
                            sitemap_urls_bulk = [
                                SitemapURL(sitemap=sitemap, url=url) for url in normalized_urls
                            ]
                            SitemapURL.objects.bulk_create(sitemap_urls_bulk)
                            new_sitemaps.append(sitemap)
                            crawled_results[sitemap_url] = normalized_urls
                            logging.info(f"Sitemap URLs stored for: {sitemap_url}")
                        else:
                            failed_sitemaps.append(sitemap_url)
                            crawled_results[sitemap_url] = 'Failed to crawl the sitemap.'
                            logging.warning(f"Failed to crawl sitemap: {sitemap_url}")

                # Step 1: Update the 'In Sitemap' status after the sitemap crawl
                update_in_sitemap_status()  # This checks and updates the 'in_sitemap' field

                # Fetch the updated sitemaps list
                sitemaps = Sitemap.objects.all().order_by('-added_at')
                paginator = Paginator(sitemaps, 10)
                page_number = request.GET.get('page', 1)
                try:
                    page_obj = paginator.get_page(page_number)
                except PageNotAnInteger:
                    page_obj = paginator.get_page(1)
                except EmptyPage:
                    page_obj = paginator.get_page(paginator.num_pages)

                # Render partial templates
                sitemaps_html = render_to_string(
                    'audit/sitemap_list.html',
                    {'sitemaps': page_obj},
                    request=request
                )
                crawl_results_html = render_to_string(
                    'audit/crawl_results.html',
                    {'crawled_results': crawled_results},
                    request=request
                )

                return JsonResponse({
                    'success': True,
                    'crawl_results_html': crawl_results_html,
                    'sitemaps_html': sitemaps_html,
                })

            else:
                # Form is invalid
                return JsonResponse({'success': False, 'error': 'Invalid form data.'}, status=400)

    elif request.method == 'GET':
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' and 'sitemap_id' in request.GET:
            # Handle AJAX GET request for sitemap content
            sitemap_id = request.GET['sitemap_id']
            try:
                sitemap = Sitemap.objects.get(id=sitemap_id)
                sitemap_urls = SitemapURL.objects.filter(sitemap=sitemap).values_list('url', flat=True)
                return JsonResponse({
                    'success': True,
                    'sitemap_url': sitemap.url,
                    'urls': list(sitemap_urls),
                })
            except Sitemap.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Sitemap not found'}, status=404)

    # Handle non-AJAX GET request
    sitemaps = Sitemap.objects.all().order_by('-added_at')  # Show the most recent first
    paginator = Paginator(sitemaps, 10)  # 10 sitemaps per page
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)

    return render(request, 'audit/sitemap_dashboard.html', {
        'form': form,
        'crawled_results': crawled_results,
        'sitemaps': page_obj
    })



@csrf_protect
def delete_sitemap(request, sitemap_id):
    if request.method == 'POST':
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            try:
                sitemap = get_object_or_404(Sitemap, id=sitemap_id)
                sitemap.delete()  # Delete the sitemap
                logging.info(f"Sitemap deleted: {sitemap_id}")

                # Fetch the updated sitemaps list
                sitemaps = Sitemap.objects.all().order_by('-added_at')
                paginator = Paginator(sitemaps, 10)
                page_number = request.GET.get('page', 1)
                try:
                    page_obj = paginator.get_page(page_number)
                except PageNotAnInteger:
                    page_obj = paginator.get_page(1)
                except EmptyPage:
                    page_obj = paginator.get_page(paginator.num_pages)

                sitemaps_html = render_to_string('audit/sitemap_list.html', {'sitemaps': page_obj}, request=request)

                return JsonResponse({'success': True, 'sitemaps_html': sitemaps_html})
            except Exception as e:
                logging.error(f"Error deleting sitemap {sitemap_id}: {e}")
                return JsonResponse({'success': False, 'error': str(e)}, status=500)
        else:
            return JsonResponse({'success': False, 'error': 'Invalid request.'}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=400)



def update_in_sitemap_status():
    """Updates the 'in_sitemap' field in UploadedFile by checking
    if the 'url' exists in the crawled SitemapURL entries."""
    
    # Fetch all uploaded file entries and sitemap URLs
    audit_files = UploadedFile.objects.all()
    sitemap_urls = SitemapURL.objects.values_list('url', flat=True)

    # Normalize sitemap URLs for comparison
    normalized_sitemap_urls = set(normalize_url(url) for url in sitemap_urls)

    # Compare audit URLs with normalized sitemap URLs
    for audit_file in audit_files:
        normalized_audit_url = normalize_url(audit_file.url)
        audit_file.in_sitemap = normalized_audit_url in normalized_sitemap_urls
        audit_file.save()




def get_page_path(url):
    """
    Extracts the path from a URL. If the URL has no path, returns '/'.
    Handles different URL formats, including those with or without trailing slashes.
    """
    logging.debug(f"Extracting path from URL: {url}")
    
    # Regular expression to extract the part of the URL after the domain
    pattern = r'https?://[^/]+(/.*)?'
    match = re.match(pattern, url)
    
    path = match.group(1) if match and match.group(1) else '/'
    logging.debug(f"Extracted path: {path}")
    
    return path




def process_csv_file(file):
    try:
        # Decode and split the CSV file for processing
        decoded_file = file.read().decode('utf-8-sig').splitlines()  # Handles BOM (\ufeff) if present
        logging.debug(f"CSV File Content: {decoded_file[:5]}")  # Log the first few lines for sanity check

        if not decoded_file:
            logging.error("The CSV file is empty.")
            return []

        reader = csv.reader(decoded_file)
        headers = next(reader, None)  # Get the header row
        if headers is None:
            logging.error("No headers found in the CSV file.")
            return []

        logging.debug(f"CSV Headers: {headers}")  # Log headers for debugging

        # Determine the type of CSV (Screaming Frog, Search Console, Google Analytics, or Keyword Research)
        csv_type = identify_csv_type(headers)
        logging.info(f"Detected CSV type: {csv_type}")

        # Dynamically map headers to relevant fields based on CSV type
        column_mapping = {}

        # Normalize headers and create a mapping
        normalized_headers = [header.strip().lower() for header in headers]
        header_to_index = {header.strip().lower(): index for index, header in enumerate(headers)}

        if csv_type == 'screaming_frog':
            # Screaming Frog column mappings (dynamically locate columns by header name)
            column_mapping = {
                'url': header_to_index.get('address'),
                'type': header_to_index.get('content type'),
                'current_title': header_to_index.get('title 1'),
                'meta': header_to_index.get('meta description 1'),
                'h1': header_to_index.get('h1-1'),
                'word_count': header_to_index.get('word count'),
                'canonical_link': header_to_index.get('canonical link element 1'),
                'status_code': header_to_index.get('status code'),
                'index_status': header_to_index.get('indexability'),
                'inlinks': header_to_index.get('inlinks'),
                'outlinks': header_to_index.get('outlinks'),
                'crawl_depth': header_to_index.get('crawl depth')
            }

            # Read all rows
            rows = list(reader)

            for row in rows:
                logging.debug(f"Processing row: {row}")  # Log each row being processed

                if not row:  # Skip empty rows
                    logging.warning("Empty row encountered, skipping.")
                    continue

                try:
                    # Extract Screaming Frog CSV data based on dynamic mapping
                    url = row[column_mapping['url']] if column_mapping['url'] is not None else None
                    page_path = get_page_path(url) if url else '/'

                    uploaded_file = UploadedFile(
                        url=url,
                        page_path=page_path,
                        type=row[column_mapping['type']] if column_mapping['type'] is not None else None,
                        current_title=row[column_mapping['current_title']] if column_mapping['current_title'] is not None else None,
                        meta=row[column_mapping['meta']] if column_mapping['meta'] is not None else None,
                        h1=row[column_mapping['h1']] if column_mapping['h1'] is not None else None,
                        word_count=int(row[column_mapping['word_count']]) if column_mapping['word_count'] is not None and row[column_mapping['word_count']].isdigit() else 0,
                        canonical_link=row[column_mapping['canonical_link']] if column_mapping['canonical_link'] is not None else None,
                        status_code=row[column_mapping['status_code']] if column_mapping['status_code'] is not None else None,
                        index_status=row[column_mapping['index_status']] if column_mapping['index_status'] is not None else None,
                        inlinks=int(row[column_mapping['inlinks']]) if column_mapping['inlinks'] is not None and row[column_mapping['inlinks']].isdigit() else 0,
                        outlinks=int(row[column_mapping['outlinks']]) if column_mapping['outlinks'] is not None and row[column_mapping['outlinks']].isdigit() else 0,
                        crawl_depth=int(row[column_mapping['crawl_depth']]) if column_mapping['crawl_depth'] is not None and row[column_mapping['crawl_depth']].isdigit() else 0
                    )
                    uploaded_file.save()
                    logging.info(f"Saved UploadedFile for URL: {url}")

                except IndexError as e:
                    logging.error(f"IndexError while processing row: {row} - {e}")
                except ValueError as e:
                    logging.error(f"ValueError while converting data: {row} - {e}")
                except Exception as e:
                    logging.error(f"Unexpected error while processing row: {row} - {e}")

            # After processing Screaming Frog CSV, update the 'in_sitemap' status
            update_in_sitemap_status()  # Call the function to update 'in_sitemap' field

        elif csv_type == 'keyword_research':
            # Keyword Research CSV column mappings
            column_mapping = {
                'url': header_to_index.get('url'),
                'keyword': header_to_index.get('keyword'),
                'search_vol': header_to_index.get('search vol.'),
                'position': header_to_index.get('position')
            }

            # Check if all required columns are present
            required_columns = ['url', 'keyword', 'search_vol', 'position']
            missing_columns = [col for col in required_columns if column_mapping[col] is None]
            if missing_columns:
                logging.error(f"Missing required columns in CSV: {missing_columns}")
                return []

            # Dictionary to store data for each URL
            url_data = {}

            # Read all rows
            rows = list(reader)  # Need to read all rows for keyword_research

            for row in rows:
                logging.debug(f"Processing row: {row}")  # Log each row being processed

                if not row:  # Skip empty rows
                    logging.warning("Empty row encountered, skipping.")
                    continue

                try:
                    # Extract data for each URL and associated keyword
                    url = row[column_mapping['url']].strip() if column_mapping['url'] is not None else None
                    keyword = row[column_mapping['keyword']].strip() if column_mapping['keyword'] is not None else None
                    search_vol_str = row[column_mapping['search_vol']].replace(',', '').strip() if column_mapping['search_vol'] is not None else '0'
                    position_str = row[column_mapping['position']].strip() if column_mapping['position'] is not None else '0'

                    search_vol = int(search_vol_str) if search_vol_str.isdigit() else 0
                    position = int(position_str) if position_str.isdigit() else float('inf')  # Use infinity if position is not a number

                    if url:
                        if url not in url_data:
                            url_data[url] = {
                                'main_kw': keyword,
                                'kw_volume': search_vol,
                                'kw_ranking': position,
                                'best_kw': keyword,
                                'best_kw_volume': search_vol,
                                'best_kw_ranking': position
                            }
                        else:
                            # Update the main keyword if the current keyword has a higher search volume
                            if search_vol > url_data[url]['kw_volume']:
                                url_data[url]['main_kw'] = keyword
                                url_data[url]['kw_volume'] = search_vol
                                url_data[url]['kw_ranking'] = position

                            # Update the best keyword if the current keyword has a better ranking (lower position value)
                            if position < url_data[url]['best_kw_ranking']:
                                url_data[url]['best_kw'] = keyword
                                url_data[url]['best_kw_volume'] = search_vol
                                url_data[url]['best_kw_ranking'] = position

                except IndexError as e:
                    logging.error(f"IndexError while processing row: {row} - {e}")
                except ValueError as e:
                    logging.error(f"ValueError while converting data: {row} - {e}")

            # Now update the Django table with the processed data
            for url, data in url_data.items():
                try:
                    # Look for the corresponding entry in the Django table by URL
                    uploaded_file = UploadedFile.objects.filter(url=url).first()
                    if uploaded_file:
                        # Update the relevant fields in the Django table
                        uploaded_file.main_kw = data['main_kw']
                        uploaded_file.kw_volume = data['kw_volume']
                        uploaded_file.kw_ranking = data['kw_ranking']
                        uploaded_file.best_kw = data['best_kw']
                        uploaded_file.best_kw_volume = data['best_kw_volume']
                        uploaded_file.best_kw_ranking = data['best_kw_ranking']
                        uploaded_file.save()
                        logging.info(f"Updated data for URL: {url}")
                    else:
                        logging.warning(f"No match found for URL: {url}")

                except Exception as e:
                    logging.error(f"Error updating data for URL {url}: {e}")

        elif csv_type == 'search_console':
            # Search Console column mappings
            column_mapping = {
                'url': header_to_index.get('top pages'),
                'impressions': header_to_index.get('impressions'),
                'ctr': header_to_index.get('ctr')
            }

            # Read all rows
            rows = list(reader)

            for row in rows:
                logging.debug(f"Processing row: {row}")  # Log each row being processed

                if not row:  # Skip empty rows
                    logging.warning("Empty row encountered, skipping.")
                    continue

                try:
                    # Extract Search Console CSV data based on dynamic mapping
                    url = row[column_mapping['url']] if column_mapping['url'] is not None else None
                    page_path = get_page_path(url) if url else '/'

                    impressions_str = row[column_mapping['impressions']].replace(',', '') if column_mapping['impressions'] is not None else '0'
                    ctr_str = row[column_mapping['ctr']].replace('%', '') if column_mapping['ctr'] is not None else '0'

                    impressions = int(impressions_str) if impressions_str.isdigit() else 0
                    serp_ctr = float(ctr_str) if ctr_str else 0.0

                    # Match the page_path with the page_path column in the UploadedFile model
                    uploaded_file = UploadedFile.objects.filter(page_path=page_path).first()
                    if uploaded_file:
                        # Update the relevant fields
                        uploaded_file.impressions = impressions
                        uploaded_file.serp_ctr = serp_ctr
                        uploaded_file.save()
                        logging.info(f"Updated data for page_path: {page_path}")
                    else:
                        logging.warning(f"No match found for page_path: {page_path}")

                except IndexError as e:
                    logging.error(f"IndexError while processing row: {row} - {e}")
                except ValueError as e:
                    logging.error(f"ValueError while converting data: {row} - {e}")
                except Exception as e:
                    logging.error(f"Unexpected error while processing row: {row} - {e}")

        elif csv_type == 'google_analytics':
            # Google Analytics column mappings
            column_mapping = {
                'page_path': header_to_index.get('page path and screen class'),
                'sessions': header_to_index.get('sessions'),
                'bounce_rate': header_to_index.get('bounce rate'),
                'avg_session_duration': header_to_index.get('average session duration'),
            }

            # Read all rows
            rows = list(reader)

            for row in rows:
                logging.debug(f"Processing row: {row}")  # Log each row being processed

                if not row:  # Skip empty rows
                    logging.warning("Empty row encountered, skipping.")
                    continue

                try:
                    page_path = row[column_mapping['page_path']] if column_mapping['page_path'] is not None else None
                    sessions_str = row[column_mapping['sessions']].replace(',', '') if column_mapping['sessions'] is not None else '0'
                    bounce_rate_str = row[column_mapping['bounce_rate']].replace('%', '') if column_mapping['bounce_rate'] is not None else '0'
                    avg_session_duration = row[column_mapping['avg_session_duration']] if column_mapping['avg_session_duration'] is not None else None

                    sessions = int(sessions_str) if sessions_str.isdigit() else 0
                    bounce_rate = float(bounce_rate_str) if bounce_rate_str else 0.0

                    # Match the page_path with the page_path column in the UploadedFile model
                    uploaded_file = UploadedFile.objects.filter(page_path=page_path).first()
                    if uploaded_file:
                        # Update the relevant fields
                        uploaded_file.sessions = sessions
                        uploaded_file.bounce_rate = bounce_rate
                        uploaded_file.avg_time_on_page = avg_session_duration
                        uploaded_file.save()
                        logging.info(f"Updated data for page_path: {page_path}")
                    else:
                        logging.warning(f"No match found for page_path: {page_path}")

                except IndexError as e:
                    logging.error(f"IndexError while processing row: {row} - {e}")
                except ValueError as e:
                    logging.error(f"ValueError while converting data: {row} - {e}")
                except Exception as e:
                    logging.error(f"Unexpected error while processing row: {row} - {e}")

        else:
            logging.error(f"Unknown CSV type: {csv_type}")
            return []

        logging.info("CSV processing complete.")
        return []

    except Exception as e:
        logging.error(f"Error while processing CSV file: {e}")
        return []



@csrf_protect
def audit_dashboard(request):
    audit_data_qs = UploadedFile.objects.all().order_by('id')  # Retrieve and order audit data by 'id'

    # Pagination Logic
    page_number = request.GET.get('page', 1)  # Get the current page number from the URL query
    rows_per_page = 15  # Set the number of rows per page

    paginator = Paginator(audit_data_qs, rows_per_page)  # Paginate the data with 15 rows per page

    try:
        page_obj = paginator.get_page(page_number)  # Get the current page of data
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)  # If page is not an integer, return the first page
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)  # If page is out of range, return the last page

    # Initialize the table with paginated data
    table = UploadedFileTable(page_obj)
    RequestConfig(request, paginate=False).configure(table)  # Set paginate=False as we're using manual pagination

    # Handle form submission for category and action_choice
    if request.method == 'POST':
        form = UploadedFileForm(request.POST)
        if form.is_valid():
            form.save()  # Save the updated form fields
            return JsonResponse({'success': True, 'message': 'Form submitted successfully.'})

    else:
        form = UploadedFileForm()

    # Render the template with the paginated table and form
    return render(request, 'audit/audit_dashboard.html', {
        'table': table,  # Pass the paginated table instance to the template
        'form': form,  # Pass the form to the template
        'page_obj': page_obj,  # Pass the page object for pagination controls in the template
    })



@csrf_protect
def delete_uploaded_files(request):
    if request.method == 'POST':
        logging.info("Received POST request to delete uploaded files.")
        try:
            # Delete all UploadedFile records
            count, _ = UploadedFile.objects.all().delete()
            logging.info(f"Deleted {count} UploadedFile records.")
            return JsonResponse({'success': True})
        except Exception as e:
            logging.error(f"Error deleting UploadedFile records: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    else:
        logging.warning("Received non-POST request to delete_uploaded_files.")
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=400)




@csrf_protect
def update_action_choice(request):
    if request.method == 'POST':
        audit_id = request.POST.get('id')
        action_choice = request.POST.get('action_choice')

        if not audit_id or not action_choice:
            return JsonResponse({'success': False, 'error': 'Invalid data provided.'}, status=400)

        try:
            audit_entry = UploadedFile.objects.get(id=audit_id)
            audit_entry.action_choice = action_choice
            audit_entry.save()
            return JsonResponse({'success': True, 'message': 'Action choice updated successfully.'})
        except UploadedFile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Audit entry not found.'}, status=404)

    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=400)







@csrf_protect
def update_category(request):
    if request.method == 'POST':
        audit_id = request.POST.get('id')
        category = request.POST.get('category')

        # Check if both ID and category are provided
        if not audit_id or not category:
            return JsonResponse({'success': False, 'error': 'Invalid data provided.'}, status=400)

        try:
            # Fetch the UploadedFile record and update the category
            audit_entry = UploadedFile.objects.get(id=audit_id)
            audit_entry.category = category
            audit_entry.save()
            
            # Return a success response as JSON
            return JsonResponse({'success': True, 'message': 'Category updated successfully.'})
        
        except UploadedFile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Audit entry not found.'}, status=404)

    # Return an error if the request is not a POST request
    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=400)



