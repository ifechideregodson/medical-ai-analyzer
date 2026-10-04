"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Activity, BarChart3, Brain, CheckCircle2, ChevronRight, FileText, KeyRound,
  Image as ImageIcon, LayoutDashboard, Microscope, Settings, ShieldCheck,
  Stethoscope, Upload, UserRound, XCircle, Users, History, RefreshCw, Save, LogOut
} from "lucide-react";\nimport type { LucideIcon } from "lucide-react";

type Mode = "xray" | "skin";
type Result = {
  label: string;
  confidence: number;
  all_scores: Record<string, number>;
  needs_review: boolean;
  model_name?: string;
  model_source?: string;
  research_status?: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [mode, setMode] = useState<Mode>("xray");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string>("");
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [page, setPage] = useState("Dashboard");
  const [error, setError] = useState("");
  const [modelReady, setModelReady] = useState<boolean | null>(null);

  async function checkModel() {
    try {
      const response = await fetch(`${API_URL}/api/v1/models/readiness/${mode}`);
      setModelReady(response.ok);
    } catch {
      setModelReady(false);
    }
  }

  const confidence = useMemo(() => result ? Math.round(result.confidence * 100) : 0, [result]);

  function selectFile(next: File | null) {
    setFile(next);
    setResult(null);
    setError("");
    if (next) setPreview(URL.createObjectURL(next));
    else setPreview("");
  }

  async function analyze() {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("image_type", mode);\n      const response = await fetch("/api/analyze", { method: "POST", body: form });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Analysis failed");
      const finalResult = data.result ?? data.prediction; setResult(finalResult);\n      const admin = sessionStorage.getItem("medai_admin_secret");\n      if (admin) {\n        const saved = await fetch(`${API_URL}/api/v1/clinical/analyses`, { method:"POST", headers:{"Content-Type":"application/json","X-Admin-Key":admin}, body:JSON.stringify({image_type:mode,source_filename:file.name,finding:finalResult.label,confidence:finalResult.confidence,needs_review:finalResult.needs_review,model_name:finalResult.model_name,model_source:finalResult.model_source,research_status:finalResult.research_status ?? "research_only_not_clinically_validated"}) });\n        if (!saved.ok) { const sd = await saved.json(); setError(sd.detail ?? "AI result was returned but could not be saved"); }\n      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to reach the analysis service");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="shell" onLoad={checkModel}>
      <aside className="sidebar">
        <div className="brand"><div className="brandMark"><Brain size={21}/></div><div><strong>MedAI</strong><span>Clinical Analyzer</span></div></div>
        <div className="navLabel">WORKSPACE</div>
        {[
          ["Dashboard", LayoutDashboard], ["Patients", Users], ["Analyze Image", ImageIcon], ["Reports", FileText],
          ["Research", Microscope], ["Models", Activity], ["Analytics", BarChart3], ["Audit Trail", History], ["API Keys", KeyRound]
        ].map(([name, Icon]) => (
          <button key={name as string} className={`navItem ${page === name ? "active" : ""}`} onClick={() => setPage(name as string)}>
            <Icon size={18}/><span>{name as string}</span>
          </button>
        ))}
        <div className="sidebarBottom">
          <button className={`navItem ${page === "Settings" ? "active" : ""}`} onClick={() => setPage("Settings")}><Settings size={18}/><span>Settings</span></button>
          <div className="userCard"><div className="avatar"><UserRound size={18}/></div><div><b>Clinician</b><small>Research workspace</small></div></div>
        </div>
      </aside>

      <section className="content">
        <header className="topbar"><div><span className="eyebrow">MEDICAL AI PLATFORM</span><h1>{page}</h1></div><div className="status"><span className={`dot ${modelReady === false ? "offline" : ""}`}/>{modelReady === true ? "Trained model ready" : modelReady === false ? "Model unavailable" : "Checking model…"}</div></header>

        {page === "Dashboard" && <Dashboard onAnalyze={() => setPage("Analyze Image")} />}
        {page === "Analyze Image" && (
          <section>
            <div className="hero"><div><span className="pill">RESEARCH + CLINICAL DECISION SUPPORT</span><h2>Analyze medical images with your trained models.</h2><p>Upload an X-ray or dermatology image and review model findings, confidence, and review status.</p></div></div>
            <div className="analysisGrid">
              <div className="panel uploadPanel">
                <div className="panelHead"><div><b>New analysis</b><span>Select an imaging workflow</span></div><ShieldCheck size={20}/></div>
                <div className="modeTabs">
                  <button className={mode === "xray" ? "selected" : ""} onClick={() => setMode("xray")}><Stethoscope size={18}/>Chest X-ray</button>
                  <button className={mode === "skin" ? "selected" : ""} onClick={() => setMode("skin")}><Activity size={18}/>Skin image</button>
                </div>
                <label className={`dropzone ${file ? "hasFile" : ""}`}>
                  <input type="file" accept="image/png,image/jpeg,image/webp" onChange={e => selectFile(e.target.files?.[0] ?? null)}/>
                  {preview ? <img src={preview} alt="Selected medical image"/> : <><Upload size={30}/><b>Upload medical image</b><span>PNG, JPG or WEBP</span></>}
                </label>
                {file && <div className="fileRow"><ImageIcon size={17}/><span>{file.name}</span><button onClick={() => selectFile(null)}><XCircle size={18}/></button></div>}
                <button className="primary full" disabled={!file || busy} onClick={analyze}>{busy ? "Analyzing…" : "Run AI analysis"}<ChevronRight size={18}/></button>
                {error && <div className="error">{error}</div>}
                <p className="notice">Outputs are decision-support findings. They are not a standalone diagnosis and should be reviewed by a qualified clinician.</p>
              </div>

              <div className="panel resultPanel">
                <div className="panelHead"><div><b>Analysis result</b><span>Model output and review status</span></div><Brain size={20}/></div>
                {!result ? <div className="empty"><Brain size={34}/><b>No analysis yet</b><span>Upload an image and run the model to see results here.</span></div> :
                  <div className="result">
                    <div className="finding"><div><small>TOP MODEL FINDING</small><h3>{result.label}</h3></div><div className="confidence"><b>{confidence}%</b><span>confidence</span></div></div>
                    <div className={`review ${result.needs_review ? "warning" : "ok"}`}>{result.needs_review ? <><XCircle size={19}/><span>Clinician review recommended</span></> : <><CheckCircle2 size={19}/><span>Above review threshold</span></>}</div>
                    <div className="scoreList">{Object.entries(result.all_scores).map(([label, score]) => <div className="score" key={label}><div><span>{label}</span><b>{Math.round(score * 100)}%</b></div><div className="bar"><i style={{width: `${Math.round(score * 100)}%`}}/></div></div>)}</div>
                    <div className="meta"><span>Model</span><b>Active trained model</b><span>Workflow</span><b>{mode === "xray" ? "X-ray analysis" : "Skin analysis"}</b></div>
                    <div className="meta"><span>Model</span><b>{result.model_name ?? "Configured trained model"}</b><span>Source</span><b>{result.model_source ?? "API registry"}</b></div>
                    <button className="secondary full"><FileText size={17}/>Create clinical review report</button>
                  </div>}
              </div>
            </div>
          </section>
        )}
        {page === "API Keys" && <APIKeys />}
        {page === "Patients" && <PatientsWorkspace />}
        {page === "Reports" && <ReportsWorkspace />}
        {page === "Research" && <ResearchWorkspace />}
        {page === "Models" && <ModelsWorkspace />}
        {page === "Analytics" && <AnalyticsWorkspace />}
        {page === "Audit Trail" && <AuditWorkspace />}
        {page === "Settings" && <SettingsWorkspace />}
        {page !== "Dashboard" && page !== "Analyze Image" && page !== "API Keys" && page !== "Patients" && page !== "Reports" && page !== "Research" && page !== "Models" && page !== "Analytics" && page !== "Audit Trail" && page !== "Settings" && <ComingSoon title={page} />}
      </section>
    </main>
  );
}

function Dashboard({onAnalyze}: {onAnalyze: () => void}) {
  const [stats,setStats]=useState<any>(null);
  const [error,setError]=useState("");
  const load=async()=>{const key=getAdminSecret();if(!key)return;try{const r=await clinicalRequest("/api/v1/clinical/analytics");const d=await r.json();if(!r.ok)throw new Error(d.detail||"Unable to load metrics");setStats(d)}catch(e){setError(e instanceof Error?e.message:"Unable to load metrics")}};
  useEffect(()=>{load()},[]);
  return <section>
    <div className="hero dashboardHero"><div><span className="pill">LIVE CLINICAL WORKSPACE</span><h2>Your medical AI operations are connected to persistent records.</h2><p>Analyze images, review findings, create reports, manage research records and inspect the audit trail from one application.</p><button className="primary" onClick={onAnalyze}>Start an analysis <ChevronRight size={18}/></button></div><div className="heroIcon"><Brain size={82}/></div></div>
    <div className="stats"><Stat icon={Users} label="Patients" value={stats?.patients??"—"} note="Database records"/><Stat icon={ImageIcon} label="Analyses" value={stats?.analyses??"—"} note={stats?(stats.pending_reviews+" pending review"):"Connect admin session"}/><Stat icon={FileText} label="Reports" value={stats?.reports??"—"} note={stats?(stats.signed_reports+" signed"):"Connect admin session"}/><Stat icon={Microscope} label="Research" value={stats?.research_records??"—"} note="Saved studies"/></div>
    <div className="lower"><div className="panel"><div className="panelHead"><div><b>Clinical workflow</b><span>Each step now writes to the backend</span></div><ClipboardCheck size={20}/></div>{["Create a patient reference","Run the trained X-ray or skin model","Review and annotate the AI finding","Draft and sign a report","Inspect the audit trail"].map((x,i)=><div className="step" key={x}><span>{i+1}</span><div><b>{x}</b><small>Live workspace functionality.</small></div><ChevronRight size={17}/></div>)}</div><div className="panel"><div className="panelHead"><div><b>Model governance</b><span>Research status</span></div><ShieldCheck size={20}/></div><div className="safety"><ShieldCheck/><div><b>Research / decision support</b><p>Inference, provenance, review state and audit events are recorded. Current models are not clinically validated for standalone diagnosis.</p></div></div>{error&&<div className="error">{error}</div>}</div></div>
  </section>;
}
function Stat({icon: Icon,label,value,note}:{icon: LucideIcon,label:string,value:string,note:string}) { return <div className="stat"><Icon size={20}/><span>{label}</span><b>{value}</b><small>{note}</small></div>; }
function ComingSoon({title}:{title:string}) { return <div className="panel coming"><Brain size={42}/><h2>{title}</h2><p>This workspace is being connected to the same backend and trained-model registry.</p></div>; }


function APIKeys() {
  const [workspace, setWorkspace] = useState<"api" | "gateway">("gateway");
  const [adminKey, setAdminKey] = useState("");
  useEffect(() => { const key = sessionStorage.getItem("medai_admin_secret"); if (key) setAdminKey(key); }, []);
  return <section>
    <div className="hero">
      <div>
        <span className="pill">DEVELOPER ACCESS</span>
        <h2>{workspace === "gateway" ? "Model Gateway keys" : "API keys"}</h2>
        <p>{workspace === "gateway"
          ? "Issue secure MODEL_GATEWAY_API_KEY credentials for approved applications. The complete secret is revealed only once."
          : "Issue keys for approved applications and developers that need to connect to the MedAI inference API."}</p>
      </div>
      <KeyRound size={72}/>
    </div>
    <div className="keyTabs">
      <button className={workspace === "gateway" ? "selected" : ""} onClick={() => setWorkspace("gateway")}>MODEL_GATEWAY_API_KEY</button>
      <button className={workspace === "api" ? "selected" : ""} onClick={() => setWorkspace("api")}>Standard API keys</button>
    </div>
    <div className="panel adminPanel">
      <div className="panelHead"><div><b>Administrator access</b><span>Required to issue, list or revoke credentials. The admin secret stays in this browser session only.</span></div><ShieldCheck size={20}/></div>
      <input className="textInput" type="password" placeholder="Admin API-key secret" value={adminKey} onChange={e=>{setAdminKey(e.target.value);sessionStorage.setItem("medai_admin_secret",e.target.value)}} />
    </div>
    {workspace === "gateway"
      ? <ModelGatewayWorkspace adminKey={adminKey}/>
      : <StandardAPIWorkspace adminKey={adminKey}/>}
  </section>;
}

function ModelGatewayWorkspace({adminKey}:{adminKey:string}) {
  const [name, setName] = useState("");
  const [owner, setOwner] = useState("");
  const [keys, setKeys] = useState<Array<{id:number;name:string;owner:string;key_prefix:string;created_at:string;is_active:boolean}>>([]);
  const [newKey, setNewKey] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function loadKeys() {
    if (!adminKey) return;
    setBusy(true); setMessage("");
    try {
      const r = await fetch(`${API_URL}/api/v1/model-gateway/keys`, {headers: {"X-Admin-Key": adminKey}});
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail ?? "Unable to load gateway keys");
      setKeys(data);
    } catch (e) { setMessage(e instanceof Error ? e.message : "Unable to load gateway keys"); }
    finally { setBusy(false); }
  }

  async function createKey() {
    setBusy(true); setMessage(""); setNewKey("");
    try {
      const r = await fetch(`${API_URL}/api/v1/model-gateway/keys`, {
        method: "POST",
        headers: {"Content-Type":"application/json", "X-Admin-Key": adminKey},
        body: JSON.stringify({name, owner})
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail ?? "Unable to create MODEL_GATEWAY_API_KEY");
      setNewKey(data.model_gateway_api_key);
      setName(""); setOwner("");
      await loadKeys();
    } catch (e) { setMessage(e instanceof Error ? e.message : "Unable to create gateway key"); }
    finally { setBusy(false); }
  }

  async function revoke(id:number) {
    if (!confirm("Revoke this MODEL_GATEWAY_API_KEY? Applications using it will stop authenticating.")) return;
    const r = await fetch(`${API_URL}/api/v1/model-gateway/keys/${id}`, {method:"DELETE", headers:{"X-Admin-Key":adminKey}});
    if (r.ok) await loadKeys(); else setMessage((await r.json()).detail ?? "Unable to revoke key");
  }

  return <div className="analysisGrid">
    <div className="panel">
      <div className="panelHead"><div><b>Issue MODEL_GATEWAY_API_KEY</b><span>Generate a unique secret for an application or approved developer.</span></div><KeyRound size={20}/></div>
      <input className="textInput" placeholder="Application / organization name" value={name} onChange={e=>setName(e.target.value)} />
      <input className="textInput" placeholder="Owner email or identifier" value={owner} onChange={e=>setOwner(e.target.value)} />
      <button className="primary full" onClick={createKey} disabled={!adminKey || !name || !owner || busy}>{busy ? "Generating…" : "Generate MODEL_GATEWAY_API_KEY"}</button>
      {newKey && <div className="gatewaySecret"><b>Copy this now — it will never be shown again:</b><code>{newKey}</code><small>Environment variable format:</small><code>MODEL_GATEWAY_API_KEY={newKey}</code></div>}
      {message && <div className="error">{message}</div>}
      <p className="notice">The website generates the credential; it does not create an OpenAI, Anthropic, or other provider secret. Provider API keys remain private server-side credentials.</p>
    </div>
    <div className="panel">
      <div className="panelHead"><div><b>Issued gateway keys</b><span>Only prefixes are retained for display after creation.</span></div><button className="secondary" onClick={loadKeys} disabled={!adminKey || busy}>Refresh</button></div>
      {!keys.length ? <div className="empty"><KeyRound size={34}/><b>No gateway keys loaded</b><span>Enter the administrator secret, then tap Refresh.</span></div> :
        keys.map(k=><div className="step" key={k.id}><span>{k.is_active ? "✓" : "×"}</span><div><b>{k.name}</b><small>{k.owner} · {k.key_prefix} · {k.is_active ? "Active" : "Revoked"}</small></div>{k.is_active && <button className="secondary" onClick={()=>revoke(k.id)}>Revoke</button>}</div>)}
    </div>
  </div>;
}

function StandardAPIWorkspace({adminKey}:{adminKey:string}) {
  const [name,setName]=useState(""),[owner,setOwner]=useState(""),[newKey,setNewKey]=useState(""),[message,setMessage]=useState("");
  async function createKey(){
    try{
      const r=await fetch(`${API_URL}/api/v1/api-keys`,{method:"POST",headers:{"Content-Type":"application/json","X-Admin-Key":adminKey},body:JSON.stringify({name,owner})});
      const d=await r.json(); if(!r.ok) throw new Error(d.detail??"Unable to create API key"); setNewKey(d.api_key); setName("");setOwner("");
    }catch(e){setMessage(e instanceof Error?e.message:"Unable to create API key")}
  }
  return <div className="panel"><div className="panelHead"><div><b>Create standard API key</b><span>For inference API access. The full secret is displayed only once.</span></div></div>
    <div className="analysisGrid">
      <input className="textInput" placeholder="Application / organization name" value={name} onChange={e=>setName(e.target.value)}/>
      <input className="textInput" placeholder="Owner email or identifier" value={owner} onChange={e=>setOwner(e.target.value)}/>
    </div>
    <button className="primary full" onClick={createKey} disabled={!adminKey||!name||!owner}>Generate API key</button>
    {newKey&&<div className="notice"><b>Copy this key now:</b><br/><code>{newKey}</code></div>}
    {message&&<div className="error">{message}</div>}
  </div>;
}

function APIDocs() {
  return <section>
    <div className="hero"><div><span className="pill">DEVELOPER API</span><h2>Connect your application to MedAI.</h2><p>Use a generated API key to submit X-ray or skin images to the inference API. Keep keys on your server and never expose them in browser code.</p></div><KeyRound size={72}/></div>
    <div className="docsGrid">
      <div className="panel">
        <div className="panelHead"><div><b>Authentication</b><span>Every inference request requires X-API-Key.</span></div><ShieldCheck size={20}/></div>
        <p className="docText">Generate a key from the API Keys workspace. The complete secret is shown only once. Store it in your server environment as a secret.</p>
        <pre className="codeBlock"><code>{`X-API-Key: medai_your_secret_key`}</code></pre>
      </div>
      <div className="panel">
        <div className="panelHead"><div><b>POST /api/v1/predict</b><span>Analyze an X-ray or skin image.</span></div><Brain size={20}/></div>
        <pre className="codeBlock"><code>{`curl -X POST \\\n  "https://medical-ai-api.onrender.com/api/v1/predict?image_type=xray" \\\n  -H "X-API-Key: medai_your_secret_key" \\\n  -F "file=@xray.jpg"`}</code></pre>
      </div>
      <div className="panel">
        <div className="panelHead"><div><b>Skin example</b><span>Use image_type=skin for dermatology images.</span></div></div>
        <pre className="codeBlock"><code>{`curl -X POST \\\n  "https://medical-ai-api.onrender.com/api/v1/predict?image_type=skin" \\\n  -H "X-API-Key: medai_your_secret_key" \\\n  -F "file=@skin.jpg"`}</code></pre>
      </div>
      <div className="panel">
        <div className="panelHead"><div><b>Response</b><span>Finding, scores, model provenance and review status.</span></div></div>
        <pre className="codeBlock"><code>{`{
  "status": "ok",
  "image_type": "xray",
  "result": {
    "label": "pneumonia",
    "confidence": 0.91,
    "needs_review": false,
    "model_name": "...",
    "model_source": "...",
    "research_status": "research_only_not_clinically_validated"
  }
}`}</code></pre>
      </div>
    </div>
    <div className="notice"><b>Important:</b> MedAI's current models are research/decision-support models and are not clinically validated for standalone diagnosis. Integrations must keep a qualified clinician in the review workflow.</div>
  </section>;
}


function getAdminSecret(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem("medai_admin_secret") || "";
}
async function clinicalRequest(path: string, init: RequestInit = {}) {
  const key = getAdminSecret();
  const headers = new Headers(init.headers);
  headers.set("X-Admin-Key", key);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  return fetch(API_URL + path, { ...init, headers });
}
function AdminGate({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(Boolean(getAdminSecret())), []);
  if (!ready) return <div className="panel coming"><ShieldCheck size={42}/><h2>Administrator access required</h2><p>Open API Keys, enter API_KEY_ADMIN_SECRET, and keep the session active. The secret is not committed to the application.</p></div>;
  return <>{children}</>;
}

function PatientsWorkspace() {
  const [patients,setPatients]=useState<any[]>([]),[ref,setRef]=useState(""),[name,setName]=useState(""),[sex,setSex]=useState(""),[dob,setDob]=useState(""),[notes,setNotes]=useState(""),[msg,setMsg]=useState("");
  const load=async()=>{const r=await clinicalRequest("/api/v1/clinical/patients");const d=await r.json();if(r.ok)setPatients(d);else setMsg(d.detail||"Unable to load patients")};
  useEffect(()=>{load()},[]);
  const create=async()=>{const r=await clinicalRequest("/api/v1/clinical/patients",{method:"POST",body:JSON.stringify({patient_ref:ref,name,date_of_birth:dob||null,sex:sex||null,notes:notes||null})});const d=await r.json();if(!r.ok){setMsg(d.detail||"Unable to create patient");return}setRef("");setName("");setSex("");setDob("");setNotes("");setMsg("Patient created");load()};
  return <AdminGate><section><div className="hero"><span className="pill">CLINICAL RECORDS</span><h2>Patient management is now connected.</h2><p>Create persistent patient references and link analyses and reports to them.</p></div><div className="analysisGrid"><div className="panel"><div className="panelHead"><div><b>New patient</b><span>Store only information appropriate for your deployment.</span></div><Users size={20}/></div><input className="textInput" placeholder="Patient reference" value={ref} onChange={e=>setRef(e.target.value)}/><input className="textInput" placeholder="Patient name" value={name} onChange={e=>setName(e.target.value)}/><div className="analysisGrid"><input className="textInput" placeholder="Date of birth" value={dob} onChange={e=>setDob(e.target.value)}/><input className="textInput" placeholder="Sex" value={sex} onChange={e=>setSex(e.target.value)}/></div><textarea className="textInput" placeholder="Notes" value={notes} onChange={e=>setNotes(e.target.value)}/><button className="primary full" disabled={!ref||!name} onClick={create}><Save size={16}/>Create patient</button>{msg&&<div className="error">{msg}</div>}</div><div className="panel"><div className="panelHead"><div><b>Saved patients</b><span>{patients.length} records</span></div><button className="secondary" onClick={load}><RefreshCw size={16}/>Refresh</button></div>{patients.length===0?<div className="empty"><Users size={34}/><b>No patients</b><span>Create the first persistent patient record.</span></div>:patients.map(p=><div className="step" key={p.id}><span>{p.id}</span><div><b>{p.name}</b><small>{p.patient_ref} · {p.sex||"sex not recorded"} · {p.date_of_birth||"DOB not recorded"}</small></div></div>)}</div></div></section></AdminGate>;
}

function ReportsWorkspace() {
  const [reports,setReports]=useState<any[]>([]),[analyses,setAnalyses]=useState<any[]>([]),[analysisId,setAnalysisId]=useState(""),[title,setTitle]=useState(""),[findings,setFindings]=useState(""),[impression,setImpression]=useState(""),[author,setAuthor]=useState(""),[msg,setMsg]=useState("");
  const load=async()=>{const [rr,ar]=await Promise.all([clinicalRequest("/api/v1/clinical/reports"),clinicalRequest("/api/v1/clinical/analyses")]);const rd=await rr.json(),ad=await ar.json();if(rr.ok)setReports(rd);if(ar.ok)setAnalyses(ad)};
  useEffect(()=>{load()},[]);
  const create=async()=>{const r=await clinicalRequest("/api/v1/clinical/reports",{method:"POST",body:JSON.stringify({analysis_id:Number(analysisId),title,findings,impression,author})});const d=await r.json();if(!r.ok){setMsg(d.detail||"Unable to create report");return}setTitle("");setFindings("");setImpression("");load()};
  const sign=async(id:number)=>{const signer=window.prompt("Clinician name for signature");if(!signer)return;const r=await clinicalRequest("/api/v1/clinical/reports/"+id+"/sign",{method:"POST",body:JSON.stringify({signer})});if(!r.ok){const d=await r.json();setMsg(d.detail||"Unable to sign report")}load()};
  return <AdminGate><section><div className="hero"><span className="pill">REPORTING</span><h2>Clinical reports are persistent and signable.</h2><p>Draft reports from stored analyses, then sign them. Signed reports are immutable.</p></div><div className="analysisGrid"><div className="panel"><div className="panelHead"><div><b>Create report</b><span>Every report links to an analysis.</span></div><FileText size={20}/></div><select className="textInput" value={analysisId} onChange={e=>setAnalysisId(e.target.value)}><option value="">Select analysis</option>{analyses.map(a=><option key={a.id} value={a.id}>#{a.id} · {a.image_type} · {a.finding}</option>)}</select><input className="textInput" placeholder="Report title" value={title} onChange={e=>setTitle(e.target.value)}/><input className="textInput" placeholder="Author" value={author} onChange={e=>setAuthor(e.target.value)}/><textarea className="textInput" placeholder="Findings" value={findings} onChange={e=>setFindings(e.target.value)}/><textarea className="textInput" placeholder="Impression" value={impression} onChange={e=>setImpression(e.target.value)}/><button className="primary full" disabled={!analysisId||!title||!author||!findings||!impression} onClick={create}><Save size={16}/>Save draft report</button>{msg&&<div className="error">{msg}</div>}</div><div className="panel"><div className="panelHead"><div><b>Reports</b><span>{reports.length} saved</span></div><button className="secondary" onClick={load}><RefreshCw size={16}/>Refresh</button></div>{reports.length===0?<div className="empty"><FileText size={34}/><b>No reports</b><span>Create a report after an analysis.</span></div>:reports.map(r=><div className="reportCard" key={r.id}><div className="reportHead"><div><b>{r.title}</b><small>Report #{r.id} · Analysis #{r.analysis_id} · {r.author}</small></div><span className={"badge "+r.status}>{r.status}</span></div><p><b>Findings:</b> {r.findings}</p><p><b>Impression:</b> {r.impression}</p>{r.status==="draft"&&<button className="secondary" onClick={()=>sign(r.id)}>Sign report</button>}{r.status==="signed"&&<small>Signed by {r.signed_by} on {new Date(r.signed_at).toLocaleString()}</small>}</div>)}</div></div></section></AdminGate>;
}

function ResearchWorkspace() {
  const [items,setItems]=useState<any[]>([]),[title,setTitle]=useState(""),[dataset,setDataset]=useState(""),[model,setModel]=useState(""),[hypothesis,setHypothesis]=useState(""),[metrics,setMetrics]=useState(""),[owner,setOwner]=useState(""),[msg,setMsg]=useState("");
  const load=async()=>{const r=await clinicalRequest("/api/v1/clinical/research");const d=await r.json();if(r.ok)setItems(d);else setMsg(d.detail||"Unable to load research")};
  useEffect(()=>{load()},[]);
  const create=async()=>{const r=await clinicalRequest("/api/v1/clinical/research",{method:"POST",body:JSON.stringify({title,dataset:dataset||null,model_name:model||null,hypothesis:hypothesis||null,metric_summary:metrics||null,status:"draft",owner})});const d=await r.json();if(!r.ok){setMsg(d.detail||"Unable to save research");return}setTitle("");setDataset("");setModel("");setHypothesis("");setMetrics("");load()};
  return <AdminGate><section><div className="hero"><span className="pill">RESEARCH REGISTRY</span><h2>Research records are stored in the database.</h2><p>Save study metadata, datasets, hypotheses, models and evaluation summaries instead of showing a placeholder page.</p></div><div className="analysisGrid"><div className="panel"><div className="panelHead"><div><b>New research record</b><span>Persistent experiment metadata.</span></div><Microscope size={20}/></div><input className="textInput" placeholder="Study title" value={title} onChange={e=>setTitle(e.target.value)}/><input className="textInput" placeholder="Dataset" value={dataset} onChange={e=>setDataset(e.target.value)}/><input className="textInput" placeholder="Model / experiment" value={model} onChange={e=>setModel(e.target.value)}/><textarea className="textInput" placeholder="Hypothesis" value={hypothesis} onChange={e=>setHypothesis(e.target.value)}/><textarea className="textInput" placeholder="Metrics / evaluation summary" value={metrics} onChange={e=>setMetrics(e.target.value)}/><input className="textInput" placeholder="Owner" value={owner} onChange={e=>setOwner(e.target.value)}/><button className="primary full" disabled={!title||!owner} onClick={create}><Save size={16}/>Save research record</button>{msg&&<div className="error">{msg}</div>}</div><div className="panel"><div className="panelHead"><div><b>Research registry</b><span>{items.length} saved</span></div><button className="secondary" onClick={load}><RefreshCw size={16}/>Refresh</button></div>{items.length===0?<div className="empty"><Microscope size={34}/><b>No research records</b><span>Save the first research project.</span></div>:items.map(x=><div className="reportCard" key={x.id}><div className="reportHead"><div><b>{x.title}</b><small>{x.owner} · {x.status}</small></div><span className="badge">{x.id}</span></div><p><b>Dataset:</b> {x.dataset||"—"} · <b>Model:</b> {x.model_name||"—"}</p><p>{x.hypothesis||"No hypothesis recorded."}</p><small>{x.metric_summary||"No evaluation summary recorded."}</small></div>)}</div></div></section></AdminGate>;
}

function ModelsWorkspace() {
  const [models,setModels]=useState<any[]>([]),[msg,setMsg]=useState("");
  const load=async()=>{const r=await fetch(API_URL+"/api/v1/models/list");const d=await r.json();if(r.ok)setModels(d.models||[]);else setMsg(d.detail||"Unable to load models")};
  useEffect(()=>{load()},[]);
  const activate=async(name:string)=>{const r=await fetch(API_URL+"/api/v1/models/activate",{method:"POST",headers:{"Content-Type":"application/json","X-Admin-Key":getAdminSecret()},body:JSON.stringify({model_name:name})});const d=await r.json();if(!r.ok)setMsg(d.detail||"Unable to activate model");else load()};
  return <section><div className="hero"><span className="pill">MODEL REGISTRY</span><h2>Model management is connected to the real registry.</h2><p>Inspect registry models and activate an uploaded model for its image type. Configured release models remain available through the readiness service.</p></div><div className="panel"><div className="panelHead"><div><b>Registered models</b><span>{models.length} registry records</span></div><button className="secondary" onClick={load}><RefreshCw size={16}/>Refresh</button></div>{models.length===0?<div className="empty"><Activity size={34}/><b>No local registry models</b><span>Training releases are loaded through the configured model URLs. Uploaded registry models will appear here.</span></div>:models.map(m=><div className="modelRow" key={m.model_name}><div><b>{m.model_name}</b><small>{m.image_type} · {m.labels?.join(", ")} · {m.file_size} bytes</small></div><span className={"badge "+(m.is_active?"active":"draft")}>{m.is_active?"active":"inactive"}</span>{!m.is_active&&<button className="secondary" onClick={()=>activate(m.model_name)}>Activate</button>}</div>)}{msg&&<div className="error">{msg}</div>}</div><div className="notice"><b>Safety:</b> registry controls do not mean a model is clinically validated.</div></section>;
}

function AnalyticsWorkspace() {
  const [data,setData]=useState<any>(null),[msg,setMsg]=useState("");
  const load=async()=>{const r=await clinicalRequest("/api/v1/clinical/analytics");const d=await r.json();if(r.ok)setData(d);else setMsg(d.detail||"Unable to load analytics")};
  useEffect(()=>{load()},[]);
  return <AdminGate><section><div className="hero"><span className="pill">LIVE ANALYTICS</span><h2>Analytics are calculated from persisted clinical records.</h2><p>No hard-coded dashboard numbers: these values come from the database.</p></div><div className="stats"><Stat icon={Users} label="Patients" value={data?.patients??"—"} note="database count"/><Stat icon={ImageIcon} label="Analyses" value={data?.analyses??"—"} note={(data?.reviewed_analyses??0)+" reviewed"}/><Stat icon={FileText} label="Reports" value={data?.reports??"—"} note={(data?.signed_reports??0)+" signed"}/><Stat icon={Brain} label="Avg confidence" value={data?Math.round(data.average_confidence*100)+"%":"—"} note="recorded analyses"/></div><div className="panel"><div className="panelHead"><div><b>Operational totals</b><span>Current database snapshot</span></div><button className="secondary" onClick={load}><RefreshCw size={16}/>Refresh</button></div><div className="metricsGrid"><div className="metric"><span>Pending reviews</span><b>{data?.pending_reviews??"—"}</b></div><div className="metric"><span>Research records</span><b>{data?.research_records??"—"}</b></div><div className="metric"><span>Audit events</span><b>{data?.audit_events??"—"}</b></div></div>{msg&&<div className="error">{msg}</div>}</div></section></AdminGate>;
}

function AuditWorkspace() {
  const [events,setEvents]=useState<any[]>([]),[msg,setMsg]=useState("");
  const load=async()=>{const r=await clinicalRequest("/api/v1/clinical/audit?limit=200");const d=await r.json();if(r.ok)setEvents(d);else setMsg(d.detail||"Unable to load audit trail")};
  useEffect(()=>{load()},[]);
  return <AdminGate><section><div className="hero"><span className="pill">AUDIT TRAIL</span><h2>Workflow events are recorded.</h2><p>Patient, analysis, review, report and research changes are timestamped with an actor and entity.</p></div><div className="panel"><div className="panelHead"><div><b>Recent events</b><span>{events.length} loaded</span></div><button className="secondary" onClick={load}><RefreshCw size={16}/>Refresh</button></div>{events.length===0?<div className="empty"><History size={34}/><b>No events yet</b><span>Use the clinical workflow and events will appear here.</span></div>:events.map(e=><div className="auditRow" key={e.id}><span>{new Date(e.created_at).toLocaleString()}</span><b>{e.event_type}</b><span>{e.entity_type} #{e.entity_id||"—"}</span><span>{e.actor}</span><small>{e.details||""}</small></div>)}{msg&&<div className="error">{msg}</div>}</div></section></AdminGate>;
}

function SettingsWorkspace() {
  const [health,setHealth]=useState<any>(null),[msg,setMsg]=useState("");
  const check=async()=>{try{const r=await fetch(API_URL+"/health");const d=await r.json();if(!r.ok)throw new Error("API unavailable");setHealth(d)}catch(e){setMsg(e instanceof Error?e.message:"API unavailable")}};
  useEffect(()=>{check()},[]);
  const clear=()=>{sessionStorage.removeItem("medai_admin_secret");window.location.reload()};
  return <section><div className="hero"><span className="pill">SETTINGS</span><h2>System settings and live service status.</h2><p>The settings workspace now reports the actual backend health state and browser administrator session.</p></div><div className="analysisGrid"><div className="panel"><div className="panelHead"><div><b>Administrator session</b><span>Credentials stay in this browser session.</span></div><Settings size={20}/></div><p className="docText">{getAdminSecret()?"Administrator session is active.":"No administrator session is active. Use API Keys to connect."}</p><button className="secondary full" onClick={clear}><LogOut size={16}/>Clear administrator session</button></div><div className="panel"><div className="panelHead"><div><b>Backend health</b><span>Live request to FastAPI.</span></div><Activity size={20}/></div>{health?<div className="safety"><CheckCircle2/><div><b>API online</b><p>{health.app} · version {health.version} · {health.environment}</p></div></div>:<div className="error">{msg||"Checking API…"}</div>}<button className="secondary full" onClick={check}><RefreshCw size={16}/>Check again</button></div></div><div className="panel"><div className="panelHead"><div><b>Clinical safety</b><span>Deployment requirements</span></div><ShieldCheck size={20}/></div><p className="docText">The current models remain research/decision-support models and are not clinically validated for standalone diagnosis. Before real patient deployment, implement jurisdiction-appropriate identity, access control, consent, retention, encryption, backup and clinical validation processes.</p></div></section>;
}
