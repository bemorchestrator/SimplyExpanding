# utils.py

import urllib.parse
import re

def identify_csv_type(headers):
    # Normalize headers by stripping whitespace and converting to lowercase
    normalized_headers = [header.strip().lower() for header in headers]

    # Columns required to identify Screaming Frog CSV
    screaming_frog_columns = {
        'url': ['address', 'url'],
        'type': ['content type', 'type'],
        'current_title': ['title 1', 'title'],
        'meta': ['meta description 1', 'meta description'],
        'h1': ['h1-1', 'h1'],
        'word_count': ['word count'],
        'canonical_link': ['canonical link element 1', 'canonical link'],
        'status_code': ['status code', 'status'],
        'index_status': ['indexability'],
        'inlinks': ['inlinks'],
        'outlinks': ['outlinks'],
        'crawl_depth': ['crawl depth']
    }

    # Columns required to identify Google Search Console CSV
    search_console_columns = {
        'url': ['top pages', 'page', 'url'],
        'impressions': ['impressions', 'total impressions'],
        'ctr': ['ctr', 'click through rate']
    }

    # Columns required to identify Google Analytics CSV
    google_analytics_columns = {
        'page_path': ['page path and screen class', 'page path'],
        'sessions': ['sessions'],
        'bounce_rate': ['bounce rate', 'bounce rate (%)'],
        'avg_session_duration': ['average session duration', 'avg. session duration'],
        'percent_change_sessions': ['sessions Δ', 'sessions delta', 'sessions δ', 'sessions Δ (%)', 'sessions delta (%)', 'sessions change (%)', 'sessions change'],
    }

    # Columns required to identify Keyword Research CSV
    keyword_research_columns = {
        'keyword': ['keyword'],
        'search_vol': ['search vol.'],
        'position': ['position'],
        'url': ['url'],
    }

    # Columns required to identify Backlinks CSV
    backlinks_columns = {
        'backlink_url': ['backlink url'],
        'destination_url': ['destination url'],
    }

    # Helper function to check if all required columns exist
    def has_columns(required_columns):
        for key, possible_names in required_columns.items():
            if not any(possible_name.lower() in normalized_headers for possible_name in possible_names):
                return False
        return True

    # Check for Screaming Frog CSV
    if has_columns(screaming_frog_columns):
        return 'screaming_frog'

    # Check for Search Console CSV
    elif has_columns(search_console_columns):
        return 'search_console'

    # Check for Google Analytics CSV
    elif has_columns(google_analytics_columns):
        return 'google_analytics'

    # Check for Keyword Research CSV
    elif has_columns(keyword_research_columns):
        return 'keyword_research'

    # Check for Backlinks CSV
    elif has_columns(backlinks_columns):
        return 'backlinks'

    # Return unknown if none match
    else:
        return 'unknown'

def normalize_url(url):
    # Remove protocol and www, and strip trailing slash
    parsed_url = urllib.parse.urlparse(url)
    netloc = parsed_url.netloc.replace('www.', '')
    path = parsed_url.path.rstrip('/')
    normalized = netloc + path
    return normalized

def normalize_page_path(page_path):
    # Ensure the page_path starts with '/'
    if not page_path.startswith('/'):
        page_path = '/' + page_path
    # Remove any trailing slashes
    page_path = page_path.rstrip('/')
    return page_path

def get_page_path(url):
    # Extract the path component from the URL
    parsed_url = urllib.parse.urlparse(url)
    path = parsed_url.path
    return path
