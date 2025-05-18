**Personal Knowledge Management (PKM) System — Revised Overview (as of May 18, 2025)**

---

### **Purpose**

The PKM system is designed to help a non-coder manage personal knowledge across Windows PC and iOS (iPhone, Apple Watch) using a Progressive Web App (PWA). It enables capture, organization, review, and querying of diverse data types—notes, PDFs, URLs, videos, audio, and more—using AI for metadata generation and semantic search.

The long-term vision includes automatic ingestion from `~/OneDrive/PKM/Inbox`, populated via:

* iOS Drafts app
* Manual file uploads
* Email Shortcuts (Phase 2)

All data will be transformed into markdown with YAML frontmatter and stored alongside original files. The system will be simple, extensible, and voice-enabled (in Phase 2).

---

### **Architecture**

#### **Backend (pkm-indexer)**

* **Stack**: Python (FastAPI), `apscheduler`, `frontmatter`, `shutil`, `openai`, `faiss`

* **Deployment**: Railway — `pkm-indexer-production.up.railway.app`

* **Core Responsibilities**:

  * Monitor/sync files from Inbox
  * Generate metadata using OpenAI (sync client fallback used for now)
  * Convert content to markdown + YAML frontmatter
  * Organize into Staging or Areas directories
  * Index and serve search endpoints
  * Expose file browsing and raw content endpoints for staging/log review

* **Key Modules**:

  * `main.py`: API endpoints `/staging`, `/approve`, `/trigger-organize`, `/files/{folder}`, `/file-content/{folder}/{filename}`, `/upload/{folder}`
  * `organize.py`: Organizes and enriches files with metadata (uses legacy OpenAI API for stability)
  * `index.py`: Indexes markdown via FAISS; currently uses an `async def indexKB()` function

* **Key Note**: Although `indexKB()` is asynchronous, it is currently called from `@app.on_event("startup")` using `await`, which works in the current MVP due to FastAPI's async support in startup events. This design is **acceptable for MVP and testing**, but should be reviewed in the future for long-term reliability, especially if we introduce background workers or refactor indexing to a scheduled or queued task.

* **Key Directories**:

  * `pkm/Inbox` — temporary holding area
  * `pkm/Staging` — review queue
  * `pkm/Areas/<category>` — finalized, structured storage
  * `pkm/Logs/` — error tracking

* **Key Endpoints**:

  * `/files/{folder}` — list files in Inbox, Staging, Areas, or Logs
  * `/file-content/{folder}/{filename}` — returns raw file content (e.g., for log review)

#### **Frontend (pkm-app)**

* **Stack**: Next.js PWA, React, Axios

* **Deployment**: Railway — `pkm-app-production.up.railway.app`

* **Core Responsibilities**:

  * Review and approve staged files
  * Search indexed KB
  * Upload markdown files (temporary MVP workflow)

* **Key Components**:

  * `index.js`: Search bar + file upload
  * `staging.js`: Review interface for files with error-guarded metadata rendering
  * `StagingForm.js`: Approve or edit metadata

---

### **Use of LangChain (Planned for Phase 2)**

LangChain will modularize prompt workflows and search pipelines:

* **Metadata Generation**:

  * Replace `get_metadata()` with LangChain chains
  * Use `PromptTemplate` + `RunnableSequence`
  * Chain: `summarize -> tag -> categorize`
* **Multi-Modal Content Handling**:

  * PDFs → text → summarize/tag
  * URLs → scrape → summarize/tag
  * Audio/video → Whisper → summarize/tag
* **Semantic Search Enhancements**:

  * Rewrite/expand queries
  * Maintain conversational context
  * Combine vector search with reasoning

LangChain is appropriate given your need for chaining, modularity, and multi-step AI workflows.

---

### **Metadata Format (YAML Frontmatter)**

```yaml
---
title: AI Drones Report
date: 2025-05-18
tags: [AI, drones, military]
category: Technology
source: military-ai-report.pdf
source_url: https://...
author: Unknown
summary: A report on AI drones in military operations.
reviewed: false
---
```

---

### **Workflow**

#### **Capture (Current: Temporary Upload | Future: OneDrive Sync)**

* Markdown files uploaded via `/upload/{folder}`
* In Phase 2: OneDrive folder watcher → `pkm/Inbox`

#### **Organize**

* `organize.py` parses markdown and enriches metadata
* Moves file to `pkm/Staging`
* Logs metadata extraction and issues
* Future: handle PDFs, audio, video, URLs

#### **Review**

* PWA shows staged files for approval
* User edits YAML frontmatter
* On approval, file moves to `pkm/Areas/<category>`

#### **Query**

* PWA sends query to `/search` (FAISS now)
* Phase 2: LangChain-enhanced retriever with semantic rephrasing

---

### **Current Status (MVP)**

* **Backend**: Deployed; API endpoints live
* **Frontend**: Deployed; staging UI fixed for null-safe rendering
* **Successes**:

  * `/trigger-organize` functional with sync OpenAI API
  * File detected and moved to staging
  * Metadata (when available) injected
* **Remaining Gaps**:

  * Metadata may still be empty for new test files
  * Frontend must safely render missing metadata (e.g. title fallback)
  * Missing file-content endpoint added for log inspection and staging review

---

### **Next Steps (Stable MVP to LangChain Upgrade)**

1. **Patch Frontend (Done)**

   * Add optional chaining to avoid crashes from missing metadata

2. **Improve Metadata Defaults in Backend**

   * Inject fallback values if summary/tags are missing

3. **LangChain Integration** (Phase 2)

   * Introduce `RunnableSequence`-based prompt chains
   * Modularize multi-step workflows for PDFs, URLs, and transcripts

4. **Enable Rich File Support**

   * Add PDF parsing (via `pdfplumber`)
   * Add URL scraping (via `requests` + `bs4`)
   * Add Whisper-based audio transcription

5. **Switch to Persistent File Store (Optional)**

   * Use Supabase Storage or S3 to persist files across deploys
   * Rewrite file handlers to support signed URLs or API-based storage access

---
