import os, re
from functools import lru_cache
from pathlib import Path
from docx import Document as WordDocument
from pypdf import PdfReader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

def extract_documents(path, ext):
    out = []
    if ext == ".pdf":
        for n, page in enumerate(PdfReader(path).pages, 1):
            text = page.extract_text() or ""
            if text.strip():
                out.append(Document(page_content=text, metadata={"page": n, "section": f"Page {n}"}))
    elif ext == ".docx":
        doc = WordDocument(path)
        section, buf = "Document", []
        for p in doc.paragraphs:
            t = p.text.strip()
            if not t: continue
            if p.style and p.style.name.lower().startswith("heading"):
                if buf: out.append(Document(page_content="\n".join(buf), metadata={"page": 0, "section": section}))
                section, buf = t, []
            buf.append(t)
        if buf: out.append(Document(page_content="\n".join(buf), metadata={"page": 0, "section": section}))
    elif ext == ".txt":
        t = Path(path).read_text(encoding="utf-8", errors="ignore")
        if t.strip(): out = [Document(page_content=t, metadata={"page": 0, "section": "Text document"})]
    else:
        raise ValueError("Unsupported file format.")
    return out

@lru_cache(maxsize=1)
def embeddings():
    model = os.getenv("HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    token = os.getenv("HF_TOKEN") or None
    kw = {"model_name": model, "encode_kwargs": {"normalize_embeddings": True}}
    if token: kw["model_kwargs"] = {"token": token}
    return HuggingFaceEmbeddings(**kw)

def build_index(uid, did, raw_docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=int(os.getenv("CHUNK_SIZE", "900")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "140")))
    chunks = splitter.split_documents(raw_docs)
    if not chunks:
        raise ValueError("No readable text found. Scanned PDFs require OCR.")
    for i, c in enumerate(chunks): c.metadata["chunk"] = i + 1
    store = FAISS.from_documents(chunks, embeddings())
    folder = Path("instance_data") / "users" / str(uid) / str(did)
    folder.mkdir(parents=True, exist_ok=True)
    store.save_local(str(folder))
    return chunks

def load_index(uid, did):
    folder = Path("instance_data") / "users" / str(uid) / str(did)
    return FAISS.load_local(str(folder), embeddings(), allow_dangerous_deserialization=True)

def summary(text):
    s = " ".join(text.split())
    return s[:500] + ("…" if len(s) > 500 else "")

def topics(text):
    stop = {"which","there","their","about","these","those","would","could","should","while","where","therefore","document"}
    words = re.findall(r"\b[a-zA-Z][a-zA-Z-]{4,}\b", text.lower())
    counts = {}
    for w in words:
        if w not in stop: counts[w] = counts.get(w, 0) + 1
    return ", ".join(w for w,n in sorted(counts.items(), key=lambda x:x[1], reverse=True)[:8])
