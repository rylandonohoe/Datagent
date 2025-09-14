import React, { useState, useCallback, useMemo, useEffect, useRef } from "react";
import ReactFlow, {
  addEdge,
  MarkerType,
  useEdgesState,
  useNodesState,
} from "reactflow";
// v11 split packages:
import { Background, BackgroundVariant } from "@reactflow/background";
import { Controls } from "@reactflow/controls";
import { MiniMap } from "@reactflow/minimap";
import "reactflow/dist/style.css";
import type { Edge, Node, Connection, ReactFlowInstance } from "reactflow";
import { getNodesBounds, getViewportForBounds } from "reactflow";

/**
 * Datagent — One‑page React Frontend (Hackathon MVP)
 * --------------------------------------------------
 * Single-file React app that implements your entire GUI vision:
 * - Login → One-page App with collapsible sidebar (projects, integrations, profile)
 * - Project creation (name + description = global context)
 * - Canvas editor (React Flow) with 4 node types: Input, Process, Visualize, Output
 * - Node rules: input→(process|visualize|output), process→(process|visualize|output), visualize→output
 * - Node modals:
 *    • Input: choose source type + config (CSV, Google Sheet, S3 path, Yahoo Finance)
 *    • Process: LLM chat (mock), dynamic goals bullets, preview (fake→real after run)
 *    • Visualize: LLM chat (mock), choose chart/text/table, preview thumbnail
 *    • Output: choose destination (Email, Slack, GDrive) + per-node schedule (cron or preset)
 * - Execution bar (top-right): run now; schedules overview; export JSON
 * - Pretty UI with Tailwind classes, status badges, icons (emoji for simplicity)
 * - All data local/in-memory; replace stubs with real APIs later
 */

// --------------------------- Types ---------------------------

type BlockType = "input" | "process" | "visualize" | "output";

type Account = {
  id: string;
  kind: "aws" | "gmail" | "outlook" | "gdrive" | "slack" | "yahoo" | "custom";
  label: string;
};

type User = {
  firstName: string;
  lastName: string;
  email: string;
  password?: string; // in-memory only for demo/profile edits
};

type Project = {
  id: string;
  name: string;
  description: string; // global context for the agent
  nodes: Node<NodeData>[];
  edges: Edge[];
};

type InputSourceKind = "csv" | "google_sheet" | "s3" | "yahoo_finance";

// minimal, extensible config payloads per source kind
interface InputConfigBase { kind: InputSourceKind }
interface CSVConfig extends InputConfigBase { path?: string; delimiter?: string; }
interface SheetConfig extends InputConfigBase { sheet?: string; range?: string; }
interface S3Config extends InputConfigBase { bucket?: string; prefix?: string; pattern?: string; }
interface YahooConfig extends InputConfigBase { tickers?: string; interval?: "1d" | "1h" | "1m" }

type InputConfig = CSVConfig | SheetConfig | S3Config | YahooConfig;

type ConversationTurn = { role: "user" | "assistant"; content: string };

type Destination = { kind: "email" | "slack" | "gdrive"; config: Record<string, any> };

type NodeData = {
  type: BlockType;
  title: string;
  status?: "empty" | "configured" | "ready" | "queued" | "running" | "done" | "error";
  // Input
  input?: { source: InputConfig; boundAccountId?: string };
  // Process / Visualize
  convo?: ConversationTurn[];
  goals?: string[];
  preview?: { kind: "table" | "chart" | "text"; payload: any; updatedAt?: number };
  // Output
  destination?: Destination;
  schedule?: string | null; // cron or preset id
  // Meta
  tokenCost?: number; // for sustainability UI
  co2Grams?: number;
};

// Icon helpers (emoji for zero-dependency aesthetics)
const ICONS = {
  input: "📥",
  process: "🛠️",
  visualize: "📊",
  output: "📤",
  aws: "☁️",
  gmail: "📧",
  outlook: "📨",
  gdrive: "🟩",
  slack: "💬",
  yahoo: "💹",
  custom: "🔌",
};

// Token→CO2 rough demo estimate
const estimateCO2 = (tokens: number) => Math.round(tokens * 0.0002 * 1000) / 1000; // grams

// --------------------------- Root App ---------------------------

export default function DatagentApp() {
  const [user, setUser] = useState<User | null>(null);

  return (
    <div className="h-screen w-screen bg-zinc-100 overflow-hidden">
      {!user ? (
        <Login onSuccess={(u)=> setUser(u)} />
      ) : (
        <Studio user={user} setUser={setUser} />)
      }
    </div>
  );
}

// --------------------------- Login ---------------------------
function Login({ onSuccess }: { onSuccess: (u: User) => void }) {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [pwd, setPwd] = useState("");
  const [pwd2, setPwd2] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  return (
    <div
      className="h-full grid place-items-center"
      style={{
        backgroundImage: "radial-gradient(rgba(98, 80, 165, 0.15) 1.5px, transparent 1px)",
        backgroundSize: "16px 16px",
        backgroundPosition: "-1px -1px",
      }}
    >
      <div className="w-[520px] rounded-2xl bg-white shadow-lg border p-6">
        <div className="flex w-full items-center justify-center gap-2 mb-4">
          <Logo size={72} />
          <div className="font-semibold leading-none text-[#000000] mt-[5.3px]" style={{ fontSize: "42px" }}>Datagent</div>
        </div>
        <div className="grid grid-cols-2 rounded-xl bg-zinc-100 p-1 text-sm mb-4">
          <button onClick={() => setMode("login")} className={`py-2 rounded-lg ${mode==="login"?"bg-white shadow":""}`}>Log in</button>
          <button onClick={() => setMode("signup")} className={`py-2 rounded-lg ${mode==="signup"?"bg-white shadow":""}`}>Sign up</button>
        </div>
        <form className="space-y-3" onSubmit={(e)=>{
          e.preventDefault();
          if(mode === "signup" && pwd !== pwd2){ setError("Passwords do not match"); return; }
          setError(null);
          const [firstName, ...rest] = (name || email.split("@")[0]).trim().split(/\s+/);
          const lastName = rest.join(" ");
          onSuccess({ firstName: firstName ?? "", lastName, email, password: pwd });
        }}>
          {mode==="signup" && (
            <div>
              <label className="text-xs text-zinc-600">Name</label>
              <input className="mt-1 w-full rounded-lg border px-3 py-2" placeholder="Ada Lovelace" value={name} onChange={(e)=> setName(e.target.value)} required />
            </div>
          )}
          <div>
            <label className="text-xs text-zinc-600">Email</label>
            <input className="mt-1 w-full rounded-lg border px-3 py-2" type="email" placeholder="you@company.com" value={email} onChange={(e)=> setEmail(e.target.value)} required />
          </div>
          <div>
            <label className="text-xs text-zinc-600">Password</label>
            <input className="mt-1 w-full rounded-lg border px-3 py-2" type="password" placeholder="••••••••" value={pwd} onChange={(e)=>{ setPwd(e.target.value); if(error) setError(null); }} required />
          </div>
          {mode==="signup" && (
            <div>
              <label className="text-xs text-zinc-600">Confirm Password</label>
              <input className="mt-1 w-full rounded-lg border px-3 py-2" type="password" placeholder="••••••••" value={pwd2} onChange={(e)=>{ setPwd2(e.target.value); if(error) setError(null); }} required />
              {error && <div className="mt-1 text-xs text-rose-600">{error}</div>}
            </div>
          )}
          <button className="mt-2 w-full bg-[#6250A5] text-white rounded-xl py-2.5 hover:bg-[#544691]">{mode==="login"?"Enter":"Create account"}</button>
        </form>
      </div>
    </div>
  )
}

function ConfirmModal({ title, message, confirmLabel = 'Delete', onConfirm, onClose }:{ title:string; message:string; confirmLabel?:string; onConfirm:()=>void; onClose:()=>void }){
  return (
    <Modal title={title} onClose={onClose}>
      <div className="space-y-3 text-sm">
        <div className="text-zinc-700">{message}</div>
        <div className="flex gap-2 justify-end pt-2">
          <button className="px-3 py-2 rounded-lg border" onClick={onClose}>Cancel</button>
          <button className="px-3 py-2 rounded-lg bg-rose-600 text-white hover:bg-rose-700" onClick={onConfirm}>{confirmLabel}</button>
        </div>
      </div>
    </Modal>
  );
}

// --------------------------- Studio (one-page app) ---------------------------
function Studio({ user, setUser }:{ user: User; setUser: React.Dispatch<React.SetStateAction<User | null>> }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sidebarWidth, setSidebarWidth] = useState(280);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const activeProject = projects.find(p=>p.id===activeProjectId) ?? null;

  const [showAddAccount, setShowAddAccount] = useState(false);
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [showOpenTip, setShowOpenTip] = useState(false);
  const [confirm, setConfirm] = useState<null | { type: 'project'|'account'; id: string; name: string }>(null);
  const [showCloseTip, setShowCloseTip] = useState(false);

  const startResize = (e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startW = sidebarWidth;
    const onMove = (ev: MouseEvent) => {
      const next = Math.min(520, Math.max(200, startW + (ev.clientX - startX)));
      setSidebarWidth(next);
    };
    const onUp = () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  };

  return (
    <div className="h-full grid" style={{ gridTemplateColumns: sidebarOpen ? `${Math.round(sidebarWidth)}px 1fr` : '0px 1fr' }}>
      {/* Sidebar */}
      <aside className={`relative h-full border-r bg-white ${sidebarOpen?"opacity-100":"opacity-0 pointer-events-none"} transition-all flex flex-col`}>
        <div className="h-14 flex items-center justify-between px-3 border-b relative">
          <div className="flex items-center gap-1">
            <Logo size={60} className="ml-[-3px] mt-[2px]" />
          </div>
          <button
            onMouseEnter={()=> setShowCloseTip(true)}
            onMouseLeave={()=> setShowCloseTip(false)}
            onClick={()=>setSidebarOpen(false)}
            className="text-zinc-500 hover:text-zinc-800"
            aria-label="Close sidebar"
          >⟨</button>
          {showCloseTip && (
            <div className="pointer-events-none absolute right-10 top-1/2 -translate-y-1/2 text-xs bg-zinc-800 text-white px-2 py-1 rounded shadow">
              Close sidebar
            </div>
          )}
        </div>
        {/* Resize handle */}
        {sidebarOpen && (
          <div
            className="absolute top-0 -right-1 h-full w-2 cursor-col-resize"
            onMouseDown={startResize}
            title="Resize sidebar"
          />
        )}
        <div className="p-3 overflow-auto flex-1">
          <Section title="Projects" actionLabel="New" onAction={()=>setShowCreateProject(true)}>
            {projects.length===0 ? (
              <EmptyRow text="No projects yet" />
            ) : (
              <div className="space-y-1 mt-3">
                {projects.map(p=> (
                  <div key={p.id} className={`group flex items-center rounded-lg px-2 py-1.5 ${p.id===activeProjectId?"bg-zinc-300":""} hover:bg-zinc-200`}>
                    <button onClick={()=>setActiveProjectId(p.id)} className="flex-1 text-left min-w-0">
                      <div className="text-sm font-medium truncate">{p.name}</div>
                      <div className="text-[11px] text-zinc-500 truncate">{p.description}</div>
                    </button>
                    <button title="Delete project" className="opacity-0 group-hover:opacity-100 text-zinc-400 hover:text-rose-600 p-1" onClick={()=> setConfirm({ type: 'project', id: p.id, name: p.name })}>🗑️</button>
                  </div>
                ))}
              </div>
            )}
          </Section>
          <div className="h-px bg-zinc-200 my-3.5" />

          <Section title="Accounts" actionLabel="Add" onAction={()=>setShowAddAccount(true)}>
            {accounts.length===0 ? <EmptyRow text="No accounts yet"/> : (
              <div className="space-y-1 mt-3">
                {accounts.map(a=> (
                  <div key={a.id} className="group px-2 py-1.5 rounded-lg flex items-center justify-between gap-2 hover:bg-zinc-200">
                    <button className="flex items-center gap-2 flex-1 text-left">
                      <AccountIcon kind={a.kind} />
                      <div className="text-sm">{a.label}</div>
                    </button>
                    <button title="Remove account" className="opacity-0 group-hover:opacity-100 text-zinc-400 hover:text-rose-600 p-1" onClick={()=> setConfirm({ type: 'account', id: a.id, name: a.label })}>🗑️</button>
                  </div>
                ))}
              </div>
            )}
          </Section>
        </div>
        <UserFooter user={user} onLogout={()=> setUser(null)} onUpdateUser={(u)=> setUser(u)} />
      </aside>

      {/* Main */}
      <main className="h-full relative">
        {/* Top bar */}
        <div className="h-14 bg-white/80 backdrop-blur border-b px-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {!sidebarOpen && (
              <div className="relative">
                <button
                  onMouseEnter={()=> setShowOpenTip(true)}
                  onMouseLeave={()=> setShowOpenTip(false)}
                  onClick={()=>setSidebarOpen(true)}
                  className="rounded-lg border px-2 py-1 text-sm"
                  aria-label="Open sidebar"
                  title="Open sidebar"
                >☰</button>
                {showOpenTip && (
                  <div className="absolute left-0 top-full mt-1 text-xs bg-zinc-800 text-white px-2 py-1 rounded shadow">
                    Open sidebar
                  </div>
                )}
              </div>
            )}
            {activeProject ? (
              <div className="flex flex-col">
                <div className="font-semibold leading-tight">{activeProject.name}</div>
                <div className="text-sm text-zinc-500 leading-tight truncate max-w-[420px]">{activeProject.description}</div>
              </div>
            ) : (
              <div className="text-sm text-zinc-600">Create a project to begin</div>
            )}
          </div>
          <div className="flex items-center gap-2">
            {activeProject && <ExecBar project={activeProject} />}
            {!activeProject && (
              <button onClick={()=>setShowCreateProject(true)} className="px-3 py-1.5 rounded-xl bg-[#6250A5] text-white hover:bg-[#544691]">Create project</button>
            )}
          </div>
        </div>

        {/* Canvas or Empty */}
        {activeProject ? (
          <ProjectCanvas project={activeProject} setProjects={setProjects} />
        ) : (
          <EmptyState onCreate={()=>setShowCreateProject(true)} />
        )}
      </main>

      {showAddAccount && (
        <AddAccountModal
          onClose={()=>setShowAddAccount(false)}
          existingKinds={accounts.map(a=> a.kind)}
          onAdd={(acc)=> setAccounts(prev=> prev.some(a=> a.kind===acc.kind) ? prev : [...prev, acc])}
        />
      )}
      {showCreateProject && (
        <CreateProjectModal onClose={()=>setShowCreateProject(false)} onCreate={(p)=>{ setProjects(prev=>[...prev, p]); setActiveProjectId(p.id); }} />
      )}
      {confirm && (
        <ConfirmModal
          title={confirm.type === 'project' ? 'Delete project' : 'Remove account'}
          message={`Are you sure you want to ${confirm.type==='project' ? 'delete project' : 'remove account'} "${confirm.name}"? This cannot be undone.`}
          confirmLabel={confirm.type === 'project' ? 'Delete project' : 'Remove account'}
          onConfirm={() => {
            if (confirm.type === 'project') {
              setProjects(prev => prev.filter(p => p.id !== confirm.id));
              if (activeProjectId === confirm.id) setActiveProjectId(null);
            } else {
              setAccounts(prev => prev.filter(a => a.id !== confirm.id));
            }
            setConfirm(null);
          }}
          onClose={() => setConfirm(null)}
        />
      )}
    </div>
  );
}

// --------------------------- Shared UI bits ---------------------------
function Section({title, children, actionLabel, onAction}:{title:string; children: React.ReactNode; actionLabel?:string; onAction?:()=>void}){
  return (
    <div className="mb-4">
      <div className="flex items-center justify-between mb-2">
        <div className="text-xs uppercase tracking-wide text-zinc-500">{title}</div>
        {actionLabel && <button onClick={onAction} className="text-xs px-2 py-1 rounded bg-zinc-100 hover:bg-zinc-200">{actionLabel}</button>}
      </div>
      {children}
    </div>
  )
}

function EmptyRow({text}:{text:string}){
  return <div className="text-xs text-zinc-500 border rounded-lg px-2 py-3 text-center">{text}</div>
}

function AccountIcon({ kind, size = 25.5, className = "" }:{ kind: Account["kind"]; size?: number; className?: string }){
  const [err, setErr] = useState(false);
  const [src, setSrc] = useState<string>(`/logos/${kind}.svg`);
  if (err) {
    return <span className={`inline-block ${className}`} style={{ width: size, height: size, lineHeight: `${size}px` }} title={kind}>{(ICONS as any)[kind] ?? "🔌"}</span>;
  }
  return (
    <img
      src={src}
      alt={kind}
      className={className}
      style={{ width: size, height: size }}
      onError={() => {
        if (src.endsWith('.svg')) setSrc(`/logos/${kind}.png`); else setErr(true);
      }}
    />
  );
}

function initialsOf(user: User){
  const a = user.firstName?.trim?.();
  const b = user.lastName?.trim?.();
  if(a || b){
    return `${a? a[0].toUpperCase():""}${b? b[0].toUpperCase():""}` || (user.email[0]||"?").toUpperCase();
  }
  return (user.email[0]||"?").toUpperCase();
}

function UserFooter({ user, onLogout, onUpdateUser }:{ user: User; onLogout: ()=>void; onUpdateUser:(u:User)=>void }){
  const [open, setOpen] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  return (
    <div className="border-t relative select-none h-14">
      <button
        className="w-full h-full flex items-center gap-2 text-sm px-3 hover:bg-zinc-200 active:bg-zinc-300"
        onClick={()=> setOpen(o=>!o)}
      >
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-full bg-[#6250A5] text-white grid place-items-center text-xs font-semibold">
            {initialsOf(user)}
          </div>
          <div className="text-left">
            <div className="font-medium leading-tight">{[user.firstName, user.lastName].filter(Boolean).join(" ") || user.email}</div>
            <div className="text-[11px] text-zinc-500 leading-tight">{user.email}</div>
          </div>
        </div>
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={(e)=>{ e.stopPropagation(); setOpen(false); }} />
          <div className="fixed left-3 bottom-12 w-64 bg-white border rounded-xl shadow-lg p-2 z-20" style={{maxWidth: 'calc(100vw - 16px)'}}>
            <button className="w-full text-left px-3 py-2 rounded-lg hover:bg-zinc-200" onClick={()=>{ setShowProfile(true); setOpen(false); }}>Profile</button>
            <div className="h-px bg-zinc-200 my-1" />
            <button className="w-full text-left px-3 py-2 rounded-lg hover:bg-zinc-200 text-rose-600" onClick={onLogout}>Log out</button>
          </div>
        </>
      )}
      {showProfile && (
        <ProfileModal user={user} onClose={()=> setShowProfile(false)} onSave={(u)=>{ onUpdateUser(u); setShowProfile(false); }} />
      )}
    </div>
  );
}

function EmptyState({ onCreate }:{ onCreate: ()=>void }){
  return (
    <div className="h-[calc(100%-56px)] grid place-items-center bg-gradient-to-b from-zinc-50 to-zinc-100">
      <div className="text-center">
        <div className="text-4xl mb-3">✨</div>
        <div className="text-xl font-semibold mb-1">Build a Datagent</div>
        <div className="text-zinc-600 mb-4">Drag in your data, build your flow, and share the results anywhere.</div>
        <button onClick={onCreate} className="px-4 py-2 rounded-xl bg-[#6250A5] text-white hover:bg-[#544691]">Create project</button>
      </div>
    </div>
  )
}

// --------------------------- Modals ---------------------------
function Modal({ title, children, onClose, wide=false }:{ title:string; children: React.ReactNode; onClose: ()=>void; wide?: boolean }){
  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className={`absolute left-1/2 top-10 -translate-x-1/2 w-[${wide?"920":"640"}px] max-w-[95vw] bg-white rounded-2xl shadow-xl border` }>
        <div className="px-5 py-3 border-b flex items-center justify-between">
          <div className="font-semibold">{title}</div>
          <button className="text-zinc-500 hover:text-black" onClick={onClose}>✕</button>
        </div>
        <div className="p-4 max-h-[70vh] overflow-auto">{children}</div>
      </div>
    </div>
  )
}

function AddAccountModal({ onClose, onAdd, existingKinds }:{ onClose:()=>void; onAdd:(a:Account)=>void; existingKinds?: Account["kind"][] }){
  const [sel, setSel] = useState<Account["kind"] | "">("");
  return (
    <Modal title="Add account" onClose={onClose}>
      <div className="space-y-1">
        <div className="-mt-2">
          <label className="text-xs text-zinc-600">Service</label>
          <div className="relative mt-1">
            <select className="w-full border rounded-lg px-2 py-2 appearance-none pr-10" value={sel} onChange={(e)=> setSel(e.target.value as Account["kind"] | "") }>
              <option value="" disabled>— Please select —</option>
              <option value="aws" disabled={!!existingKinds?.includes("aws")}>AWS</option>
              <option value="gmail" disabled={!!existingKinds?.includes("gmail")}>Gmail</option>
              <option value="outlook" disabled={!!existingKinds?.includes("outlook")}>Outlook</option>
              <option value="gdrive" disabled={!!existingKinds?.includes("gdrive")}>Google Drive</option>
              <option value="slack" disabled={!!existingKinds?.includes("slack")}>Slack</option>
              <option value="yahoo" disabled={!!existingKinds?.includes("yahoo")}>Yahoo Finance</option>
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-6 flex items-center text-zinc-500 rotate-270">⟨</div>
          </div>
        </div>
        {sel && existingKinds?.includes(sel as Account["kind"]) && (
          <div className="text-xs text-zinc-500">This service is already linked.</div>
        )}
        <button
          disabled={!sel}
          onClick={()=>{ if(!sel) return; const kind = sel as Account["kind"]; onAdd({ id: rid(), kind, label: displayNameForKind(kind) }); onClose(); }}
          className={`w-full rounded-xl py-2 mt-3 ${sel?"bg-[#6250A5] text-white":"bg-zinc-200 text-zinc-500"}`}
        >
          Connect
        </button>
      </div>
    </Modal>
  )
}

function ProfileModal({ user, onClose, onSave }:{ user: User; onClose:()=>void; onSave:(u:User)=>void }){
  const [firstName, setFirstName] = useState(user.firstName);
  const [lastName, setLastName] = useState(user.lastName);
  const [email, setEmail] = useState(user.email);
  const [currentPwd, setCurrentPwd] = useState("");
  const [newPwd, setNewPwd] = useState("");
  const [confirmPwd, setConfirmPwd] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const canChangePassword = newPwd.length > 0 || confirmPwd.length > 0 || currentPwd.length > 0;

  const handleSave = () => {
    if(canChangePassword){
      if(user.password){
        if(currentPwd !== user.password){ setErr("Current password is incorrect"); return; }
      }
      if(newPwd.length < 6){ setErr("New password must be at least 6 characters"); return; }
      if(newPwd !== confirmPwd){ setErr("New passwords do not match"); return; }
    }
    setErr(null);
    onSave({
      ...user,
      firstName: firstName.trim(),
      lastName: lastName.trim(),
      email: email.trim(),
      password: canChangePassword ? newPwd : user.password,
    });
  };

  return (
    <Modal title="Profile" onClose={onClose}>
      <div className="space-y-3 text-sm">
        <div className="grid grid-cols-2 gap-2 -mt-1">
          <div>
            <label className="text-xs text-zinc-600">First name</label>
            <input className="mt-1 w-full border rounded-lg px-2 py-2" value={firstName} onChange={(e)=> setFirstName(e.target.value)} />
          </div>
          <div>
            <label className="text-xs text-zinc-600">Last name</label>
            <input className="mt-1 w-full border rounded-lg px-2 py-2" value={lastName} onChange={(e)=> setLastName(e.target.value)} />
          </div>
        </div>
        <div>
          <label className="text-xs text-zinc-600">Email</label>
          <input className="mt-1 w-full border rounded-lg px-2 py-2" type="email" value={email} onChange={(e)=> setEmail(e.target.value)} />
        </div>
        <div className="grid grid-cols-3 gap-2">
          <div>
            <label className="text-xs text-zinc-600">Current password</label>
            <input className="mt-1 w-full border rounded-lg px-2 py-2" type="password" value={currentPwd} onChange={(e)=> setCurrentPwd(e.target.value)} />
          </div>
          <div>
            <label className="text-xs text-zinc-600">New password</label>
            <input className="mt-1 w-full border rounded-lg px-2 py-2" type="password" value={newPwd} onChange={(e)=> setNewPwd(e.target.value)} />
          </div>
          <div>
            <label className="text-xs text-zinc-600">Confirm new password</label>
            <input className="mt-1 w-full border rounded-lg px-2 py-2" type="password" value={confirmPwd} onChange={(e)=> setConfirmPwd(e.target.value)} />
          </div>
        </div>
        {err && <div className="text-xs text-rose-600">{err}</div>}
        <div className="flex gap-2 mt-4">
          <button className="px-3 py-2 rounded-lg border" onClick={onClose}>Cancel</button>
          <button className="px-3 py-2 rounded-lg bg-[#6250A5] text-white" onClick={handleSave}>Save changes</button>
        </div>
      </div>
    </Modal>
  );
}

function CreateProjectModal({ onClose, onCreate }:{ onClose:()=>void; onCreate:(p:Project)=>void }){
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  return (
    <Modal title="Create project" onClose={onClose}>
      <div className="space-y-2.5">
        <div className="-mt-2">
          <label className="text-xs text-zinc-600">Project name</label>
          <input className="mt-1 w-full border rounded-lg px-2 py-2" value={name} onChange={(e)=>setName(e.target.value)} placeholder="Sales Weekly Report" />
        </div>
        <div>
          <label className="text-xs text-zinc-600">Global context</label>
          <textarea className="mt-1 w-full border rounded-lg px-2 py-2 h-24" value={desc} onChange={(e)=>setDesc(e.target.value)} placeholder="Analyze weekly sales by country and deliver email + slack dashboards." required/>
        </div>
        <button disabled={!name || !desc} onClick={()=>{
          const p: Project = { id: rid(), name, description: desc, nodes: [], edges: [] };
          onCreate(p);
          onClose();
        }} className={`w-full rounded-xl py-2 ${name && desc?"bg-[#6250A5] text-white":"bg-zinc-200 text-zinc-500"}`}>Create</button>
      </div>
    </Modal>
  )
}

// --------------------------- Project Canvas ---------------------------
function ProjectCanvas({ project, setProjects }:{ project: Project; setProjects: React.Dispatch<React.SetStateAction<Project[]>> }){
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const rfInstRef = useRef<ReactFlowInstance | null>(null);
  const resizeTimerRef = useRef<number | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState(project.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(project.edges);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [locked, setLocked] = useState(false);
  const miniMapHeight = 120;
  const [miniMapWidth, setMiniMapWidth] = useState<number>(200);

  // keep outer project state in sync
  useEffect(()=>{
    setProjects(curr=> curr.map(p=> p.id===project.id ? ({...p, nodes, edges}) : p));
  }, [nodes, edges]);

  const onConnect = useCallback((conn: Edge | Connection) => {
    setEdges((eds) => addEdge({ ...conn, animated: true, markerEnd:{ type: MarkerType.ArrowClosed } }, eds));
  }, []);

  useEffect(() => {
    const root = canvasRef.current;
    if (!root) return;
    const measure = () => {
      const w = root.clientWidth;
      const h = root.clientHeight || 1;
      const ratio = w / h;
      const desired = Math.max(160, Math.min(300, Math.round(120 * ratio)));
      setMiniMapWidth(desired);
      // debounce equal-fit so the viewport padding stays consistent on resize
      if (resizeTimerRef.current) {
        window.clearTimeout(resizeTimerRef.current);
      }
      resizeTimerRef.current = window.setTimeout(() => {
        const inst = rfInstRef.current;
        const el = canvasRef.current;
        if (!inst || !el) return;
        const nodes = inst.getNodes().filter(n => !n.hidden && n.width && n.height);
        if (nodes.length === 0) return;
        const b = getNodesBounds(nodes as any);
        const vw = el.clientWidth, vh = el.clientHeight;
        const R = vw / vh;
        let bx = b.x, by = b.y, bw = b.width, bh = b.height;
        const r = bw / bh;
        if (r < R) { // expand width to match aspect
          const newW = bh * R; const dx = (newW - bw) / 2; bw = newW; bx -= dx;
        } else if (r > R) { // expand height
          const newH = bw / R; const dy = (newH - bh) / 2; bh = newH; by -= dy;
        }
        const { x, y, zoom } = getViewportForBounds({ x: bx, y: by, width: bw, height: bh } as any, vw, vh, 0.1, 4, 0.04);
        inst.setViewport({ x, y, zoom });
      }, 60);
    };
    measure();
    const ro = new ResizeObserver(() => measure());
    ro.observe(root);
    window.addEventListener('resize', measure);
    return () => { ro.disconnect(); window.removeEventListener('resize', measure); };
  }, []);

  // Palette (left overlay)
  const addNode = (type: BlockType) => {
    const id = `${type}-${rid().slice(0,5)}`;
    const base: NodeData = { type, title: titleFor(type), status: "empty" };
    const position = { x: 160 + Math.random() * 480, y: 120 + Math.random() * 320 };
    setNodes(ns=> ns.concat({ id, position, data: base, type: "default" }));
  };

  const selectedNode = useMemo(()=> nodes.find(n=> n.id===selectedNodeId) ?? null, [nodes, selectedNodeId]);
  const setNodeData = (id: string, updater: (d: NodeData)=>NodeData) => setNodes(ns => ns.map(n => n.id===id ? ({...n, data: updater(n.data)}) : n));

  const openModalFor = (node: Node<NodeData>) => {
    switch(node.data.type){
      case "input": setShowInputModal(node.id, true); break;
      case "process": setShowProcessModal(node.id, true); break;
      case "visualize": setShowVisualizeModal(node.id, true); break;
      case "output": setShowOutputModal(node.id, true); break;
    }
  };

  // Modal visibility per node
  const [inputModalId, setInputModalId] = useState<string| null>(null);
  const [processModalId, setProcessModalId] = useState<string| null>(null);
  const [visualizeModalId, setVisualizeModalId] = useState<string| null>(null);
  const [outputModalId, setOutputModalId] = useState<string| null>(null);
  const setShowInputModal = (id:string, v:boolean)=> setInputModalId(v? id : null);
  const setShowProcessModal = (id:string, v:boolean)=> setProcessModalId(v? id : null);
  const setShowVisualizeModal = (id:string, v:boolean)=> setVisualizeModalId(v? id : null);
  const setShowOutputModal = (id:string, v:boolean)=> setOutputModalId(v? id : null);

  // Run stub: traverse in topological order and mark statuses + previews
  const handleRun = async () => {
    // validate edges vs rules (simple check)
    for(const e of edges){
      const s = nodes.find(n=>n.id===e.source)!, t = nodes.find(n=>n.id===e.target)!;
      if(!isConnectionAllowed(s.data.type, t.data.type)){
        alert(`Invalid edge: ${s.data.type} → ${t.data.type}`);
        return;
      }
    }
    // reset statuses
    setNodes(ns => ns.map(n => ({...n, data: {...n.data, status: "queued"}})));
    const order = topo(nodes, edges);
    for(const id of order){
      setNodeData(id, d=> ({...d, status: "running" }));
      await sleep(400);
      // fake token + preview
      const tokens = dice(50, 140) - (Math.random()<0.5?20:0);
      const co2 = estimateCO2(tokens);
      setNodeData(id, d=> ({
        ...d,
        status: "done",
        tokenCost: tokens,
        co2Grams: co2,
        preview: d.preview ?? defaultPreviewFor(d.type)
      }));
    }
  };

  return (
    <div ref={canvasRef} className="h-[calc(100%-56px)] relative">
      {/* Palette */}
      <div className="absolute z-10 left-4 top-4 bg-white/90 backdrop-blur rounded-2xl border shadow p-2">
        <div className="text-xs text-zinc-500 px-2 pb-1">Blocks</div>
        <div className="grid grid-cols-4 gap-1">
          <BlockBtn label="Input" icon={ICONS.input} onClick={()=>addNode("input")} />
          <BlockBtn label="Process" icon={ICONS.process} onClick={()=>addNode("process")} />
          <BlockBtn label="Visualize" icon={ICONS.visualize} onClick={()=>addNode("visualize")} />
          <BlockBtn label="Output" icon={ICONS.output} onClick={()=>addNode("output")} />
        </div>
      </div>

      {/* Canvas */}
      <ReactFlow
        nodes={nodes.map(n=> ({...n, type: "default"}))}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={(_, node)=> setSelectedNodeId(node.id)}
        onNodeDoubleClick={(_, node)=> openModalFor(node as Node<NodeData>)}
        onInit={(inst) => { rfInstRef.current = inst; /* equal-fit happens in measure */ }}
        isValidConnection={(c)=> {
          const s = nodes.find(n=> n.id === c.source);
          const t = nodes.find(n=> n.id === c.target);
          if(!s || !t) return false;
          return isConnectionAllowed((s.data as NodeData).type, (t.data as NodeData).type);
        }}
        nodesDraggable={!locked}
        nodesConnectable={!locked}
        elementsSelectable={!locked}
        fitView
        fitViewOptions={{ padding: 0.08 }}
        snapToGrid
        snapGrid={[16,16]}
        defaultViewport={{ x: 0, y: 0, zoom: 1 }}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
        <MiniMap
          pannable
          zoomable
          position="bottom-right"
          style={{
            width: miniMapWidth,
            height: miniMapHeight,
            right: 56,
            bottom: 8,
            backgroundColor: '#ffffff',
            border: '1px solid #0a0a0a',
            borderRadius: 0,
            boxSizing: 'border-box',
            display: 'block',
            overflow: 'hidden',
          }}
        />
        <Controls
          position="bottom-right"
          style={{
            right: 8,
            bottom: 8,
            height: miniMapHeight,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            backgroundColor: '#ffffff',
            border: '1px solid #0a0a0a',
            borderRadius: 0,
            padding: 4,
          }}
        />
      </ReactFlow>

      {/* Right inspector */}
      <div className="absolute right-4 top-4 z-10 w-[320px] rounded-2xl border bg-white/90 backdrop-blur shadow p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="text-xs uppercase tracking-wide text-zinc-500">Inspector</div>
          <div className="flex items-center gap-2">
            <button
              onClick={()=> setLocked(v=>!v)}
              className={`px-2 py-1 rounded-lg border ${locked?"bg-zinc-100 text-zinc-700":"bg-white"}`}
              title={locked?"Unlock layout":"Lock layout"}
            >{locked?"🔒 Locked":"🔓 Lock"}</button>
            <button onClick={handleRun} className="px-3 py-1.5 rounded-xl bg-[#6250A5] text-white hover:bg-[#544691]">Run</button>
          </div>
        </div>
        {!selectedNode ? (
          <div className="text-sm text-zinc-500">Select a node to edit.</div>
        ) : (
          <NodeInspector node={selectedNode} setNodeData={setNodeData} openModal={()=>openModalFor(selectedNode)} />
        )}
      </div>

      {/* Node modals */}
      {!!inputModalId && (
        <InputNodeModal node={nodes.find(n=>n.id===inputModalId)!} onClose={()=>setShowInputModal("", false)} onSave={(d)=> setNodeData(inputModalId, ()=> d)} />
      )}
      {!!processModalId && (
        <ProcessNodeModal node={nodes.find(n=>n.id===processModalId)!} onClose={()=>setShowProcessModal("", false)} onSave={(d)=> setNodeData(processModalId, ()=> d)} />
      )}
      {!!visualizeModalId && (
        <VisualizeNodeModal node={nodes.find(n=>n.id===visualizeModalId)!} onClose={()=>setVisualizeModalId(null)} onSave={(d)=> setNodeData(visualizeModalId, ()=> d)} />
      )}
      {!!outputModalId && (
        <OutputNodeModal node={nodes.find(n=>n.id===outputModalId)!} onClose={()=>setOutputModalId(null)} onSave={(d)=> setNodeData(outputModalId, ()=> d)} />
      )}
    </div>
  );
}

function BlockBtn({ label, icon, onClick }:{ label:string; icon:string; onClick:()=>void }){
  return (
    <button onClick={onClick} className="px-2 py-2 rounded-xl border bg-white hover:shadow text-sm flex items-center gap-2">
      <span>{icon}</span>
      <span>{label}</span>
    </button>
  )
}

function titleFor(t: BlockType){
  switch(t){
    case "input": return "Input";
    case "process": return "Process";
    case "visualize": return "Visualize";
    case "output": return "Output";
  }
}

function displayNameForKind(kind: Account["kind"]) {
  switch (kind) {
    case "aws": return "AWS";
    case "gmail": return "Gmail";
    case "outlook": return "Outlook";
    case "gdrive": return "Google Drive";
    case "slack": return "Slack";
    case "yahoo": return "Yahoo Finance";
    default: return "Custom";
  }
}

function isConnectionAllowed(a: BlockType, b: BlockType){
  if(a==="input" && (b==="process"||b==="visualize"||b==="output")) return true;
  if(a==="process" && (b==="process"||b==="visualize"||b==="output")) return true;
  if(a==="visualize" && b==="output") return true;
  return false;
}

function defaultPreviewFor(t: BlockType): NodeData["preview"]{
  if(t==="visualize") return { kind: "chart", payload: { type: "bar", title: "Preview Chart", data: [{x:"A", y: 10},{x:"B", y:22},{x:"C", y:14}] } };
  if(t==="process") return { kind: "table", payload: sampleRows(8) };
  if(t==="output") return { kind: "text", payload: "will deliver downstream result" };
  return { kind: "table", payload: sampleRows(6) };
}

// --------------------------- Inspector ---------------------------
function NodeInspector({ node, setNodeData, openModal }:{ node: Node<NodeData>; setNodeData:(id:string, up:(d:NodeData)=>NodeData)=>void; openModal:()=>void }){
  const d = node.data;
  return (
    <div className="space-y-3 text-sm">
      <div className="flex items-center gap-2">
        <div className="text-xl">{(ICONS as any)[d.type]}</div>
        <input className="flex-1 border rounded-lg px-2 py-1" value={d.title} onChange={(e)=> setNodeData(node.id, (dd)=> ({...dd, title: e.target.value}))} />
        <span className={`text-[10px] px-2 py-0.5 rounded-full ${badgeFor(d.status)}`}>{d.status ?? "empty"}</span>
      </div>
      <div className="text-xs text-zinc-500">{descFor(d.type)}</div>
      {d.preview && <PreviewCard preview={d.preview} />}
      <button onClick={openModal} className="w-full rounded-lg border bg-zinc-50 py-2 hover:bg-zinc-100">Configure…</button>
      {(d.tokenCost!=null) && (
        <div className="text-xs text-zinc-500">tokens: <b>{d.tokenCost}</b> • CO₂: <b>{(d.co2Grams??0).toFixed(3)}g</b></div>
      )}
    </div>
  )
}

function badgeFor(s?: NodeData["status"]){
  switch(s){
    case "running": return "bg-amber-100 text-amber-700";
    case "done": return "bg-emerald-100 text-emerald-700";
    case "queued": return "bg-zinc-100 text-zinc-600";
    case "error": return "bg-rose-100 text-rose-700";
    case "ready": return "bg-sky-100 text-sky-700";
    case "configured": return "bg-violet-100 text-violet-700";
    default: return "bg-zinc-100 text-zinc-600";
  }
}

function descFor(t: BlockType){
  switch(t){
    case "input": return "Define a data source (CSV, sheet, object store, finance API).";
    case "process": return "Transform data (clean, join, aggregate, derive features).";
    case "visualize": return "Choose a chart/text/table to represent the data.";
    case "output": return "Deliver result to Email, Slack, or Drive; optionally schedule.";
  }
}

function PreviewCard({ preview }:{ preview: NonNullable<NodeData["preview"]> }){
  if(preview.kind==="text") return (
    <div className="rounded-lg border bg-white p-2 text-xs text-zinc-700">{String(preview.payload)}</div>
  );
  if(preview.kind==="chart") return (
    <div className="rounded-lg border bg-white p-2">
      <div className="text-xs text-zinc-500 mb-1">{preview.payload.title ?? "Chart"}</div>
      {/* Mini chart placeholder */}
      <div className="grid grid-cols-8 gap-1 h-20 items-end">
        {preview.payload.data?.slice(0,8).map((d:any,i:number)=> (
          <div key={i} className="bg-indigo-400 rounded" style={{height: Math.max(6, Math.min(64, d.y*2))}} />
        ))}
      </div>
    </div>
  );
  // table
  return (
    <div className="rounded-lg border bg-white overflow-hidden">
      <table className="w-full text-xs">
        <thead className="bg-zinc-50">
          <tr>{Object.keys(preview.payload[0]??{a:"A"}).slice(0,5).map((k)=> <th key={k} className="px-2 py-1 text-left text-zinc-600">{k}</th>)}</tr>
        </thead>
        <tbody>
          {preview.payload.slice(0,6).map((row:any, i:number)=> (
            <tr key={i} className="border-t">
              {Object.values(row).slice(0,5).map((v:any, j:number)=> <td key={j} className="px-2 py-1 text-zinc-700">{String(v)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// --------------------------- Node Modals ---------------------------
function InputNodeModal({ node, onClose, onSave }:{ node: Node<NodeData>; onClose:()=>void; onSave:(d:NodeData)=>void }){
  const d = node.data;
  const [kind, setKind] = useState<InputSourceKind>((d.input?.source.kind) || "csv");
  const [cfg, setCfg] = useState<InputConfig>(d.input?.source || { kind: "csv", delimiter: "," });
  const [account, setAccount] = useState<string>(d.input?.boundAccountId || "");

  const updateCfg = (patch: Partial<InputConfig>) => setCfg(prev => ({...prev, ...patch} as any));

  return (
    <Modal title="Configure Input" onClose={onClose}>
      <div className="space-y-3 text-sm">
        <div>
          <label className="text-xs text-zinc-600">Source Type</label>
          <select className="mt-1 border rounded-lg px-2 py-2 w-full" value={kind} onChange={(e)=>{ const v = e.target.value as InputSourceKind; setKind(v); setCfg({kind:v} as any); }}>
            <option value="csv">CSV</option>
            <option value="google_sheet">Google Sheet</option>
            <option value="s3">AWS S3</option>
            <option value="yahoo_finance">Yahoo Finance</option>
          </select>
        </div>
        {kind==="csv" && (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs">Path</label>
              <input className="mt-1 w-full border rounded-lg px-2 py-2" placeholder="/uploads/data.csv" onChange={(e)=> updateCfg({ path: e.target.value } as any)} />
            </div>
            <div>
              <label className="text-xs">Delimiter</label>
              <input className="mt-1 w-full border rounded-lg px-2 py-2" defaultValue="," onChange={(e)=> updateCfg({ delimiter: e.target.value } as any)} />
            </div>
          </div>
        )}
        {kind==="google_sheet" && (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs">Sheet (doc!tab)</label>
              <input className="mt-1 w-full border rounded-lg px-2 py-2" placeholder="customers!A:Z" onChange={(e)=> updateCfg({ sheet: e.target.value } as any)} />
            </div>
            <div>
              <label className="text-xs">Range</label>
              <input className="mt-1 w-full border rounded-lg px-2 py-2" placeholder="A:Z" onChange={(e)=> updateCfg({ range: e.target.value } as any)} />
            </div>
          </div>
        )}
        {kind==="s3" && (
          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="text-xs">Bucket</label>
              <input className="mt-1 w-full border rounded-lg px-2 py-2" placeholder="my-bucket" onChange={(e)=> updateCfg({ bucket: e.target.value } as any)} />
            </div>
            <div>
              <label className="text-xs">Prefix</label>
              <input className="mt-1 w-full border rounded-lg px-2 py-2" placeholder="sales/" onChange={(e)=> updateCfg({ prefix: e.target.value } as any)} />
            </div>
            <div>
              <label className="text-xs">Pattern</label>
              <input className="mt-1 w-full border rounded-lg px-2 py-2" placeholder="*.parquet" onChange={(e)=> updateCfg({ pattern: e.target.value } as any)} />
            </div>
          </div>
        )}
        {kind==="yahoo_finance" && (
          <div className="grid grid-cols-3 gap-2">
            <div className="col-span-2">
              <label className="text-xs">Tickers</label>
              <input className="mt-1 w-full border rounded-lg px-2 py-2" placeholder="AAPL,MSFT" onChange={(e)=> updateCfg({ tickers: e.target.value } as any)} />
            </div>
            <div>
              <label className="text-xs">Interval</label>
              <select className="mt-1 w-full border rounded-lg px-2 py-2" onChange={(e)=> updateCfg({ interval: e.target.value as any } as any)}>
                <option value="1d">1d</option>
                <option value="1h">1h</option>
                <option value="1m">1m</option>
              </select>
            </div>
          </div>
        )}

        <div>
          <label className="text-xs text-zinc-600">Bound account (optional)</label>
          <input className="mt-1 w-full border rounded-lg px-2 py-2" placeholder="Account ID or nickname" value={account} onChange={(e)=> setAccount(e.target.value)} />
        </div>
        <button className="w-full bg-indigo-600 text-white rounded-xl py-2" onClick={()=> { onSave({ ...d, input: { source: cfg, boundAccountId: account }, status: "configured", preview: { kind: "table", payload: sampleRows(6) } }); onClose(); }}>Save</button>
      </div>
    </Modal>
  )
}

function ProcessNodeModal({ node, onClose, onSave }:{ node: Node<NodeData>; onClose:()=>void; onSave:(d:NodeData)=>void }){
  const d = node.data;
  const [chat, setChat] = useState<ConversationTurn[]>(
    d.convo ?? ([{ role: "assistant", content: "Hi! Tell me how you'd like to transform the data." }] as ConversationTurn[])
  );
  const [msg, setMsg] = useState("");
  const [goals, setGoals] = useState<string[]>(d.goals ?? []);

  const send = () => {
    if(!msg.trim()) return;
    const next: ConversationTurn[] = [...chat, { role: "user", content: msg } as const];
    // mock assistant synthesis
    const g = synthesizeGoals([...goals], msg);
    next.push({ role: "assistant", content: "Got it. I'll include that in the transformation plan." } as const);
    setGoals(g);
    setChat(next);
    setMsg("");
  };

  return (
    <Modal title="Configure Process" onClose={onClose} wide>
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-xl border bg-white">
          <div className="p-3 border-b text-sm font-medium">Conversation</div>
          <div className="p-3 h-64 overflow-auto space-y-2">
            {chat.map((t,i)=> (
              <div key={i} className={`text-sm ${t.role==="user"?"text-zinc-900":"text-zinc-700"}`}>
                <span className={`text-xs px-2 py-0.5 rounded ${t.role==="user"?"bg-indigo-50 text-indigo-700":"bg-zinc-100 text-zinc-700"}`}>{t.role}</span>
                <div className="mt-1">{t.content}</div>
              </div>
            ))}
          </div>
          <div className="p-3 border-t flex gap-2">
            <input className="flex-1 border rounded-lg px-2 py-2" value={msg} onChange={(e)=>setMsg(e.target.value)} placeholder="e.g., drop nulls in customer_id; lowercase email; convert currencies to USD" />
            <button onClick={send} className="px-3 rounded-lg bg-indigo-600 text-white">Send</button>
          </div>
        </div>
        <div className="space-y-3">
          <div className="rounded-xl border bg-white p-3">
            <div className="text-sm font-medium mb-2">Goals</div>
            {goals.length===0 ? <div className="text-xs text-zinc-500">No goals yet. They'll appear here as you chat.</div> : (
              <ul className="list-disc ml-5 text-sm space-y-1">
                {goals.map((g,i)=> <li key={i}>{g}</li>)}
              </ul>
            )}
          </div>
          <div className="rounded-xl border bg-white p-3">
            <div className="text-sm font-medium mb-2">Preview</div>
            <PreviewCard preview={d.preview ?? { kind: "table", payload: sampleRows(8) }} />
          </div>
          <button className="w-full bg-indigo-600 text-white rounded-xl py-2" onClick={()=>{ onSave({ ...d, convo: chat, goals, status: "configured", preview: { kind: "table", payload: sampleRows(8) } }); onClose(); }}>Save</button>
        </div>
      </div>
    </Modal>
  )
}

function VisualizeNodeModal({ node, onClose, onSave }:{ node: Node<NodeData>; onClose:()=>void; onSave:(d:NodeData)=>void }){
  const d = node.data;
  const [chat, setChat] = useState<ConversationTurn[]>(
    d.convo ?? ([{ role: "assistant", content: "How would you like to visualize the data? (bar, line, pie, heatmap, text summary, table)" }] as ConversationTurn[])
  );
  const [msg, setMsg] = useState("");
  const [goals, setGoals] = useState<string[]>(d.goals ?? ["Bar chart of weekly revenue by country"]);

  const send = () => {
    if(!msg.trim()) return;
    const next: ConversationTurn[] = [...chat, { role: "user", content: msg } as const];
    const g = synthesizeGoals([...goals], msg);
    next.push({ role: "assistant", content: "Great, updated the visualization spec." } as const);
    setGoals(g);
    setChat(next);
    setMsg("");
  };

  const preview: NodeData["preview"] = d.preview ?? { kind: "chart", payload: { title: "Revenue by Country", data: [{x:"US", y:40},{x:"CA",y:22},{x:"UK",y:18},{x:"DE",y:15}] } };

  return (
    <Modal title="Configure Visualization" onClose={onClose}>
      <div className="space-y-3">
        <div className="rounded-xl border bg-white">
          <div className="p-3 border-b text-sm font-medium">Conversation</div>
          <div className="p-3 h-48 overflow-auto space-y-2">
            {chat.map((t,i)=> (
              <div key={i} className={`text-sm ${t.role==="user"?"text-zinc-900":"text-zinc-700"}`}>
                <span className={`text-xs px-2 py-0.5 rounded ${t.role==="user"?"bg-indigo-50 text-indigo-700":"bg-zinc-100 text-zinc-700"}`}>{t.role}</span>
                <div className="mt-1">{t.content}</div>
              </div>
            ))}
          </div>
          <div className="p-3 border-t flex gap-2">
            <input className="flex-1 border rounded-lg px-2 py-2" value={msg} onChange={(e)=>setMsg(e.target.value)} placeholder="e.g., stacked bar chart by region; annotate anomaly" />
            <button onClick={send} className="px-3 rounded-lg bg-indigo-600 text-white">Send</button>
          </div>
        </div>
        <div className="rounded-xl border bg-white p-3">
          <div className="text-sm font-medium mb-2">Goals</div>
          <ul className="list-disc ml-5 text-sm space-y-1">
            {goals.map((g,i)=> <li key={i}>{g}</li>)}
          </ul>
        </div>
        <div className="rounded-xl border bg-white p-3">
          <div className="text-sm font-medium mb-2">Preview</div>
          <PreviewCard preview={preview} />
        </div>
        <button className="w-full bg-indigo-600 text-white rounded-xl py-2" onClick={()=>{ onSave({ ...d, convo: chat, goals, status: "configured", preview }); onClose(); }}>Save</button>
      </div>
    </Modal>
  )
}

function OutputNodeModal({ node, onClose, onSave }:{ node: Node<NodeData>; onClose:()=>void; onSave:(d:NodeData)=>void }){
  const d = node.data;
  const [kind, setKind] = useState<Destination["kind"]>(d.destination?.kind ?? "email");
  const [config, setConfig] = useState<Record<string,any>>(d.destination?.config ?? {});
  const [schedule, setSchedule] = useState<string>(d.schedule ?? "");

  return (
    <Modal title="Configure Output" onClose={onClose}>
      <div className="space-y-3 text-sm">
        <div>
          <label className="text-xs text-zinc-600">Destination</label>
          <select className="mt-1 w-full border rounded-lg px-2 py-2" value={kind} onChange={(e)=> setKind(e.target.value as any)}>
            <option value="email">Email</option>
            <option value="slack">Slack</option>
            <option value="gdrive">Google Drive</option>
          </select>
        </div>

        {kind==="email" && (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs">To</label>
              <input className="mt-1 w-full border rounded-lg px-2 py-2" placeholder="ops@company.com" onChange={(e)=> setConfig({...config, to: e.target.value})} />
            </div>
            <div>
              <label className="text-xs">Subject</label>
              <input className="mt-1 w-full border rounded-lg px-2 py-2" placeholder="Weekly KPI" onChange={(e)=> setConfig({...config, subject: e.target.value})} />
            </div>
          </div>
        )}
        {kind==="slack" && (
          <div>
            <label className="text-xs">Channel</label>
            <input className="mt-1 w-full border rounded-lg px-2 py-2" placeholder="#analytics" onChange={(e)=> setConfig({...config, channel: e.target.value})} />
          </div>
        )}
        {kind==="gdrive" && (
          <div>
            <label className="text-xs">Folder path</label>
            <input className="mt-1 w-full border rounded-lg px-2 py-2" placeholder="/Reports/Weekly" onChange={(e)=> setConfig({...config, folder: e.target.value})} />
          </div>
        )}

        <div>
          <label className="text-xs text-zinc-600">Schedule (optional)</label>
          <input className="mt-1 w-full border rounded-lg px-2 py-2" placeholder="cron e.g. 0 9 * * 1 (Mon 9am)" value={schedule} onChange={(e)=> setSchedule(e.target.value)} />
          <div className="text-[11px] text-zinc-500 mt-1">Tip: Leave empty to only send on manual runs.</div>
        </div>

        <button className="w-full bg-indigo-600 text-white rounded-xl py-2" onClick={()=> { onSave({ ...d, destination: { kind, config }, schedule: schedule || null, status: "ready", preview: { kind: "text", payload: `Will deliver via ${kind}` } }); onClose(); }}>Save</button>
      </div>
    </Modal>
  )
}

// --------------------------- Exec Bar (top-right) ---------------------------
function ExecBar({ project }:{ project: Project }){
  const [open, setOpen] = useState(false);

  const exportJSON = () => {
    const payload = {
      project: {
        id: project.id,
        name: project.name,
        description: project.description,
        blocks: project.nodes.map(n=> serializeNode(n)),
        edges: project.edges.map(e=> ({ source: e.source, target: e.target }))
      }
    };
    const text = JSON.stringify(payload, null, 2);
    downloadText(`${slug(project.name)}.datagent.json`, text);
  };

  return (
    <div className="relative">
      <button onClick={()=>setOpen(o=>!o)} className="relative pl-3 pr-8 py-1.5 rounded-xl border bg-white hover:bg-zinc-200">
        <span>Execution</span>
        <span className={`pointer-events-none absolute right-[2px] top-1/2 -translate-y-1/2 text-zinc-500 ${open?'-rotate-90':'rotate-90'}`}>⟨</span>
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-[380px] bg-white border rounded-xl shadow-xl p-3 z-20">
          <div className="text-sm font-medium mb-2">Schedules</div>
          <div className="max-h-60 overflow-auto space-y-2">
            {project.nodes.filter(n=> n.data.type==="output").map(n=> (
              <div key={n.id} className="border rounded-lg p-2">
                <div className="text-sm font-medium">{n.data.title || "Output"}</div>
                <div className="text-xs text-zinc-500">{n.data.destination?.kind ?? "not set"}</div>
                <div className="text-xs mt-1">schedule: <b>{n.data.schedule ?? "—"}</b></div>
              </div>
            ))}
            {project.nodes.filter(n=> n.data.type==="output").length===0 && (
              <div className="text-xs text-zinc-500">No output blocks yet.</div>
            )}
          </div>
          <div className="h-px bg-zinc-200 my-2" />
          <div className="text-sm font-medium mb-2">Actions</div>
          <div className="grid grid-cols-2 gap-2">
            <button className="rounded-lg border py-2 hover:bg-zinc-50" onClick={exportJSON}>Export JSON</button>
            <button className="rounded-lg border py-2 hover:bg-zinc-50" onClick={()=> window.alert("Background scheduler is not implemented in the frontend.")}>Start Schedules</button>
          </div>
        </div>
      )}
    </div>
  )
}

function serializeNode(n: Node<NodeData>){
  const d = n.data;
  return {
    id: n.id,
    type: d.type,
    title: d.title,
    inputs: undefined, // derive from edges on backend
    // properties by type
    ...(d.type==="input" ? { source: d.input?.source, accountId: d.input?.boundAccountId } : {}),
    ...(d.type==="process" || d.type==="visualize" ? { conversation: d.convo ?? [], goals: d.goals ?? [] } : {}),
    ...(d.type==="output" ? { destination: d.destination, schedule: d.schedule } : {}),
  };
}

// --------------------------- Utils ---------------------------
function rid(){ return Math.random().toString(36).slice(2); }
function slug(s:string){ return s.toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/(^-|-$)/g,""); }
function sleep(ms:number){ return new Promise(r=> setTimeout(r, ms)); }
function dice(min:number,max:number){ return Math.floor(min + Math.random()*(max-min+1)); }
function downloadText(filename: string, text: string){
  const blob = new Blob([text], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function topo(nodes: Node[], edges: Edge[]){
  const incoming = new Map<string, number>();
  for(const n of nodes) incoming.set(n.id, 0);
  for(const e of edges) incoming.set(e.target as string, (incoming.get(e.target as string)??0)+1);
  const q = nodes.filter(n=> (incoming.get(n.id)??0)===0).map(n=> n.id);
  const adj = new Map<string,string[]>();
  for(const e of edges){ const arr = adj.get(e.source as string) ?? []; arr.push(e.target as string); adj.set(e.source as string, arr); }
  const out: string[] = [];
  while(q.length){ const id = q.shift()!; out.push(id); for(const nb of adj.get(id)??[]){ const v=(incoming.get(nb)??0)-1; incoming.set(nb,v); if(v===0) q.push(nb);} }
  if(out.length < nodes.length){ const remain = nodes.map(n=>n.id).filter(id=>!out.includes(id)); return out.concat(remain); }
  return out;
}

function sampleRows(n:number){
  const rows = [] as Array<Record<string, any>>;
  for(let i=0;i<n;i++) rows.push({ id: i+1, customer_id: 1000+i, amount: +(Math.random()*1000).toFixed(2), currency: ["USD","EUR","CAD"][i%3], country: ["US","CA","UK","DE"][i%4] });
  return rows;
}

function synthesizeGoals(goals:string[], msg:string){
  const parts = msg.split(/[.;]|\nand\b|,\s*/i).map(s=> s.trim()).filter(Boolean);
  for(const p of parts){ if(!goals.some(g=> g.toLowerCase()===p.toLowerCase())) goals.push(p); }
  return goals.slice(0,12);
}
function Logo({ size = 28, className = "" }: { size?: number; className?: string }){
  const [err, setErr] = useState(false);
  const [src, setSrc] = useState<string>("/logo.png");
  return (
    <div
      className={`inline-grid place-items-center ${className}`}
      style={{ width: size, height: size }}
    >
      {err ? (
        <div className="bg-indigo-600 w-full h-full" />
      ) : (
        <img
          src={src}
          alt="Datagent"
          className="block max-w-[90%] max-h-[90%] object-contain"
          onError={() => {
            if (src !== "/logo.svg") setSrc("/logo.svg"); else setErr(true);
          }}
        />
      )}
    </div>
  );
}
