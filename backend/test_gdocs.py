from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

# Load credentials
SCOPES = ['https://www.googleapis.com/auth/documents.readonly']
creds = service_account.Credentials.from_service_account_file(
    'google-credentials.json',
    scopes=SCOPES
)

# Build service
service = build('docs', 'v1', credentials=creds)

# Test: Fetch your Acceldata doc
DOC_ID = '1mn_Zryn4XiXonQScIM3o3CcTXOUKVrfyJGu3r4czjkM'

try:
    document = service.documents().get(documentId=DOC_ID).execute()
    title = document.get('title')
    print(f"✅ Success! Document title: {title}")
    print(f"✅ Google Docs API is working!")
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nMake sure:")
    print("1. Service account email is added to Google Doc")
    print("2. JSON credentials file exists")
    print("3. Google Docs API is enabled")