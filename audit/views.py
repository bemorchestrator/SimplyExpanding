# views.py

import os, csv, re, requests, logging, tempfile, json, xml.etree.ElementTree as ET
from .filters import UploadedFileFilter 
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.db.models import Q 
from .forms import FileUploadForm, SitemapForm
from .models import UploadedFile, SitemapURL, Sitemap
from .google_drive_utils import upload_file_to_drive
from google_auth import get_credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from django_tables2 import RequestConfig  
from .tables import UploadedFileTable 


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

# Define relevant column indexes (adjust based on your Screaming Frog CSV structure)
RELEVANT_COLUMNS = {
    'url': 0,
    'type': 2,
    'current_title': 7,
    'meta': 10,
    'h1': 15,
    'word_count': 37,
    'canonical_link': 26,
    'status_code': 3,
    'index_status': 5,
    'inlinks': 46,
    'outlinks': 50,
    'crawl_depth': 43
}



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
                    audit_data = process_csv_file(file)
                    
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

def scrape_sitemap(sitemap_url):
    try:
        response = requests.get(sitemap_url)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            urls = []
            for url_element in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                loc = url_element.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc').text
                urls.append(loc)
            logging.info(f"Sitemap scraped successfully: {sitemap_url}")
            return urls
        else:
            logging.warning(f"Failed to retrieve sitemap: {sitemap_url}, status code: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Error scraping sitemap: {e}")
        return None

def crawl_sitemaps(request):
    form = SitemapForm()
    crawled_results = {}

    if request.method == 'POST':
        form = SitemapForm(request.POST)
        if form.is_valid():
            sitemap_urls = form.cleaned_data['sitemap_urls'].splitlines()

            for sitemap_url in sitemap_urls:
                sitemap_url = sitemap_url.strip()
                if sitemap_url:
                    urls = scrape_sitemap(sitemap_url)
                    if urls:
                        sitemap = Sitemap.objects.create(url=sitemap_url)
                        for url in urls:
                            SitemapURL.objects.create(sitemap=sitemap, url=url)

                        crawled_results[sitemap_url] = urls
                        logging.info(f"Sitemap URLs stored for: {sitemap_url}")
                    else:
                        crawled_results[sitemap_url] = 'Failed to crawl the sitemap.'
                        logging.warning(f"Failed to crawl sitemap: {sitemap_url}")

    return render(request, 'audit/sitemap_dashboard.html', {'form': form, 'crawled_results': crawled_results})

# Extracts the page path from the URL
def get_page_path(url):
    # This regex extracts the part of the URL after the domain
    pattern = r'https?://[^/]+(/.*)'
    match = re.match(pattern, url)
    return match.group(1) if match else '/'

# Processes the CSV file and returns the audit data
def process_csv_file(file):
    try:
        decoded_file = file.read().decode('utf-8').splitlines()
        reader = csv.reader(decoded_file)
        headers = next(reader)  # Skip header row
        logging.debug(f"CSV Headers: {headers}")

        audit_data = []
        for row in reader:
            logging.debug(f"Processing row: {row}")
            try:
                # Extract page path from the URL
                page_path = get_page_path(row[RELEVANT_COLUMNS['url']])

                # Handle crawl depth, ensuring it's a valid number or default to 0
                crawl_depth = row[RELEVANT_COLUMNS['crawl_depth']].strip()
                crawl_depth = int(crawl_depth) if crawl_depth.isdigit() else 0

                # Handle inlinks and outlinks, ensuring numeric conversion
                inlinks = int(row[RELEVANT_COLUMNS['inlinks']]) if row[RELEVANT_COLUMNS['inlinks']].isdigit() else 0
                outlinks = int(row[RELEVANT_COLUMNS['outlinks']]) if row[RELEVANT_COLUMNS['outlinks']].isdigit() else 0

                # Append the processed data to the audit_data list
                audit_data.append({
                    'url': row[RELEVANT_COLUMNS['url']],
                    'type': row[RELEVANT_COLUMNS['type']],
                    'current_title': row[RELEVANT_COLUMNS['current_title']],
                    'meta': row[RELEVANT_COLUMNS['meta']],
                    'h1': row[RELEVANT_COLUMNS['h1']],
                    'word_count': int(row[RELEVANT_COLUMNS['word_count']]) if row[RELEVANT_COLUMNS['word_count']].isdigit() else 0,
                    'canonical_link': row[RELEVANT_COLUMNS['canonical_link']],
                    'status_code': row[RELEVANT_COLUMNS['status_code']],
                    'index_status': row[RELEVANT_COLUMNS['index_status']],
                    'inlinks': inlinks,
                    'outlinks': outlinks,
                    'page_path': page_path,
                    'crawl_depth': crawl_depth,  # Validated crawl depth
                })
            except IndexError as e:
                logging.error(f"IndexError while processing row: {row} - {e}")
            except ValueError as e:
                logging.error(f"ValueError while converting inlinks/outlinks: {row} - {e}")

        logging.info(f"CSV processing complete. Total rows processed: {len(audit_data)}")
        return audit_data

    except Exception as e:
        logging.error(f"Error while processing CSV file: {e}")
        return []

def audit_dashboard(request):
    audit_data = UploadedFile.objects.all()

    # Apply the filters using django-filter
    uploaded_file_filter = UploadedFileFilter(request.GET, queryset=audit_data)

    # Get filtered data
    filtered_audit_data = uploaded_file_filter.qs

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

    paginator = Paginator(filtered_audit_data, rows_per_page)

    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver the first page
        page_obj = paginator.get_page(1)
    except EmptyPage:
        # If page is out of range, deliver the last page of results
        page_obj = paginator.get_page(paginator.num_pages)

    # Configure the table using django-tables2
    table = UploadedFileTable(page_obj.object_list)  # Pass only the paginated data to the table
    RequestConfig(request, paginate={"per_page": rows_per_page}).configure(table)

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
        'audit_data': table,  # Pass the table instance to the template
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
