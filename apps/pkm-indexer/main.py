from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from organize import organize_files
from index import indexKB, searchKB
import os
import frontmatter
import shutil
import re
import base64

app = FastAPI()

# Enable CORS for testing/development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scheduler = AsyncIOScheduler()

class Query(BaseModel):
    query: str

class File(BaseModel):
    file: dict

@app.post("/search")
async def search(query: Query):
    results = await searchKB(query.query)
    return {"response": results}

@app.get("/staging")
async def get_staging():
    staging = "pkm/Staging"
    os.makedirs(staging, exist_ok=True)
    files = []
    for md_file in [f for f in os.listdir(staging) if f.endswith(".md")]:
        with open(os.path.join(staging, md_file), "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
            files.append({
                "name": md_file,
                "content": post.content,
                "metadata": post.metadata
            })
    return {"files": files}

@app.post("/approve")
async def approve(file: File):
    staging = "pkm/Staging"
    areas = "pkm/Areas"
    inbox = "pkm/Inbox"
    file_data = file.file
    md_file = file_data["name"]
    content = file_data["content"]
    metadata = file_data["metadata"]
    category = metadata.get("category", "General")
    pdf_name = metadata.get("pdf", "")
    pdf_path = os.path.join(staging, pdf_name) if pdf_name else ""

    if re.search(r"# Reviewed: true", content, re.IGNORECASE):
        dest_dir = os.path.join(areas, category)
        os.makedirs(dest_dir, exist_ok=True)
        dest_md_file = os.path.join(dest_dir, md_file)
        post = frontmatter.Post(content=content, **metadata)

        with open(os.path.join(staging, md_file), "w", encoding="utf-8") as f:
            frontmatter.dump(post, f)

        shutil.move(os.path.join(staging, md_file), dest_md_file)

        if pdf_name and os.path.exists(pdf_path):
            shutil.move(pdf_path, os.path.join(dest_dir, pdf_name))

        inbox_pdf = os.path.join(inbox, pdf_name)
        if pdf_name and os.path.exists(inbox_pdf):
            os.remove(inbox_pdf)

        return {"status": f"Approved {md_file}"}

    return {"status": "Not approved: # Reviewed: false"}

@app.post("/organize")
async def manual_organize():
    organize_files()
    return {"status": "Organized"}

@app.get("/trigger-organize")
async def trigger_organize():
    organize_files()
    return {"status": "Organized"}

@app.post("/upload/{folder}")
async def upload_file(folder: str, file_data: dict):
    allowed_folders = ["Inbox", "Staging", "Areas"]
    if folder not in allowed_folders:
        raise HTTPException(status_code=400, detail="Invalid folder")

    path = f"pkm/{folder}"
    os.makedirs(path, exist_ok=True)

    filename = file_data.get("filename")
    content = file_data.get("content")

    if not filename or not content:
        raise HTTPException(status_code=400, detail="Filename and content are required")

    try:
        # Decode base64 content
        decoded = base64.b64decode(content.encode())

        with open(os.path.join(path, filename), "wb") as f:
            f.write(decoded)

        return {"status": f"File uploaded to {folder}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

@app.get("/files/{folder}")
async def list_files(folder: str):
    allowed_folders = ["Inbox", "Staging", "Areas", "Logs"]
    if folder not in allowed_folders:
        raise HTTPException(status_code=400, detail="Invalid folder")
    path = f"pkm/{folder}"
    if not os.path.exists(path):
        return {"files": []}
    files = os.listdir(path)
    return {"files": files}

@app.get("/file-content/{folder}/{filename}")
async def get_file_content(folder: str, filename: str):
    allowed_folders = ["Inbox", "Staging", "Areas", "Logs"]
    if folder not in allowed_folders:
        raise HTTPException(status_code=400, detail="Invalid folder")
    file_path = os.path.join("pkm", folder, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Not Found")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not read file: {e}")

@app.get("/")
async def root():
    return {"message": "PKM Indexer API is running. Use /search, /staging, /approve, or /organize endpoints."}

@app.on_event("startup")
async def startup_event():
    os.makedirs("pkm/Inbox", exist_ok=True)
    os.makedirs("pkm/Staging", exist_ok=True)
    os.makedirs("pkm/Areas", exist_ok=True)
    os.makedirs("pkm/Logs", exist_ok=True)

    try:
        await indexKB()
    except Exception as e:
        print(f"Startup indexing error: {e}")

    scheduler.add_job(organize_files, "cron", hour=2)
    scheduler.start()
