const $=id=>document.getElementById(id);
const S={docs:[],active:null};
async function api(path,opt={}){
  let h={...(opt.headers||{})};
  if(opt.body&&!(opt.body instanceof FormData))h["Content-Type"]="application/json";
  let r;
  try{r=await fetch("/api"+path,{...opt,headers:h})}
  catch(e){throw Error("Cannot reach the DocuLens server. Check that python run.py is still running.")}
  const raw=await r.text();
  let d;
  try{d=raw?JSON.parse(raw):{}}
  catch{
    const detail=raw.replace(/<[^>]*>/g," ").replace(/\s+/g," ").trim().slice(0,220);
    if(r.status===413)throw Error("File is too large. Maximum upload size is 25 MB.");
    throw Error(`Server returned a non-JSON response (HTTP ${r.status}). ${detail||"Check the PowerShell window for the error."}`);
  }
  if(!r.ok)throw Error(d.error||`Request failed (HTTP ${r.status})`);
  return d;
}
function toast(t){let e=$("toast");e.textContent=t;e.classList.add("show");setTimeout(()=>e.classList.remove("show"),2800)}
async function showApp(){ $("appShell").hidden=false; await loadDocs(); }
function esc(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
async function loadDocs(){S.docs=await api("/documents");$("docCount").textContent=S.docs.length;renderLists();if(S.active&&S.docs.some(x=>x.id===S.active.id))await openDoc(S.active.id);else showWelcome()}
function renderLists(){let list=S.docs.map(d=>`<button class="doc-item ${S.active?.id===d.id?"selected":""}" data-id="${d.id}">${esc(d.file_type.toUpperCase())}　${esc(d.original_name)}</button>`).join("");$("documentList").innerHTML=list||"Your documents will appear here.";$("documentList").querySelectorAll("[data-id]").forEach(b=>b.onclick=()=>openDoc(+b.dataset.id));$("recentGrid").innerHTML=S.docs.length?S.docs.slice(0,3).map(d=>`<button class="recent-doc" data-id="${d.id}"><span class="filetype">${d.file_type.toUpperCase()}</span><b>${esc(d.original_name)}</b><small>${d.page_count||"—"} pages / sections · ${d.chunk_count} searchable chunks</small></button>`).join(""):"No documents yet. Upload a file to begin.";$("recentGrid").querySelectorAll("[data-id]").forEach(b=>b.onclick=()=>openDoc(+b.dataset.id))}
function showWelcome(){$("welcomeView").hidden=false;$("readerView").hidden=true;$("crumbDoc").textContent="Overview";S.active=null;renderLists()}
async function openDoc(id){try{let d=await api(`/documents/${id}`);S.active=d;$("welcomeView").hidden=true;$("readerView").hidden=false;$("crumbDoc").textContent=d.original_name;$("activeDocName").textContent=d.original_name;$("activeDocMeta").textContent=`${new Date(d.created_at).toLocaleDateString()} · ${d.file_type.toUpperCase()}`;$("activeFileIcon").textContent=d.file_type.toUpperCase();$("docSummary").textContent=d.summary||"No overview available.";$("pageStat").textContent=d.page_count||"—";$("chunkStat").textContent=d.chunk_count||"—";$("topicTags").innerHTML=(d.topics||"").split(",").filter(Boolean).map(x=>`<span class="topic">${esc(x.trim())}</span>`).join("")||"No topics detected";$("answerArea").innerHTML="";let c=await api(`/documents/${id}/content`);$("documentPaper").innerHTML=c.pages.map((p,i)=>`<article class="paper-section"><h3>${esc(p.section||"Section "+(i+1))}${p.page?` · Page ${p.page}`:""}</h3><p>${esc(p.text)}</p></article>`).join("")||"No readable text found.";renderLists()}catch(e){toast(e.message)}}
$("uploadTrigger").onclick=$("welcomeUpload").onclick=()=>$("fileInput").click();
$("fileInput").onchange=async e=>{let f=e.target.files[0];if(!f)return;let fd=new FormData();fd.append("file",f);toast("Reading and indexing your document…");try{let d=await api("/documents/upload",{method:"POST",body:fd});toast("Document added to your library.");S.active=null;await loadDocs();await openDoc(d.id)}catch(x){toast(x.message)}e.target.value=""};
async function ask(q){q=(q||$("questionInput").value).trim();if(!q)return toast("Type a question first.");if(!S.active)return; $("askBtn").disabled=true;$("answerArea").innerHTML="<p>✦ Retrieving relevant passages and preparing your answer…</p>";try{let d=await api(`/documents/${S.active.id}/ask`,{method:"POST",body:JSON.stringify({question:q})});$("answerArea").innerHTML=`<div class="answer-box"><div class="answer-label">✦ DOCULENS ANSWER</div><div class="answer-text">${esc(d.answer)}</div></div><div class="evidence-title">SUPPORTING EVIDENCE · ${d.evidence.length} PASSAGES</div>${d.evidence.map(x=>`<div class="evidence"><b>${esc(x.location)} · ${esc(x.source)}</b><p>${esc(x.text)}</p></div>`).join("")}`}catch(e){$("answerArea").innerHTML=`<div class="answer-box">${esc(e.message)}</div>`}finally{$("askBtn").disabled=false}}
$("askBtn").onclick=()=>ask();$("questionInput").onkeydown=e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();ask()}};$("deleteDoc").onclick=async()=>{if(S.active&&confirm("Delete this document from your library?"))try{await api(`/documents/${S.active.id}`,{method:"DELETE"});S.active=null;await loadDocs();toast("Document deleted.")}catch(e){toast(e.message)}};
document.querySelectorAll(".suggestions button").forEach(b=>b.onclick=()=>ask(b.textContent));$("themeBtn").onclick=()=>document.body.classList.toggle("dark");
showApp().catch(e=>toast(e.message));
