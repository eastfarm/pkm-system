# File: apps/pkm-indexer/main.py
from fastapi import FastAPI, Request, Response, BackgroundTasks
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import io
import json
import base64
import asyncio
import uuid
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from organize import organize_files
from index import indexKB, searchKB
import logging
from datetime import datetime, timedelta

app = FastAPI()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("pkm-indexer")

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
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://pkm-indexer-production.up.railway.app/drive-webhook")
CHANNEL_ID = str(uuid.uuid4())  # Unique channel ID for Google Drive notifications

CLIENT_CONFIG = {
    "web": {
        "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        "redirect_uris": [REDIRECT_URI],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

# Store webhook data
webhook_state = {
    "channel_id": CHANNEL_ID,
    "resource_id": None,
    "expiration": None,
    "inbox_id": None,
    "last_renewal": None
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

# ─── WEBHOOK MANAGEMENT ─────────────────────────────────────────────

@app.post("/drive-webhook")
async def handle_drive_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle Google Drive webhook notifications when files change
    """
    # Verify request is from Google Drive
    channel_id = request.headers.get("X-Goog-Channel-ID")
    resource_state = request.headers.get("X-Goog-Resource-State")
    
    # Log the notification
    logger.info(f"Received webhook notification: {resource_state} for channel {channel_id}")
    
    # Check resource state - we're interested in 'change' events
    if resource_state in ["sync", "change"]:
        # Process the notification in the background
        background_tasks.add_task(process_drive_changes)
        
    # Always respond with 204 No Content quickly to acknowledge receipt
    return Response(status_code=204)

async def process_drive_changes():
    """
    Process changes in Google Drive inbox folder
    """
    logger.info("Processing Drive changes...")
    try:
        # Call the sync_drive function to process files
        result = sync_drive()
        if isinstance(result, dict) and result.get("uploaded"):
            logger.info(f"Webhook sync completed: {len(result.get('uploaded', []))} files processed")
        else:
            logger.info(f"Webhook sync completed: {result}")
    except Exception as e:
        logger.error(f"Error processing Drive changes: {str(e)}")

def setup_webhook_registration():
    """
    Set up or renew Google Drive webhook for the PKM/Inbox folder
    """
    try:
        token_json = os.environ.get("GOOGLE_TOKEN_JSON")
        if not token_json:
            logger.error("Google Drive credentials missing - can't set up webhook")
            return False
            
        creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
        drive_service = build('drive', 'v3', credentials=creds)
        
        # First, find or create the PKM/Inbox folder
        pkm_id = find_pkm_folder(drive_service)
        inbox_id = find_inbox_folder(drive_service, pkm_id)
        
        if not inbox_id:
            logger.error("Could not find or create PKM/Inbox folder")
            return False
        
        # Store the inbox_id for later use
        webhook_state["inbox_id"] = inbox_id
        
        # If there's an existing webhook, stop it first
        if webhook_state["resource_id"]:
            try:
                drive_service.channels().stop(
                    body={
                        "id": webhook_state["channel_id"],
                        "resourceId": webhook_state["resource_id"]
                    }
                ).execute()
                logger.info(f"Stopped existing webhook with channel ID: {webhook_state['channel_id']}")
            except Exception as e:
                logger.warning(f"Error stopping existing webhook: {str(e)}")
        
        # Generate a new channel ID for each registration
        webhook_state["channel_id"] = str(uuid.uuid4())
        
        # Register for changes on the inbox folder
        webhook_expiration = datetime.now() + timedelta(days=7)  # Max 7 days for webhook
        expiration_ms = int(webhook_expiration.timestamp() * 1000)
        
        # Set up the webhook using Drive API
        webhook_body = {
            "id": webhook_state["channel_id"],
            "type": "web_hook",
            "address": WEBHOOK_URL,
            "expiration": expiration_ms,
        }
        
        # Create the webhook
        response = drive_service.files().watch(
            fileId=inbox_id,
            body=webhook_body
        ).execute()
        
        # Store the webhook information
        webhook_state["resource_id"] = response.get("resourceId")
        webhook_state["expiration"] = response.get("expiration")
        webhook_state["last_renewal"] = datetime.now().isoformat()
        
        logger.info(f"Webhook set up successfully. Channel ID: {webhook_state['channel_id']}, Expires: {webhook_expiration}")
        
        return True
    except Exception as e:
        logger.error(f"Webhook setup error: {str(e)}")
        return False

def check_webhook_expiration():
    """Check if webhook needs renewal and renew if needed"""
    try:
        # If webhook isn't set up or doesn't have expiration, set it up
        if not webhook_state["expiration"]:
            return setup_webhook_registration()
            
        # Check if expiration is approaching (less than 1 day remaining)
        expiration_time = datetime.fromtimestamp(int(webhook_state["expiration"]) / 1000)
        now = datetime.now()
        
        # If webhook expires in less than 24 hours, renew it
        if expiration_time - now < timedelta(hours=24):
            logger.info("Webhook expiration approaching, renewing...")
            return setup_webhook_registration()
            
        # Webhook is still valid
        return True
    except Exception as e:
        logger.error(f"Error checking webhook expiration: {str(e)}")
        return False

@app.get("/webhook/status")
def webhook_status():
    """
    Get the status of the Google Drive webhook - for monitoring only
    """
    try:
        now = datetime.now()
        is_expired = False
        
        if webhook_state["expiration"]:
            expiration_time = datetime.fromtimestamp(int(webhook_state["expiration"]) / 1000)
            is_expired = now > expiration_time
        
        is_active = webhook_state["resource_id"] is not None and not is_expired
        
        status_info = {
            "is_active": is_active,
            "channel_id": webhook_state["channel_id"],
            "inbox_id": webhook_state["inbox_id"],
            "expiration": None,
            "last_renewal": webhook_state["last_renewal"]
        }
        
        if webhook_state["expiration"]:
            expiration_time = datetime.fromtimestamp(int(webhook_state["expiration"]) / 1000)
            status_info["expiration"] = expiration_time.isoformat()
            status_info["time_remaining"] = str(expiration_time - now) if expiration_time > now else "Expired"
        
        return status_info
    except Exception as e:
        logger.error(f"Webhook status error: {str(e)}")
        return JSONResponse(
            status_code=500, 
            content={"status": f"Failed to get webhook status: {str(e)}", "error": str(e)}
        )

# ─── FOLDER HELPERS ───────────────────────────────────────────────

def find_pkm_folder(service):
    """Find or create the PKM folder"""
    query_pkm = "name='PKM' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    pkm_results = service.files().list(q=query_pkm, fields="files(id,name)").execute()
    pkm_folders = pkm_results.get('files', [])
    
    if not pkm_folders:
        # PKM folder doesn't exist, create it
        pkm_id = find_or_create_folder(service, "root", "PKM")
        logger.info(f"Created PKM folder: {pkm_id}")
    else:
        pkm_id = pkm_folders[0]['id']
        logger.info(f"Found PKM folder: {pkm_id}")
    
    return pkm_id

def find_inbox_folder(service, pkm_id):
    """Find or create the Inbox folder under PKM"""
    query_inbox = f"'{pkm_id}' in parents and name='Inbox' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    inbox_results = service.files().list(q=query_inbox, fields="files(id,name)").execute()
    inbox_folders = inbox_results.get('files', [])
    
    if not inbox_folders:
        # Inbox folder doesn't exist, create it
        inbox_id = find_or_create_folder(service, pkm_id, "Inbox")
        logger.info(f"Created Inbox folder: {inbox_id}")
    else:
        inbox_id = inbox_folders[0]['id']
        logger.info(f"Found Inbox folder: {inbox_id}")
    
    return inbox_id

# ─── SYNC DRIVE ───────────────────────────────────────────────────

@app.post("/sync-drive")
def sync_drive():
    try:
        LOCAL_INBOX = "pkm/Inbox"
        LOCAL_METADATA = "pkm/Processed/Metadata"
        LOCAL_SOURCES = "pkm/Processed/Sources"
        downloaded = []
        uploaded = []
        debug_info = {
            "token_exists": False,
            "drive_folders": [],
            "inbox_files_count": 0,
            "error": None
        }

        token_json = os.environ.get("GOOGLE_TOKEN_JSON")
        if not token_json:
            return {"status": "Failed - Google Drive credentials missing", "debug": debug_info}
            
        debug_info["token_exists"] = True
        
        try:
            creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
            service = build('drive', 'v3', credentials=creds)
        except Exception as auth_error:
            debug_info["error"] = f"Authentication error: {str(auth_error)}"
            return {"status": "Failed to authenticate with Google Drive", "debug": debug_info}

        # 1. Locate PKM + subfolders
        try:
            # Find or create the PKM folder
            pkm_id = find_pkm_folder(service)
            debug_info["drive_folders"].append(f"PKM folder: {pkm_id}")
            
            # Find or create the Inbox folder
            inbox_id = find_inbox_folder(service, pkm_id)
            debug_info["drive_folders"].append(f"Inbox folder: {inbox_id}")
            
            # Update webhook state with inbox ID if needed
            if inbox_id and not webhook_state["inbox_id"]:
                webhook_state["inbox_id"] = inbox_id
            
            # Continue with other folders
            processed_id = find_or_create_folder(service, pkm_id, "Processed")
            metadata_id = find_or_create_folder(service, processed_id, "Metadata")
            sources_id = find_or_create_folder(service, processed_id, "Sources")
            
            debug_info["drive_folders"].append(f"Processed folder: {processed_id}")
            debug_info["drive_folders"].append(f"Metadata folder: {metadata_id}")
            debug_info["drive_folders"].append(f"Sources folder: {sources_id}")
        except Exception as folder_error:
            debug_info["error"] = f"Folder creation error: {str(folder_error)}"
            return {"status": "Failed to locate or create Google Drive folders", "debug": debug_info}

        # 2. Download files from /Inbox
        try:
            query_files = f"'{inbox_id}' in parents and trashed = false"
            files_result = service.files().list(q=query_files, fields="files(id, name)").execute()
            files = files_result.get('files', [])
            
            debug_info["inbox_files_count"] = len(files)
            
            if not files:
                return {
                    "status": "✅ Synced - No files found in Google Drive Inbox folder",
                    "debug": debug_info
                }
            
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
        except Exception as download_error:
            debug_info["error"] = f"Download error: {str(download_error)}"
            return {"status": "Failed to download files from Google Drive", "debug": debug_info}

        # 3. Run metadata extraction
        try:
            organize_files()
        except Exception as organize_error:
            debug_info["error"] = f"Organization error: {str(organize_error)}"
            return {
                "status": "Files downloaded but processing failed", 
                "downloaded": [f[1] for f in downloaded],
                "debug": debug_info
            }

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
                    md_id = upload_file_to_drive(service, local_md_path, md_filename, metadata_id)
                    debug_info["drive_folders"].append(f"Uploaded metadata: {md_filename} to {metadata_id}")
                else:
                    debug_info["error"] = f"Missing .md file for {file_name} at {local_md_path}"
                    raise Exception(f"Missing .md file for {file_name}")

                # Upload original
                if os.path.exists(local_original_path):
                    ft_folder_id = find_or_create_folder(service, sources_id, file_type)
                    orig_id = upload_file_to_drive(service, local_original_path, file_name, ft_folder_id)
                    debug_info["drive_folders"].append(f"Uploaded source file: {file_name} to {ft_folder_id}")
                else:
                    debug_info["error"] = f"Missing source file for {file_name} at {local_original_path}"
                    raise Exception(f"Missing source file for {file_name}")

                # Delete from Inbox (only if both uploads succeeded)
                delete_result = service.files().delete(fileId=file_id).execute()
                debug_info["drive_folders"].append(f"Deleted inbox file: {file_id}")
                uploaded.append(file_name)

            except Exception as e:
                debug_info["error"] = f"Upload error for {file_name}: {str(e)}"
                print(f"❌ Failed to upload/delete {file_name}: {e}")

        return {
            "status": f"✅ Synced and organized - {len(uploaded)} files processed",
            "downloaded": [f[1] for f in downloaded],
            "uploaded": uploaded,
            "skipped": [f[1] for f in downloaded if f[1] not in uploaded],
            "debug": debug_info
        }
    except Exception as e:
        return {
            "status": f"❌ Sync failed: {str(e)}",
            "error": str(e)
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

    # Handle reprocess request
    if metadata.get("reprocess_status") == "requested":
        try:
            print(f"Reprocessing requested for {file_name}")
            # Save the current metadata with reprocess status
            metadata["reprocess_status"] = "in_progress"
            
            # Get the file path
            file_path = f"pkm/Processed/Metadata/{file_name}"
            
            # Format tags for YAML
            if "tags" in metadata and isinstance(metadata["tags"], list):
                tags_yaml = "\n- " + "\n- ".join(metadata["tags"])
                metadata["tags"] = tags_yaml
            
            # Rebuild the file with updated metadata
            metadata_lines = []
            for key, value in metadata.items():
                metadata_lines.append(f"{key}: {value}")
                
            file_content = "---\n" + "\n".join(metadata_lines) + "\n---\n\n" + content
            
            # Save the updated file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(file_content)
                
            # Start a background task for reprocessing
            # This could be enhanced to actually reprocess using AI
            # For now, we just mark it as completed
            metadata["reprocess_status"] = "complete"
            
            return {"status": "reprocessing", "filename": file_name}
            
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": f"Failed to queue reprocessing: {str(e)}"})
        
    # Standard approval flow
    try:
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
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to approve: {str(e)}"})

# ─── PROCESS FILES ENDPOINT ─────────────────────────────────────────

@app.post("/trigger-organize")
def trigger_organize():
    """Trigger the file organization process"""
    try:
        result = organize_files()
        return {
            "status": f"Files processed and organized: {result['success_count']} successful, {len(result['failed_files'])} failed",
            "log_file": result['log_file'],
            "failed_files": result['failed_files']
        }
    except Exception as e:
        return {"status": f"Organization error: {str(e)}", "error": str(e)}

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
        "/file-stats - Get file statistics",
        "/webhook/status - Check automatic sync status"
    ]}

# ─── BACKGROUND TASK TO CHECK WEBHOOK EXPIRATION ─────────────────

async def renew_webhook_if_needed():
    """Periodic task to check and renew webhook if needed"""
    while True:
        try:
            check_webhook_expiration()
            # Check every 12 hours
            await asyncio.sleep(12 * 60 * 60)
        except Exception as e:
            logger.error(f"Error in webhook renewal background task: {str(e)}")
            # Still sleep before retrying
            await asyncio.sleep(60 * 60)  # 1 hour on error

# ─── STARTUP EVENT ───────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Initialize the system on startup"""
    try:
        # Set up the webhook immediately on startup
        setup_webhook_registration()
        logger.info("Startup: Webhook setup initiated")
        
        # Start background task to periodically check and renew webhook
        asyncio.create_task(renew_webhook_if_needed())
        logger.info("Started webhook renewal background task")
    except Exception as e:
        logger.error(f"Error during application startup: {str(e)}")