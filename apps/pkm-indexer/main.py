import os
import io
import json
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
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

    # ✅ Return the token directly so it can be copied into Railway
    return JSONResponse(content=json.loads(creds.to_json()))

# ─── GOOGLE DRIVE SYNC ─────────────────────────────────────────────

@app.post("/sync-drive")
def sync_drive():
    LOCAL_INBOX = "pkm/Inbox"
    DRIVE_FOLDER_NAME = "Inbox"

    if "GOOGLE_TOKEN_JSON" not in os.environ:
        return {"error": "Missing GOOGLE_TOKEN_JSON env variable"}

    creds = Credentials.from_authorized_user_info(json.loads(os.environ["GOOGLE_TOKEN_JSON"]), SCOPES)
    service = build('drive', 'v3', credentials=creds)

    # Find PKM root folder
    query_pkm = "name='PKM' and mimeType='application/vnd.google-apps.folder' and trashed = false"
    pkm_folders = service.files().list(q=query_pkm, fields="files(id)").execute().get('files', [])
    if not pkm_folders:
        return {"error": "No 'PKM' folder found in Drive."}

    pkm_id = pkm_folders[0]['id']

    # Find Inbox inside PKM
    query_inbox = f"'{pkm_id}' in parents and name='{DRIVE_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder'"
    inbox_folder = service.files().list(q=query_inbox, fields="files(id)").execute().get('files', [])
    if not inbox_folder:
        return {"error": "No 'Inbox' folder found inside 'PKM'."}

    inbox_id = inbox_folder[0]['id']
    query_files = f"'{inbox_id}' in parents and trashed = false"
    file_list = service.files().list(q=query_files, fields="files(id, name)").execute().get('files', [])

    os.makedirs(LOCAL_INBOX, exist_ok=True)
    downloaded = []

    for file in file_list:
        file_id = file['id']
        file_name = file['name']
        local_path = os.path.join(LOCAL_INBOX, file_name)

        request = service.files().get_media(fileId=file_id)
        with io.FileIO(local_path, 'wb') as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

        downloaded.append(file_name)

    # Process files into metadata
    organize_files()

    return {
        "status": "✅ Synced and organized",
        "downloaded": downloaded,
        "organized_count": len(downloaded)
    }

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
