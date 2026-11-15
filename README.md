# DocuLens AI — Intelligent Document Reader

A local, single-user document intelligence workspace. The app opens directly to the dashboard: no login, registration, password, or authentication token is required.

## Features
- Direct-open document workspace and library
- PDF, DOCX and TXT extraction
- LangChain text splitting, Hugging Face embeddings and FAISS semantic retrieval
- Gemini-powered answers grounded in retrieved document passages
- Evidence cards with page/section references
- Document overview, key-topic extraction, upload and delete

## Setup — Windows PowerShell
```powershell
cd DocuLens_AI
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```
Add your Gemini API key to `.env`:
`GEMINI_API_KEY=your_key_here`

## Run
```powershell
python run.py
```
Open http://127.0.0.1:5000. The dashboard loads directly. Upload a document and ask questions.

## Architecture
Frontend (HTML/CSS/JS) → Flask REST API → LangChain text splitting → Hugging Face sentence-transformer embeddings → FAISS retrieval → Gemini grounded answer.

## Notes
- `GEMINI_MODEL` defaults to `gemini-2.5-flash`; adjust if unavailable for your API account.
- First launch downloads the Hugging Face embedding model. `HF_TOKEN` is optional for the public embedding model.
- Scanned/image-only PDFs need OCR; this edition extracts selectable text.
- Local data is stored under `instance_data/`. Anyone who can access this local app can access its documents. Do not expose it publicly without adding authentication and other security controls.
- Never commit or share `.env`.
