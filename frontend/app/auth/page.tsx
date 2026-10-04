"use client";

import { useEffect, useState } from "react";
import { Building2, LogIn, UserPlus, Users, ShieldCheck, LogOut, RefreshCw } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type User = {
  id: number;
  email: string;
  full_name: string;
  role: string;
  organization: { id: number; name: string; slug: string };
};

type Member = {
  membership_id: number;
  user_id: number;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
};

export default function AuthPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [user, setUser] = useState<User | null>(null);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [members, setMembers] = useState<Member[]>([]);
  const [memberEmail, setMemberEmail] = useState("");
  const [memberName, setMemberName] = useState("");
  const [memberPassword, setMemberPassword] = useState("");
  const [memberRole, setMemberRole] = useState("staff");

  useEffect(() => {
    const token = localStorage.getItem("medai_access_token");
    if (!token) return;
    fetch(API_URL + "/api/v1/auth/me", { headers: { Authorization: "Bearer " + token } })
      .then(async r => r.ok ? setUser(await r.json()) : localStorage.removeItem("medai_access_token"))
      .catch(() => setMessage("Unable to reach the MedAI API"));
  }, []);

  async function submit() {
    setMessage("");
    const endpoint = mode === "login" ? "/api/v1/auth/login" : "/api/v1/auth/register";
    const body = mode === "login"
      ? { email, password }
      : { organization_name: organizationName, email, full_name: fullName, password };
    try {
      const r = await fetch(API_URL + endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail ?? "Authentication failed");
      localStorage.setItem("medai_access_token", data.access_token);
      setUser(data.user);
      setPassword("");
      setMessage(mode === "register" ? "Organization created and owner account signed in." : "Signed in successfully.");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Authentication failed");
    }
  }

  async function loadMembers() {
    const token = localStorage.getItem("medai_access_token");
    if (!token) return;
    const r = await fetch(API_URL + "/api/v1/auth/members", { headers: { Authorization: "Bearer " + token } });
    const data = await r.json();
    if (!r.ok) { setMessage(data.detail ?? "Unable to load members"); return; }
    setMembers(data);
  }

  async function addMember() {
    const token = localStorage.getItem("medai_access_token");
    if (!token) return;
    const r = await fetch(API_URL + "/api/v1/auth/members", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + token },
      body: JSON.stringify({ email: memberEmail, full_name: memberName, password: memberPassword, role: memberRole }),
    });
    const data = await r.json();
    if (!r.ok) { setMessage(data.detail ?? "Unable to add member"); return; }
    setMessage("Member created. Give the temporary password to the staff member securely.");
    setMemberEmail(""); setMemberName(""); setMemberPassword("");
    loadMembers();
  }

  function logout() {
    localStorage.removeItem("medai_access_token");
    setUser(null);
    setMembers([]);
  }

  if (user) {
    return (
      <main className="shell">
        <section className="content" style={{maxWidth: 1100, margin: "0 auto", width: "100%"}}>
          <header className="topbar">
            <div><span className="eyebrow">MEDAI ACCOUNT</span><h1>Organization</h1></div>
            <button className="secondary" onClick={logout}><LogOut size={16}/>Sign out</button>
          </header>
          <div className="hero">
            <div>
              <span className="pill">AUTHENTICATED</span>
              <h2>{user.organization.name}</h2>
              <p>{user.full_name} · {user.email} · <b>{user.role}</b></p>
              <p>Organization ID: {user.organization.id} · Slug: {user.organization.slug}</p>
            </div>
            <Building2 size={72}/>
          </div>
          <div className="analysisGrid">
            <div className="panel">
              <div className="panelHead"><div><b>Organization access</b><span>Role-based account foundation is active.</span></div><ShieldCheck size={20}/></div>
              <p className="docText">Owners and admins can manage organization members. Available roles include doctor, radiologist, dermatologist, researcher, nurse, staff and patient.</p>
              <button className="secondary full" onClick={loadMembers}><RefreshCw size={16}/>Load members</button>
            </div>
            {(user.role === "owner" || user.role === "admin") && <div className="panel">
              <div className="panelHead"><div><b>Add organization member</b><span>Create a real account with a role.</span></div><UserPlus size={20}/></div>
              <input className="textInput" placeholder="Full name" value={memberName} onChange={e=>setMemberName(e.target.value)}/>
              <input className="textInput" placeholder="Email" value={memberEmail} onChange={e=>setMemberEmail(e.target.value)}/>
              <input className="textInput" type="password" placeholder="Temporary password (8+ chars)" value={memberPassword} onChange={e=>setMemberPassword(e.target.value)}/>
              <select className="textInput" value={memberRole} onChange={e=>setMemberRole(e.target.value)}>
                <option value="doctor">Doctor</option><option value="radiologist">Radiologist</option><option value="dermatologist">Dermatologist</option>
                <option value="researcher">Researcher</option><option value="nurse">Nurse</option><option value="staff">Staff</option><option value="patient">Patient</option><option value="admin">Admin</option>
              </select>
              <button className="primary full" disabled={!memberName || !memberEmail || memberPassword.length < 8} onClick={addMember}><UserPlus size={16}/>Create member</button>
            </div>}
          </div>
          {(user.role === "owner" || user.role === "admin") && <div className="panel">
            <div className="panelHead"><div><b>Organization members</b><span>{members.length} loaded</span></div><Users size={20}/></div>
            {members.length === 0 ? <div className="empty"><Users size={34}/><b>No members loaded</b><span>Tap Load members.</span></div> :
              members.map(m => <div className="step" key={m.membership_id}><span>{m.user_id}</span><div><b>{m.full_name}</b><small>{m.email} · {m.role} · {m.is_active ? "active" : "inactive"}</small></div></div>)}
          </div>}
          {message && <div className="error">{message}</div>}
          <div className="notice"><b>Next:</b> the clinical records layer will be connected to this organization identity so hospitals cannot see another organization's patients, images or reports.</div>
        </section>
      </main>
    );
  }

  return (
    <main className="shell">
      <section className="content" style={{maxWidth: 720, margin: "0 auto", width: "100%"}}>
        <div className="hero">
          <div><span className="pill">MEDAI SECURE ACCESS</span><h2>{mode === "login" ? "Sign in to MedAI" : "Create your organization"}</h2><p>{mode === "login" ? "Use your MedAI organization account." : "Create the first organization owner account for your hospital, clinic or research team."}</p></div>
          <Building2 size={64}/>
        </div>
        <div className="panel">
          <div className="keyTabs">
            <button className={mode === "login" ? "selected" : ""} onClick={()=>{setMode("login");setMessage("")}}><LogIn size={16}/>Sign in</button>
            <button className={mode === "register" ? "selected" : ""} onClick={()=>{setMode("register");setMessage("")}}><UserPlus size={16}/>New organization</button>
          </div>
          {mode === "register" && <input className="textInput" placeholder="Hospital / clinic / research organization name" value={organizationName} onChange={e=>setOrganizationName(e.target.value)}/>}
          {mode === "register" && <input className="textInput" placeholder="Your full name" value={fullName} onChange={e=>setFullName(e.target.value)}/>}
          <input className="textInput" type="email" placeholder="Email address" value={email} onChange={e=>setEmail(e.target.value)}/>
          <input className="textInput" type="password" placeholder="Password (8+ characters)" value={password} onChange={e=>setPassword(e.target.value)}/>
          <button className="primary full" disabled={!email || password.length < 8 || (mode === "register" && (!organizationName || !fullName))} onClick={submit}>{mode === "login" ? "Sign in" : "Create organization and account"} <LogIn size={17}/></button>
          {message && <div className="error">{message}</div>}
        </div>
        <div className="notice"><b>Security:</b> authentication is backed by the MedAI database. This account system is separate from provider API keys and model-gateway credentials.</div>
      </section>
    </main>
  );
}
