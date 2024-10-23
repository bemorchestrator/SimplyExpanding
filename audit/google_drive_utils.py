import os
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

# Configure logging
logger = logging.getLogger(__name__)

# Path to your service account key JSON file for Google Drive access
SERVICE_ACCOUNT_FILE = r'C:\Users\bem\Desktop\credentials\se_service_account.json'

def get_drive_credentials():
    """Get Google Drive credentials using service account."""
    SCOPES = ['https://www.googleapis.com/auth/drive']
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        return credentials
    except Exception as e:
        logger.error(f"Failed to load service account credentials: {e}")
        return None

def upload_file_to_drive(request, file_path, file_name):
    creds = get_drive_credentials()
    if not creds:
        logger.error("Could not obtain Drive credentials.")
        return None, None  # Handle no credentials case

    service = build('drive', 'v3', credentials=creds)

    # Metadata for the Google Drive file
    file_metadata = {
        'name': file_name,
        'parents': ['<Your-Google-Drive-Folder-ID>']  # Replace with your folder ID
    }

    # Upload the file to Google Drive
    media = MediaFileUpload(file_path, resumable=True)  # Adjust MIME type and parameters as needed
    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()

    # Return both the file ID and the webViewLink for storing in the database
    return uploaded_file.get('id'), uploaded_file.get('webViewLink')
