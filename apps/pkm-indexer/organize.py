import os
import shutil
import time
import frontmatter
import openai
import re
import json
from pathlib import Path
import pdfplumber
import pytesseract
from PIL import Image
import requests
from bs4 import BeautifulSoup

openai.api_key = os.getenv("OPENAI_API_KEY")

def infer_file_type(filename):
    ext = Path(filename).suffix.lower()
    if ext in [".md", ".txt"]: return "text"
    if ext in [".pdf"]: return "pdf"
    if ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp"]: return "image"
    if ext in [".mp3", ".wav", ".m4a"]: return "audio"
    if ext in [".doc", ".docx"]: return "document"
    return "other"

def extract_text_from_pdf(path):
    try:
        with pdfplumber.open(path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as e:
        return f"[PDF extraction failed: {e}]"

def extract_text_from_image(path):
    try:
        image = Image.open(path).convert("L")  # Grayscale
        image = image.point(lambda x: 0 if x < 140 else 255)  # Threshold
        text = pytesseract.image_to_string(image, lang="eng")
        print("🖼️ OCR output:", repr(text[:500]))
        return text
    except Exception as e:
        return f"[OCR failed: {e}]"

def extract_urls(text):
    urls = re.findall(r"https?://\S+", text)
    print("🔗 URLs detected:", urls)
    return urls

def enrich_urls(urls):
    enriched = []
    for url in urls:
        try:
            r = requests.get(url, timeout=5)
            soup = BeautifulSoup(r.text, "html.parser")
            title = soup.title.string.strip() if soup.title else "(No title)"
            enriched.append(f"- [{title}]({url})")
        except Exception:
            enriched.append(f"- {url} (unreachable)")
    print("🔍 Enriched URLs block:\n", "\n".join(enriched))
    return "\n".join(enriched)

def get_extract(content, log_f=None):
    try:
        print("🧠 Content sent to GPT (preview):\n", content[:500])
        prompt = (
            "You are a semantic summarizer. Return a short title and a deeper thematic summary, plus relevant tags.\n\n"
            "Respond in this JSON format:\n"
            "{\n  \"extract_title\": \"...\",\n  \"extract_content\": \"...\",\n  \"tags\": [\"tag1\", \"tag2\"]\n}\n\n"
            f"Content:\n{content[:3000]}"
        )
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You analyze content and extract semantic meaning."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        raw = response["choices"][0]["message"]["content"]
        parsed = json.loads(raw)
        return parsed.get("extract_title", "Untitled"), parsed.get("extract_content", "No summary."), parsed.get("tags", ["untagged"])
    except Exception as e:
        if log_f:
            log_f.write(f"OpenAI ERROR: {e}\n")
        return "Untitled", "Extract not available", ["uncategorized"]

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
                log_f.write(f"\n\n## Processing {filename}\n")
                input_path = os.path.join(inbox, filename)
                file_type = infer_file_type(filename)

                if file_type == "pdf":
                    text_content = extract_text_from_pdf(input_path)
                    extraction_method = "pdfplumber"
                elif file_type == "image":
                    text_content = extract_text_from_image(input_path)
                    extraction_method = "ocr"
                else:
                    with open(input_path, "rb") as f:
                        raw_bytes = f.read()
                    try:
                        text_content = raw_bytes.decode("utf-8")
                        extraction_method = "decode"
                    except UnicodeDecodeError:
                        text_content = raw_bytes.decode("latin-1")
                        extraction_method = "decode"

                log_f.write(f"📝 Raw Text Preview:\n{text_content[:500]}\n")

                urls = extract_urls(text_content)
                if urls:
                    enriched = enrich_urls(urls)
                    text_content += "\n\n---\n\n## Referenced Links\n" + enriched

                base_name = Path(filename).stem
                today = time.strftime("%Y-%m-%d")
                md_filename = f"{today}_{base_name}.md"

                title, extract, tags = get_extract(text_content, log_f)

                metadata = {
                    "title": title,
                    "date": today,
                    "file_type": file_type,
                    "source": filename,
                    "source_url": None,
                    "tags": tags,
                    "author": "Unknown",
                    "extract_title": title,
                    "extract_content": extract,
                    "reviewed": False,
                    "parse_status": "success",
                    "extraction_method": extraction_method
                }

                post = frontmatter.Post(
                    content=text_content if file_type == "text" and len(text_content) < 3000 else "[Content omitted]",
                    **metadata
                )

                meta_path = os.path.join(meta_out, md_filename)
                with open(meta_path, "w", encoding="utf-8") as f:
                    f.write(frontmatter.dumps(post))

                dest_dir = os.path.join(source_out, file_type)
                os.makedirs(dest_dir, exist_ok=True)
                shutil.move(input_path, os.path.join(dest_dir, filename))

                log_f.write(f"✅ Metadata saved: {md_filename}\n")
                log_f.write(f"✅ File moved to: {file_type}/{filename}\n")

            except Exception as e:
                log_f.write(f"❌ Error processing {filename}: {str(e)}\n")
                print(f"❌ ERROR in organize_files(): {e}")
                continue

    print("🏁 organize_files() complete.")

if __name__ == "__main__":
    organize_files()
