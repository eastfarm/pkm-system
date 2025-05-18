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
    metadata_path = "pkm/Processed/Metadata"
    os.makedirs(metadata_path, exist_ok=True)
    files = []
    for md_file in [f for f in os.listdir(metadata_path) if f.endswith(".md")]:
        with open(os.path.join(metadata_path, md_file), "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
            files.append({
                "name": md_file,
                "content": post.content,
                "metadata": post.metadata
            })
    return {"files": files}

@app.post("/approve")
async def approve(file: File):
    approved_dir = "pkm/Approved"
    os.makedirs(approved_dir, exist_ok=True)

    file_data = file.file
    md_file = file_data["name"]
    content = file_data["content"]
    metadata = file_data["metadata"]

    post = frontmatter.Post(content=content, **metadata)
    with open(os.path.join(approved_dir, md_file), "w", encoding="utf-8") as f:
        frontmatter.dump(post, f)

    return {"status": f"Approved {md_file}"}

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
    allowed_folders = ["Inbox"]
    if folder not in allowed_folders:
        raise HTTPException(status_code=400, detail="Invalid folder")

    path = f"pkm/{folder}"
    os.makedirs(path, exist_ok=True)

    filename = file_data.get("filename")
    content = file_data.get("content")

    if not filename or not content:
        raise HTTPException(status_code=400, detail="Filename and content are required")

    try:
        decoded = base64.b64decode(content.encode())
        with open(os.path.join(path, filename), "wb") as f:
            f.write(decoded)
        return {"status": f"File uploaded to {folder}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

@app.get("/files/{folder:path}")
async def list_files(folder: str):
    base_path = os.path.join("pkm", *folder.split("/"))
    if not os.path.exists(base_path):
        raise HTTPException(status_code=404, detail="Folder not found")
    files = []
    for root, _, filenames in os.walk(base_path):
        for filename in filenames:
            rel_path = os.path.relpath(os.path.join(root, filename), base_path)
            files.append(rel_path)
    return {"files": files}

@app.get("/file-content/{folder:path}")
async def get_file_content(folder: str):
    file_path = os.path.join("pkm", *folder.split("/"))
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not read file: {e}")

@app.get("/")
async def root():
    return {"message": "PKM Indexer API is running."}

@app.on_event("startup")
async def startup_event():
    os.makedirs("pkm/Inbox", exist_ok=True)
    os.makedirs("pkm/Processed/Metadata", exist_ok=True)
    os.makedirs("pkm/Processed/Sources", exist_ok=True)
    os.makedirs("pkm/Logs", exist_ok=True)
    os.makedirs("pkm/Approved", exist_ok=True)

    try:
        await indexKB()
    except Exception as e:
        print(f"Startup indexing error: {e}")

    scheduler.add_job(organize_files, "cron", hour=2)
    scheduler.start()
