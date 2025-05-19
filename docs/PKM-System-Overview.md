**Personal Knowledge Management (PKM) System — Overview (last updated: 2024-05-18 20:25 CET)**

---

### **Purpose**

The PKM system is designed to help a non-coder manage personal knowledge across Windows PC and iOS (iPhone, Apple Watch) using a Progressive Web App (PWA). It enables capture, organization, review, and querying of diverse data types—notes, PDFs, URLs, videos, audio, and more—using AI for metadata generation and semantic search.

The long-term vision includes automatic ingestion from `~/OneDrive/PKM/Inbox`, populated via:

* iOS Drafts app
* Manual file uploads
* Email Shortcuts (Phase 2)

All data will be transformed into structured markdown metadata records containing AI-enriched extracts (semantic summaries), tags, and references to the original source files. Text content is included only when appropriate. The system will be simple, extensible, and voice-enabled (in Phase 2).

---

### **Enhancement Ideas & Future Considerations**

#### **1. Extract as Primary Field**

* The `extract` field replaces `summary` and is the primary semantic output for each document.
* An extract captures the document's meaning or core insights, ignoring format and technical structure.
* All search and LLM prompt chaining will operate over extracts as the core knowledge layer.

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

#### **4. Differentiated Document Processing Pipeline**

* Different file types and content genres require different extraction strategies:

  * 🧠 A **quote** requires no summarization — only accurate tagging and storage in the quote archive.
  * 📑 A **longform research article** requires semantic structuring, argument distillation, and page-aware summarization.
  * 🎧 An **audio transcript** may require preprocessing (e.g. diarization) before extract creation.
* In the future, document type detection (via filename, file type, or AI inference) will route documents through tailored prompt pipelines.
* Prompt selection and chunking strategy will become programmable via rules or configuration files (e.g. `prompt_profile: "quote"` vs. `"research"`).

#### **5. Additional Enhancements (Candidate List)**

* Multi-lingual support and language detection
* User-defined metadata fields (e.g. `confidence_score`, `intent`, `relevance`)
* Version history and editing logs for metadata records
* Bulk reprocessing (e.g. re-extract with a new model or updated prompt)
* Integration with Notion, Obsidian, or Logseq for surfacing extracts
* Web UI to browse metadata records by theme or source file type
* Extract quality scoring (manual or AI-assisted)
* Optional extract auto-promotion: extract → permanent note (via trigger or rule)

---

### **Architecture**

#### **Backend (pkm-indexer)**

* **Stack**: Python (FastAPI), `apscheduler`, `frontmatter`, `shutil`, `openai`, `faiss`

* **Deployment**: Railway — `pkm-indexer-production.up.railway.app`

* **Core Responsibilities**:

  * Monitor/sync files from Inbox
  * Generate rich metadata extracts using OpenAI
  * Extract and summarize content from PDFs, audio, URLs, and markdown
  * Store structured `.md` metadata files with frontmatter and optional content
  * Serve metadata extracts via API and enable approval/review
  * Index extracts and metadata fields into FAISS for retrieval

* **Key Modules**:

  * `main.py`: API endpoints `/staging`, `/approve`, `/trigger-organize`, `/files/{folder}`, `/file-content/{folder}/{filename}`, `/upload/{folder}`
  * `organize.py`: Processes files, generates AI extracts, injects metadata
  * `index.py`: Indexes extracts and metadata (not full file bodies)

* **File Structure for OneDrive Compatibility**:

  * `Inbox/` — where unprocessed uploads arrive
  * `Processed/`

    * `Metadata/` — YAML frontmatter `.md` records (extracts, tags, source refs)
    * `Sources/` — original files, organized by type (PDFs, images, audio, etc.)
  * `Archive/` — optional long-term storage for previously handled files

  This layout replaces the older `Areas/` model, which conflated category and storage. Categories are now handled via metadata tags and can be visualized dynamically rather than being embedded in the directory structure.

* **Scalability Note**: In Phase 2, content chunking and document splitting will support indexing long PDFs or audio transcripts across multiple `.md` metadata records.

#### **Frontend (pkm-app)**

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

  * The `extract` is the primary field shown to the user in the staging interface
  * If the original file is short and plain-text, the extract may include or resemble its content
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

---
