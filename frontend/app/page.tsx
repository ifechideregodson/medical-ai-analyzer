"use client";

import { useMemo, useState } from "react";
import {
  Activity, BarChart3, Brain, CheckCircle2, ChevronRight, FileText,
  Image as ImageIcon, LayoutDashboard, Microscope, Settings, ShieldCheck,
  Stethoscope, Upload, UserRound, XCircle
} from "lucide-react";

type Mode = "xray" | "skin";
type Result = {
  label: string;
  confidence: number;
  all_scores: Record<string, number>;
  needs_review: boolean;
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
      const response = await fetch(`${API_URL}/api/v1/predict?image_type=${mode}`, { method: "POST", body: form });
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
    <main className="shell">
      <aside className="sidebar">
        <div className="brand"><div className="brandMark"><Brain size={21}/></div><div><strong>MedAI</strong><span>Clinical Analyzer</span></div></div>
        <div className="navLabel">WORKSPACE</div>
        {[
          ["Dashboard", LayoutDashboard], ["Analyze Image", ImageIcon], ["Reports", FileText],
          ["Research", Microscope], ["Models", Activity], ["Analytics", BarChart3]
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
        <header className="topbar"><div><span className="eyebrow">MEDICAL AI PLATFORM</span><h1>{page}</h1></div><div className="status"><span className="dot"/>AI service connected</div></header>

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
                    <button className="secondary full"><FileText size={17}/>Create clinical review report</button>
                  </div>}
              </div>
            </div>
          </section>
        )}
        {page !== "Dashboard" && page !== "Analyze Image" && <ComingSoon title={page} />}
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
