
```markdown
# Research Assistant AI

An AI-powered research assistant that lets you upload multiple PDFs into a
research session, parses them into Markdown, and answers questions across
all documents — with source-file citations and contradiction detection.

## Features

- **Multi-PDF sessions** — upload several PDFs into one `ResearchSession`;
  each file is stored as a `Document` linked to that session.
- **Async processing** — PDFs are parsed in the background via Celery
  (`process_document_task`) using LlamaParse (PDF → Markdown).
- **Cross-document Q&A** — a LangGraph workflow (`retrieve → grade → generate`)
  powered by Gemini 2.5 Flash Lite synthesizes answers across all documents,
  citing filenames and flagging contradictions.
- **Chat history** — every user/AI turn is persisted as a `ChatMessage`;
  sessions can be listed, renamed, and deleted.
- **React UI** — sidebar history, chat view with Markdown rendering,
  and task-status polling.

## Architecture

```
React (frontend/) ──► Django REST API (backend/api/)
                          │
                          ├─► Celery worker ──► LlamaParse ──► Document (Markdown)
                          │
                          └─► LangGraph (backend/ai_engine/graph.py)
                                  └─► Gemini 2.5 Flash Lite ──► brief
```

## Tech Stack

| Layer     | Technology                                        |
|-----------|---------------------------------------------------|
| Frontend  | React, `react-markdown`                           |
| Backend   | Django, Django REST Framework, `corsheaders`      |
| Task queue| Celery                                            |
| Parsing   | LlamaParse (`result_type="markdown"`)             |
| AI engine | LangGraph, LangChain, `ChatGoogleGenerativeAI`    |
| LLM       | Gemini 2.5 Flash Lite (1M-token context window)   |

## Data Models

- `ResearchSession` — UUID-keyed container for a research thread.
- `Document` — parsed Markdown content of an uploaded PDF, FK → session.
- `ChatMessage` — a `user`/`ai` message with timestamp, FK → session.

## API Endpoints

| Method | Endpoint                  | Description                                  |
|--------|---------------------------|----------------------------------------------|
| POST   | `/api/upload/`            | Upload a PDF + query; returns `task_id`, `session_id` |
| GET    | `/api/status/<task_id>/`  | Poll Celery task status                      |
| POST   | `/api/chat/`              | Ask a question across all session documents  |
| GET    | `/api/history/`           | List all research sessions                   |
| GET    | `/api/session/<id>/`      | Get all messages for a session               |
| PATCH  | `/api/history/<id>/`      | Rename a session                             |
| DELETE | `/api/history/<id>/`      | Delete a session                             |

## AI Engine

The LangGraph workflow in `backend/ai_engine/graph.py` uses an `AgentState`
(`query`, `context`, `brief`, `is_relevant`) and three nodes:

1. `retrieve_node` — passes through document context.
2. `grade_node` — sets the `is_relevant` flag (conditional edge to `END`).
3. `generate_brief_node` — prompts Gemini to compare documents, cite
   filenames, and surface contradictions; returns the `brief`.

## Setup

### Prerequisites
- Python 3.10+, Node.js 18+, a Celery broker (e.g. Redis)

### Backend
```bash
cd backend
pip install -r requirements.txt
```

Create a `.env` with:
```
GOOGLE_API_KEY=...
LLAMA_CLOUD_API_KEY=...
```

```bash
python manage.py migrate
python manage.py runserver          # API on :8000
celery -A core worker -l info       # in a second terminal
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Usage

1. Upload one or more PDFs — the first upload creates a session; subsequent
   uploads append to it via `session_id`.
2. The frontend polls `/api/status/<task_id>/` until parsing succeeds.
3. Chat with the assistant; answers cite `--- SOURCE FILE: <name> ---` blocks.
4. Revisit, rename, or delete past sessions from the history sidebar.
```

---

## Key details behind the draft

- **Upload flow:** `UploadDocumentView.post` creates or reuses a `ResearchSession` from `session_id`, saves the file to `temp/`, and dispatches `process_document_task.delay(file_path, query, session.id)` [1](#0-0) .
- **Background task:** `process_document_task` parses the PDF via `LlamaParse(result_type="markdown")`, creates a `Document`, invokes the graph, saves the AI's first `ChatMessage`, and deletes the temp file [2](#0-1) .
- **Chat flow:** `ChatView.post` wraps every session document in `--- SOURCE FILE: {file_name} ---` blocks, invokes `ai_graph`, and persists both turns [3](#0-2) .
- **Graph:** `AgentState` + `retrieve`/`grade`/`generate` nodes with a conditional edge on `is_relevant`; generation uses `ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")` [4](#0-3) .
- **Models:** `ResearchSession` (UUID), `Document`, `ChatMessage` [5](#0-4) .
- **Frontend:** `App.jsx` handles multi-file upload with session tracking and polls the last file's `task_id` [6](#0-5) .

