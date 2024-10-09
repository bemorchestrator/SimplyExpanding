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

    # Helper function to check if any of the possible columns exist
    def has_columns(required_columns):
        return all(any(col in normalized_headers for col in possible_names) for possible_names in required_columns.values())

    # Check for Screaming Frog CSV
    if has_columns(screaming_frog_columns):
        return 'screaming_frog'

    # Check for Search Console CSV
    if has_columns(search_console_columns):
        return 'search_console'

    # Return unknown if neither type matches
    return 'unknown'