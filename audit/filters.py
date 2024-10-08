# filters.py

import django_filters
from .models import UploadedFile
from django.db.models import Q

class UploadedFileFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method='filter_by_all_fields', label='Search')

    class Meta:
        model = UploadedFile
        fields = {
            'url': ['icontains'],  # Filter URLs by partial match
            'page_path': ['icontains'],  # Filter page paths
            'crawl_depth': ['exact', 'gte', 'lte'],  # Filter by exact or range
            'category': ['icontains'],  # Filter by category (partial match)
            'main_kw': ['icontains'],  # Filter by main keyword
            'kw_volume': ['exact', 'gte', 'lte'],  # Keyword volume (range)
            'kw_ranking': ['exact', 'gte', 'lte'],  # Keyword ranking
            'best_kw': ['icontains'],  # Best keyword filter
            'best_kw_volume': ['exact', 'gte', 'lte'],  # Best keyword volume filter
            'best_kw_ranking': ['exact', 'gte', 'lte'],  # Best keyword ranking
            'impressions': ['exact', 'gte', 'lte'],  # Filter by impressions (range)
            'sessions': ['exact', 'gte', 'lte'],  # Filter by session count
            'percent_change_sessions': ['exact', 'gte', 'lte'],  # Filter session % change
            'bounce_rate': ['exact', 'gte', 'lte'],  # Filter by bounce rate
            'avg_time_on_page': ['exact', 'gte', 'lte'],  # Filter avg time on page
            'losing_traffic': ['exact'],  # Exact filter for losing traffic
            'links': ['exact', 'gte', 'lte'],  # Filter by number of links
            'serp_ctr': ['exact', 'gte', 'lte'],  # Filter SERP click-through-rate
            'type': ['icontains'],  # Filter by type (partial match)
            'current_title': ['icontains'],  # Filter by current title
            'meta': ['icontains'],  # Filter by meta description
            'h1': ['icontains'],  # Filter by H1 tag content
            'word_count': ['exact', 'gte', 'lte'],  # Filter by word count
            'canonical_link': ['icontains'],  # Filter by canonical link
            'status_code': ['exact'],  # Filter by status code
            'index_status': ['icontains'],  # Filter by index status (partial match)
            'inlinks': ['exact', 'gte', 'lte'],  # Filter by inlinks
            'outlinks': ['exact', 'gte', 'lte'],  # Filter by outlinks
            'action_choice': ['exact'],  # Filter by action choice
        }

    def filter_by_all_fields(self, queryset, name, value):
        """Search across multiple fields."""
        return queryset.filter(
            Q(url__icontains=value) |
            Q(page_path__icontains=value) |
            Q(main_kw__icontains=value) |
            Q(current_title__icontains=value) |
            Q(meta__icontains=value) |
            Q(h1__icontains=value)
        )
