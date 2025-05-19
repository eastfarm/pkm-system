import os
import io
import json
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from organize import organize_files

app = FastAPI()

SCOPES = ["https://www.googleapis.com/auth/drive"]
REDIRECT_URI = os.environ["GOOGLE_REDIRECT_URI"]

CLIENT_CONFIG = {
    "web": {
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "redirect_uris": [REDIRECT_URI],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

# ─── AUTH FLOW ─────────────────────────────────────────────────────

@app.get("/auth/initiate")
def auth_initiate():
    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
    return RedirectResponse(auth_url)

@app.get("/oauth/callback")
async def auth_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return JSONResponse(status_code=400, content={"error": "Missing auth code"})
    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    flow.fetch_token(code=code)
    creds = flow.credentials
    return JSONResponse(content=json.loads(creds.to_json()))

# ─── UPLOAD HELPERS ───────────────────────────────────────────────

def upload_file_to_drive(service, local_path, filename, parent_id):
    media = MediaFileUpload(local_path, resumable=True)
    body = {"name": filename, "parents": [parent_id]}
    uploaded = service.files().create(body=body, media_body=media, fields="id").execute()
    return uploaded.get("id")

def find_or_create_folder(service, parent_id, name):
    query = f"'{parent_id}' in parents and name='{name}' and mimeType='application/vnd.google-apps.folder'"
    res = service.files().list(q=query, fields="files(id)").execute()
    folders = res.get("files", [])
    if folders:
        return folders[0]['id']
    folder_metadata = {
        "name": name,
        "parents": [parent_id],
        "mimeType": "application/vnd.google-apps.folder"
    }
    folder = service.files().create(body=folder_metadata, fields="id").execute()
    return folder['id']

# ─── SYNC DRIVE ───────────────────────────────────────────────────

@app.post("/sync-drive")
def sync_drive():
    LOCAL_INBOX = "pkm/Inbox"
    LOCAL_METADATA = "pkm/Processed/Metadata"
    LOCAL_SOURCES = "pkm/Processed/Sources"
    downloaded = []
    uploaded = []

    creds = Credentials.from_authorized_user_info(json.loads(os.environ["GOOGLE_TOKEN_JSON"]), SCOPES)
    service = build('drive', 'v3', credentials=creds)

    # 1. Locate PKM + subfolders
    pkm_id = find_or_create_folder(service, "root", "PKM")
    inbox_id = find_or_create_folder(service, pkm_id, "Inbox")
    processed_id = find_or_create_folder(service, pkm_id, "Processed")
    metadata_id = find_or_create_folder(service, processed_id, "Metadata")
    sources_id = find_or_create_folder(service, processed_id, "Sources")

    # 2. Download files from /Inbox
    query_files = f"'{inbox_id}' in parents and trashed = false"
    files = service.files().list(q=query_files, fields="files(id, name)").execute().get('files', [])
    os.makedirs(LOCAL_INBOX, exist_ok=True)

    for f in files:
        file_id = f['id']
        file_name = f['name']
        local_path = os.path.join(LOCAL_INBOX, file_name)
        request = service.files().get_media(fileId=file_id)
        with io.FileIO(local_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        downloaded.append((file_id, file_name))

    # 3. Run metadata extraction
    organize_files()

    # 4. Upload files and metadata
    for file_id, file_name in downloaded:
        base = os.path.splitext(file_name)[0]
        md_filename = next((f for f in os.listdir(LOCAL_METADATA) if base in f), None)
        local_md_path = os.path.join(LOCAL_METADATA, md_filename) if md_filename else None
        file_type = infer_file_type(file_name)
        local_original_path = os.path.join(LOCAL_SOURCES, file_type, file_name)

        try:
            # Upload metadata
            if local_md_path and os.path.exists(local_md_path):
                upload_file_to_drive(service, local_md_path, md_filename, metadata_id)
            else:
                raise Exception(f"Missing .md file for {file_name}")

            # Upload original
            if os.path.exists(local_original_path):
                ft_folder_id = find_or_create_folder(service, sources_id, file_type)
                upload_file_to_drive(service, local_original_path, file_name, ft_folder_id)
            else:
                raise Exception(f"Missing source file for {file_name}")

            # Delete from Inbox (only if both uploads succeeded)
            service.files().delete(fileId=file_id).execute()
            uploaded.append(file_name)

        except Exception as e:
            print(f"❌ Failed to upload/delete {file_name}: {e}")

    return {
        "status": "✅ Synced and organized",
        "downloaded": [f[1] for f in downloaded],
        "uploaded": uploaded,
        "skipped": [f[1] for f in downloaded if f[1] not in uploaded]
    }

# ─── UTILITIES ─────────────────────────────────────────────────────

def infer_file_type(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in [".md", ".txt"]: return "text"
    if ext in [".pdf"]: return "pdf"
    if ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp"]: return "image"
    if ext in [".mp3", ".wav", ".m4a"]: return "audio"
    if ext in [".doc", ".docx"]: return "document"
    return "other"

# ─── STAGING MOCK ENDPOINTS ────────────────────────────────────────

@app.get("/staging")
def get_staging():
    return {"status": "placeholder", "message": "List unprocessed files here"}

@app.post("/approve")
def approve_file(payload: dict):
    return {"status": "approved", "payload": payload}

@app.post("/trigger-organize")
def trigger_organize():
    organize_files()
    return {"status": "triggered"}
