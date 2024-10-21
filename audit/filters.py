import django_filters
from django import forms  # Import the forms module from Django
from .models import UploadedFile

CONTAINS_CHOICES = [
    ('contains', 'Contains'),
    ('does_not_contain', 'Does Not Contain'),
]

SITEMAP_CHOICES = [
    (True, 'Yes'),
    (False, 'No')
]

class UploadedFileFilter(django_filters.FilterSet):
    # Action choice filter with a consistent width
    action_choice = django_filters.ChoiceFilter(
        field_name='action_choice',
        choices=UploadedFile.ACTION_CHOICES,
        label='Action Choice',
        widget=forms.Select(attrs={
            'class': 'bg-gray-800 text-white border border-gray-600 rounded-md py-2 px-3 w-48'
        })
    )

    # Filter to select contains/does not contain with consistent width
    url_contains = django_filters.ChoiceFilter(
        choices=CONTAINS_CHOICES,
        label='URL Filter Type',
        method='filter_by_url_type',
        widget=forms.Select(attrs={
            'class': 'bg-gray-800 text-white border-l border-gray-600 rounded-l-md py-2 px-3 w-48'
        })
    )

    # Input field for the URL filter with consistent width
    url_value = django_filters.CharFilter(
        field_name='url',
        label='URL',
        method='filter_by_url_value',
        widget=forms.TextInput(attrs={
            'class': 'bg-gray-800 text-white border-t border-r border-b border-gray-600 rounded-r-md py-2 px-3 w-48',
            'placeholder': 'Enter URL...'
        })
    )

    # Input field for crawl depth with consistent width
    crawl_depth = django_filters.NumberFilter(
        field_name='crawl_depth',
        label='Crawl Depth',
        widget=forms.NumberInput(attrs={
            'class': 'bg-gray-800 text-white border border-gray-600 rounded-md py-2 px-3 w-48',
            'placeholder': 'Enter depth...'
        })
    )

    # Dropdown filter for the category column with consistent width
    category = django_filters.ChoiceFilter(
        field_name='category',
        label='Category',
        choices=UploadedFile.CATEGORY_CHOICES,
        widget=forms.Select(attrs={
            'class': 'bg-gray-800 text-white border border-gray-600 rounded-md py-2 px-3 w-48'
        })
    )

    # Dropdown filter for In Sitemap (Yes/No)
    in_sitemap = django_filters.ChoiceFilter(
        field_name='in_sitemap',
        label='In Sitemap',
        choices=SITEMAP_CHOICES,
        widget=forms.Select(attrs={
            'class': 'bg-gray-800 text-white border border-gray-600 rounded-md py-2 px-3 w-48'
        })
    )

    class Meta:
        model = UploadedFile
        fields = ['action_choice', 'url_contains', 'url_value', 'crawl_depth', 'category', 'in_sitemap']

    def filter_by_url_type(self, queryset, name, value):
        self.url_filter_type = value
        return queryset

    def filter_by_url_value(self, queryset, name, value):
        filter_type = getattr(self, 'url_filter_type', 'contains')
        if filter_type == 'contains':
            return queryset.filter(url__icontains=value)
        elif filter_type == 'does_not_contain':
            return queryset.exclude(url__icontains=value)
        return queryset
