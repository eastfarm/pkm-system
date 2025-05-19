**Personal Knowledge Management (PKM) System — Overview (last updated: 2025-05-19 18:42 CET)**

---

### **Purpose**

The PKM system is designed to help a non-coder manage personal knowledge across Windows PC and iOS (iPhone, Apple Watch) using a Progressive Web App (PWA). It enables capture, organization, review, and querying of diverse data types—notes, PDFs, URLs, videos, audio, and more—using AI for metadata generation and semantic search.

The long-term vision includes automatic ingestion from `~/GoogleDrive/PKM/Inbox`, populated via:

* iOS Drafts app
* Manual file uploads
* Email Shortcuts (Phase 2)

All data will be transformed into structured markdown metadata records containing AI-enriched extracts (semantic summaries), tags, and references to the original source files. Text content is included only when appropriate. The system will be simple, extensible, and voice-enabled (in Phase 2).

---

### **Enhancement Ideas & Future Considerations**

#### **Approval Workflow: Save vs Reprocess**

* Metadata schema will include:

  * `reprocess_status`: `none`, `requested`, `in_progress`, `complete`
  * `reprocess_rounds`: count of times a file has been reprocessed
  * `reprocess_notes`: optional user instructions for improving analysis or clarifying intent
  * `processing_profile`: preset applied by system or selected by user (e.g. `quote`, `memo`, `report`)

* Replace the current "Approve" model with two options: **Save** and **Reprocess**.

* **Save** finalizes the current extract, tags, and metadata.

* **Reprocess** allows the user to:

  * Add clarifying instructions (e.g. “This is a quote from a lecture; just tag it”)
  * Trigger a new LLM extract or retry with a different method
  * Eventually choose from prompt profiles (e.g. `quote`, `memo`, `deep_analysis`)

* A background agent (LLM-based or rules-based) will monitor failed or reprocessed records and:

  * Normalize freeform reprocessing instructions
  * Suggest or auto-assign standard `processing_profile` values
  * Improve consistency and performance of future LLM prompts

* This pattern supports:

  * Recovery from failed extractions
  * Higher-quality metadata over time
  * User involvement in steering extract quality

* Reprocessing will not be implemented in the MVP, but all systems (metadata format, staging UI, and LLM prompt structure) should anticipate its future role.

#### **1. Extract Title and Content**

* The extract is now split into `extract_title` and `extract_content`.
* `extract_title` can be inferred by the AI or taken from document content if clearly present.
* `extract_content` captures the semantic core of the file.

#### **2. Thematic Taxonomy (Beyond Tags)**

* Introduce a curated **theme classification layer** in addition to freeform tags.
* Themes represent broader conceptual categories such as "Systems Thinking", "Ethics", "Personal Development", "Military Strategy".
* Each metadata file may include a new `themes:` field (distinct from `tags:`).
* A `themes.json` file will serve as the editable, centralized theme taxonomy.
* The user will periodically review and update the theme list via a dashboard or text interface.
* Over time, AI extracts will be prompted with awareness of current themes to improve classification precision.

#### **3. Centralized Theme Awareness for LLM Prompts**

* During `organize.py` summarization, the prompt will optionally include a reference to the current set of themes.

#### **4. Differentiated Document Processing Pipeline**

* The system supports different strategies for different file types:

  * 🧠 Quotes are tagged and archived.
  * 📑 Research articles are semantically summarized.
  * 🎧 Audio is preprocessed.
  * 🖼 Images use OCR (`pytesseract`) to extract readable text.
  * 🌐 URLs are detected and enriched using `requests` and `BeautifulSoup`.

#### **5. Additional Enhancements (Candidate List)**

* Multi-lingual support
* User-defined metadata fields
* Version history
* Bulk reprocessing
* Integration with tools like Notion or Obsidian
* Extract quality scoring

---

### **Architecture**

#### **Cloud-Based Google Drive Integration**

* Files are pulled from `/PKM/Inbox` via the Google Drive API
* Extracted metadata is saved locally, then uploaded to:

  * `/PKM/Processed/Metadata/` (markdown files)
  * `/PKM/Processed/Sources/<filetype>/` (original files)
* Original files in `/PKM/Inbox` are only deleted if both uploads succeed
* `GOOGLE_TOKEN_JSON` is stored in Railway env vars for OAuth reuse

#### **/sync-drive Endpoint**

* Can be triggered manually via API or frontend button
* Will later be run on a schedule (e.g. every 5–15 minutes)
* Modular helper functions manage Drive folder creation, upload, and conditional deletion

#### **Backend + Frontend Responsibilities**

All backend responsibilities and frontend staging behavior (as described earlier) remain unchanged, with the addition of:

* OCR for `.jpg`, `.png`, etc.
* URL parsing and inline enrichment
* Distinct `extract_title` + `extract_content`

The system now fully supports a Google Drive–based, LLM-powered, multimodal PKM ingestion pipeline with extensible automation and review controls.

---

### **Backend (pkm-indexer)**

* **Stack**: Python (FastAPI), `apscheduler`, `frontmatter`, `shutil`, `openai`, `faiss`

* **Deployment**: Railway — `pkm-indexer-production.up.railway.app`

* **Core Responsibilities**:

  * Monitor/sync files from Google Drive Inbox
  * Generate rich metadata extracts using OpenAI
  * Extract and summarize content from PDFs, audio, images, URLs, and markdown
  * Store structured `.md` metadata files with frontmatter and optional content
  * Serve metadata extracts via API and enable approval/review
  * Index extracts and metadata fields into FAISS for retrieval

* **Key Modules**:

  * `main.py`: API endpoints `/staging`, `/approve`, `/trigger-organize`, `/sync-drive`, `/upload/{folder}`
  * `organize.py`: Processes files, generates AI extracts, injects metadata
  * `index.py`: Indexes extracts and metadata

* **File Structure (Local Runtime)**:

  * `Inbox/` — where downloaded files land from Google Drive
  * `Processed/`

    * `Metadata/` — YAML frontmatter `.md` records (extracts, tags, source refs)
    * `Sources/` — original files, organized by type (PDFs, images, audio, etc.)
  * `Archive/` — optional long-term storage for previously handled files

* **Scalability Note**: In Phase 2, content chunking and document splitting will support indexing long PDFs or audio transcripts across multiple `.md` metadata records.

---

### **Frontend (pkm-app)**

* **Stack**: Next.js PWA, React, Axios

* **Deployment**: Railway — `pkm-app-production.up.railway.app`

* **Core Responsibilities**:

  * Review metadata extracts in staging
  * Edit and approve titles, tags, categories, extracts
  * Provide access to the original file when applicable
  * Search indexed extracts via semantic search

* **Key Components**:

  * `index.js`: Query/search interface
  * `staging.js`: File review queue
  * `StagingTable.js`: Metadata editor (with emphasis on extract)

* **Extract-Centric Design**:

  * The `extract_title` and `extract_content` fields are shown to the user in the staging interface
  * The full `content` field is hidden from the UI unless needed for debugging or future use
  * Future enhancements may include download buttons or side-by-side original content viewers

* **Tag and Theme Management** (planned):

  * A registry of unique tags and themes will be generated based on all `.md` metadata
  * Admins can browse, rename, merge, or delete tags and themes
  * Optional **custom actions** can be configured for specific tags or themes (e.g. if tag is `life wisdom`, auto-append extract to `wisdom.md`)
  * A dashboard endpoint (e.g. `/tags`) or a static tag index file (e.g. `tags.json`) can be regenerated after each indexing pass

---

### **Appendix: Research-Grade Extraction Prompt**

```text
You are an expert literary analyst with exceptional comprehension and synthesis abilities. Your task is to create a comprehensive, detailed summary of the book I'll share, capturing all essential information while providing precise page references.

Follow this analytical framework:

1. First, examine the book's structure and organization to understand its framework
- Identify major sections, chapters, and logical divisions
- Note how information flows and connects throughout the text

2. Systematically identify and extract:
- Central arguments and key claims (with exact page references)
- Critical evidence supporting each major point
- Important data, statistics, and research findings
- Essential frameworks, models, or methodologies
- Notable quotes that capture core concepts

3. Step by step, analyze the relationships between concepts by:
- Mapping how ideas build upon each other
- Identifying cause-effect relationships
- Noting comparative analyses or contrasting viewpoints
- Recognizing progression of arguments or narrative development

4. Create a comprehensive summary that:
- Maintains the book's logical structure
- Includes ALL key information with exact page references
- Preserves complex nuances and sophisticated reasoning
- Captures both explicit statements and implicit conclusions
- Retains critical examples that illustrate main concepts

Format your summary with:
- Clear hierarchical organization matching the book's structure
- Bullet points for discrete information with page numbers in parentheses (p.XX)
- Short paragraphs for connected concepts with inline page citations
- Special sections for methodologies, frameworks, or models
- Brief concluding synthesis of the book's most essential contributions

Remember:
- Prioritize depth and comprehensiveness over brevity
- Include ALL significant information, not just highlights
- Reference specific pages for every important point
- Preserve the author's original reasoning process
- Think step by step through the entire content before summarizing
```
