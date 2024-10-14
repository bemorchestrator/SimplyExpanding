# views.py
import os
import csv
import re
from uuid import uuid4
from django.urls import reverse
import requests
import logging
import tempfile
import json
import xml.etree.ElementTree as ET
import cloudscraper
import certifi
import ssl
from urllib.parse import urlparse

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
from .forms import AuditDashboardForm, FileUploadForm, SitemapForm, UploadedFileForm
from .models import AuditDashboard, UploadedFile, SitemapURL, Sitemap
from .google_drive_utils import upload_file_to_drive
from google_auth import get_credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from django_tables2 import RequestConfig
from django.views.decorators.csrf import csrf_exempt
from .tables import UploadedFileTable 
from .utils import identify_csv_type, normalize_page_path
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
from django.shortcuts import redirect
from django.contrib import messages
import logging
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google_auth import get_credentials
from django.views.decorators.http import require_POST
from django.db.models import ProtectedError


logger = logging.getLogger(__name__)

# Configure logging: log only to the console and show only ERROR messages
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.ERROR)  # Only show top-level errors in the terminal

# Set the logging format
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Get the root logger and configure it
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)  # You can adjust this level if needed
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
    parsed_url = urlparse(url)
    netloc = parsed_url.netloc
    if netloc.startswith('www.'):
        netloc = netloc[4:]
    path = parsed_url.path.rstrip('/')
    return netloc + path


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

                            # Step 1: Update the 'In Sitemap' status for crawled URLs
                            update_in_sitemap_status()

                        else:
                            failed_sitemaps.append(sitemap_url)
                            crawled_results[sitemap_url] = 'Failed to crawl the sitemap.'
                            logging.warning(f"Failed to crawl sitemap: {sitemap_url}")

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
    """
    Updates the 'in_sitemap' field in UploadedFile by checking
    if the 'url' exists in the crawled SitemapURL entries.
    """
    # Fetch all sitemap URLs and normalize them for comparison
    sitemap_urls = SitemapURL.objects.values_list('url', flat=True)
    normalized_sitemap_urls = set(normalize_url(url) for url in sitemap_urls)

    # Fetch all audit files that are not yet flagged as in_sitemap (to minimize unnecessary updates)
    audit_files = UploadedFile.objects.all()

    # Batch update to avoid too many save() calls in a loop
    bulk_updates = []

    for audit_file in audit_files:
        normalized_audit_url = normalize_url(audit_file.url)

        # If the audit file URL is in the normalized sitemap URLs, mark it as 'in_sitemap'
        new_in_sitemap_status = normalized_audit_url in normalized_sitemap_urls

        # Only update if there is a change to avoid unnecessary saves
        if audit_file.in_sitemap != new_in_sitemap_status:
            audit_file.in_sitemap = new_in_sitemap_status
            bulk_updates.append(audit_file)

    # Use Django's bulk_update to update all files in a single query
    if bulk_updates:
        UploadedFile.objects.bulk_update(bulk_updates, ['in_sitemap'])





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

        # Determine the type of CSV
        csv_type = identify_csv_type(headers)
        logging.info(f"Detected CSV type: {csv_type}")

        # Normalize headers and create a mapping
        normalized_headers = [header.strip().lower() for header in headers]
        header_to_index = {header.strip().lower(): index for index, header in enumerate(headers)}

        # Helper function to get index from possible header names
        def get_header_index(possible_headers):
            for header in possible_headers:
                index = header_to_index.get(header.lower())
                if index is not None:
                    return index
            return None

        if csv_type == 'screaming_frog':
            # Screaming Frog column mappings
            column_mapping = {
                'url': get_header_index(['address', 'url']),
                'type': get_header_index(['content type', 'type']),
                'current_title': get_header_index(['title 1', 'title']),
                'meta': get_header_index(['meta description 1', 'meta description']),
                'h1': get_header_index(['h1-1', 'h1']),
                'word_count': get_header_index(['word count']),
                'canonical_link': get_header_index(['canonical link element 1', 'canonical link']),
                'status_code': get_header_index(['status code', 'status']),
                'index_status': get_header_index(['indexability']),
                'inlinks': get_header_index(['inlinks']),
                'outlinks': get_header_index(['outlinks']),
                'crawl_depth': get_header_index(['crawl depth'])
            }

            # Read all rows
            rows = list(reader)

            for row in rows:
                logging.debug(f"Processing row: {row}")

                if not row:
                    logging.warning("Empty row encountered, skipping.")
                    continue

                try:
                    # Extract data
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
            # (Assuming you have a function named update_in_sitemap_status)
            # update_in_sitemap_status()

        elif csv_type == 'keyword_research':
            # Keyword Research CSV column mappings
            column_mapping = {
                'url': get_header_index(['url']),
                'keyword': get_header_index(['keyword']),
                'search_vol': get_header_index(['search vol.']),
                'position': get_header_index(['position'])
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
            rows = list(reader)

            for row in rows:
                logging.debug(f"Processing row: {row}")

                if not row:
                    logging.warning("Empty row encountered, skipping.")
                    continue

                try:
                    # Extract data
                    url = row[column_mapping['url']].strip() if column_mapping['url'] is not None else None
                    keyword = row[column_mapping['keyword']].strip() if column_mapping['keyword'] is not None else None
                    search_vol_str = row[column_mapping['search_vol']].replace(',', '').strip() if column_mapping['search_vol'] is not None else '0'
                    position_str = row[column_mapping['position']].strip() if column_mapping['position'] is not None else '0'

                    search_vol = int(search_vol_str) if search_vol_str.isdigit() else 0
                    position = int(position_str) if position_str.isdigit() else float('inf')

                    if url:
                        normalized_url = normalize_url(url)
                        if normalized_url not in url_data:
                            url_data[normalized_url] = {
                                'main_kw': keyword,
                                'kw_volume': search_vol,
                                'kw_ranking': position,
                                'best_kw': keyword,
                                'best_kw_volume': search_vol,
                                'best_kw_ranking': position
                            }
                        else:
                            # Update main_kw if higher search_vol
                            if search_vol > url_data[normalized_url]['kw_volume']:
                                url_data[normalized_url]['main_kw'] = keyword
                                url_data[normalized_url]['kw_volume'] = search_vol
                                url_data[normalized_url]['kw_ranking'] = position

                            # Update best_kw if better ranking
                            if position < url_data[normalized_url]['best_kw_ranking']:
                                url_data[normalized_url]['best_kw'] = keyword
                                url_data[normalized_url]['best_kw_volume'] = search_vol
                                url_data[normalized_url]['best_kw_ranking'] = position

                except IndexError as e:
                    logging.error(f"IndexError while processing row: {row} - {e}")
                except ValueError as e:
                    logging.error(f"ValueError while converting data: {row} - {e}")

            # Now update the Django table with the processed data
            uploaded_files = UploadedFile.objects.all()
            uploaded_files_dict = {normalize_url(u.url): u for u in uploaded_files}

            for normalized_url, data in url_data.items():
                try:
                    uploaded_file = uploaded_files_dict.get(normalized_url)
                    if uploaded_file:
                        uploaded_file.main_kw = data['main_kw']
                        uploaded_file.kw_volume = data['kw_volume']
                        uploaded_file.kw_ranking = data['kw_ranking']
                        uploaded_file.best_kw = data['best_kw']
                        uploaded_file.best_kw_volume = data['best_kw_volume']
                        uploaded_file.best_kw_ranking = data['best_kw_ranking']
                        uploaded_file.save()
                        logging.info(f"Updated data for URL: {uploaded_file.url}")
                    else:
                        logging.warning(f"No match found for URL: {normalized_url}")

                except Exception as e:
                    logging.error(f"Error updating data for URL {normalized_url}: {e}")

        elif csv_type == 'search_console':
            # Search Console column mappings
            column_mapping = {
                'url': get_header_index(['top pages', 'page', 'url']),
                'impressions': get_header_index(['impressions', 'total impressions']),
                'ctr': get_header_index(['ctr', 'click through rate'])
            }

            # Read all rows
            rows = list(reader)

            # Build mapping from normalized URL to UploadedFile
            uploaded_files = UploadedFile.objects.all()
            uploaded_files_dict = {normalize_url(u.url): u for u in uploaded_files}

            for row in rows:
                logging.debug(f"Processing row: {row}")

                if not row:
                    logging.warning("Empty row encountered, skipping.")
                    continue

                try:
                    url = row[column_mapping['url']] if column_mapping['url'] is not None else None
                    impressions_str = row[column_mapping['impressions']].replace(',', '') if column_mapping['impressions'] is not None else '0'
                    ctr_str = row[column_mapping['ctr']].replace('%', '') if column_mapping['ctr'] is not None else '0'

                    impressions = int(impressions_str) if impressions_str.replace('.', '', 1).isdigit() else 0
                    serp_ctr = float(ctr_str) if ctr_str.replace('.', '', 1).isdigit() else 0.0

                    normalized_url = normalize_url(url)

                    uploaded_file = uploaded_files_dict.get(normalized_url)
                    if uploaded_file:
                        uploaded_file.impressions = impressions
                        uploaded_file.serp_ctr = serp_ctr
                        uploaded_file.save()
                        logging.info(f"Updated data for URL: {uploaded_file.url}")
                    else:
                        logging.warning(f"No match found for URL: {normalized_url}")

                except IndexError as e:
                    logging.error(f"IndexError while processing row: {row} - {e}")
                except ValueError as e:
                    logging.error(f"ValueError while converting data: {row} - {e}")
                except Exception as e:
                    logging.error(f"Unexpected error while processing row: {row} - {e}")

        elif csv_type == 'google_analytics':
            # Define possible headers to look for in the CSV
            possible_headers = {
                'page_path': ['page path and screen class', 'page path'],
                'sessions': ['sessions'],
                'bounce_rate': ['bounce rate', 'bounce rate (%)'],
                'avg_session_duration': ['average session duration', 'avg. session duration'],
                'percent_change_sessions': ['sessions Δ', 'sessions delta', 'sessions δ', 'sessions Δ (%)', 'sessions delta (%)', 'sessions change (%)', 'sessions change'],
            }

            # Map the headers in the CSV to their corresponding indices
            column_mapping = {key: get_header_index(possible_headers[key]) for key in possible_headers}

            # Read the CSV rows
            rows = list(reader)

            # Create a dictionary mapping normalized page_path to UploadedFile instances
            uploaded_files = UploadedFile.objects.all()
            uploaded_files_dict = {normalize_page_path(u.page_path): u for u in uploaded_files}

            # Process each row in the CSV
            for row in rows:
                logging.debug(f"Processing row: {row}")

                if not row:
                    logging.warning("Empty row encountered, skipping.")
                    continue

                try:
                    # Extract values from the row using the column mapping
                    page_path = row[column_mapping['page_path']] if column_mapping['page_path'] is not None else None
                    page_path = normalize_page_path(page_path)
                    sessions_str = row[column_mapping['sessions']].replace(',', '') if column_mapping['sessions'] is not None else '0'
                    bounce_rate_str = row[column_mapping['bounce_rate']].replace('%', '') if column_mapping['bounce_rate'] is not None else '0'
                    avg_session_duration_str = row[column_mapping['avg_session_duration']] if column_mapping['avg_session_duration'] is not None else '0:00'
                    percent_change_sessions_str = row[column_mapping['percent_change_sessions']].replace('%', '').replace('−', '-') if column_mapping['percent_change_sessions'] is not None else '0.0'

                    # Convert extracted data into their appropriate types
                    sessions = int(float(sessions_str)) if re.match(r'^-?\d+(\.\d+)?$', sessions_str) else 0
                    bounce_rate = float(bounce_rate_str) if re.match(r'^-?\d+(\.\d+)?$', bounce_rate_str) else 0.0
                    avg_time_on_page = avg_session_duration_str  # Keep the original string (no conversion)
                    percent_change_sessions = float(percent_change_sessions_str) if re.match(r'^-?\d+(\.\d+)?$', percent_change_sessions_str) else 0.0

                    # Find the corresponding UploadedFile by page_path
                    uploaded_file = uploaded_files_dict.get(page_path)
                    if uploaded_file:
                        # Update the fields of the UploadedFile instance
                        uploaded_file.sessions = sessions
                        uploaded_file.bounce_rate = bounce_rate
                        uploaded_file.avg_time_on_page = avg_time_on_page  # Save the original avg_session_duration string
                        uploaded_file.percent_change_sessions = percent_change_sessions

                        # Update losing_traffic field based on percent_change_sessions
                        if percent_change_sessions > 0:
                            uploaded_file.losing_traffic = 'up'
                        elif percent_change_sessions < 0:
                            uploaded_file.losing_traffic = 'down'
                        else:
                            uploaded_file.losing_traffic = 'none'

                        # Save the updated instance to the database
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

        elif csv_type == 'backlinks':
            # Backlinks CSV column mappings
            column_mapping = {
                'backlink_url': get_header_index(['backlink url']),
                'destination_url': get_header_index(['destination url']),
            }

            # Check if all required columns are present
            required_columns = ['backlink_url', 'destination_url']
            missing_columns = [col for col in required_columns if column_mapping[col] is None]
            if missing_columns:
                logging.error(f"Missing required columns in CSV: {missing_columns}")
                return []

            # Dictionary to count backlinks
            backlink_counts = {}

            # Read all rows
            rows = list(reader)

            for row in rows:
                logging.debug(f"Processing row: {row}")

                if not row:
                    logging.warning("Empty row encountered, skipping.")
                    continue

                try:
                    destination_url = row[column_mapping['destination_url']].strip() if column_mapping['destination_url'] is not None else None

                    if destination_url:
                        destination_url_normalized = normalize_url(destination_url)
                        backlink_counts[destination_url_normalized] = backlink_counts.get(destination_url_normalized, 0) + 1

                except IndexError as e:
                    logging.error(f"IndexError while processing row: {row} - {e}")
                except Exception as e:
                    logging.error(f"Unexpected error while processing row: {row} - {e}")

            # Now update the Django table with the backlink counts
            uploaded_files = UploadedFile.objects.all()
            uploaded_files_dict = {normalize_url(u.url): u for u in uploaded_files}

            for normalized_url, count in backlink_counts.items():
                try:
                    uploaded_file = uploaded_files_dict.get(normalized_url)
                    if uploaded_file:
                        uploaded_file.links = count
                        uploaded_file.save()
                        logging.info(f"Updated backlinks count for URL: {uploaded_file.url} with count: {count}")
                    else:
                        logging.warning(f"No match found for URL: {normalized_url}")

                except Exception as e:
                    logging.error(f"Error updating backlinks for URL {normalized_url}: {e}")

        else:
            logging.error(f"Unknown CSV type: {csv_type}")
            return []

        logging.info("CSV processing complete.")
        return []

    except Exception as e:
        logging.error(f"Error while processing CSV file: {e}")
        return []



def audit_dashboard(request):
    # Ensure that the 'in_sitemap' status is always updated when the dashboard is loaded
    update_in_sitemap_status()  # This will update the in_sitemap field for all uploaded files

    # Retrieve unsaved files (those with no associated dashboard) and order by 'id' for consistent ordering
    audit_data_qs = UploadedFile.objects.filter(dashboard__isnull=True).order_by('id')

    # Pagination logic
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
    RequestConfig(request, paginate=False).configure(table)  # Set paginate=False to prevent Django Tables2 from auto-paginating

    # Handle form submission for category and action_choice
    if request.method == 'POST':
        form = UploadedFileForm(request.POST)
        if form.is_valid():
            form.save()  # Save the updated form fields
            return JsonResponse({'success': True, 'message': 'Form submitted successfully.'})
        else:
            return JsonResponse({'success': False, 'error': 'Invalid form data.'}, status=400)

    else:
        form = UploadedFileForm()

    # Render the template with the paginated table and form
    return render(request, 'audit/audit_dashboard.html', {
        'table': table,  # Pass the paginated table instance to the template
        'form': form,  # Pass the form to the template
        'page_obj': page_obj,  # Pass the page object for pagination controls in the template
    })




@csrf_protect
@require_POST
def delete_uploaded_files(request, dashboard_id=None):
    logger.info(f"delete_uploaded_files called with dashboard_id: {dashboard_id}")
    try:
        if dashboard_id:
            # If dashboard_id is provided, delete files associated with the dashboard
            logger.info(f"Attempting to delete UploadedFiles for dashboard ID: {dashboard_id}")
            dashboard = get_object_or_404(AuditDashboard, id=dashboard_id)
            files_to_delete = UploadedFile.objects.filter(dashboard=dashboard)
        else:
            # If no dashboard_id, delete files not associated with any dashboard
            logger.info("Attempting to delete all unsaved UploadedFiles (those without a dashboard).")
            files_to_delete = UploadedFile.objects.filter(dashboard__isnull=True)

        # Delete files and count the number of deletions
        count = files_to_delete.count()
        files_to_delete.delete()
        logger.info(f"Deleted {count} UploadedFile records.")

        # Return a successful response with the count of deleted files
        return JsonResponse({'success': True, 'deleted_count': count})

    except AuditDashboard.DoesNotExist:
        # If the dashboard is not found, return an error
        logger.error(f"Dashboard with ID {dashboard_id} not found.")
        return JsonResponse({'success': False, 'error': 'Dashboard not found.'}, status=404)

    except Exception as e:
        # Catch any other exceptions and return a generic error response
        logger.error(f"Error deleting UploadedFile records: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



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



@csrf_protect
def save_audit_dashboard(request):
    if request.method == 'POST':
        form = AuditDashboardForm(request.POST)
        
        if form.is_valid():
            dashboard_name = form.cleaned_data['name']
            overwrite = form.cleaned_data.get('overwrite_existing', False)
            
            # Check if a dashboard with the same name already exists
            existing_dashboard = AuditDashboard.objects.filter(name=dashboard_name).first()
            
            if existing_dashboard:
                if overwrite:
                    # If overwriting is allowed, delete the old dashboard
                    existing_dashboard.delete()
                    messages.success(request, f"Dashboard '{dashboard_name}' was overwritten.")
                else:
                    # If not overwriting, ask the user to provide a new name
                    messages.error(request, f"A dashboard with the name '{dashboard_name}' already exists. Please choose a new name or select 'Overwrite existing dashboard'.")
                    return redirect('audit_dashboard')  # Redirect back to the audit dashboard for name input

            # Create the new dashboard
            dashboard = AuditDashboard.objects.create(
                user=request.user,  # Associate the dashboard with the current user
                name=dashboard_name,
                description=form.cleaned_data.get('description', '')
            )

            # Move current unsaved data (those without a dashboard) to the new dashboard
            uploaded_files = UploadedFile.objects.filter(dashboard__isnull=True)  # Current unsaved data
            uploaded_files.update(dashboard=dashboard)  # Associate the files with the new dashboard

            # Notify the user that the audit has been saved and the workspace cleared
            messages.success(request, "Audit saved successfully. The working area has been cleared.")

            # Redirect to the list of saved dashboards
            return redirect('list_dashboard')

    # If not POST, redirect back to the dashboard page
    return redirect('audit_dashboard')


    


    

def list_dashboard(request):
    dashboards = AuditDashboard.objects.all()  # Fetch all saved dashboards
    return render(request, 'audit/list_dashboards.html', {'dashboards': dashboards})

def load_dashboard(request, id):
    # Get the specific dashboard
    dashboard = get_object_or_404(AuditDashboard, id=id)
    
    # Filter uploaded files related only to this specific dashboard
    uploaded_files = UploadedFile.objects.filter(dashboard=dashboard)
    
    # Pagination Logic
    page_number = request.GET.get('page', 1)  # Get the current page number from the URL query
    rows_per_page = 15  # Set the same number of rows per page as in audit_dashboard

    paginator = Paginator(uploaded_files, rows_per_page)  # Paginate the data with 15 rows per page

    try:
        page_obj = paginator.get_page(page_number)  # Get the current page of data
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)  # If page is not an integer, return the first page
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)  # If page is out of range, return the last page

    # Initialize the table with paginated data
    table = UploadedFileTable(page_obj)
    RequestConfig(request, paginate=False).configure(table)  # Set paginate=False to prevent Django Tables2 from auto-paginating

    # Render the template with the paginated table
    return render(request, 'audit/audit_dashboard.html', {
        'dashboard': dashboard,
        'table': table,  # Pass the paginated table to the template
        'page_obj': page_obj,  # Pass the page object for pagination controls
    })




@csrf_protect
def delete_dashboard(request, id):
    # Fetch the dashboard with the given ID
    dashboard = get_object_or_404(AuditDashboard, id=id)

    if request.method == 'POST':
        try:
            # Delete the dashboard
            dashboard_name = dashboard.name
            dashboard.delete()

            # Log and add a success message for the user
            logging.info(f"Dashboard '{dashboard_name}' deleted successfully.")
            messages.success(request, f"Dashboard '{dashboard_name}' has been deleted successfully.")
        
        except ProtectedError as e:
            # Handle protected relationships
            logging.error(f"ProtectedError: Cannot delete dashboard '{dashboard.name}' due to related records.")
            messages.error(request, f"Cannot delete dashboard '{dashboard.name}' because it has related records.")
        
        except Exception as e:
            # Log the error and add an error message for the user
            logging.error(f"Error deleting dashboard '{dashboard.name}': {e}")
            messages.error(request, f"Failed to delete dashboard '{dashboard.name}': {e}")
        
        # Redirect to the list of saved dashboards
        return redirect('list_dashboard')
    
    # Handle GET requests or other methods by redirecting to the dashboard list
    return redirect('list_dashboard')



@csrf_protect
def generate_shareable_link(request, id):
    if request.method == 'POST':
        dashboard = get_object_or_404(AuditDashboard, id=id)
        # Ensure only the owner can generate the shareable link
        if dashboard.user != request.user:
            return JsonResponse({'success': False, 'error': 'You do not have permission to share this dashboard.'}, status=403)
        # Generate a unique share token if not already present
        if not dashboard.share_token:
            dashboard.share_token = uuid4().hex
            dashboard.save()
        # Build the shareable link
        shareable_link = request.build_absolute_uri(reverse('shared_dashboard', args=[dashboard.share_token]))
        return JsonResponse({'success': True, 'shareable_link': shareable_link})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=400)
    

    

def shared_dashboard(request, share_token):
    # Retrieve the dashboard using the share token
    dashboard = get_object_or_404(AuditDashboard, share_token=share_token)
    uploaded_files = UploadedFile.objects.filter(dashboard=dashboard)
    
    # Pagination logic (same as in your existing load_dashboard view)
    page_number = request.GET.get('page', 1)
    rows_per_page = 15
    paginator = Paginator(uploaded_files, rows_per_page)
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)
    
    # Initialize the table with paginated data
    table = UploadedFileTable(page_obj)
    RequestConfig(request, paginate=False).configure(table)
    
    # Render the template with the 'is_shared_view' flag and 'hide_sidebar'
    return render(request, 'audit/shared_dashboard.html', {
        'dashboard': dashboard,
        'table': table,
        'page_obj': page_obj,
        'is_shared_view': True,  # Indicate that this is a shared view
        'hide_sidebar': True,    # Hide the sidebar in the template
    })