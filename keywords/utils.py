import csv

def identify_serp_csv_type(headers):
    """
    Identify the type of CSV file based on its headers for SERP analysis.
    """
    # Normalize headers by stripping whitespace and converting to lowercase
    normalized_headers = [header.strip().lower() for header in headers]

    # Columns required to identify SERP Analysis CSV
    serp_analysis_columns = {
        'position': ['position'],
        'serp_features': ['position serp features', 'serp features'],
        'previous_position': ['previous position'],
        'url': ['url'],
        'title': ['title'],
        'total_traffic': ['total traffic'],
        'total_traffic_cost': ['total traffic cost'],
        'keywords_total': ['keywords total'],
        'dt': ['dt'],
        'pt': ['pt'],
        'backlinks': ['backlinks'],
        'referring_domains': ['referring domains']
    }

    # Helper function to check if all required columns exist
    def has_columns(required_columns):
        for key, possible_names in required_columns.items():
            if not any(possible_name.lower() in normalized_headers for possible_name in possible_names):
                return False
        return True

    # Check if the CSV matches the SERP analysis format
    if has_columns(serp_analysis_columns):
        return 'serp_analysis'

    # Return 'unknown' if the file type does not match the SERP analysis format
    return 'unknown'


def read_and_identify_csv(file):
    """
    Read the CSV file and identify its type using the headers.
    """
    file.seek(0)  # Ensure the file pointer is at the beginning
    reader = csv.reader(file.read().decode('utf-8').splitlines())
    headers = next(reader, None)

    if headers is None:
        raise ValueError("No headers found in the CSV file.")

    # Identify the type of CSV file
    csv_type = identify_serp_csv_type(headers)
    return csv_type
