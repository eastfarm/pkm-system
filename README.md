# PKM System

This repository contains a complete AI-powered personal knowledge management system built as a monorepo with separate frontend and backend applications.

---

## 🧠 Overview

The PKM System allows users to capture, organize, review, and query their personal notes, documents, and media — with AI-enriched metadata, semantic search, and a structured review process.

See [`docs/PKM-System-Overview.md`](docs/PKM-System-Overview.md) for full system architecture and roadmap.

---

## 📁 Structure

```

pkm-system/
├── apps/
│   ├── pkm-app/         # Frontend (Next.js)
│   └── pkm-indexer/     # Backend (FastAPI)
├── docs/
│   └── PKM-System-Overview\.md
├── README.md
└── .gitignore

````

---

## 🖥 Apps

### 📦 `pkm-indexer` (FastAPI)

- Handles file intake, metadata generation, indexing (FAISS), and review routing.
- Sync OpenAI API used in MVP (LangChain planned).
- Deployed to Railway at [`pkm-indexer-production.up.railway.app`](https://pkm-indexer-production.up.railway.app)

### 🌐 `pkm-app` (Next.js)

- Progressive Web App to review, approve, and query content.
- Supports file upload and AI-powered search.
- Deployed to Railway at [`pkm-app-production.up.railway.app`](https://pkm-app-production.up.railway.app)

---

## 🚀 Getting Started

Clone and run each app independently:

```bash
cd apps/pkm-indexer
pip install -r requirements.txt
uvicorn main:app --reload

cd apps/pkm-app
npm install
npm run dev
````

---

## 🛣️ Roadmap

* [x] Basic upload, organize, review, and search loop
* [x] Frontend metadata editor
* [x] FAISS indexing on startup
* [ ] LangChain chains for metadata and search
* [ ] OneDrive sync
* [ ] Voice commands and transcription


