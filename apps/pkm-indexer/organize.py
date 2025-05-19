# File: apps/pkm-indexer/organize.py
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
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            
            # Check if this looks like a LinkedIn post
            if "Profile viewers" in text[:500] or "Post impressions" in text[:500] or "linkedin.com" in text.lower():
                return process_linkedin_pdf(text, path)
            
            return text
    except Exception as e:
        return f"[PDF extraction failed: {e}]"

def process_linkedin_pdf(text, path):
    """Process LinkedIn PDF content to extract the main post and ignore comments."""
    try:
        # Pattern to detect the start of comments section
        comment_indicators = [
            "Reactions", 
            "Like · Reply",
            "comments · ",
            "reposts",
            "Most relevant"
        ]
        
        # Pattern to detect URLs in the text
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[-\w%!.~\'()*+,;=:@/&?=]*)?'
        
        # Find all URLs in the original content
        main_urls = re.findall(url_pattern, text)
        important_urls = []
        
        # Split content by lines to process
        lines = text.split('\n')
        main_content_lines = []
        
        # Track if we're in the comments section
        in_comments = False
        author_comment_section = False
        post_author = None
        
        # Extract the post author if available (usually near the beginning)
        for i, line in enumerate(lines[:15]):
            if "• Author" in line or "• 1st" in line or "• 2nd" in line or "• 3rd" in line:
                # The line before often contains the author name
                if i > 0:
                    post_author = lines[i-1].strip()
                    break
                    
        # Process the content line by line
        for i, line in enumerate(lines):
            # Check if we've hit the comments section
            if any(indicator in line for indicator in comment_indicators) and i > 10:
                in_comments = True
                continue
                
            # If we're still in the main content, keep the line
            if not in_comments:
                main_content_lines.append(line)
                continue
                
            # Check for author comments (only process if we know the author)
            if post_author and post_author in line and i+2 < len(lines) and "Author" in lines[i:i+2]:
                author_comment_section = True
                continue
                
            # Process author comment content
            if author_comment_section:
                # Look for URLs or other important info in first author comment
                urls_in_comment = re.findall(url_pattern, line)
                if urls_in_comment:
                    important_urls.extend(urls_in_comment)
                    
                # Check if author comment section is ending
                if "Like · Reply" in line or "Like · " in line:
                    author_comment_section = False
        
        # Combine the main content
        main_content = '\n'.join(main_content_lines)
        
        # Add any important URLs from author comments if they weren't in the main content
        for url in important_urls:
            if url not in main_urls and ("lnkd.in" in url or ".com" in url):  # LinkedIn short URLs are often important
                main_content += f"\n\nAdditional URL from author comment: {url}"
                
        print("📱 Detected LinkedIn post, removed comments section")
        return main_content
    except Exception as e:
        print(f"Error processing LinkedIn content: {e}")
        return text  # Return original if processing fails

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
    """
    Extract URLs from text, including both standard http/https URLs and potential 
    title-based references that might be links.
    """
    # Standard URL pattern
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[-\w%!.~\'()*+,;=:@/&?=]*)?'
    urls = re.findall(url_pattern, text)
    
    # Also look for linked text with URLs like [text](url)
    markdown_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', text)
    markdown_urls = [link[1] for link in markdown_links if link[1].startswith('http')]
    
    # Look for potential title links in specific formats
    potential_links = []
    
    # Look for titles that might be links (for PDF resources lists)
    # Pattern: title followed by "by Author" - common in resource lists
    title_pattern = r'(?:^|\n)(?:\d+\)|\-)\s*([^""\n]+?)(?= by | \()'
    potential_titles = re.findall(title_pattern, text)
    
    # Also look for text that appears to be a clickable reference
    # Common in PDFs with links that don't have explicit URLs
    reference_patterns = [
        r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)*\s(?:AI|ML|for\sEveryone|Intelligence|Awareness|Machine|clone))',  # AI-related titles
        r'(my book|my AI clone|Appendix [A-Z]|Foundry from HBS)',  # References to books, appendices, etc.
        r'(?<=see\s)([^\.,:;\n]+)'  # Things after "see" are often references
    ]
    
    for pattern in reference_patterns:
        found = re.findall(pattern, text)
        potential_links.extend([link.strip() for link in found if len(link.strip()) > 5])
    
    # Add potential titles that look like resources
    potential_links.extend([title.strip() for title in potential_titles if len(title.strip()) > 5])
    
    # Remove duplicates and very common words that aren't likely to be meaningful links
    potential_links = list(set(potential_links))
    filtered_links = [link for link in potential_links if link.lower() not in 
                     ['and', 'the', 'this', 'that', 'with', 'from', 'after', 'before']]
    
    all_urls = list(set(urls + markdown_urls))  # Remove duplicates
    print("🔗 URLs detected:", all_urls)
    print("🔍 Potential link titles:", filtered_links[:15])
    
    return all_urls, filtered_links

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

def get_extract(content, file_type=None, urls_metadata=None, log_f=None, is_linkedin=False):
    try:
        print("🧠 Content sent to GPT (preview):\n", content[:500])
        
        # Determine appropriate extract length based on content
        content_length = len(content)
        if content_length < 1000:
            # For very short content, keep extract concise
            extract_length = 200
            model = "gpt-4"
        elif content_length < 5000:
            # For medium content, medium extract
            extract_length = 500
            model = "gpt-4"
        else:
            # For longer, complex content, allow longer extracts
            extract_length = 2000  # Up to ~400 words for complex content
            model = "gpt-4"  # Better for complex content
        
        # Check if this appears to be a resource list/links-heavy doc
        has_resource_patterns = (
            "resources" in content.lower() and 
            (content.count("\n1)") > 1 or content.count("\n2)") > 1)
        )
        
        # Different prompt based on content type
        if has_resource_patterns:
            # For resource-list style documents
            prompt = (
                "You are analyzing a document that appears to be a resource list with references, links, and learning materials.\n\n"
                "Create a detailed summary that specifically includes ALL referenced resources, people, and links. "
                "Also provide relevant tags that capture the subject matter and type of resources.\n\n"
                "In your extract, make sure to preserve:\n"
                "1. All resource names and titles\n"
                "2. All author names and affiliations\n"
                "3. All categories of resources\n"
                "4. Any referenced websites, tools, or platforms\n\n"
                "Respond in this JSON format:\n"
                "{\n  \"extract_title\": \"...\",\n  \"extract_content\": \"...\",\n  \"tags\": [\"tag1\", \"tag2\"]\n}\n\n"
                f"Content:\n{content[:5000]}"
            )
        elif is_linkedin:
            prompt = (
                "You are analyzing a LinkedIn post. Create a clear title and detailed summary that captures "
                "the key points, insights, and any URLs/resources mentioned in the post. Ignore promotional content.\n\n"
                "Focus on what makes this post valuable for knowledge management purposes.\n\n"
                "Respond in this JSON format:\n"
                "{\n  \"extract_title\": \"...\",\n  \"extract_content\": \"...\",\n  \"tags\": [\"tag1\", \"tag2\"]\n}\n\n"
                f"LinkedIn Post Content:\n{content[:5000]}"
            )
        elif file_type == "image":
            prompt = (
                "You are analyzing text extracted from an image via OCR. The text may have errors or be incomplete.\n\n"
                "Create a meaningful title and summary of what this image contains, plus relevant tags.\n\n"
                "For complex content, provide a detailed summary that captures the key information.\n\n"
                "Respond in this JSON format:\n"
                "{\n  \"extract_title\": \"...\",\n  \"extract_content\": \"...\",\n  \"tags\": [\"tag1\", \"tag2\"]\n}\n\n"
                f"OCR Text:\n{content[:5000]}"
            )
        elif urls_metadata and len(urls_metadata) > 0:
            # Create a summary of URLs for the prompt
            url_summary = "\n".join([f"- {data['title']}: {data['url']}" for url, data in urls_metadata.items()])
            
            prompt = (
                "You are summarizing content that contains valuable URLs and references.\n\n"
                "Create a title and detailed summary preserving key information, plus relevant tags.\n"
                "For rich content with many references, provide a comprehensive summary.\n\n"
                "Pay special attention to these detected URLs and resources:\n\n"
                f"{url_summary}\n\n"
                "Respond in this JSON format:\n"
                "{\n  \"extract_title\": \"...\",\n  \"extract_content\": \"...\",\n  \"tags\": [\"tag1\", \"tag2\"]\n}\n\n"
                f"Content:\n{content[:5000]}"
            )
        else:
            prompt = (
                "You are a semantic summarizer. Return a short title and a deeper thematic summary, plus relevant tags.\n\n"
                "For complex or information-rich content, provide a detailed summary that captures the key points.\n\n"
                "Respond in this JSON format:\n"
                "{\n  \"extract_title\": \"...\",\n  \"extract_content\": \"...\",\n  \"tags\": [\"tag1\", \"tag2\"]\n}\n\n"
                f"Content:\n{content[:5000]}"
            )
            
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You analyze content and extract semantic meaning."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=extract_length  # Dynamic based on content
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
                    
                    # Check if this is a LinkedIn post
                    is_linkedin = "linkedin.com" in text_content.lower() or "Profile viewers" in text_content[:500]
                elif file_type == "image":
                    text_content = extract_text_from_image(input_path)
                    extraction_method = "ocr"
                    is_linkedin = False
                else:
                    with open(input_path, "rb") as f:
                        raw_bytes = f.read()
                    try:
                        text_content = raw_bytes.decode("utf-8")
                        extraction_method = "decode"
                    except UnicodeDecodeError:
                        text_content = raw_bytes.decode("latin-1")
                        extraction_method = "decode"
                    is_linkedin = False

                log_f.write(f"📝 Raw Text Preview:\n{text_content[:500]}\n")

                # Enhanced URL processing
                urls, potential_titles = extract_urls(text_content)
                urls_metadata = {}
                
                # Special handling for resource lists - add potential titles as "reference links"
                if file_type == "pdf" and ("resources" in text_content.lower() or text_content.count("\n1)") > 1):
                    if len(potential_titles) > 3:  # If we found several potential resource titles
                        log_f.write(f"📚 Detected resource list with {len(potential_titles)} potential references\n")
                        
                        # Store reference metadata
                        for title in potential_titles:
                            urls_metadata[title] = {
                                "title": title,
                                "description": "Referenced resource",
                                "url": f"reference:{title}"  # Use a special prefix to indicate this isn't a real URL
                            }
                
                if urls:
                    enriched, url_data = enrich_urls(urls, potential_titles)
                    # Update the metadata with real URL data
                    urls_metadata.update(url_data)
                    
                    # Add the enriched URLs to a separate section
                    url_section = "\n\n---\n\n## Referenced Links\n" + enriched
                    
                    # Don't modify the original text content, keep it untouched
                    # Instead store the enriched URL data for display purposes
                    metadata["url_section"] = url_section

                base_name = Path(filename).stem
                today = time.strftime("%Y-%m-%d")
                md_filename = f"{today}_{base_name}.md"

                # For resource lists, store the list of references in metadata
                if file_type == "pdf" and ("resources" in text_content.lower() or text_content.count("\n1)") > 1):
                    has_resource_patterns = True
                    if len(potential_titles) > 3:  # If we found several potential resource titles
                        metadata["referenced_resources"] = potential_titles
                else:
                    has_resource_patterns = False
                    
                title, extract, tags = get_extract(text_content, file_type, urls_metadata, log_f, is_linkedin)

                # Default category based on file type
                if is_linkedin:
                    category = "LinkedIn Post"
                else:
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