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
        'page_path': ['page path and screen class'],
        'sessions': ['sessions'],
        'bounce_rate': ['bounce rate'],
        'avg_session_duration': ['average session duration']
    }

    # Columns required to identify Keyword Research CSV
    keyword_research_columns = {
        'keyword': ['keyword'],
        'difficulty': ['difficulty'],
        'position': ['position'],
        'previous_position': ['previous position'],
        'position_serp_features': ['position serp features'],
        'search_vol': ['search vol.'],
        'search_intent': ['search intent'],
        'serp_features': ['serp features'],
        'competition': ['competition'],
        'cpc': ['cpc'],
        'url': ['url'],
        'traffic': ['traffic'],
        'traffic_share': ['traffic share'],
        'traffic_cost': ['traffic cost']
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

    # Check for Google Analytics CSV
    if has_columns(google_analytics_columns):
        return 'google_analytics'

    # Check for Keyword Research CSV
    if has_columns(keyword_research_columns):
        return 'keyword_research'

    # Return unknown if neither type matches
    return 'unknown'
