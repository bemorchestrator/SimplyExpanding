# filters.py

import django_filters
from .models import UploadedFile

class UploadedFileFilter(django_filters.FilterSet):
    class Meta:
        model = UploadedFile
        fields = {
            'url': ['icontains'],
            'page_path': ['icontains'],
            'crawl_depth': ['exact', 'gte', 'lte'],
            'category': ['icontains'],
            'main_kw': ['icontains'],
            'kw_volume': ['exact', 'gte', 'lte'],
            'kw_ranking': ['exact', 'gte', 'lte'],
            'best_kw': ['icontains'],
            'best_kw_volume': ['exact', 'gte', 'lte'],
            'best_kw_ranking': ['exact', 'gte', 'lte'],
            'impressions': ['exact', 'gte', 'lte'],
            'sessions': ['exact', 'gte', 'lte'],
            'percent_change_sessions': ['exact', 'gte', 'lte'],
            'bounce_rate': ['exact', 'gte', 'lte'],
            'avg_time_on_page': ['exact', 'gte', 'lte'],
            'losing_traffic': ['exact'],
            'links': ['exact', 'gte', 'lte'],
            'serp_ctr': ['exact', 'gte', 'lte'],
            'type': ['icontains'],
            'current_title': ['icontains'],
            'meta': ['icontains'],
            'h1': ['icontains'],
            'word_count': ['exact', 'gte', 'lte'],
            'canonical_link': ['icontains'],
            'status_code': ['exact'],
            'index_status': ['icontains'],
            'inlinks': ['exact', 'gte', 'lte'],
            'outlinks': ['exact', 'gte', 'lte'],
            'action_choice': ['exact'],
        }
