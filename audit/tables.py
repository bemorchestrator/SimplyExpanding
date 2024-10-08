import django_tables2 as tables
from django.utils.html import format_html
from .models import UploadedFile

class UploadedFileTable(tables.Table):
    action_choice = tables.Column(
        verbose_name='Actions',
        orderable=False,
        empty_values=(),
        attrs={
            "td": {
                "class": "sticky-col-1",
                "style": "white-space: nowrap; position: sticky; left: 0; background-color: #2d3748; z-index: 1; width: 150px; min-height: 100px;"  # Ensure minimum height
            },
            "th": {
                "class": "sticky-col-1",
                "style": "position: sticky; top: 0; background-color: #2d3748; z-index: 2; width: 150px;"
            }
        }
    )

    def render_url(self, value, record):
        # Truncate the URL and show full URL on hover
        truncated_url = value if len(value) <= 150 else value[:150] + "..."
        return format_html(
            '<a href="{}" title="{}" style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: inline-block; max-width: 480px;">{}</a>',
            value, value, truncated_url
        )

    url = tables.URLColumn(
        verbose_name='URL',
        attrs={
            "td": {
                "class": "sticky-col-2",
                "style": "white-space: nowrap; position: sticky; left: 152px; background-color: #2d3748; z-index: 1; width: 300px; min-height: 100px;"  # Ensure minimum height
            },
            "th": {
                "class": "sticky-col-2",
                "style": "position: sticky; top: 0; left: 152px; background-color: #2d3748; z-index: 2; width: 300px;"
            }
        }
    )




    page_path = tables.Column(verbose_name='Page Path', attrs={"td": {"style": "white-space: nowrap;"}})
    crawl_depth = tables.Column(verbose_name='Crawl Depth', attrs={"td": {"style": "white-space: nowrap;"}})
    category = tables.Column(verbose_name='Category', attrs={"td": {"style": "white-space: nowrap;"}})
    in_sitemap = tables.Column(verbose_name='In Sitemap', attrs={"td": {"style": "white-space: nowrap;"}})
    
    # Keyword Performance
    main_kw = tables.Column(verbose_name='Main KW', attrs={"td": {"style": "white-space: nowrap;"}})
    kw_volume = tables.Column(verbose_name='Volume', attrs={"td": {"style": "white-space: nowrap;"}})
    kw_ranking = tables.Column(verbose_name='Ranking', attrs={"td": {"style": "white-space: nowrap;"}})
    best_kw = tables.Column(verbose_name='Best KW', attrs={"td": {"style": "white-space: nowrap;"}})
    best_kw_volume = tables.Column(verbose_name='Best KW Volume', attrs={"td": {"style": "white-space: nowrap;"}})
    best_kw_ranking = tables.Column(verbose_name='Best KW Ranking', attrs={"td": {"style": "white-space: nowrap;"}})

    # Page Performance
    impressions = tables.Column(verbose_name='Impressions', attrs={"td": {"style": "white-space: nowrap;"}})
    sessions = tables.Column(verbose_name='Sessions', attrs={"td": {"style": "white-space: nowrap;"}})
    percent_change_sessions = tables.Column(verbose_name='% Change Sessions', attrs={"td": {"style": "white-space: nowrap;"}})
    bounce_rate = tables.Column(verbose_name='Bounce Rate', attrs={"td": {"style": "white-space: nowrap;"}})
    avg_time_on_page = tables.Column(verbose_name='Avg Time on Page', attrs={"td": {"style": "white-space: nowrap;"}})
    losing_traffic = tables.Column(verbose_name='Losing Traffic?', attrs={"td": {"style": "white-space: nowrap;"}})
    links = tables.Column(verbose_name='Links', attrs={"td": {"style": "white-space: nowrap;"}})
    serp_ctr = tables.Column(verbose_name='SERP CTR', attrs={"td": {"style": "white-space: nowrap;"}})

    # Screaming Frog On-Page
    type = tables.Column(verbose_name='Type', attrs={"td": {"style": "white-space: nowrap;"}})
    current_title = tables.Column(verbose_name='Current Title', attrs={"td": {"style": "white-space: nowrap;"}})
    meta = tables.Column(verbose_name='Meta', attrs={"td": {"style": "white-space: nowrap;"}})
    h1 = tables.Column(verbose_name='H1', attrs={"td": {"style": "white-space: nowrap;"}})
    word_count = tables.Column(verbose_name='Word Count', attrs={"td": {"style": "white-space: nowrap;"}})
    canonical_link = tables.URLColumn(verbose_name='Canonical Link', attrs={"td": {"style": "white-space: nowrap;"}})
    status_code = tables.Column(verbose_name='Status Code', attrs={"td": {"style": "white-space: nowrap;"}})
    index_status = tables.Column(verbose_name='Index/No Index', attrs={"td": {"style": "white-space: nowrap;"}})
    inlinks = tables.Column(verbose_name='Inlinks', attrs={"td": {"style": "white-space: nowrap;"}})
    outlinks = tables.Column(verbose_name='Outlinks', attrs={"td": {"style": "white-space: nowrap;"}})

    class Meta:
        model = UploadedFile
        template_name = 'django_tables2/bootstrap.html'  # Customize if needed
        fields = [
            'action_choice', 'url', 'page_path', 'crawl_depth', 'category', 'in_sitemap',
            'main_kw', 'kw_volume', 'kw_ranking', 'best_kw', 'best_kw_volume', 'best_kw_ranking',
            'impressions', 'sessions', 'percent_change_sessions', 'bounce_rate', 'avg_time_on_page', 
            'losing_traffic', 'links', 'serp_ctr', 'type', 'current_title', 'meta', 'h1', 
            'word_count', 'canonical_link', 'status_code', 'index_status', 'inlinks', 'outlinks'
        ]
        attrs = {'class': 'table table-striped text-white'}

    def render_action_choice(self, value, record):
        # This is the dropdown with different background colors for each action
        return format_html('''
            <select class="shadow border rounded w-32 py-1 text-white action-dropdown" data-id="{}" onchange="changeColor(this)">
                <option value="leave" class="text-blue-500" {}>1. Leave As Is</option>
                <option value="update_on_page" class="text-green-500" {}>2. Update "On Page"</option>
                <option value="target_with_links" class="text-yellow-500" {}>3. Target w/ Links</option>
                <option value="301" class="text-red-500" {}>4. 301</option>
                <option value="canonicalize" class="text-purple-500" {}>5. Canonicalize</option>
                <option value="block_crawl" class="text-pink-500" {}>6. Block Crawl</option>
                <option value="no_index" class="text-indigo-500" {}>7. No Index</option>
                <option value="content_audit" class="text-teal-500" {}>8. Content Audit</option>
                <option value="merge" class="text-orange-500" {}>9. Merge</option>
            </select>
        ''', record.id,
            'selected' if value == 'leave' else '',
            'selected' if value == 'update_on_page' else '',
            'selected' if value == 'target_with_links' else '',
            'selected' if value == '301' else '',
            'selected' if value == 'canonicalize' else '',
            'selected' if value == 'block_crawl' else '',
            'selected' if value == 'no_index' else '',
            'selected' if value == 'content_audit' else '',
            'selected' if value == 'merge' else ''
        )
