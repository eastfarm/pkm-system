import os
import shutil
import time
import frontmatter
import openai
import re
import json
from pathlib import Path

openai.api_key = os.getenv("OPENAI_API_KEY")

def get_extract(content, log_f=None):
    try:
        prompt = (
            "You are a critical reader and semantic summarizer. Your task is to extract the core insights and arguments from the document below.\n\n"
            "Ignore layout, metadata, and technical structure (e.g., PDF version, file format).\n\n"
            "Focus on meaning, not structure. Identify the main themes, ideas, or takeaways in clear language.\n\n"
            "Respond in this JSON format:\n"
            '{\n  "extract": "...",\n  "tags": ["tag1", "tag2"]\n}\n\n'
            f"Content:\n{content[:3000]}"
        )
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You summarize content into clear extracts and thematic tags."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300
        )

        raw = response["choices"][0]["message"]["content"]
        parsed = json.loads(raw)
        extract = parsed.get("extract", "Extract not available")
        tags = parsed.get("tags", ["uncategorized"])

        if log_f:
            log_f.write("OpenAI raw response:\n")
            log_f.write(raw + "\n\n")

        return extract, tags

    except Exception as e:
        if log_f:
            log_f.write(f"OpenAI ERROR: {e}\n")
        return "Extract not available", ["uncategorized"]

def infer_file_type(filename):
    ext = Path(filename).suffix.lower()
    if ext in [".md", ".txt"]: return "text"
    if ext in [".pdf"]: return "pdf"
    if ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp"]: return "image"
    if ext in [".mp3", ".wav", ".m4a"]: return "audio"
    if ext in [".doc", ".docx"]: return "document"
    return "other"

def organize_files():
    inbox = "pkm/Inbox"
    meta_out = "pkm/Processed/Metadata"
    source_out = "pkm/Processed/Sources"
    logs = "pkm/Logs"

    os.makedirs(inbox, exist_ok=True)
    os.makedirs(meta_out, exist_ok=True)
    os.makedirs(source_out, exist_ok=True)
    os.makedirs(logs, exist_ok=True)

    log_file_path = os.path.join(logs, f"log_organize_{int(time.time())}.md")
    with open(log_file_path, "a", encoding="utf-8") as log_f:
        log_f.write(f"# Organize run at {time.time()}\n\n")

        files = [f for f in os.listdir(inbox) if os.path.isfile(os.path.join(inbox, f))]
        log_f.write(f"Found files in Inbox: {files}\n")

        for filename in files:
            try:
                log_f.write(f"Processing {filename}\n")

                input_path = os.path.join(inbox, filename)
                with open(input_path, "rb") as f:
                    raw_bytes = f.read()

                try:
                    text_content = raw_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    text_content = raw_bytes.decode("latin-1")

                file_type = infer_file_type(filename)
                base_name = Path(filename).stem
                today = time.strftime("%Y-%m-%d")
                md_filename = f"{today}_{base_name}.md"

                extract, tags = get_extract(text_content, log_f)

                metadata = {
                    "title": base_name,
                    "date": today,
                    "file_type": file_type,
                    "source": filename,
                    "source_url": None,
                    "tags": tags,
                    "author": "Unknown",
                    "extract": extract,
                    "reviewed": False
                }

                post = frontmatter.Post(
                    content=text_content if file_type == "text" and len(text_content) < 3000 else "[Content omitted]",
                    **metadata
                )

                # Write metadata file
                meta_path = os.path.join(meta_out, md_filename)
                with open(meta_path, "w", encoding="utf-8") as f:
                    f.write(frontmatter.dumps(post))

                # Move original file to sources folder
                dest_dir = os.path.join(source_out, file_type)
                os.makedirs(dest_dir, exist_ok=True)
                shutil.move(input_path, os.path.join(dest_dir, filename))

                log_f.write(f"Metadata saved: {md_filename}\n")
                log_f.write(f"Source moved to: {file_type}/{filename}\n\n")

            except Exception as e:
                log_f.write(f"# Error processing {filename} at {time.time()}\n")
                log_f.write(f"Message: {str(e)}\n\n")
                continue

if __name__ == "__main__":
    organize_files()
