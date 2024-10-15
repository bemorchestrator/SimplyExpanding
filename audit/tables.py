import django_tables2 as tables
from django.utils.html import format_html
from .models import UploadedFile
from .forms import UploadedFileForm
from django.urls import reverse
from django.middleware.csrf import get_token

class UploadedFileTable(tables.Table):
    action_choice = tables.Column(
        verbose_name='Action choice',
        attrs={
            "td": {
                "class": "sticky-col-1",
                "style": (
                    "white-space: nowrap; position: sticky; left: 0; "
                    "background-color: #2d3748; z-index: 3; width: 120px;"
                )
            },
            "th": {
                "class": "sticky-col-1",
                "style": (
                    "position: sticky; top: 0; left: 0; "
                    "background-color: #2d3748; z-index: 5; width: 120px;"
                )
            }
        }
    )

    def render_action_choice(self, value, record):
        form = UploadedFileForm(instance=record)
        options_html = ""
        for key, choice in record.ACTION_CHOICES:
            selected = "selected" if record.action_choice == key else ""
            options_html += f'<option value="{key}" {selected}>{choice}</option>'

        return format_html(
            '''
            <form method="post" class="sticky-col-1" style="position: sticky; left: 0; z-index: 3;">
                <select name="action_choice" class="action-dropdown">
                    {}
                </select>
            </form>
            ''',
            options_html
        )


    def render_category(self, value, record):
        form = UploadedFileForm(instance=record)
        options_html = ""
        for key, choice in record.CATEGORY_CHOICES:
            selected = "selected" if record.category == key else ""
            options_html += f'<option value="{key}" {selected}>{choice}</option>'

        return format_html(
            '''
            <form method="post">
                <select name="category" class="category-dropdown">
                    {}
                </select>
            </form>
            ''',
            options_html
        )



    # URL Column with Custom Rendering
    def render_url(self, value, record):
        truncated_url = value if len(value) <= 150 else value[:150] + "..."
        return format_html(
            '''
            <a href="{}" title="{}" style="
                white-space: nowrap; 
                overflow: hidden; 
                text-overflow: ellipsis; 
                display: inline-block; 
                max-width: 480px;
            ">
                {}
            </a>
            ''',
            value, value, truncated_url
        )

    url = tables.URLColumn(
        verbose_name='URL',
        attrs={
            "td": {
                "class": "sticky-col-2",
                "style": (
                    "white-space: nowrap; position: sticky; left: 121px; "
                    "background-color: #2d3748; z-index: 1; width: 300px; min-height: 100px;"
                )
            },
            "th": {
                "class": "sticky-col-2",
                "style": (
                    "position: sticky; top: 0; left: 121px; "
                    "background-color: #2d3748; z-index: 2; width: 300px;"
                )
            }
        }
    )

    page_path = tables.Column(
        verbose_name='Page Path',
        attrs={
            "td": {
                "style": "white-space: nowrap; padding-left: 40px;"
            },
            "th": {
                "style": "text-align: left; padding-left: 50px;"
            }
        }
    )

    def render_page_path(self, value, record):
        truncated_page_path = value if len(value) <= 150 else value[:150] + "..."
        return format_html(
            '''
            <div title="{}" style="
                white-space: nowrap; 
                overflow: hidden; 
                text-overflow: ellipsis; 
                display: inline-block; 
                max-width: 480px;
                padding-left: 15px;
            ">
                {}
            </div>
            ''',
            value, truncated_page_path
        )

    crawl_depth = tables.Column(verbose_name='Crawl Depth', attrs={"td": {"style": "white-space: nowrap;"}})

    in_sitemap = tables.Column(verbose_name='In Sitemap', attrs={"td": {"style": "white-space: nowrap;"}})

    def render_in_sitemap(self, value):
        if value:
            return format_html('<span style="color: green;">&#10003;</span>')
        else:
            return format_html('<span style="color: red;">&#10007;</span>')

    # Keyword Performance Columns
    main_kw = tables.Column(verbose_name='Main KW', attrs={"td": {"style": "white-space: nowrap;"}})

    def render_main_kw(self, value, record):
        return value if value else '-'

    kw_volume = tables.Column(verbose_name='Volume', attrs={"td": {"style": "white-space: nowrap;"}})

    def render_kw_volume(self, value, record):
        return value if value else '-'

    kw_ranking = tables.Column(verbose_name='Ranking', attrs={"td": {"style": "white-space: nowrap;"}})

    def render_kw_ranking(self, value, record):
        return value if value else '-'

    best_kw = tables.Column(verbose_name='Best KW', attrs={"td": {"style": "white-space: nowrap;"}})

    def render_best_kw(self, value, record):
        return value if value else '-'

    best_kw_volume = tables.Column(verbose_name='Best KW Volume', attrs={"td": {"style": "white-space: nowrap;"}})

    def render_best_kw_volume(self, value, record):
        return value if value else '-'

    best_kw_ranking = tables.Column(verbose_name='Best KW Ranking', attrs={"td": {"style": "white-space: nowrap;"}})

    def render_best_kw_ranking(self, value, record):
        return value if value else '-'

    # Page Performance Columns
    impressions = tables.Column(verbose_name='Impressions', attrs={"td": {"style": "white-space: nowrap;"}})
    sessions = tables.Column(verbose_name='Sessions', attrs={"td": {"style": "white-space: nowrap;"}})

    def render_sessions(self, value, record):
        return value if value else '-'

    percent_change_sessions = tables.Column(verbose_name='% Change Sessions', attrs={"td": {"style": "white-space: nowrap;"}})

    def render_percent_change_sessions(self, value, record):
        if value is None:
            return '-'
        try:
            value_float = float(value)
        except (ValueError, TypeError):
            return '-'
        if value_float > 0:
            color = 'green'
        elif value_float < 0:
            color = 'red'
        else:
            color = 'orange'
        formatted_value = '{:+.2f}%'.format(value_float)
        return format_html('<span style="color: {};">{}</span>', color, formatted_value)

    bounce_rate = tables.Column(verbose_name='Bounce Rate', attrs={"td": {"style": "white-space: nowrap;"}})

    def render_bounce_rate(self, value, record):
        if value:
            try:
                value_float = float(value)
                formatted_value = f"{value_float:.2f}%"
                return formatted_value
            except (ValueError, TypeError):
                return '-'
        else:
            return '-'

    avg_time_on_page = tables.Column(verbose_name='Avg Time on Page', attrs={"td": {"style": "white-space: nowrap;"}})

    def render_avg_time_on_page(self, value, record):
        if value:
            # Directly return the value from the CSV without conversion
            return value
        else:
            return '-'



    links = tables.Column(verbose_name='Links', attrs={"td": {"style": "white-space: nowrap;"}})

    def render_links(self, value, record):
        return value if value else '-'

    serp_ctr = tables.Column(verbose_name='SERP CTR', attrs={"td": {"style": "white-space: nowrap;"}})

    def render_serp_ctr(self, value, record):
        if value is not None:
            try:
                return f"{float(value):.2f}%"
            except (ValueError, TypeError):
                return '-'
        else:
            return '-'

    # Screaming Frog On-Page Columns
    type = tables.Column(verbose_name='Type', attrs={"td": {"style": "white-space: nowrap;"}})
    current_title = tables.Column(verbose_name='Current Title', attrs={"td": {"style": "white-space: nowrap;"}})

    # Meta Column with Custom Rendering
    def render_meta(self, value, record):
        truncated_meta = value if len(value) <= 150 else value[:150] + "..."
        return format_html(
            '''
            <div title="{}" style="
                white-space: nowrap; 
                overflow: hidden; 
                text-overflow: ellipsis; 
                display: inline-block; 
                max-width: 480px;
            ">
                {}
            </div>
            ''',
            value, truncated_meta
        )

    h1 = tables.Column(verbose_name='H1', attrs={"td": {"style": "white-space: nowrap;"}})
    word_count = tables.Column(verbose_name='Word Count', attrs={"td": {"style": "white-space: nowrap;"}})
    canonical_link = tables.URLColumn(verbose_name='Canonical Link', attrs={"td": {"style": "white-space: nowrap;"}})
    status_code = tables.Column(verbose_name='Status Code', attrs={"td": {"style": "white-space: nowrap;"}})
    index_status = tables.Column(verbose_name='Index/No Index', attrs={"td": {"style": "white-space: nowrap;"}})
    inlinks = tables.Column(verbose_name='Inlinks', attrs={"td": {"style": "white-space: nowrap;"}})
    outlinks = tables.Column(verbose_name='Outlinks', attrs={"td": {"style": "white-space: nowrap;"}})

    class Meta:
        model = UploadedFile
        template_name = 'audit/custom_table.html'
        fields = [
            'action_choice', 'url', 'page_path', 'crawl_depth', 'category', 'in_sitemap',
            'main_kw', 'kw_volume', 'kw_ranking', 'best_kw', 'best_kw_volume', 'best_kw_ranking',
            'impressions', 'sessions', 'percent_change_sessions', 'bounce_rate', 'avg_time_on_page',
            'losing_traffic', 'links', 'serp_ctr', 'type', 'current_title', 'meta', 'h1',
            'word_count', 'canonical_link', 'status_code', 'index_status', 'inlinks', 'outlinks'
        ]
        attrs = {'class': 'table table-striped text-white'}



class KeywordResearchTable(tables.Table):
    action_choice = tables.Column(
        verbose_name='Action Choice',
        attrs={
            "td": {"class": "sticky-col-1", "style": "white-space: nowrap; position: sticky; left: 0; background-color: #2d3748; z-index: 3; width: 150px; padding: 0 20px;"},
            "th": {"class": "sticky-col-1", "style": "position: sticky; top: 0; left: 0; background-color: #2d3748; z-index: 5; width: 150px; padding: 0 20px;"}
        }
    )

    def render_action_choice(self, value, record):
        action_choice_colors = {
            'Leave As Is': '#9b51e0',  # Purple
            'Update On Page': '#6a5acd',  # Slate Blue
            'Target w/ Links': '#2d9cdb',  # Cyan
            '301': '#f2994a',  # Orange
            'Canonicalize': '#6fcf97',  # Light Teal
            'Block Crawl': '#e67e22',  # Darker Orange
            'No Index': '#eb5757',  # Red
            'Content Audit': '#56ccf2',  # Light Blue
            'Merge': '#2f80ed'  # Royal Blue
        }

        button_width = '150px'
        background_color = action_choice_colors.get(value, '#ffffff')

        return format_html(
            '<span style="background-color: {}; padding: 5px 10px; border-radius: 4px; color: #fff; display: inline-block; width: {}; text-align: center;">{}</span>',
            background_color, button_width, value
        )

    url = UploadedFileTable.base_columns['url']
    
    def render_url(self, value, record):
        truncated_url = value if len(value) <= 120 else value[:120] + "..."
        return format_html(
            '''
            <a href="{}" title="{}" style="
                white-space: nowrap; 
                overflow: hidden; 
                text-overflow: ellipsis; 
                display: inline-block; 
                max-width: 380px;
            ">
                {}
            </a>
            ''',
            value, value, truncated_url
        )

    category = UploadedFileTable.base_columns['category']
    main_kw = UploadedFileTable.base_columns['main_kw']
    kw_volume = UploadedFileTable.base_columns['kw_volume']
    kw_ranking = UploadedFileTable.base_columns['kw_ranking']
    best_kw = UploadedFileTable.base_columns['best_kw']
    best_kw_volume = UploadedFileTable.base_columns['best_kw_volume']
    best_kw_ranking = UploadedFileTable.base_columns['best_kw_ranking']
    primary_keyword = tables.Column(verbose_name="Primary Keyword")
    pk_volume = tables.Column(verbose_name="PK Volume")
    pk_ranking = tables.Column(verbose_name="PK Ranking")
    secondary_keywords = tables.Column(verbose_name="Secondary Keywords")
    

    class Meta:
        model = UploadedFile
        template_name = "django_tables2/bootstrap.html"
        fields = ['action_choice', 'url', 'category', 'main_kw', 'kw_volume', 
                  'kw_ranking', 'best_kw', 'best_kw_volume', 'best_kw_ranking', 'primary_keyword', 'pk_volume', 'pk_ranking','secondary_keywords']

        # Apply consistent padding for all columns except Action Choice and URL
        attrs = {
            'class': 'table table-striped text-white',
            'td': {
                'style': lambda column: 'white-space: nowrap; padding: 0 20px; text-align: left;' if column.name not in ['action_choice', 'url'] else 'white-space: nowrap; text-align: left;',
                'class': lambda record, column: 'px-6' if column.name not in ['action_choice', 'url'] else ''
            },
            'th': {
                'style': lambda column: 'white-space: nowrap; padding: 0 20px; text-align: left;' if column.name not in ['action_choice', 'url'] else 'white-space: nowrap;',
                'class': lambda column: 'px-6' if column.name not in ['action_choice', 'url'] else ''
            }
        }



