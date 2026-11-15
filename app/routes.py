import os, uuid
from pathlib import Path
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from .db import db
from .reader import extract_documents, build_index, load_index, summary, topics

api = Blueprint("api", __name__)
ALLOWED = {".pdf", ".docx", ".txt"}

LOCAL_USER_ID = 1

@api.get("/documents")
def documents():
    uid = LOCAL_USER_ID
    with db() as c:
        rows = c.execute("SELECT id,original_name,file_type,page_count,chunk_count,summary,topics,created_at FROM documents WHERE user_id=? ORDER BY id DESC",(uid,)).fetchall()
    return jsonify([dict(r) for r in rows])

@api.post("/documents/upload")
def upload():
    uid = LOCAL_USER_ID
    f = request.files.get("file")
    if not f: return jsonify({"error":"Choose a document first."}),400
    original = f.filename or ""
    ext = Path(original).suffix.lower()
    if ext not in ALLOWED: return jsonify({"error":"Supported formats: PDF, DOCX and TXT."}),400
    if not secure_filename(original): return jsonify({"error":"Invalid filename."}),400
    with db() as c:
        cur = c.execute("INSERT INTO documents(user_id,original_name,stored_name,file_type) VALUES(?,?,?,?)",(uid,original,"",ext[1:]))
        did = cur.lastrowid
    stored = uuid.uuid4().hex + ext
    folder = Path("instance_data")/"uploads"/str(uid)
    folder.mkdir(parents=True,exist_ok=True)
    path = folder/stored
    try:
        f.save(path)
        raw = extract_documents(str(path),ext)
        full = "\n".join(x.page_content for x in raw)
        chunks = build_index(uid,did,raw)
        with db() as c:
            c.execute("UPDATE documents SET stored_name=?,page_count=?,chunk_count=?,summary=?,topics=? WHERE id=? AND user_id=?",
                      (stored,len(raw),len(chunks),summary(full),topics(full),did,uid))
        return jsonify({"id":did,"name":original,"pages":len(raw),"chunks":len(chunks)}),201
    except Exception as e:
        with db() as c: c.execute("DELETE FROM documents WHERE id=? AND user_id=?",(did,uid))
        if path.exists(): path.unlink()
        return jsonify({"error":str(e)}),500

@api.get("/documents/<int:did>")
def detail(did):
    uid = LOCAL_USER_ID
    with db() as c:
        r=c.execute("SELECT id,original_name,file_type,page_count,chunk_count,summary,topics,created_at FROM documents WHERE id=? AND user_id=?",(did,uid)).fetchone()
    return jsonify(dict(r)) if r else (jsonify({"error":"Document not found."}),404)

@api.get("/documents/<int:did>/content")
def content(did):
    uid = LOCAL_USER_ID
    with db() as c:
        r=c.execute("SELECT stored_name,file_type FROM documents WHERE id=? AND user_id=?",(did,uid)).fetchone()
    if not r: return jsonify({"error":"Document not found."}),404
    p=Path("instance_data")/"uploads"/str(uid)/r["stored_name"]
    docs=extract_documents(str(p),"."+r["file_type"])
    return jsonify({"pages":[{"page":x.metadata.get("page",0),"section":x.metadata.get("section","Document"),"text":x.page_content} for x in docs]})

@api.post("/documents/<int:did>/ask")
def ask(did):
    uid = LOCAL_USER_ID
    q=(request.get_json(silent=True) or {}).get("question","").strip()
    if not q: return jsonify({"error":"Type a question about this document."}),400
    with db() as c: r=c.execute("SELECT original_name FROM documents WHERE id=? AND user_id=?",(did,uid)).fetchone()
    if not r: return jsonify({"error":"Document not found."}),404
    if not os.getenv("GEMINI_API_KEY"):
        return jsonify({"error":"Gemini API key missing. Add GEMINI_API_KEY to .env and restart."}),503
    try:
        hits=load_index(uid,did).similarity_search_with_score(q,k=int(os.getenv("TOP_K","5")))
        if not hits: return jsonify({"answer":"I couldn't find this information in the selected document.","evidence":[]})
        evidence=[]; context=[]
        for n,(doc,score) in enumerate(hits,1):
            page=doc.metadata.get("page",0); loc=f"Page {page}" if page else doc.metadata.get("section","Document")
            evidence.append({"rank":n,"source":r["original_name"],"location":loc,"text":doc.page_content[:650]})
            context.append(f"[Evidence {n} | {loc}]\n{doc.page_content}")
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.prompts import ChatPromptTemplate
        llm=ChatGoogleGenerativeAI(model=os.getenv("GEMINI_MODEL","gemini-3.8-flash"),google_api_key=os.getenv("GEMINI_API_KEY"),temperature=0.15)
        prompt=ChatPromptTemplate.from_messages([
            ("system","You are DocuLens AI, a careful document analyst. Answer ONLY from the supplied evidence. If evidence does not contain the answer, say: I couldn't find this information in the selected document. Do not invent facts. Use clear structure and mention page or section references."),
            ("human","QUESTION:\n{question}\n\nDOCUMENT EVIDENCE:\n{context}\n\nAnswer using only this evidence.")])
        answer=(prompt|llm).invoke({"question":q,"context":"\n\n".join(context)})
        return jsonify({"answer":answer.content,"evidence":evidence,"document":r["original_name"]})
    except Exception as e:
        return jsonify({"error":"Question answering failed: "+str(e)}),500

@api.delete("/documents/<int:did>")
def delete(did):
    uid = LOCAL_USER_ID
    with db() as c:
        r=c.execute("SELECT stored_name FROM documents WHERE id=? AND user_id=?",(did,uid)).fetchone()
        if not r: return jsonify({"error":"Document not found."}),404
        c.execute("DELETE FROM documents WHERE id=? AND user_id=?",(did,uid))
    f=Path("instance_data")/"uploads"/str(uid)/r["stored_name"]
    if f.exists(): f.unlink()
    import shutil
    shutil.rmtree(Path("instance_data")/"users"/str(uid)/str(did),ignore_errors=True)
    return jsonify({"success":True})
