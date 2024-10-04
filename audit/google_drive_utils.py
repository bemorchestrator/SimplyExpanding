import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth import get_credentials  # Use your existing authentication

def upload_file_to_drive(request, file_path, file_name):
    creds = get_credentials(request)
    if not creds:
        return None, None  # Handle no credentials case

    service = build('drive', 'v3', credentials=creds)

    # Metadata for the Google Drive file
    file_metadata = {
        'name': file_name,
        'parents': ['<Your-Google-Drive-Folder-ID>']  # Set the folder ID where you want to store the file
    }

    # Upload the file to Google Drive
    media = MediaFileUpload(file_path, mimetype='application/vnd.ms-excel')  # Adjust MIME type as needed
    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()

    # Return both the file ID and the webViewLink for storing in the database
    return uploaded_file.get('id'), uploaded_file.get('webViewLink')
