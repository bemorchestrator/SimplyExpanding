import os
import csv
import requests
import logging
import xml.etree.ElementTree as ET
from django.shortcuts import render, redirect
from django.core.exceptions import ValidationError
from django.contrib import messages
from .forms import FileUploadForm, SitemapForm
from .models import UploadedFile, SitemapURL, Sitemap
from .google_drive_utils import upload_file_to_drive
from google_auth import get_credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import tempfile

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
    'meta': 12,
    'h1': 16,
    'word_count': 14,
    'canonical_link': 21,
    'status_code': 3,
    'index_status': 5,
    'last_modified': 18,
    'inlinks': 26,
    'outlinks': 27
}

def audit_result(request):
    uploaded_files = UploadedFile.objects.all()
    logging.info(f"Audit data retrieved for dashboard: {len(uploaded_files)} files.")
    return render(request, 'audit/audit_dashboard.html', {'audit_data': uploaded_files})

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
                    return redirect('audit_result')

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

            return redirect('audit_result')
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
                audit_data.append({
                    'url': row[RELEVANT_COLUMNS['url']],
                    'type': row[RELEVANT_COLUMNS['type']],
                    'current_title': row[RELEVANT_COLUMNS['current_title']],
                    'meta': row[RELEVANT_COLUMNS['meta']],
                    'h1': row[RELEVANT_COLUMNS['h1']],
                    'word_count': row[RELEVANT_COLUMNS['word_count']],
                    'canonical_link': row[RELEVANT_COLUMNS['canonical_link']],
                    'status_code': row[RELEVANT_COLUMNS['status_code']],
                    'index_status': row[RELEVANT_COLUMNS['index_status']],
                    'last_modified': row[RELEVANT_COLUMNS['last_modified']],
                    # Ensure 'inlinks' and 'outlinks' are numbers, defaulting to 0 if empty or non-numeric
                    'inlinks': int(row[RELEVANT_COLUMNS['inlinks']]) if row[RELEVANT_COLUMNS['inlinks']].isdigit() else 0,
                    'outlinks': int(row[RELEVANT_COLUMNS['outlinks']]) if row[RELEVANT_COLUMNS['outlinks']].isdigit() else 0,
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
    logging.info(f"Audit data retrieved for dashboard: {len(audit_data)} files.")
    return render(request, 'audit/audit_dashboard.html', {'audit_data': audit_data})
