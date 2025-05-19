**Personal Knowledge Management (PKM) System — Overview (last updated: 2024-05-18 20:25 CET)**

---

### **Purpose**

The PKM system is designed to help a non-coder manage personal knowledge across Windows PC and iOS (iPhone, Apple Watch) using a Progressive Web App (PWA). It enables capture, organization, review, and querying of diverse data types—notes, PDFs, URLs, videos, audio, and more—using AI for metadata generation and semantic search.

The long-term vision includes automatic ingestion from `~/OneDrive/PKM/Inbox`, populated via:

* iOS Drafts app
* Manual file uploads
* Email Shortcuts (Phase 2)

All data will be transformed into structured markdown metadata records containing AI-enriched summaries, tags, and references to the original source files. Text content is included only when appropriate. The system will be simple, extensible, and voice-enabled (in Phase 2).

**Personal Knowledge Management (PKM) System — Overview (last updated: 2024-05-18 20:25 CET)**

---

### **Purpose**

The PKM system is designed to help a non-coder manage personal knowledge across Windows PC and iOS (iPhone, Apple Watch) using a Progressive Web App (PWA). It enables capture, organization, review, and querying of diverse data types—notes, PDFs, URLs, videos, audio, and more—using AI for metadata generation and semantic search.

The long-term vision includes automatic ingestion from `~/OneDrive/PKM/Inbox`, populated via:

* iOS Drafts app
* Manual file uploads
* Email Shortcuts (Phase 2)

All data will be transformed into structured markdown metadata records containing AI-enriched extracts (summaries), tags, and references to the original source files. Text content is included only when appropriate. The system will be simple, extensible, and voice-enabled (in Phase 2).

---

### **Enhancement Ideas & Future Considerations**

#### **1. Summary as Extract**

* The `summary` field is now considered an **AI-generated extract** of the file — concise but semantically rich.
* Especially for long or non-text documents, the extract should convey the core insight without referencing structure or formatting.
* The extract may include direct quotes or synthesized statements from the full source, and will serve as the basis for indexing and semantic search.

#### **2. Thematic Taxonomy (Beyond Tags)**

* Introduce a curated **theme classification layer** in addition to freeform tags.
* Themes represent broader conceptual categories such as "Systems Thinking", "Ethics", "Personal Development", "Military Strategy".
* Each metadata file may include a new `themes:` field (distinct from `tags:`).
* A `themes.json` file will serve as the editable, centralized theme taxonomy.
* The user will periodically review and update the theme list via a dashboard or text interface.
* Over time, AI extracts will be prompted with awareness of current themes to improve classification precision.

#### **3. Centralized Theme Awareness for LLM Prompts**

* During `organize.py` summarization, the prompt will optionally include a reference to the current set of themes.
* Example: "Given the following content and the following themes, extract a summary and assign the most relevant theme(s)..."
* This helps the LLM converge toward human-curated structure without enforcing rigid taxonomy.

#### **4. Additional Enhancements (Candidate List)**

* Multi-lingual support and language detection
* User-defined metadata fields (e.g. `confidence_score`, `intent`, `relevance`)
* Version history and editing logs for metadata records
* Bulk reprocessing (e.g. re-summarize all metadata with a new model or updated prompt)
* Integration with Notion, Obsidian, or Logseq for surfacing extracts
* Web UI to browse metadata records by theme or source file type
* Summary quality scoring (manual or AI-assisted)
* Optional summary auto-promotion: extract → permanent note (via trigger or rule)

---

### **Architecture**

#### **Backend (pkm-indexer)**

* **Stack**: Python (FastAPI), `apscheduler`, `frontmatter`, `shutil`, `openai`, `faiss`

* **Deployment**: Railway — `pkm-indexer-production.up.railway.app`

* **Core Responsibilities**:

  * Monitor/sync files from Inbox
  * Generate rich metadata summaries using OpenAI
  * Extract and summarize content from PDFs, audio, URLs, and markdown
  * Store structured `.md` metadata files with frontmatter and optional content
  * Serve metadata summaries via API and enable approval/review
  * Index summaries and metadata fields into FAISS for retrieval

* **Key Modules**:

  * `main.py`: API endpoints `/staging`, `/approve`, `/trigger-organize`, `/files/{folder}`, `/file-content/{folder}/{filename}`, `/upload/{folder}`
  * `organize.py`: Processes files, generates AI summaries, injects metadata
  * `index.py`: Indexes summaries and metadata (not full file bodies)

* **File Structure for OneDrive Compatibility**:

  * `Inbox/` — where unprocessed uploads arrive
  * `Processed/`

    * `Metadata/` — YAML frontmatter `.md` records (summaries, tags, source refs)
    * `Sources/` — original files, organized by type (PDFs, images, audio, etc.)
  * `Archive/` — optional long-term storage for previously handled files

  This layout replaces the older `Areas/` model, which conflated category and storage. Categories are now handled via metadata tags and can be visualized dynamically rather than being embedded in the directory structure.

* **Scalability Note**: In Phase 2, content chunking and document splitting will support indexing long PDFs or audio transcripts across multiple `.md` metadata records.

#### **Frontend (pkm-app)**

* **Stack**: Next.js PWA, React, Axios

* **Deployment**: Railway — `pkm-app-production.up.railway.app`

* **Core Responsibilities**:

  * Review metadata summaries in staging
  * Edit and approve titles, tags, categories, summaries
  * Provide access to the original file when applicable
  * Search indexed summaries via semantic search

* **Key Components**:

  * `index.js`: Query/search interface
  * `staging.js`: File review queue
  * `StagingForm.js`: Metadata and summary editor

* **Tag Management & Extension** (planned):

  * A registry of unique tags will be generated based on all `.md` metadata
  * Admins can browse, rename, merge, or delete tags
  * Optional **custom actions** can be configured for specific tags (e.g. if tag is `life wisdom`, auto-append content to `wisdom.md`)
  * A dashboard endpoint (e.g. `/tags`) or a static tag index file (e.g. `tags.json`) can be regenerated after each indexing pass

---

### **LangChain & Retrieval Pipeline (Planned for Phase 2)**

LangChain will modularize prompt workflows, document parsing, and multi-turn query routing:

* **Metadata Generation**:

  * Replace `get_metadata()` with LangChain chains
  * Use structured prompt templates and output parsers
  * Chain steps: summarize → extract tags → infer category → inject metadata

* **Semantic Search / RAG Setup**:

  * Index only the AI-generated summaries and key metadata (not raw file content)
  * Use FAISS + LangChain Retriever to find top-matching `.md` summaries
  * Return metadata + `source:` link so the user can download the original
  * Future: use conversational memory or query rewriting for refinement

* **Multi-File Summarization**:

  * Long files split into meaningful semantic chunks (LangChain splitter)
  * Each chunk gets its own metadata `.md` entry (linked via file + page ID)
  * Enables reasoning across large documents or sessions

---

### **Metadata Format (YAML Frontmatter)**

```yaml
---
title: AI Strategy Brief
date: 2025-05-18
file_type: pdf
source: ai-strategy-brief.pdf
source_url: null
tags: [AI, logistics, autonomous systems]
author: Unknown
summary: |
  This 8-page brief outlines how autonomous agents will disrupt logistics and procurement.
  It highlights real-world deployments by Maersk and Amazon. Core themes include decision latency,
  autonomous workflows, and multi-agent systems.
reviewed: false
---
```

---

### **Workflow**

#### **Capture**

* Files uploaded via `/upload/{folder}`
* In Phase 2: Sync from OneDrive or webhook integrations

#### **Organize**

* `organize.py` uses OpenAI to summarize and tag the content
* If the file is short and plain-text, content is included below the frontmatter
* If long or non-text (PDF, image), summary + metadata only — source is referenced
* All outputs stored in `Processed/Metadata/`, while original files are moved to `Processed/Sources/`

#### **Review**

* UI shows:

  * Title, summary, tags, category
  * Link to download original source file
  * Optional full content (if included)
* Users edit metadata and approve

#### **Query**

* `/search` endpoint uses FAISS to retrieve top-k summaries
* Future: LangChain-enhanced retriever handles query expansion + citations
* Retrieved results are rendered with summary + source reference

---

### **MVP Status & Outlook**

* ✅ Upload → summarize → approve loop functional
* ✅ Structured metadata + file tracking in place
* ✅ Staging UI renders metadata with fallbacks
* ✅ OpenAI now returns JSON metadata reliably
* 🟡 Tag governance + custom tag triggers planned
* 🚧 Phase 2: LangChain + PDF + URL support + voice transcripts

---
