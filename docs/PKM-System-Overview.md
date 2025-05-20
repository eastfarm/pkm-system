# Personal Knowledge Management (PKM) System — Overview (last updated: 2025-05-20 06:45 CET)

---

## **Purpose**

The PKM system is designed to help a non-coder manage personal knowledge across Windows PC and iOS (iPhone, Apple Watch) using a Progressive Web App (PWA). It enables capture, organization, review, and querying of diverse data types—notes, PDFs, URLs, videos, audio, and more—using AI for metadata generation and semantic search.

The system automatically ingests files from `~/GoogleDrive/PKM/Inbox`, which can be populated via:

* iOS Drafts app
* Manual file uploads
* Email Shortcuts (Phase 2)

All data is transformed into structured markdown metadata records containing AI-enriched extracts (semantic summaries), tags, and references to the original source files. Text content is included only when appropriate. The system is simple, extensible, and will be voice-enabled (in Phase 2).

---

## **System Architecture**

![System Architecture Diagram]

### **Data Flow**

1. Files are added to Google Drive PKM/Inbox folder
2. Webhook notification triggers backend processing
3. Files are downloaded to local inbox
4. OpenAI processes files to generate metadata
5. Metadata and original files are uploaded to separate folders
6. Files are indexed for semantic search
7. Frontend displays files for review and querying

### **Component Overview**

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

## **Metadata Schema**

All processed files generate a metadata record with the following fields:

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| title | string | Document title | Yes |
| date | string | Processing date (YYYY-MM-DD) | Yes |
| file_type | string | Original file type (pdf, image, text, etc.) | Yes |
| source | string | Original filename | Yes |
| source_url | string/null | URL if applicable | No |
| tags | array | Topic-related tags | Yes |
| category | string | Document category | Yes |
| author | string | Content author | No |
| extract_title | string | AI-generated title | Yes |
| extract_content | string | AI-generated summary | Yes |
| reviewed | boolean | Whether file has been approved | Yes |
| parse_status | string | Processing status | Yes |
| extraction_method | string | Method used to extract content | Yes |
| reprocess_status | string | Status of reprocessing (none, requested, in_progress, complete, failed) | Yes |
| reprocess_rounds | string | Number of reprocessing attempts | Yes |
| reprocess_notes | string | User instructions for reprocessing | No |
| processing_profile | string | AI processing profile used | No |
| referenced_urls | array | URLs found in the content | No |
| referenced_resources | array | Resources referenced in content | No |

---

## **API Endpoints**

### **Core Endpoints**

| Endpoint | Method | Description | Parameters |
|----------|--------|-------------|------------|
| `/staging` | GET | Get files in staging area for review | None |
| `/approve` | POST | Approve or reprocess a file | `file` object with metadata |
| `/sync-drive` | POST | Sync files from Google Drive | None |
| `/search` | POST | Search the knowledge base | `query` string |
| `/trigger-organize` | POST | Process files in local inbox | None |
| `/webhook/status` | GET | Check webhook status | None |
| `/file-stats` | GET | Get file and system statistics | None |
| `/logs` | GET | List available log files | None |
| `/logs/{log_file}` | GET | Get content of specific log | `log_file` string |
| `/upload/{folder}` | POST | Upload file to specified folder | `filename`, `content` (base64) |

### **Google Drive Endpoints**

| Endpoint | Method | Description | Parameters |
|----------|--------|-------------|------------|
| `/drive-webhook` | POST | Handle Google Drive change notifications | None |
| `/auth/initiate` | GET | Initiate OAuth flow for Google Drive | None |
| `/oauth/callback` | GET | OAuth callback handler | `code` query param |

---

## **Development Environment Setup**

### **Prerequisites**
- Node.js 16+ for frontend development
- Python 3.10+ for backend development
- Google Cloud account with Drive API enabled
- OpenAI API key
- Railway.app account for deployment

### **Local Development Setup**
1. Clone the repository: `git clone https://github.com/eastfarm/pkm-system.git`
2. Set up backend:
   ```bash
   cd apps/pkm-indexer
   pip install -r requirements.txt
   # Create a .env file with the following variables:
   # OPENAI_API_KEY=your_key_here
   # GOOGLE_TOKEN_JSON=your_json_here
   # WEBHOOK_URL=your_webhook_url
   uvicorn main:app --reload
   ```
3. Set up frontend:
   ```bash
   cd apps/pkm-app
   npm install
   npm run dev
   ```

### **Testing Environment**
- The system uses manual testing on the Railway.app deployment
- Frontend: https://pkm-app-production.up.railway.app
- Backend: https://pkm-indexer-production.up.railway.app

---

## **Current Status and Roadmap**

### **Completed Features (May 2025)**
- ✅ Complete backend implementation with FastAPI
- ✅ Complete frontend implementation with Next.js
- ✅ Google Drive webhook integration for real-time file processing
- ✅ AI-powered metadata extraction for various file types
- ✅ Comprehensive logging system
- ✅ Semantic search functionality
- ✅ Save and Reprocess workflow for metadata editing

### **In Progress**
- 🔄 Improving AI extraction reliability and error handling
- 🔄 Fixing metadata display issues in the staging UI
- 🔄 Enhancing reprocessing workflow for failed extractions

### **Next Milestones (June 2025)**
1. Implement thematic taxonomy beyond simple tags
2. Add multi-modal processing improvements for images and audio
3. Develop email integration for direct capture
4. Create dashboard for system monitoring

### **Future Expansion (Q3 2025)**
1. Voice-enabled commands and control
2. Integration with additional storage providers
3. Mobile-optimized UI enhancements
4. AI-assisted content organization recommendations

---

## **Known Issues and Troubleshooting**

### **Common Issues**
1. **Missing Extracts**: If extracts are not being generated, check:
   - OPENAI_API_KEY environment variable is set correctly
   - OpenAI API has not reached its rate limit
   - The file content is readable and not corrupted

2. **Google Drive Sync Issues**:
   - Webhook registration may fail if the WEBHOOK_URL is not publicly accessible
   - Ensure GOOGLE_TOKEN_JSON contains valid OAuth credentials
   - Check logs in `pkm/Logs/` for detailed error messages

3. **Frontend Build Errors**:
   - JavaScript files must use `//` comments, not `#` comments
   - Ensure Next.js compatibility with Link components

### **Debugging Tools**
- Backend logs accessible at `/logs` endpoint
- System status displayed on the frontend homepage
- Railway.app provides deployment logs for debugging

---

## **Code Patterns and Conventions**

### **File Organization**
- Backend Python files follow the single-responsibility principle
- Frontend components are organized by feature
- Logs and data files are stored in a structured folder hierarchy

### **Naming Conventions**
- Python: snake_case for functions and variables, PascalCase for classes
- JavaScript: camelCase for variables and functions, PascalCase for components
- Files: descriptive names with hyphens for multi-word filenames

### **Error Handling**
- Backend errors are logged to timestamped files in pkm/Logs/
- Critical errors send meaningful responses to the frontend
- Frontend displays user-friendly error messages

### **State Management**
- Frontend uses React useState and useEffect for local component state
- Backend maintains a webhook state object for tracking Google Drive integration

---

## **Integration Details**

### **Google Drive Integration**
- Authentication uses OAuth 2.0 flow
- Webhook notifications trigger real-time processing
- File hierarchy mirrors the local PKM structure
- Credentials are stored in Railway environment variables

### **OpenAI Integration**
- Uses GPT-4 for complex content, optimizes for smaller content
- Extracts use structured prompting with JSON output format
- Error handling includes retries and fallbacks
- API key management via environment variable

### **Future Integrations**
- Email capture will use IMAP/POP3 protocols
- Voice integration will leverage OpenAI Whisper API
- Additional cloud providers will use standardized adapter pattern

---

## **Multi-Modal Processing Pipeline**

The system supports different strategies for different file types:

* **Notes & Text**: Captured and summarized with tags
* **PDFs**: Analyzed for structure, key points extracted with AI
* **Images**: OCR-processed to extract readable text
* **URLs**: Detected and enriched using requests and BeautifulSoup
* **Audio**: Preprocessed (transcription planned for Phase 2)

---

## **Required Environment Variables**

| Variable | Purpose | Format | Required |
|----------|---------|--------|----------|
| OPENAI_API_KEY | Authenticates with OpenAI API | String | Yes |
| GOOGLE_TOKEN_JSON | Google Drive OAuth credentials | JSON String | Yes |
| WEBHOOK_URL | URL for Google Drive webhooks | String | Yes |
| PORT | Web server port | Number | No (defaults to 8000) |

---

## **Deployment Guide**

### **Railway.app Deployment**
1. Fork the repository to your GitHub account
2. Connect your Railway account to GitHub
3. Create two new Railway projects:
   - pkm-indexer
   - pkm-app
4. Set the following environment variables for pkm-indexer:
   - OPENAI_API_KEY
   - GOOGLE_TOKEN_JSON (base64-encoded OAuth credentials)
   - WEBHOOK_URL (set to your Railway deployment URL + "/drive-webhook")
5. Deploy both services from your GitHub repository
6. Configure the Railway domain for CORS (if needed)

---

## **Recent Enhancements**

### **1. Google Drive Real-time Integration**

* Implemented webhook-based monitoring of the PKM/Inbox folder
* Files are processed immediately when added to Google Drive (no manual intervention needed)
* The integration includes automatic renewal of webhooks and comprehensive error handling
* Detailed logs are created for all operations, making troubleshooting easier

### **2. Enhanced Logging System**

* All operations (file discovery, download, processing, upload) are now extensively logged
* Log files are created for each sync operation with timestamp-based naming
* Logs are accessible via the UI for easy troubleshooting
* Error conditions are clearly indicated with detailed information

### **3. Improved Error Handling**

* The system now handles errors gracefully at each step of the process
* Error details are captured in the logs for easier diagnosis
* The UI shows clear information about sync status and issues

### **4. Deployment Optimizations**

* Railway.app deployment has been optimized for reliable operation
* Background tasks ensure webhook registration stays active
* Startup processes automatically set up necessary folders and integrations

### **5. Extract Title and Content Separation**

* The extract is now split into `extract_title` and `extract_content`
* `extract_title` can be inferred by the AI or taken from document content if clearly present
* `extract_content` captures the semantic core of the file

### **6. Approval Workflow: Save vs Reprocess**

* Metadata schema includes:
  * `reprocess_status`: `none`, `requested`, `in_progress`, `complete`
  * `reprocess_rounds`: count of times a file has been reprocessed
  * `reprocess_notes`: optional user instructions for improving analysis or clarifying intent
  * `processing_profile`: preset applied by system or selected by user

* Replaced the "Approve" model with **Save** and **Reprocess** options.

---

## **Glossary**

- **Extract**: An AI-generated summary of a file's content that captures its semantic meaning
- **Frontmatter**: YAML metadata at the beginning of markdown files
- **Metadata**: Structured information about a file, including title, tags, and extracts
- **PKM**: Personal Knowledge Management
- **Reprocessing**: The process of regenerating AI extracts with different parameters
- **Staging Area**: UI for reviewing and approving processed files before they enter the knowledge base
- **Webhook**: HTTP callback that notifies the system when files change in Google Drive

---

## **Research-Grade Extraction Prompt**

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