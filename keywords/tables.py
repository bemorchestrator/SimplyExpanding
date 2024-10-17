import django_tables2 as tables
from django.utils.html import format_html
from .models import KeywordResearchEntry  # Use the correct model for Keyword Research

class KeywordResearchTable(tables.Table):
    action_choice = tables.Column(
        verbose_name='Action Choice',
        attrs={
            "td": {
                "class": "sticky-col-1", 
                "style": "white-space: nowrap; position: sticky; left: 0; background-color: #2d3748; z-index: 3; min-width: 150px; padding: 10px 20px; font-size: 14px; line-height: 1.6;"
            },
            "th": {
                "class": "sticky-col-1", 
                "style": "white-space: nowrap; position: sticky; top: 0; left: 0; background-color: #2d3748; z-index: 5; min-width: 150px; padding: 10px 20px; font-size: 14px; line-height: 1.6;"
            }
        }
    )

    def render_action_choice(self, value, record):
        action_choice_colors = {
            'Leave As Is': '#9b51e0',        # Purple
            'Update On Page': '#6a5acd',     # Slate Blue
            'Target w/ Links': '#2d9cdb',    # Cyan
            '301': '#f2994a',                 # Orange
            'Canonicalize': '#6fcf97',        # Light Teal
            'Block Crawl': '#e67e22',         # Darker Orange
            'No Index': '#eb5757',            # Red
            'Content Audit': '#56ccf2',       # Light Blue
            'Merge': '#2f80ed'               # Royal Blue
        }

        background_color = action_choice_colors.get(value, '#ffffff')
        return format_html(
            '<span style="background-color: {}; padding: 5px 10px; border-radius: 4px; color: #fff; display: inline-block; min-width: 150px; text-align: center;">{}</span>',
            background_color, value
        )

    url = tables.URLColumn(
        verbose_name='URL',
        attrs={
            "td": {
                "class": "sticky-col-2", 
                "style": "white-space: nowrap; position: sticky; left: 150px; background-color: #2d3748; z-index: 4; padding: 10px 20px; font-size: 14px; line-height: 1.6;"
            },
            "th": {
                "class": "sticky-col-2", 
                "style": "white-space: nowrap; position: sticky; top: 0; left: 150px; background-color: #2d3748; z-index: 5; padding: 10px 20px; font-size: 14px; line-height: 1.6;"
            }
        }
    )

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
                font-size: 14px;
                line-height: 1.6;
            ">
                {}
            </a>
            ''',
            value, value, truncated_url
        )

    # Column: Category
    category = tables.Column(
        verbose_name='Category',
        attrs={
            "td": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"},
            "th": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"}
        }
    )

    # Column: Main Keyword
    main_kw = tables.Column(
        verbose_name='Main Keyword',
        attrs={
            "td": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"},
            "th": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"}
        }
    )

    # Column: KW Volume
    kw_volume = tables.Column(
        verbose_name='Volume',
        attrs={
            "td": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"},
            "th": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"}
        }
    )

    # Column: KW Ranking
    kw_ranking = tables.Column(
        verbose_name='Ranking',
        attrs={
            "td": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"},
            "th": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"}
        }
    )

    # Column: Best KW
    best_kw = tables.Column(
        verbose_name='Best KW',
        attrs={
            "td": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"},
            "th": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"}
        }
    )

    # Column: Best KW Volume
    best_kw_volume = tables.Column(
        verbose_name='Best KW Volume',
        attrs={
            "td": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"},
            "th": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"}
        }
    )

    # Column: Best KW Ranking
    best_kw_ranking = tables.Column(
        verbose_name='Best KW Ranking',
        attrs={
            "td": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"},
            "th": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"}
        }
    )

    # Column: Primary Keyword (Editable)
    primary_keyword = tables.Column(
        verbose_name="Primary Keyword",
        attrs={
            "td": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"},
            "th": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"}
        }
    )

    primary_keyword = tables.Column(
        verbose_name="Primary Keyword",
        attrs={
            "td": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"},
            "th": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"}
        }
    )
    
    def render_primary_keyword(self, value, record):
        return format_html(
            '<input type="text" class="editable" data-id="{}" data-field="primary_keyword" value="{}" style="width: 150px;">',
            record.id, value or ''
        )

    # PK Volume (Editable Number Input)
    pk_volume = tables.Column(
        verbose_name="PK Volume",
        attrs={
            "td": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"},
            "th": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"}
        }
    )
    
    def render_pk_volume(self, value, record):
        return format_html(
            '<input type="number" class="editable" data-id="{}" data-field="pk_volume" value="{}" style="width: 100px;">',
            record.id, value or 0
        )

    # PK Ranking (Editable Number Input)
    pk_ranking = tables.Column(
        verbose_name="PK Ranking",
        attrs={
            "td": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"},
            "th": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"}
        }
    )
    
    def render_pk_ranking(self, value, record):
        return format_html(
            '<input type="number" class="editable" data-id="{}" data-field="pk_ranking" value="{}" style="width: 100px;">',
            record.id, value or 0
        )

    # Secondary Keywords (Editable Text Input)
    secondary_keywords = tables.Column(
        verbose_name="Secondary Keywords",
        attrs={
            "td": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"},
            "th": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"}
        }
    )
    
    def render_secondary_keywords(self, value, record):
        return format_html(
            '<input type="text" class="editable" data-id="{}" data-field="secondary_keywords" value="{}" style="width: 250px;">',
            record.id, value or ''
        )

    # Column: Customer Journey
    customer_journey = tables.Column(
        verbose_name='Customer Journey',
        attrs={
            "td": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"},
            "th": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"}
        }
    )

    # Column: SERP Content Type
    serp_content_type = tables.Column(
        verbose_name='SERP Content Type',
        attrs={
            "td": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"},
            "th": {"style": "white-space: nowrap; font-size: 14px; line-height: 1.6; padding: 10px 30px;"}
        }
    )

    class Meta:
        model = KeywordResearchEntry  # Use the correct model
        template_name = "django_tables2/bootstrap.html"
        fields = [
            'action_choice', 'url', 'category', 'main_kw', 'kw_volume', 'kw_ranking', 
            'best_kw', 'best_kw_volume', 'best_kw_ranking', 'primary_keyword', 'pk_volume', 
            'pk_ranking', 'secondary_keywords', 'customer_journey', 'serp_content_type'
        ]

        # Updated attrs to include column spacing and consistent padding
        attrs = {
            'class': 'table table-striped text-white',
            'style': 'border-spacing: 0 20px; border-collapse: separate;',  # Add horizontal and vertical spacing between cells
            'td': {
                'style': 'white-space: nowrap; padding: 10px 30px; text-align: left; font-size: 14px; line-height: 1.6;'  # Added padding for column spacing
            },
            'th': {
                'style': 'white-space: nowrap; padding: 10px 30px; text-align: left; min-width: 150px; font-size: 14px; line-height: 1.6;'  # Added padding for column spacing
            }
        }
