# keywords/views.py

import json
import logging
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_POST
from .models import KeywordResearchDashboard, KeywordResearchEntry
from audit.models import AuditDashboard, UploadedFile
from .forms import KeywordDashboardForm
from keywords.tables import KeywordResearchTable

# Configure logging
logger = logging.getLogger(__name__)

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

    return render(request, 'audit/list_dashboards.html', {
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
