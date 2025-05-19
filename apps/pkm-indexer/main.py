from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import io
import json
import base64
import asyncio
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from organize import organize_files
from index import indexKB, searchKB

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

SCOPES = ["https://www.googleapis.com/auth/drive"]
REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8000/oauth/callback")

CLIENT_CONFIG = {
    "web": {
        "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
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

    token_json = os.environ.get("GOOGLE_TOKEN_JSON")
    if not token_json:
        return {"status": "Failed - Google Drive credentials missing"}
        
    creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
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
        "status": f"✅ Synced and organized - {len(uploaded)} files processed",
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

# ─── FILE STATS ENDPOINT ────────────────────────────────────────────

@app.get("/file-stats")
def get_file_stats():
    """Get statistics about files in the system"""
    stats = {
        "inbox_count": 0,
        "metadata_count": 0,
        "source_types": {},
    }
    
    # Count files in Inbox
    inbox_path = "pkm/Inbox"
    if os.path.exists(inbox_path):
        stats["inbox_count"] = len([f for f in os.listdir(inbox_path) if os.path.isfile(os.path.join(inbox_path, f))])
    
    # Count metadata files
    metadata_path = "pkm/Processed/Metadata"
    if os.path.exists(metadata_path):
        stats["metadata_count"] = len([f for f in os.listdir(metadata_path) if f.endswith(".md")])
    
    # Count source files by type
    sources_path = "pkm/Processed/Sources"
    if os.path.exists(sources_path):
        for source_type in os.listdir(sources_path):
            type_path = os.path.join(sources_path, source_type)
            if os.path.isdir(type_path):
                file_count = len([f for f in os.listdir(type_path) if os.path.isfile(os.path.join(type_path, f))])
                if file_count > 0:
                    stats["source_types"][source_type] = file_count
    
    return stats

# ─── LOGS ENDPOINT ────────────────────────────────────────────────

@app.get("/logs")
def list_logs():
    """List all available log files"""
    logs_path = "pkm/Logs"
    if not os.path.exists(logs_path):
        return {"logs": []}
        
    log_files = [f for f in os.listdir(logs_path) if f.endswith(".md")]
    log_files.sort(reverse=True)  # Most recent first
    
    return {
        "logs": log_files,
        "count": len(log_files)
    }

@app.get("/logs/{log_file}")
def get_log(log_file: str):
    """Get the content of a specific log file"""
    log_path = f"pkm/Logs/{log_file}"
    
    if not os.path.exists(log_path):
        return JSONResponse(status_code=404, content={"error": "Log file not found"})
        
    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    return {"filename": log_file, "content": content}

# ─── STAGING AND APPROVAL ENDPOINTS ─────────────────────────────────

@app.get("/staging")
def get_staging():
    """List files in staging that need review"""
    metadata_path = "pkm/Processed/Metadata"
    if not os.path.exists(metadata_path):
        return {"files": []}
        
    staging_files = []
    
    for filename in os.listdir(metadata_path):
        if not filename.endswith(".md"):
            continue
            
        file_path = os.path.join(metadata_path, filename)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Parse frontmatter
            if content.startswith("---"):
                # Extract YAML frontmatter
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter_yaml = parts[1]
                    file_content = parts[2].strip()
                    
                    # Basic YAML parsing
                    metadata = {}
                    for line in frontmatter_yaml.strip().split("\n"):
                        if ":" in line:
                            key, value = line.split(":", 1)
                            metadata[key.strip()] = value.strip()
                            
                    # Handle special fields
                    if "reviewed" in metadata and metadata["reviewed"].lower() != "true":
                        # Convert string tags to list
                        if "tags" in metadata and metadata["tags"].startswith("[") and metadata["tags"].endswith("]"):
                            tag_str = metadata["tags"][1:-1]
                            metadata["tags"] = [tag.strip().strip("'\"") for tag in tag_str.split(",") if tag.strip()]
                            
                        staging_files.append({
                            "name": filename,
                            "metadata": metadata,
                            "content": file_content
                        })
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    
    return {"files": staging_files}

@app.post("/approve")
async def approve_file(payload: dict):
    """Approve a file from staging"""
    file_data = payload.get("file")
    if not file_data:
        return JSONResponse(status_code=400, content={"error": "Missing file data"})
        
    file_name = file_data.get("name")
    metadata = file_data.get("metadata", {})
    content = file_data.get("content", "")
    
    if not file_name:
        return JSONResponse(status_code=400, content={"error": "Missing file name"})
        
    # Format tags for YAML
    if "tags" in metadata and isinstance(metadata["tags"], list):
        tags_yaml = "\n- " + "\n- ".join(metadata["tags"])
        metadata["tags"] = tags_yaml
        
    # Make sure reviewed is set to true
    metadata["reviewed"] = "true"
    
    # Rebuild the file with updated metadata
    metadata_lines = []
    for key, value in metadata.items():
        metadata_lines.append(f"{key}: {value}")
        
    file_content = "---\n" + "\n".join(metadata_lines) + "\n---\n\n" + content
    
    # Save the updated file
    file_path = f"pkm/Processed/Metadata/{file_name}"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(file_content)
        
    return {"status": "approved", "filename": file_name}

# ─── PROCESS FILES ENDPOINT ─────────────────────────────────────────

@app.post("/trigger-organize")
def trigger_organize():
    """Trigger the file organization process"""
    result = organize_files()
    return {"status": "Files processed and organized"}

# ─── SEARCH ENDPOINT ───────────────────────────────────────────────

@app.post("/search")
async def search(payload: dict):
    query = payload.get("query", "")
    if not query:
        return {"response": "Please provide a search query"}
        
    try:
        # First make sure the index exists
        await indexKB()
        # Then search
        response = await searchKB(query)
        return {"response": response}
    except Exception as e:
        return {"response": f"Search error: {str(e)}"}

# ─── UPLOAD ENDPOINT ───────────────────────────────────────────────

@app.post("/upload/{folder}")
async def upload_file(folder: str, payload: dict):
    """Upload a file to a specific folder"""
    filename = payload.get("filename")
    content_b64 = payload.get("content")
    
    if not filename or not content_b64:
        return JSONResponse(status_code=400, content={"error": "Missing filename or content"})
        
    # Create the folder if it doesn't exist
    folder_path = f"pkm/{folder}"
    os.makedirs(folder_path, exist_ok=True)
    
    # Decode base64 content
    try:
        content_bytes = base64.b64decode(content_b64)
    except:
        return JSONResponse(status_code=400, content={"error": "Invalid base64 content"})
        
    # Save the file
    file_path = os.path.join(folder_path, filename)
    with open(file_path, "wb") as f:
        f.write(content_bytes)
        
    return {"status": f"File uploaded to {folder}/{filename}"}

# ─── ROOT ENDPOINT ───────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "PKM Indexer is running", "endpoints": [
        "/staging - Get files ready for review",
        "/approve - Approve a file from staging",
        "/trigger-organize - Process new files",
        "/sync-drive - Sync with Google Drive",
        "/search - Search the knowledge base",
        "/upload/{folder} - Upload a file to a folder",
        "/logs - View processing logs",
        "/file-stats - Get file statistics"
    ]}