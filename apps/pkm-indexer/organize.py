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
        # Open and process image
        image = Image.open(path)
        
        # Try multiple preprocessing approaches
        texts = []
        
        # Approach 1: Original with adjusted threshold
        img1 = image.convert("L")
        img1 = img1.point(lambda x: 0 if x < 120 else 255)  # Lowered threshold
        texts.append(pytesseract.image_to_string(img1, lang="eng"))
        
        # Approach 2: Try Danish language if available
        try:
            texts.append(pytesseract.image_to_string(img1, lang="dan"))
        except:
            # If Danish not installed, try with English
            pass
        
        # Approach 3: Try with different preprocessing
        img3 = image.convert("L")
        img3 = img3.resize((int(img3.width * 1.5), int(img3.height * 1.5)), Image.LANCZOS)  # Upsample
        img3 = img3.point(lambda x: 0 if x < 150 else 255)  # Different threshold
        
        # Try multilingual if available
        try:
            texts.append(pytesseract.image_to_string(img3, lang="dan+eng"))
        except:
            texts.append(pytesseract.image_to_string(img3, lang="eng"))
        
        # Approach 4: Higher contrast for slide presentations
        img4 = image.convert("L")
        # Apply more aggressive contrast for presentation slides
        img4 = img4.point(lambda x: 0 if x < 180 else 255)
        texts.append(pytesseract.image_to_string(img4, lang="eng"))
        
        # Use the longest text result that isn't just garbage
        valid_texts = [t for t in texts if len(t.strip()) > 20]
        if valid_texts:
            text = max(valid_texts, key=len)
        else:
            text = max(texts, key=len)
        
        # If we got nothing meaningful, report failure
        if len(text.strip()) < 20:
            return "[OCR produced insufficient text. Manual processing recommended.]"
            
        print("🖼️ OCR output:", repr(text[:500]))
        return text
    except Exception as e:
        return f"[OCR failed: {e}]"

def extract_urls(text):
    # More comprehensive regex that handles URLs in various formats
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[-\w%!.~\'()*+,;=:@/&?=]*)?'
    urls = re.findall(url_pattern, text)
    
    # Also look for linked text with URLs like [text](url)
    markdown_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', text)
    markdown_urls = [link[1] for link in markdown_links if link[1].startswith('http')]
    
    # Look for labeled links like "GenAI for Everyone by Andrew Ng" where GenAI for Everyone might be a link
    potential_link_titles = re.findall(r'["\']([^"\']+)["\']', text)
    
    all_urls = list(set(urls + markdown_urls))  # Remove duplicates
    print("🔗 URLs detected:", all_urls)
    print("🔍 Potential link titles:", potential_link_titles[:10])
    return all_urls, potential_link_titles

def enrich_urls(urls, potential_titles=None):
    enriched = []
    metadata = {}
    
    # Create a mapping of potential titles to improve URL descriptions
    title_map = {}
    if potential_titles:
        for title in potential_titles:
            # Store lowercase version for case-insensitive matching
            title_map[title.lower()] = title
    
    for url in urls:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            r = requests.get(url, timeout=10, headers=headers)
            soup = BeautifulSoup(r.text, "html.parser")
            
            # Try to get title
            title = "(No title)"
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
            
            # Try to get description
            description = ""
            meta_desc = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
            if meta_desc and 'content' in meta_desc.attrs:
                description = meta_desc['content'].strip()
                if len(description) > 150:
                    description = description[:150] + "..."
            
            # Check if this URL might match a potential title we found
            url_lower = url.lower()
            matching_title = None
            for potential_title_lower, original_title in title_map.items():
                # See if any words from the potential title appear in the URL
                words = potential_title_lower.split()
                if any(word in url_lower for word in words if len(word) > 3):
                    matching_title = original_title
                    break
            
            # Use matching title if found
            if matching_title and len(matching_title) > 5:
                display_title = matching_title
            else:
                display_title = title
                
            enriched_entry = f"- [{display_title}]({url})"
            if description:
                enriched_entry += f"\n  *{description}*"
                
            enriched.append(enriched_entry)
            
            # Store metadata for later use
            metadata[url] = {
                "title": display_title,
                "description": description[:150] if description else "",
                "url": url
            }
            
        except Exception as e:
            enriched.append(f"- {url} (unreachable: {str(e)[:50]})")
            metadata[url] = {
                "title": url,
                "description": f"Error: {str(e)[:50]}",
                "url": url
            }
    
    print("🔍 Enriched URLs block:\n", "\n".join(enriched))
    return "\n".join(enriched), metadata

def get_extract(content, file_type=None, urls_metadata=None, log_f=None):
    try:
        print("🧠 Content sent to GPT (preview):\n", content[:500])
        
        # Different prompt based on content type
        if file_type == "image":
            prompt = (
                "You are analyzing text extracted from an image via OCR. The text may have errors or be incomplete.\n\n"
                "Create a meaningful title and summary of what this image contains, plus relevant tags.\n\n"
                "Respond in this JSON format:\n"
                "{\n  \"extract_title\": \"...\",\n  \"extract_content\": \"...\",\n  \"tags\": [\"tag1\", \"tag2\"]\n}\n\n"
                f"OCR Text:\n{content[:3000]}"
            )
        elif urls_metadata and len(urls_metadata) > 0:
            # Create a summary of URLs for the prompt
            url_summary = "\n".join([f"- {data['title']}: {data['url']}" for url, data in urls_metadata.items()])
            
            prompt = (
                "You are summarizing content that contains valuable URLs and references.\n\n"
                "Create a title and detailed summary preserving key information, plus relevant tags.\n"
                "Pay special attention to these detected URLs and resources:\n\n"
                f"{url_summary}\n\n"
                "Respond in this JSON format:\n"
                "{\n  \"extract_title\": \"...\",\n  \"extract_content\": \"...\",\n  \"tags\": [\"tag1\", \"tag2\"]\n}\n\n"
                f"Content:\n{content[:3000]}"
            )
        else:
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
        print(f"🚫 Error in get_extract: {e}")
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

                # Enhanced URL processing
                urls, potential_titles = extract_urls(text_content)
                urls_metadata = {}
                
                if urls:
                    enriched, urls_metadata = enrich_urls(urls, potential_titles)
                    # Add the enriched URLs to a separate section
                    url_section = "\n\n---\n\n## Referenced Links\n" + enriched
                    
                    # Don't modify the original text content, keep it untouched
                    # Instead store the enriched URL data for display purposes
                    metadata["url_section"] = url_section

                base_name = Path(filename).stem
                today = time.strftime("%Y-%m-%d")
                md_filename = f"{today}_{base_name}.md"

                title, extract, tags = get_extract(text_content, file_type, urls_metadata, log_f)

                # Default category based on file type
                category = "Reference" if file_type == "pdf" else "Image" if file_type == "image" else "Note"
                
                # Try to improve tags when we have little information
                if tags == ["uncategorized"] or tags == ["untagged"]:
                    if file_type == "pdf" and "AI" in text_content:
                        tags = ["AI", "Document", "Reference"]
                    elif file_type == "image" and extraction_method == "ocr":
                        tags = ["Image", "Slide", "Presentation"]

                metadata = {
                    "title": title,
                    "date": today,
                    "file_type": file_type,
                    "source": filename,
                    "source_url": None,
                    "tags": tags,
                    "category": category,
                    "author": "Unknown",
                    "extract_title": title,
                    "extract_content": extract,
                    "reviewed": False,
                    "parse_status": "success",
                    "extraction_method": extraction_method
                }
                
                # Store URL information if relevant
                if urls:
                    metadata["referenced_urls"] = urls
                    # Store url titles in a more accessible format
                    url_titles = {}
                    for url, data in urls_metadata.items():
                        url_titles[url] = data.get("title", "Unknown")
                    metadata["url_titles"] = url_titles

                # For short documents, keep the full content regardless of file type
                # This applies to all file types where we've extracted text
                keep_full_content = (
                    len(text_content) < 10000 or  # Any text under 10K chars
                    len(urls) > 0                 # Any content with URLs
                )
                
                post = frontmatter.Post(
                    content=text_content if keep_full_content else "[Content omitted]",
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