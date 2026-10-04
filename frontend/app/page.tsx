"use client";

import { useMemo, useState } from "react";
import {
  Activity, BarChart3, Brain, CheckCircle2, ChevronRight, FileText, KeyRound,
  Image as ImageIcon, LayoutDashboard, Microscope, Settings, ShieldCheck,
  Stethoscope, Upload, UserRound, XCircle
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
      setResult(data.result ?? data.prediction);
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
          ["Dashboard", LayoutDashboard], ["Analyze Image", ImageIcon], ["Reports", FileText],
          ["Research", Microscope], ["Models", Activity], ["Analytics", BarChart3], ["API Keys", KeyRound]
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
        {page !== "Dashboard" && page !== "Analyze Image" && page !== "API Keys" && <ComingSoon title={page} />}
      </section>
    </main>
  );
}

function Dashboard({onAnalyze}: {onAnalyze: () => void}) {
  return <section>
    <div className="hero dashboardHero"><div><span className="pill">MODEL WORKSPACE</span><h2>Welcome to your medical AI workspace.</h2><p>Manage trained models, analyze images, review findings, and maintain research records from one place.</p><button className="primary" onClick={onAnalyze}>Start an analysis <ChevronRight size={18}/></button></div><div className="heroIcon"><Brain size={82}/></div></div>
    <div className="stats"><Stat icon={ImageIcon} label="Analyses" value="Ready" note="Upload to begin"/><Stat icon={ShieldCheck} label="Review workflow" value="Enabled" note="Human review supported"/><Stat icon={Activity} label="Model status" value="Connected" note="API ready"/><Stat icon={Microscope} label="Research" value="Active" note="Dataset pipeline available"/></div>
    <div className="lower"><div className="panel"><div className="panelHead"><div><b>Clinical workflow</b><span>Recommended next actions</span></div></div>{["Upload an X-ray or skin image","Run the trained model","Review confidence and class scores","Create a clinician-reviewed report"].map((x,i)=><div className="step" key={x}><span>{i+1}</span><div><b>{x}</b><small>{i === 3 ? "Final interpretation stays with the responsible clinician." : "Available in the workspace."}</small></div><ChevronRight size={17}/></div>)}</div><div className="panel"><div className="panelHead"><div><b>Safety status</b><span>Model governance</span></div></div><div className="safety"><CheckCircle2/><div><b>Research model pipeline</b><p>Training, evaluation and model provenance are tracked. Clinical validation is still required before diagnostic use.</p></div></div></div></div>
  </section>;
}
function Stat({icon: Icon,label,value,note}:{icon: LucideIcon,label:string,value:string,note:string}) { return <div className="stat"><Icon size={20}/><span>{label}</span><b>{value}</b><small>{note}</small></div>; }
function ComingSoon({title}:{title:string}) { return <div className="panel coming"><Brain size={42}/><h2>{title}</h2><p>This workspace is being connected to the same backend and trained-model registry.</p></div>; }


function APIKeys() {
  const [workspace, setWorkspace] = useState<"api" | "gateway">("gateway");
  const [adminKey, setAdminKey] = useState("");
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
      <input className="textInput" type="password" placeholder="Admin API-key secret" value={adminKey} onChange={e=>setAdminKey(e.target.value)} />
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
