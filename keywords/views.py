# keywords/views.py

import csv
import json
import logging
import tempfile
from statistics import mean

import numpy as np
from django.contrib import messages
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
from scipy import stats

from audit.models import AuditDashboard, UploadedFile

from .forms import KeywordDashboardForm
from .models import KeywordResearchDashboard, KeywordResearchEntry
from .utils import read_and_identify_csv

# Configure logging
logger = logging.getLogger(__name__)

# Google Drive folder ID
GOOGLE_DRIVE_FIXED_FOLDER_ID = '1yEieevdY2PQgJH4eV4QIcdLO5kJ-w1nB'

# Path to your service account key JSON file for Google Drive access
SERVICE_ACCOUNT_DRIVE_FILE = r'C:\Users\bem\Desktop\credentials\se_service_account.json'  # Update with your actual path


def get_drive_credentials():
    """Get Google Drive credentials using service account."""
    SCOPES = ['https://www.googleapis.com/auth/drive']
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_DRIVE_FILE, scopes=SCOPES
        )
        return credentials
    except Exception as e:
        logger.error(f"Failed to load Drive service account credentials: {e}")
        return None


def import_update_on_page_entries(dashboard):
    """
    Imports all UploadedFile entries with action_choice 'update_on_page'
    from the linked AuditDashboard into the KeywordResearchDashboard.
    Also removes any KeywordResearchEntry linked to UploadedFile entries
    that are no longer 'update_on_page'.
    """
    audit_dashboard = dashboard.audit_dashboard
    update_on_page_entries = UploadedFile.objects.filter(
        dashboard=audit_dashboard,
        action_choice='update_on_page'
    )

    # Mapping between UploadedFile action_choice and KeywordResearchEntry action_choice
    ACTION_CHOICE_MAPPING = {
        'leave': 'Leave As Is',
        'update_on_page': 'Update On Page',
        'target_with_links': 'Target w/ Links',
        '301': '301',
        'canonicalize': 'Canonicalize',
        'block_crawl': 'Block Crawl',
        'no_index': 'No Index',
        'content_audit': 'Content Audit',
        'merge': 'Merge',
    }

    # Collect the set of URLs that should be present in KeywordResearchEntry
    current_urls = set(update_on_page_entries.values_list('url', flat=True))

    # Create or update KeywordResearchEntry for each 'update_on_page' UploadedFile
    for entry in update_on_page_entries:
        keyword_entry, created = KeywordResearchEntry.objects.update_or_create(
            keyword_dashboard=dashboard,
            url=entry.url,
            defaults={
                'category': entry.category or '',
                'main_kw': entry.main_kw or '',
                'kw_volume': entry.kw_volume,
                'kw_ranking': entry.kw_ranking,
                'best_kw': entry.best_kw or '',
                'best_kw_volume': entry.best_kw_volume,
                'best_kw_ranking': entry.best_kw_ranking,
                'action_choice': entry.action_choice or '',
                'links': entry.links,
            }
        )
        if created:
            logger.info(f"KeywordResearchEntry created: {keyword_entry}")
        else:
            # Avoid overwriting user-edited fields by only updating non-editable fields
            keyword_entry.category = entry.category or keyword_entry.category
            keyword_entry.main_kw = entry.main_kw or keyword_entry.main_kw
            keyword_entry.kw_volume = entry.kw_volume or keyword_entry.kw_volume
            keyword_entry.kw_ranking = entry.kw_ranking or keyword_entry.kw_ranking
            keyword_entry.best_kw = entry.best_kw or keyword_entry.best_kw
            keyword_entry.best_kw_volume = entry.best_kw_volume or keyword_entry.best_kw_volume
            keyword_entry.best_kw_ranking = entry.best_kw_ranking or keyword_entry.best_kw_ranking
            keyword_entry.action_choice = entry.action_choice or keyword_entry.action_choice
            keyword_entry.save()
            logger.info(f"KeywordResearchEntry updated (non-editable fields): {keyword_entry}")

    # Now, delete any KeywordResearchEntry linked to URLs not in current_urls
    stale_entries = KeywordResearchEntry.objects.filter(
        keyword_dashboard=dashboard
    ).exclude(
        url__in=current_urls
    )

    deleted_count, _ = stale_entries.delete()
    if deleted_count > 0:
        logger.info(f"Deleted {deleted_count} stale KeywordResearchEntry instances from dashboard '{dashboard.name}'.")


@csrf_protect
def create_keyword_dashboard(request):
    """
    View to create a new KeywordResearchDashboard and import relevant entries.
    """
    # Fetch available audit dashboards to link
    audit_dashboards = AuditDashboard.objects.all()

    if request.method == 'POST':
        form = KeywordDashboardForm(request.POST)

        if form.is_valid():
            dashboard_name = form.cleaned_data['name']
            audit_dashboard_id = request.POST.get('audit_dashboard')

            # Ensure an audit dashboard is selected
            if not audit_dashboard_id:
                messages.error(request, "Please select an audit dashboard to link.")
                return redirect('create_keyword_dashboard')

            # Check if a dashboard with the same name already exists
            if KeywordResearchDashboard.objects.filter(name=dashboard_name).exists():
                messages.error(request, f"A dashboard with the name '{dashboard_name}' already exists.")
                return redirect('create_keyword_dashboard')

            # Fetch the selected AuditDashboard
            audit_dashboard = get_object_or_404(AuditDashboard, id=audit_dashboard_id)

            # Create a new KeywordResearchDashboard
            dashboard = KeywordResearchDashboard.objects.create(
                name=dashboard_name,
                audit_dashboard=audit_dashboard
            )

            # Import relevant UploadedFile entries
            import_update_on_page_entries(dashboard)

            messages.success(request, "Keyword research dashboard created successfully.")
            return redirect('save_keyword_dashboard', dashboard_id=dashboard.id)

    else:
        form = KeywordDashboardForm()

    # No dashboard or table is passed for creation
    context = {
        'form': form,
        'audit_dashboards': audit_dashboards,
        'dashboard': None,  # No dashboard yet when creating
        'table': None,      # Table is set to None
        'per_page_options': [10, 15, 20, 50],  # Options for rows per page
        'per_page': 15  # Default value for rows per page
    }

    return render(request, 'keywords/keyword_research.html', context)


def save_keyword_dashboard(request, dashboard_id=None):
    """
    View to save or update an existing KeywordResearchDashboard and import relevant entries.
    """
    # Fetch the KeywordResearchDashboard instance or handle creation
    dashboard = get_object_or_404(KeywordResearchDashboard, id=dashboard_id) if dashboard_id else None

    if dashboard:
        # Import relevant entries every time the dashboard is accessed or saved
        import_update_on_page_entries(dashboard)

    if request.method == 'POST':
        form = KeywordDashboardForm(request.POST, instance=dashboard)

        if form.is_valid():
            dashboard_name = form.cleaned_data['name']

            if dashboard:
                form.save()  # Save updates to the existing dashboard
                messages.success(request, f"Keyword research dashboard '{dashboard_name}' updated successfully.")
            else:
                dashboard = form.save()
                messages.success(request, f"Keyword research dashboard '{dashboard_name}' created successfully.")

            return redirect('save_keyword_dashboard', dashboard_id=dashboard.id)

    else:
        form = KeywordDashboardForm(instance=dashboard)

    # Fetch keyword research entries related to this dashboard
    keyword_entries = KeywordResearchEntry.objects.filter(keyword_dashboard=dashboard) if dashboard else []

    # Pagination Logic (still used for hardcoded table)
    page_number = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 15)
    paginator = Paginator(keyword_entries, per_page)

    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)

    # Pass data to the template
    return render(request, 'keywords/keyword_research.html', {
        'form': form,
        'keyword_entries': page_obj,  # Pass paginated keyword entries to the hardcoded table
        'per_page_options': [10, 15, 20, 50],
        'dashboard': dashboard,  # Pass the dashboard to the template
        'per_page': per_page,  # Pass current per_page to template for selection
    })


def load_keyword_dashboard(request, id):
    """
    View to load a specific KeywordResearchDashboard and import relevant entries.
    """
    # Fetch the specific saved KeywordResearchDashboard by its ID
    dashboard = get_object_or_404(KeywordResearchDashboard, id=id)

    # Import relevant entries every time the dashboard is loaded
    import_update_on_page_entries(dashboard)

    # Fetch related entries for the KeywordResearchDashboard
    keyword_entries = KeywordResearchEntry.objects.filter(keyword_dashboard=dashboard).order_by('id')

    # Pagination Logic
    per_page = request.GET.get('per_page', 10)  # Default to 10 entries per page
    paginator = Paginator(keyword_entries, per_page)
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)

    # Pass the saved dashboard and paginated entries to the template
    return render(request, 'keywords/keyword_research.html', {
        'dashboard': dashboard,
        'keyword_entries': page_obj,  # Pass paginated keyword entries to the hardcoded table
        'per_page_options': [10, 25, 50],  # Options for the dropdown
        'per_page': per_page,  # Current per_page value
    })


def delete_keyword_dashboard(request, id):
    """
    View to delete a specific KeywordResearchDashboard.
    """
    dashboard = get_object_or_404(KeywordResearchDashboard, id=id)

    if request.method == 'POST':
        dashboard_name = dashboard.name
        dashboard.delete()
        messages.success(request, f"Keyword Research Dashboard '{dashboard_name}' has been deleted successfully.")
        return redirect('list_dashboard')  # Redirect back to the list of dashboards

    return redirect('list_dashboard')


def list_keyword_dashboards(request):
    """
    View to list all KeywordResearchDashboards.
    """
    dashboards = KeywordResearchDashboard.objects.all().order_by('-created_at')

    # Pagination Logic
    page_number = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 15)
    paginator = Paginator(dashboards, per_page)

    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)

    return render(request, 'keywords/list_dashboards.html', {
        'dashboards': page_obj.object_list,
        'page_obj': page_obj,
        'per_page': per_page,
        'per_page_options': [10, 15, 20, 50],
    })


@require_POST
@csrf_protect
def update_field(request):
    """
    AJAX view to update a field of a KeywordResearchEntry.
    Expects JSON data with 'id', 'field_name', and 'new_value'.
    """
    try:
        data = json.loads(request.body)
        entry_id = data.get('id')
        field_name = data.get('field_name')
        new_value = data.get('new_value', '').strip()

        if not entry_id or not field_name:
            logger.warning("Invalid data received: missing 'id' or 'field_name'.")
            return JsonResponse({'success': False, 'error': 'Invalid data provided.'}, status=400)

        # List of editable fields
        editable_fields = [
            'primary_keyword',
            'pk_volume',
            'pk_ranking',
            'secondary_keywords',
            'customer_journey',
            'serp_content_type',
        ]

        if field_name not in editable_fields:
            logger.warning(f"Attempt to edit invalid field: {field_name}.")
            return JsonResponse({'success': False, 'error': 'Invalid field name.'}, status=400)

        # Fetch the entry
        entry = get_object_or_404(KeywordResearchEntry, id=entry_id)

        # Validate and set the new value
        if field_name in ['pk_volume', 'pk_ranking']:
            if new_value == '':
                new_value_converted = None
            else:
                try:
                    new_value_converted = int(new_value)
                except ValueError:
                    logger.error(f"Invalid value for {field_name}: {new_value}")
                    return JsonResponse({'success': False, 'error': 'Please enter a valid number.'}, status=400)
            setattr(entry, field_name, new_value_converted)
        elif field_name == 'customer_journey':
            allowed_choices = ['Customer', 'Consider', 'Discover', 'Awareness', 'Attention']
            if new_value not in allowed_choices:
                logger.error(f"Invalid value for customer_journey: {new_value}")
                return JsonResponse({'success': False, 'error': 'Invalid choice for Customer Journey.'}, status=400)
            setattr(entry, field_name, new_value)
        else:
            setattr(entry, field_name, new_value)

        # Save the entry
        entry.save()
        logger.info(f"KeywordResearchEntry (ID: {entry.id}) updated: {field_name} set to '{new_value}'.")

        return JsonResponse({'success': True})

    except json.JSONDecodeError:
        logger.error("JSON decoding failed for update_field view.")
        return JsonResponse({'success': False, 'error': 'Invalid JSON data.'}, status=400)
    except Exception as e:
        logger.exception(f"Unexpected error in update_field view: {str(e)}")
        return JsonResponse({'success': False, 'error': 'An unexpected error occurred.'}, status=500)


def upload_keyword_file(request):
    """
    View to upload keyword research CSV files, process the top 10 entries,
    and update the corresponding Primary Keyword in the dashboard.
    """
    try:
        dashboard_id = request.GET.get('dashboard_id')
        if not dashboard_id:
            messages.error(request, "Dashboard ID is missing.")
            return redirect('list_keyword_dashboard')

        # Ensure the dashboard exists
        dashboard = get_object_or_404(KeywordResearchDashboard, id=dashboard_id)

        if request.method == 'POST':
            primary_keyword_id = request.POST.get('primary_keyword')
            file = request.FILES.get('file')

            # Log the received primary_keyword_id
            logging.info(f"Primary keyword ID received: {primary_keyword_id}")
            logging.info(f"File received: {file}")

            # Validate form inputs
            if not primary_keyword_id:
                messages.error(request, "Please select a primary keyword.")
                return redirect_with_keyword_entries(request, dashboard_id)

            if not file:
                messages.error(request, "No file selected.")
                return redirect_with_keyword_entries(request, dashboard_id)

            # Handle file upload and process CSV
            try:
                # Fetch the KeywordResearchEntry based on primary_keyword_id
                keyword_entry = KeywordResearchEntry.objects.get(pk=primary_keyword_id)
                logging.info(f"Keyword entry found: {keyword_entry}")

                # Save file temporarily for processing
                temp_file_path = handle_file_upload(file)

                # Process CSV and update the entry
                if temp_file_path:
                    process_csv_and_update_entry(temp_file_path, keyword_entry)
                    messages.success(request, "File uploaded and averages calculated successfully.")

                    # Upload file to Google Drive
                    creds = get_drive_credentials()
                    if not creds:
                        messages.error(request, "Google Drive authentication failed.")
                        return redirect('upload_keyword_file')

                    upload_file_to_google_drive(creds, temp_file_path, file.name)

                    # Redirect to the specific dashboard using its ID
                    return redirect('load_keyword_dashboard', id=dashboard.id)
                else:
                    messages.error(request, "File could not be processed.")

            except KeywordResearchEntry.DoesNotExist:
                logging.error(f"KeywordResearchEntry with ID {primary_keyword_id} does not exist.")
                messages.error(request, "The selected primary keyword does not exist.")
            except Exception as e:
                logging.error(f"Error processing file: {str(e)}")
                messages.error(request, f"Error processing file: {str(e)}")

            # Redirect back to upload page if something went wrong
            return redirect(f"{reverse('upload_keyword_file')}?dashboard_id={dashboard_id}")

        else:
            # It's a GET request
            return redirect_with_keyword_entries(request, dashboard_id)

    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return redirect(f"{reverse('upload_keyword_file')}?dashboard_id={dashboard_id}")


def upload_file_to_google_drive(creds, temp_file_path, original_filename):
    """
    Upload the processed file to a fixed Google Drive folder using the credentials.
    """
    try:
        service = build('drive', 'v3', credentials=creds)
        file_metadata = {
            'name': original_filename,
            'parents': [GOOGLE_DRIVE_FIXED_FOLDER_ID]  # Use the fixed folder ID
        }
        media = MediaFileUpload(temp_file_path, resumable=True)

        # Upload the file and get the web link
        uploaded_file_drive = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()

        if uploaded_file_drive:
            logging.info(f"File uploaded to Google Drive: {uploaded_file_drive['webViewLink']}")
        else:
            raise Exception("File upload to Google Drive failed.")

    except Exception as e:
        logging.error(f"Error uploading file to Google Drive: {str(e)}")


def handle_file_upload(file):
    """
    Handle file upload and save it temporarily.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            for chunk in file.chunks():
                temp_file.write(chunk)
        logging.info(f"File successfully saved: {temp_file.name}")
        return temp_file.name
    except Exception as e:
        logging.error(f"Error saving file: {str(e)}")
        return None


def process_csv_and_update_entry(temp_file_path, keyword_entry):
    """
    Process the CSV file, extract data, and update the keyword entry.
    Now includes outlier detection using Z-scores and IQR.
    """
    try:
        with open(temp_file_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            data = list(reader)

            if not data:
                raise Exception("CSV file is empty or improperly formatted.")

            # Process the top 10 rows for analysis
            top_10_results = data[:10]

            # Extract the necessary columns for analysis
            referring_domains = [float(row['Referring Domains']) for row in top_10_results if row['Referring Domains'].isdigit()]
            dt = [float(row['DT']) for row in top_10_results if row['DT'].isdigit()]
            pt = [float(row['PT']) for row in top_10_results if row['PT'].isdigit()]
            backlinks = [float(row['Backlinks']) for row in top_10_results if row['Backlinks'].isdigit()]

            # Detect and remove outliers from each column
            filtered_rd = remove_outliers(referring_domains)
            filtered_dt = remove_outliers(dt)
            filtered_pt = remove_outliers(pt)
            filtered_backlinks = remove_outliers(backlinks)

            # Update the keyword entry with the calculated averages from filtered data
            keyword_entry.avg_da = mean(filtered_dt) if filtered_dt else 0
            keyword_entry.avg_pa = mean(filtered_pt) if filtered_pt else 0
            keyword_entry.avg_rd = mean(filtered_rd) if filtered_rd else 0
            keyword_entry.avg_backlinks = mean(filtered_backlinks) if filtered_backlinks else 0
            keyword_entry.save()

            logging.info(f"Keyword entry updated successfully for {keyword_entry.primary_keyword}")

    except Exception as e:
        logging.error(f"Error processing CSV: {str(e)}")
        raise Exception(f"CSV processing failed: {str(e)}")


def remove_outliers(data):
    """
    Removes outliers from the data using Z-scores and IQR.
    """
    if not data:
        return []

    # Step 1: Calculate Z-Scores
    z_scores = np.abs(stats.zscore(data))

    # Step 2: Calculate IQR (Interquartile Range)
    q1, q3 = np.percentile(data, [25, 75])
    iqr = q3 - q1
    lower_bound = q1 - 2 * iqr
    upper_bound = q3 + 2 * iqr

    # Step 3: Filter out outliers using both Z-Scores and IQR
    z_score_threshold = 3.5  # Adjusted Z-score threshold
    return [value for value, z in zip(data, z_scores) if z <= z_score_threshold and lower_bound <= value <= upper_bound]


def calculate_column_average(data, column_name):
    """
    Calculate the average value of a given column in the CSV data.
    Now includes outlier removal.
    """
    try:
        column_data = [float(row[column_name]) for row in data if row[column_name].isdigit()]
        filtered_data = remove_outliers(column_data)
        return mean(filtered_data) if filtered_data else 0
    except Exception as e:
        logging.warning(f"Could not calculate average for column {column_name}: {str(e)}")
        return 0


def redirect_with_keyword_entries(request, dashboard_id):
    """
    Helper function to pass available keywords to the template for selection.
    """
    keyword_entries = KeywordResearchEntry.objects.filter(
        keyword_dashboard__id=dashboard_id,
        primary_keyword__isnull=False
    ).exclude(primary_keyword="")
    return render(request, 'keywords/upload.html', {
        'keyword_entries': keyword_entries,
        'dashboard_id': dashboard_id
    })
