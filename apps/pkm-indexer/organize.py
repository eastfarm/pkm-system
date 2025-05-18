import os
import shutil
import time
import frontmatter
import openai
import re
import json

openai.api_key = os.getenv("OPENAI_API_KEY")

def get_metadata(content):
    try:
        prompt = (
            f"Please return a short metadata object in JSON format.\n"
            f"Input:\n{content}\n\n"
            f"Return format:\n"
            f'{{"summary": "...", "tags": ["tag1", "tag2", "tag3"]}}'
        )
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes content and generates structured metadata."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200
        )

        raw = response["choices"][0]["message"]["content"]
        parsed = json.loads(raw)
        summary = parsed.get("summary", "Summary not available")
        tags = parsed.get("tags", ["uncategorized"])
        return summary, tags
    except Exception as e:
        logs = "pkm/Logs"
        os.makedirs(logs, exist_ok=True)
        log_file = os.path.join(logs, f"log_organize_{int(time.time())}.md")
        with open(log_file, "a", encoding="utf-8") as log_f:
            log_f.write(f"# Error in get_metadata at {time.time()}\n")
            log_f.write(f"Message: {str(e)}\n")
            log_f.write(f"Raw response: {locals().get('raw', '')}\n\n")
        return "Summary not available", ["uncategorized"]

def organize_files():
    inbox = "pkm/Inbox"
    staging = "pkm/Staging"
    logs = "pkm/Logs"
    os.makedirs(inbox, exist_ok=True)
    os.makedirs(staging, exist_ok=True)
    os.makedirs(logs, exist_ok=True)

    log_file = os.path.join(logs, f"log_organize_{int(time.time())}.md")
    with open(log_file, "a", encoding="utf-8") as log_f:
        log_f.write(f"# Organize run at {time.time()}\n\n")

    files = [f for f in os.listdir(inbox) if f.endswith(".md")]
    with open(log_file, "a", encoding="utf-8") as log_f:
        log_f.write(f"Found files in Inbox: {files}\n")

    for md_file in files:
        try:
            with open(log_file, "a", encoding="utf-8") as log_f:
                log_f.write(f"Processing {md_file}\n")

            with open(os.path.join(inbox, md_file), "rb") as f:
                raw_bytes = f.read()

            try:
                content = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                content = raw_bytes.decode("latin-1")

            post = frontmatter.loads(content)
            post.content = str(post.content)

            if not post.metadata:
                post.metadata = {}

            post.metadata.setdefault("title", md_file.replace(".md", ""))
            post.metadata.setdefault("date", time.strftime("%Y-%m-%d"))
            post.metadata.setdefault("category", "General")
            post.metadata.setdefault("pdf", "")

            summary, tags = get_metadata(post.content)
            post.metadata["summary"] = summary
            post.metadata["tags"] = tags

            if not re.search(r"# Reviewed: (true|false)", post.content, re.IGNORECASE):
                post.content += "\n\n# Reviewed: false"

            rendered = frontmatter.dumps(post)
            with open(os.path.join(staging, md_file), "w", encoding="utf-8") as f:
                f.write(rendered)

            with open(log_file, "a", encoding="utf-8") as log_f:
                log_f.write(f"Wrote {md_file} to Staging\n")

            os.remove(os.path.join(inbox, md_file))
            with open(log_file, "a", encoding="utf-8") as log_f:
                log_f.write(f"Removed {md_file} from Inbox\n")

        except Exception as e:
            with open(log_file, "a", encoding="utf-8") as log_f:
                log_f.write(f"# Error processing {md_file} at {time.time()}\n")
                log_f.write(f"Message: {str(e)}\n\n")
            continue

if __name__ == "__main__":
    organize_files()
