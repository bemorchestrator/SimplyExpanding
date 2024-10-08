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
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.template.loader import render_to_string

from .filters import UploadedFileFilter 
from .forms import FileUploadForm, SitemapForm
from .models import UploadedFile, SitemapURL, Sitemap
from .google_drive_utils import upload_file_to_drive
from google_auth import get_credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from django_tables2 import RequestConfig  
from .tables import UploadedFileTable 
from .utils import identify_csv_type
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
from django.shortcuts import redirect
from django.contrib import messages
import logging



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
    rows_per_page = request.GET.get('rows', 25)  # Default to 25 rows per page

    # Ensure rows_per_page is an integer
    try:
        rows_per_page = int(rows_per_page)
        if rows_per_page <= 0:
            rows_per_page = 25
    except ValueError:
        rows_per_page = 25

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
                creds = get_credentials(request)
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

                    uploaded_file = service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id, webViewLink'
                    ).execute()

                    drive_file_id = uploaded_file.get('id')
                    drive_file_link = uploaded_file.get('webViewLink')

                    logging.info(f"File uploaded to Google Drive: {drive_file_id}, link: {drive_file_link}")

                    if not drive_file_id or not drive_file_link:
                        raise Exception("Failed to upload file to Google Drive")

                    # Step 3: Process CSV data before storing in the database
                    file.seek(0)  # Reset file pointer to process CSV
                    audit_data = process_csv_file(file)  # Updated to use the expanded function
                    
                    if audit_data:
                        for data in audit_data:
                            UploadedFile.objects.create(
                                file_name=file.name,
                                drive_file_id=drive_file_id,
                                drive_file_link=drive_file_link,
                                **data
                            )
                        logging.info(f"Audit data processed and saved for file: {file.name}")
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
            clicks = row.get('clicks', 0)
            impressions = row.get('impressions', 0)
            ctr = row.get('ctr', 0) * 100  # Convert to percentage
            position = row.get('position', 0)

            # Update or create the UploadedFile record
            uploaded_file, created = UploadedFile.objects.update_or_create(
                url=page_url,
                defaults={
                    'impressions': impressions,
                    'serp_ctr': ctr,
                    'clicks': clicks,
                    'position': position,
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




# Function to extract the path from the URL
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
        logging.debug(f"CSV File Content: {decoded_file[:5]}")  # Debugging: Log the first few lines for sanity check
        
        if not decoded_file:
            logging.error("The CSV file is empty.")
            return []

        reader = csv.reader(decoded_file)
        headers = next(reader, None)  # Get the header row
        if headers is None:
            logging.error("No headers found in the CSV file.")
            return []
        
        logging.debug(f"CSV Headers: {headers}")  # Log headers for debugging
        
        audit_data = []

        # Determine the type of CSV (Screaming Frog or Search Console)
        csv_type = identify_csv_type(headers)
        logging.info(f"Detected CSV type: {csv_type}")

        # Dynamically map headers to relevant fields based on CSV type
        column_mapping = {}

        if csv_type == 'screaming_frog':
            # Screaming Frog column mappings (dynamically locate columns by header name)
            column_mapping = {
                'url': headers.index('Address') if 'Address' in headers else None,
                'type': headers.index('Content Type') if 'Content Type' in headers else None,
                'current_title': headers.index('Title 1') if 'Title 1' in headers else None,
                'meta': headers.index('Meta Description 1') if 'Meta Description 1' in headers else None,
                'h1': headers.index('H1-1') if 'H1-1' in headers else None,
                'word_count': headers.index('Word Count') if 'Word Count' in headers else None,
                'canonical_link': headers.index('Canonical Link Element 1') if 'Canonical Link Element 1' in headers else None,
                'status_code': headers.index('Status Code') if 'Status Code' in headers else None,
                'index_status': headers.index('Indexability') if 'Indexability' in headers else None,
                'inlinks': headers.index('Inlinks') if 'Inlinks' in headers else None,
                'outlinks': headers.index('Outlinks') if 'Outlinks' in headers else None,
                'crawl_depth': headers.index('Crawl Depth') if 'Crawl Depth' in headers else None
            }

        elif csv_type == 'search_console':
            # Search Console column mappings (adjust as per your Search Console headers)
            column_mapping = {
                'url': headers.index('Top pages') if 'Top pages' in headers else None,
                'impressions': headers.index('Impressions') if 'Impressions' in headers else None,
                'ctr': headers.index('CTR') if 'CTR' in headers else None
            }

        for row in reader:
            logging.debug(f"Processing row: {row}")  # Log each row being processed
            
            if not row:  # Skip empty rows
                logging.warning("Empty row encountered, skipping.")
                continue

            try:
                if csv_type == 'screaming_frog':
                    # Extract Screaming Frog CSV data based on dynamic mapping
                    url = row[column_mapping['url']] if column_mapping['url'] is not None else None
                    page_path = get_page_path(url) if url else '/'
                    
                    audit_data.append({
                        'url': url,
                        'type': row[column_mapping['type']] if column_mapping['type'] is not None else None,
                        'current_title': row[column_mapping['current_title']] if column_mapping['current_title'] is not None else None,
                        'meta': row[column_mapping['meta']] if column_mapping['meta'] is not None else None,
                        'h1': row[column_mapping['h1']] if column_mapping['h1'] is not None else None,
                        'word_count': int(row[column_mapping['word_count']]) if row[column_mapping['word_count']].isdigit() else 0,
                        'canonical_link': row[column_mapping['canonical_link']] if column_mapping['canonical_link'] is not None else None,
                        'status_code': row[column_mapping['status_code']] if column_mapping['status_code'] is not None else None,
                        'index_status': row[column_mapping['index_status']] if column_mapping['index_status'] is not None else None,
                        'inlinks': int(row[column_mapping['inlinks']]) if row[column_mapping['inlinks']].isdigit() else 0,
                        'outlinks': int(row[column_mapping['outlinks']]) if row[column_mapping['outlinks']].isdigit() else 0,
                        'crawl_depth': int(row[column_mapping['crawl_depth']]) if row[column_mapping['crawl_depth']].isdigit() else 0,
                        'page_path': page_path  # Include the extracted page path
                    })

                elif csv_type == 'search_console':
                    # Extract Search Console CSV data based on dynamic mapping
                    url = row[column_mapping['url']] if column_mapping['url'] is not None else None
                    page_path = get_page_path(url) if url else '/'
                    
                    audit_data.append({
                        'url': url,
                        'impressions': int(row[column_mapping['impressions']]) if row[column_mapping['impressions']].isdigit() else 0,
                        'serp_ctr': float(row[column_mapping['ctr']].replace('%', '')) if row[column_mapping['ctr']] else 0.0,
                        'page_path': page_path  # Include the extracted page path
                    })

            except IndexError as e:
                logging.error(f"IndexError while processing row: {row} - {e}")
            except ValueError as e:
                logging.error(f"ValueError while converting data: {row} - {e}")

        logging.info(f"CSV processing complete. Total rows processed: {len(audit_data)}")
        return audit_data

    except Exception as e:
        logging.error(f"Error while processing CSV file: {e}")
        return []



@csrf_protect
def audit_dashboard(request):
    audit_data_qs = UploadedFile.objects.all()
    
    # Apply the filters using django-filter
    uploaded_file_filter = UploadedFileFilter(request.GET, queryset=audit_data_qs)
    
    # Get filtered data and apply ordering to avoid UnorderedObjectListWarning
    filtered_audit_data = uploaded_file_filter.qs.order_by('id')  # Apply ordering by 'id', you can replace 'id' with any field you prefer
    
    # Pagination Logic
    page_number = request.GET.get('page', 1)
    rows_per_page = request.GET.get('rows', 25)  # Default to 25 rows per page
    
    # Ensure rows_per_page is an integer
    try:
        rows_per_page = int(rows_per_page)
        if rows_per_page <= 0:
            rows_per_page = 25
    except ValueError:
        rows_per_page = 25
    
    # Initialize Paginator with filtered and ordered data
    paginator = Paginator(filtered_audit_data, rows_per_page)
    
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)
    
    # Initialize the table with the current page's data
    table = UploadedFileTable(page_obj.object_list)
    RequestConfig(request, paginate=False).configure(table)  # Disable django-tables2 pagination
    
    # Check if the request is an AJAX request for instant search
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Serialize the paginated audit data
        audit_list = list(page_obj.object_list.values(
            'id', 'url', 'type', 'current_title', 'meta', 'h1', 'word_count', 
            'canonical_link', 'status_code', 'index_status', 'inlinks', 'outlinks', 
            'page_path', 'crawl_depth'
        ))
        return JsonResponse({
            'audit_data': audit_list,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'num_pages': paginator.num_pages,
            'current_page': page_obj.number,
        })
    
    # For normal requests, render the template with context
    return render(request, 'audit/audit_dashboard.html', {
        'audit_data': table,  # Pass the table instance with current page data
        'paginator': paginator,
        'page_obj': page_obj,
        'rows_per_page': rows_per_page,  # Pass rows_per_page to the template
        'filter': uploaded_file_filter,  # Pass the filter object to the template
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
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            audit_id = data.get('id')
            action = data.get('action_choice')

            if not audit_id or not action:
                return JsonResponse({'success': False, 'error': 'Invalid data.'}, status=400)

            if action not in dict(UploadedFile.ACTION_CHOICES).keys():
                return JsonResponse({'success': False, 'error': 'Invalid action choice.'}, status=400)

            try:
                audit_entry = UploadedFile.objects.get(id=audit_id)
                audit_entry.action_choice = action
                audit_entry.save()
                logging.info(f"Action choice updated for UploadedFile id {audit_id} to {action}.")
                return JsonResponse({'success': True})
            except UploadedFile.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Audit entry not found.'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON.'}, status=400)
        except Exception as e:
            logging.error(f"Error updating action choice: {e}")
            return JsonResponse({'success': False, 'error': 'An error occurred.'}, status=500)
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=400)
