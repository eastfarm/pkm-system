**Personal Knowledge Management (PKM) System — Overview (last updated: 2025-05-20 05:28 CET)**

---

### **Purpose**

The PKM system is designed to help a non-coder manage personal knowledge across Windows PC and iOS (iPhone, Apple Watch) using a Progressive Web App (PWA). It enables capture, organization, review, and querying of diverse data types—notes, PDFs, URLs, videos, audio, and more—using AI for metadata generation and semantic search.

The system automatically ingests files from `~/GoogleDrive/PKM/Inbox`, which can be populated via:

* iOS Drafts app
* Manual file uploads
* Email Shortcuts (Phase 2)

All data is transformed into structured markdown metadata records containing AI-enriched extracts (semantic summaries), tags, and references to the original source files. Text content is included only when appropriate. The system is simple, extensible, and will be voice-enabled (in Phase 2).

---

### **Current Status**

As of May 20, 2025, the system has:

* ✅ Complete backend implementation with FastAPI
* ✅ Complete frontend implementation with Next.js
* ✅ Automatic Google Drive webhook integration that processes files as they're added
* ✅ AI-powered metadata extraction for various file types
* ✅ Comprehensive logging system for all processes
* ✅ Semantic search functionality for retrieving knowledge (not tested yet)
* ✅ Deployed on Railway.app as a fully functional cloud service

Current challenges being addressed:
* Ensuring OpenAI API key is properly configured for the AI extraction
* Optimizing the webhook-based file monitoring
* Making sure the application logs are accessible and informative

---

### **Recent Enhancements**

#### **1. Google Drive Real-time Integration**

* Implemented webhook-based monitoring of the PKM/Inbox folder
* Files are processed immediately when added to Google Drive (no manual intervention needed)
* The integration includes automatic renewal of webhooks and comprehensive error handling
* Detailed logs are created for all operations, making troubleshooting easier

#### **2. Enhanced Logging System**

* All operations (file discovery, download, processing, upload) are now extensively logged
* Log files are created for each sync operation with timestamp-based naming
* Logs are accessible via the UI for easy troubleshooting
* Error conditions are clearly indicated with detailed information

#### **3. Improved Error Handling**

* The system now handles errors gracefully at each step of the process
* Error details are captured in the logs for easier diagnosis
* The UI shows clear information about sync status and issues

#### **4. Deployment Optimizations**

* Railway.app deployment has been optimized for reliable operation
* Background tasks ensure webhook registration stays active
* Startup processes automatically set up necessary folders and integrations

#### **5. Extract Title and Content Separation**

* The extract is now split into `extract_title` and `extract_content`
* `extract_title` can be inferred by the AI or taken from document content if clearly present
* `extract_content` captures the semantic core of the file

#### **6. Approval Workflow: Save vs Reprocess**

* Metadata schema includes:
  * `reprocess_status`: `none`, `requested`, `in_progress`, `complete`
  * `reprocess_rounds`: count of times a file has been reprocessed
  * `reprocess_notes`: optional user instructions for improving analysis or clarifying intent
  * `processing_profile`: preset applied by system or selected by user

* Replaced the "Approve" model with **Save** and **Reprocess** options.

---

### **Architecture**

#### **Cloud-Based Google Drive Integration**

* Files are monitored in `/PKM/Inbox` via the Google Drive API webhook system
* Processed metadata is saved locally, then uploaded to:
  * `/PKM/Processed/Metadata/` (markdown files)
  * `/PKM/Processed/Sources/<filetype>/` (original files)
* Original files in `/PKM/Inbox` are only deleted if both uploads succeed
* `GOOGLE_TOKEN_JSON` is stored in Railway env vars for OAuth reuse
* Webhook-based notification system ensures files are processed immediately

#### **Backend (pkm-indexer)**

* **Stack**: Python (FastAPI), `frontmatter`, `openai`, `faiss`, Google Drive API
* **Deployment**: Railway — `pkm-indexer-production.up.railway.app`
* **Core Responsibilities**:
  * Monitor/sync files from Google Drive Inbox via webhooks
  * Generate rich metadata extracts using OpenAI
  * Extract and summarize content from PDFs, audio, images, URLs, and markdown
  * Store structured `.md` metadata files with frontmatter and optional content
  * Serve metadata extracts via API and enable approval/review
  * Index extracts and metadata fields into FAISS for retrieval

* **Key Modules**:
  * `main.py`: API endpoints, webhook handling, and Google Drive integration
  * `organize.py`: Processes files, generates AI extracts, injects metadata
  * `index.py`: Indexes extracts and metadata

* **File Structure**:
  * `Inbox/` — where downloaded files land from Google Drive
  * `Processed/`
    * `Metadata/` — YAML frontmatter `.md` records (extracts, tags, source refs)
    * `Sources/` — original files, organized by type (PDFs, images, audio, etc.)
  * `Logs/` — detailed logs of all operations
  * `Archive/` — optional long-term storage for previously handled files

#### **Frontend (pkm-app)**

* **Stack**: Next.js PWA, React, Axios
* **Deployment**: Railway — `pkm-app-production.up.railway.app`
* **Core Responsibilities**:
  * Review metadata extracts in staging
  * Edit and approve titles, tags, categories, extracts
  * Provide access to logs and system status
  * Search indexed extracts via semantic search

* **Key Components**:
  * `index.js`: Query/search interface and system status
  * `staging.js`: File review queue
  * `StagingTable.js`: Metadata editor with Save and Reprocess options

---

### **Multi-Modal Processing Pipeline**

The system supports different strategies for different file types:

* **Notes & Text**: Captured and summarized with tags
* **PDFs**: Analyzed for structure, key points extracted with AI
* **Images**: OCR-processed to extract readable text
* **URLs**: Detected and enriched using requests and BeautifulSoup
* **Audio**: Preprocessed (transcription planned for Phase 2)

---

### **Required Environment Variables**

* `OPENAI_API_KEY` - For AI-powered metadata extraction
* `GOOGLE_TOKEN_JSON` - Google Drive OAuth credentials
* `WEBHOOK_URL` - Set to the Railway deployment URL + "/drive-webhook"

---

### **Next Steps**

1. **Optimize AI Extraction**: 
   * Review and refine prompt templates for different document types
   * Implement better fallback behaviors when AI extraction fails

2. **Implement Thematic Taxonomy**:
   * Create a curated theme classification system beyond simple tags
   * Develop a theme management interface
   * Update AI extraction to consider theme taxonomy

3. **Enhanced Multimodal Support**:
   * Improve image OCR quality and reliability
   * Add audio transcription capabilities
   * Implement better URL content extraction

4. **Frontend Improvements**:
   * Add a dedicated dashboard for system status monitoring
   * Implement a tag/theme management interface
   * Develop visualization for knowledge connections

5. **Integration Expansions**:
   * Add email integration for direct capture
   * Support additional cloud storage providers
   * Create integration points for Notion, Obsidian, and other knowledge tools

6. **Deployment & Reliability**:
   * Set up monitoring for system health
   * Implement automatic backups
   * Add error recovery mechanisms for more resilient processing

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