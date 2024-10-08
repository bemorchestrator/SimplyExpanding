def identify_csv_type(headers):
    # Columns required to identify Screaming Frog CSV
    required_columns = {
        'url': 'Address',
        'type': 'Content Type',
        'current_title': 'Title 1',
        'meta': 'Meta Description 1',
        'h1': 'H1-1',
        'word_count': 'Word Count',
        'canonical_link': 'Canonical Link Element 1',
        'status_code': 'Status Code',
        'index_status': 'Indexability',
        'inlinks': 'Inlinks',
        'outlinks': 'Outlinks',
        'crawl_depth': 'Crawl Depth'
    }

    # Check if all required columns for Screaming Frog CSV are present in the file
    if all(column in headers for column in required_columns.values()):
        return 'screaming_frog'
    
    # Check for Google Search Console CSV
    if 'Top pages' in headers and 'Impressions' in headers:
        return 'search_console'
    
    # Return unknown if neither type matches
    return 'unknown'
