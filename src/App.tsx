import React, { useState, useCallback, useEffect, useRef } from "react";
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
import type { Edge, Node, Connection, ReactFlowInstance, NodeProps } from "reactflow";
import { Handle, Position, getNodesBounds, getViewportForBounds } from "reactflow";

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

type InputSourceKind = "csv" | "google_sheet" | "s3" | "yahoo_finance" | "url";

// minimal, extensible config payloads per source kind
interface InputConfigBase { kind: InputSourceKind }
interface CSVConfig extends InputConfigBase { path?: string; delimiter?: string; }
interface SheetConfig extends InputConfigBase { sheet?: string; range?: string; }
interface S3Config extends InputConfigBase { bucket?: string; prefix?: string; pattern?: string; }
interface YahooConfig extends InputConfigBase { tickers?: string; interval?: "1d" | "1h" | "1m" }
interface URLConfig extends InputConfigBase { url?: string; }

type InputConfig = CSVConfig | SheetConfig | S3Config | YahooConfig | URLConfig;

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
  _in?: number;
  _out?: number;
  _selected?: boolean;
  _onSelect?: () => void;
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

// Token→CO2 estimate removed with inspector

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
      <div className={`absolute left-1/2 top-10 -translate-x-1/2 ${wide ? "w-[920px]" : "w-[640px]"} max-w-[95vw] bg-white rounded-2xl shadow-xl border`}>
        <div className="px-5 py-3 border-b flex items-center justify-between">
          <div className="font-semibold">{title}</div>
          <button className="text-zinc-500 hover:text-black" onClick={onClose}>✕</button>
        </div>
        <div className="p-4 max-h-[85vh] overflow-auto">{children}</div>
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
  const locked = false;
  const miniMapHeight = 120;
  const [miniMapWidth, setMiniMapWidth] = useState<number>(200);

  // keep outer project state in sync
  useEffect(()=>{
    setProjects(curr=> curr.map(p=> p.id===project.id ? ({...p, nodes, edges}) : p));
  }, [nodes, edges]);

  // Keyboard event handler for 'e' key to open modal
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.key === 'e' || e.key === 'E') {
        if (selectedNodeId) {
          const selectedNode = nodes.find(n => n.id === selectedNodeId);
          if (selectedNode) {
            openModalFor(selectedNode as Node<NodeData>);
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [selectedNodeId, nodes]);

  const onConnect = useCallback((conn: Edge | Connection) => {
    setEdges((eds) => addEdge({ ...conn, animated: true, markerEnd:{ type: MarkerType.ArrowClosed } }, eds));
  }, []);

  // Remove the old datagent-configure event listener since we're using keyboard now

  // drag from palette disabled; click to add

  const onDragOver = (event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  };

  const onDrop = (event: React.DragEvent) => {
    event.preventDefault();
    const type = event.dataTransfer.getData('application/datagent') as BlockType;
    if (!type) return;
    const inst = rfInstRef.current;
    if (!inst) return;
    const pos = inst.screenToFlowPosition({ x: event.clientX, y: event.clientY });
    const id = `${type}-${rid().slice(0,5)}`;
    const base: NodeData = { type, title: titleFor(type), status: "empty" };
    setNodes(ns => ns.concat({ id, position: pos, data: base, type } as Node<NodeData>));
  };

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
    setNodes(ns=> ns.concat({ id, position, data: base, type: type as any }));
  };

  // no inspector selection needed
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

  // Inspector run removed

  return (
    <div ref={canvasRef} className="h-[calc(100%-56px)] relative">
      {/* Palette */}
      <div className="absolute z-10 left-4 top-4 bg-white rounded-2xl border shadow py-3 px-0 overflow-visible">
        <div className="text-xs uppercase tracking-wide text-zinc-500 px-4 pb-2">Blocks</div>
        <div className="flex items-center gap-4 px-5">
          <div>
            <ShapeBtn type="input" color="sky" onClick={()=>addNode("input")} onDragStart={()=>{}} />
          </div>
          <div className="mr-[1px]">
            <ShapeBtn type="process" color="violet" onClick={()=>addNode("process")} onDragStart={()=>{}} />
          </div>
          <div className="ml-[1px]">
            <ShapeBtn type="visualize" color="emerald" onClick={()=>addNode("visualize")} onDragStart={()=>{}} />
          </div>
          <div>
            <ShapeBtn type="output" color="amber" onClick={()=>addNode("output")} onDragStart={()=>{}} />
          </div>
        </div>
      </div>

      {/* Canvas */}
      <ReactFlow
        nodeTypes={{ input: CanvasNode, process: CanvasNode, visualize: CanvasNode, output: CanvasNode }}
        nodes={nodes.map(n=> {
          const inCount = edges.filter(e=> e.target===n.id).length;
          const outCount = edges.filter(e=> e.source===n.id).length;

          return { 
            ...n, 
            type: (n.data.type as any), 
            style: { background: 'transparent', border: 'none', boxShadow: 'none', padding: 0 },
            data: { ...n.data, _in: inCount, _out: outCount, _selected: selectedNodeId === n.id, _onSelect: () => setSelectedNodeId(selectedNodeId === n.id ? null : n.id) }
          };
        })}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onDragOver={onDragOver}
        onDrop={onDrop}
        onNodeClick={(_, node) => {
          setSelectedNodeId(selectedNodeId === node.id ? null : node.id);
        }}
        onNodeDrag={(_, node) => {
          setSelectedNodeId(node.id);
        }}
        onPaneClick={() => setSelectedNodeId(null)}
        onInit={(inst) => { rfInstRef.current = inst; /* equal-fit happens in measure */ }}
        isValidConnection={(c)=> {
          const s = nodes.find(n=> n.id === c.source);
          const t = nodes.find(n=> n.id === c.target);
          if(!s || !t) return false;
          // prevent multiple edges on the same handle
          if (c.source && c.sourceHandle && edges.some(e=> e.source===c.source && e.sourceHandle===c.sourceHandle)) return false;
          if (c.target && c.targetHandle && edges.some(e=> e.target===c.target && e.targetHandle===c.targetHandle)) return false;
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
        {/* listen for configure events from nodes */}
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

      {/* Inspector removed */}

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

function ShapeBtn({ type, color: _color, onClick, onDragStart }:{ type: BlockType; color: 'sky'|'violet'|'emerald'|'amber'; onClick:()=>void; onDragStart:(e:React.DragEvent)=>void }){
  // Show lowercase labels as requested
  const label = type;
  const fill = type==='input' ? '#17BDFD' : type==='process' ? '#F14D1D' : type==='visualize' ? '#A259FF' : '#03CF83';
  const H = 64; // unified visual height for all shapes
  const TRI_W = Math.round(H * Math.sqrt(3) / 2);
  const DIAMOND_SIDE = Math.round(H / Math.sqrt(2)); // rotated square fits into H
  const BOX_W = 64; // unify width for consistent spacing

  let shape: React.ReactElement;
  if(type==='input'){
    const h = H;
    const w = TRI_W;
    const vX = w - 0.5; // align vertical stroke on pixel grid
    shape = (
      <svg className="block" width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
        <polygon points={`0,${h/2} ${w},0 ${w},${h}`} fill={fill} />
        <line x1={0} y1={h/2} x2={w} y2={0} stroke="#000" strokeWidth={1} shapeRendering="crispEdges" vectorEffect="non-scaling-stroke" />
        <line x1={vX} y1={0} x2={vX} y2={h} stroke="#000" strokeWidth={1.5} shapeRendering="crispEdges" vectorEffect="non-scaling-stroke" />
        <line x1={w} y1={h} x2={0} y2={h/2} stroke="#000" strokeWidth={1} shapeRendering="crispEdges" vectorEffect="non-scaling-stroke" />
      </svg>
    );
  } else if(type==='process'){
    shape = <div className="block" style={{ width: H, height: H, background: fill, border: '1px solid #000' }} />;
  } else if(type==='visualize'){
    shape = <div className="block" style={{ width: DIAMOND_SIDE, height: DIAMOND_SIDE, background: fill, transform: 'rotate(45deg)', border: '1px solid #000' }} />;
  } else {
    const h = H;
    const w = TRI_W;
    const vX = 0.5; // align vertical stroke on pixel grid (left side)
    shape = (
      <svg className="block" width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
        <polygon points={`0,0 0,${h} ${w},${h/2}`} fill={fill} />
        <line x1={0} y1={0} x2={w} y2={h/2} stroke="#000" strokeWidth={1} shapeRendering="crispEdges" vectorEffect="non-scaling-stroke" />
        <line x1={vX} y1={0} x2={vX} y2={h} stroke="#000" strokeWidth={1.5} shapeRendering="crispEdges" vectorEffect="non-scaling-stroke" />
        <line x1={w} y1={h/2} x2={0} y2={h} stroke="#000" strokeWidth={1} shapeRendering="crispEdges" vectorEffect="non-scaling-stroke" />
      </svg>
    );
  }
  const labelShift = type==='output' ? 1 : 0; // move output text 1px right
  return (
    <div className="flex items-center justify-center">
      <button onClick={onClick} draggable={false} onDragStart={onDragStart} className="relative flex flex-col items-center">
        <div className="grid place-items-center" style={{ width: BOX_W, height: H }}>
          {shape}
        </div>
        <div className="text-[12px] text-black font-bold" style={{ marginLeft: labelShift, marginTop: 6 }}>
          {label}
        </div>
      </button>
    </div>
  );
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

// defaultPreviewFor removed with inspector run

// --------------------------- Inspector ---------------------------
// Inspector removed

// --------------------------- Custom Canvas Nodes ---------------------------
// node props type imported at top

function CanvasNode(props: NodeProps<NodeData>){
  const t = props.type as BlockType;
  const inCount = props.data._in ?? 0;
  const outCount = props.data._out ?? 0;
  const isSelected = props.data._selected ?? false;
  const cfg = t==='input' ? { leftTargets: 0, rightSources: outCount + 1 }
    : t==='process' ? { leftTargets: inCount + 1, rightSources: outCount + 1 }
    : t==='visualize' ? { leftTargets: 1, rightSources: 1 }
    : { leftTargets: inCount + 1, rightSources: 0 };
  // Keep process 100x100, others 100 tall; make input/output equilateral (width = sqrt(3)/2 * height)
  const isTriangle = t==='input' || t==='output';
  const sizeH = 100;
  const sizeW = t==='process' ? 100 : (t==='visualize' ? sizeH : (isTriangle ? Math.round(sizeH * Math.sqrt(3) / 2) : 120));
  
  // Base colors; selected becomes slightly lighter
  const baseColors = {
    input: '#17BDFD',
    process: '#F14D1D', 
    visualize: '#A259FF',
    output: '#03CF83'
  };
  const lightenHex = (hex: string, amt: number) => {
    try {
      const h = hex.replace('#','');
      const r = parseInt(h.slice(0,2), 16);
      const g = parseInt(h.slice(2,4), 16);
      const b = parseInt(h.slice(4,6), 16);
      const f = (v:number)=> Math.max(0, Math.min(255, Math.round(v + (255 - v) * amt)));
      const to2 = (v:number)=> v.toString(16).padStart(2, '0');
      return `#${to2(f(r))}${to2(f(g))}${to2(f(b))}`;
    } catch { return hex; }
  };
  const fill = (props.data._selected ? lightenHex(baseColors[t], 0.3) : baseColors[t]);
  // Border thickness to indicate selection
  const edgeStroke = isSelected ? 3 : 1;     // diagonal edges
  const vertStroke = isSelected ? 4 : 1.5;   // vertical edge slightly thicker for visual parity

  const makeHandles = (side: 'left'|'right', count: number, type: 'source'|'target') => {
    const arr: React.ReactElement[] = [];
    for(let i=0;i<count;i++){
      const topPct = ((i+1)/(count+1))*100;
      arr.push(
        <Handle
          key={`${side}-${type}-${i}`}
          type={type}
          position={side==='left'?Position.Left:Position.Right}
          id={`${side}-${type}-${i}`}
          style={{ top: `${topPct}%`, background: '#000', width: 8, height: 8, borderRadius: 4, border: 'none' }}
        />
      );
    }
    return arr;
  };

  return (
    <div 
      className="relative select-none cursor-pointer" 
      style={{ 
        width: sizeW, 
        height: sizeH,
        filter: isSelected ? 'drop-shadow(0 0 8px rgba(0,0,0,0.3))' : 'none'
      }} 
    >
      {t==='process' && (
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2" style={{ width: sizeW, height: sizeH, background: fill, border: `${isSelected ? 4 : 1}px solid #000` }} />
      )}
      {t==='visualize' && (
        (() => {
          const side = Math.round(sizeH / Math.sqrt(2));
          return (
            <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2" style={{ width: side, height: side, background: fill, transform: 'rotate(45deg)', border: `${isSelected ? 4 : 1}px solid #000` }} />
          );
        })()
      )}
      {t==='input' && (
        // Equilateral right-facing triangle with crisp, uniform edges
        <svg className="absolute inset-0" width={sizeW} height={sizeH} viewBox={`0 0 ${sizeW} ${sizeH}`}>
          {/* fill */}
          <polygon points={`0,${sizeH/2} ${sizeW},0 ${sizeW},${sizeH}`} fill={fill} />
          {/* edges */}
          <line x1={0} y1={sizeH/2} x2={sizeW} y2={0} stroke="#000" strokeWidth={edgeStroke} shapeRendering="crispEdges" vectorEffect="non-scaling-stroke" />
          <line x1={sizeW - 0.5} y1={0} x2={sizeW - 0.5} y2={sizeH} stroke="#000" strokeWidth={vertStroke} shapeRendering="crispEdges" vectorEffect="non-scaling-stroke" />
          <line x1={sizeW} y1={sizeH} x2={0} y2={sizeH/2} stroke="#000" strokeWidth={edgeStroke} shapeRendering="crispEdges" vectorEffect="non-scaling-stroke" />
        </svg>
      )}
      {t==='output' && (
        // Equilateral left-facing triangle with crisp, uniform edges
        <svg className="absolute inset-0" width={sizeW} height={sizeH} viewBox={`0 0 ${sizeW} ${sizeH}`}>
          {/* fill */}
          <polygon points={`0,0 0,${sizeH} ${sizeW},${sizeH/2}`} fill={fill} />
          {/* edges */}
          <line x1={0} y1={0} x2={sizeW} y2={sizeH/2} stroke="#000" strokeWidth={edgeStroke} shapeRendering="crispEdges" vectorEffect="non-scaling-stroke" />
          <line x1={0.5} y1={0} x2={0.5} y2={sizeH} stroke="#000" strokeWidth={vertStroke} shapeRendering="crispEdges" vectorEffect="non-scaling-stroke" />
          <line x1={sizeW} y1={sizeH/2} x2={0} y2={sizeH} stroke="#000" strokeWidth={edgeStroke} shapeRendering="crispEdges" vectorEffect="non-scaling-stroke" />
        </svg>
      )}

      {makeHandles('left', (cfg as any).leftTargets, 'target')}
      {makeHandles('right', (cfg as any).rightSources, 'source')}

      {/* double-click the node to configure; no inline button */}
    </div>
  );
}

// PreviewCard removed

// --------------------------- Node Modals ---------------------------
function InputNodeModal({ node, onClose, onSave }:{ node: Node<NodeData>; onClose:()=>void; onSave:(d:NodeData)=>void }){
  const d = node.data;
  const [kind, setKind] = useState<InputSourceKind>((d.input?.source.kind) || "csv");
  const [cfg, setCfg] = useState<InputConfig>(d.input?.source || { kind: "csv", delimiter: "," });

  const updateCfg = (patch: Partial<InputConfig>) => setCfg(prev => ({...prev, ...patch} as any));

  const handleSave = () => {
    const updatedData: NodeData = {
      ...d,
      input: {
        source: cfg,
        boundAccountId: d.input?.boundAccountId
      },
      status: "configured"
    };
    onSave(updatedData);
    onClose();
  };

  return (
    <Modal title="Configure Input" onClose={onClose}>
      <div className="space-y-3 text-sm">
        <div>
          <label className="text-xs text-zinc-600 block mb-2">Data Source</label>
          <div className="flex gap-3">
            <button
              onClick={() => { setKind("url"); setCfg({kind:"url"} as any); }}
              className={`flex items-center justify-center w-16 h-16 rounded-lg border-2 transition-colors ${
                kind === "url" 
                  ? "border-violet-500 bg-violet-50 text-violet-600" 
                  : "border-gray-200 hover:border-gray-300 text-gray-500"
              }`}
            >
              <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M12.586 4.586a2 2 0 112.828 2.828l-3 3a2 2 0 01-2.828 0 1 1 0 00-1.414 1.414 4 4 0 005.656 0l3-3a4 4 0 00-5.656-5.656l-1.5 1.5a1 1 0 101.414 1.414l1.5-1.5zm-5 5a2 2 0 012.828 0 1 1 0 101.414-1.414 4 4 0 00-5.656 0l-3 3a4 4 0 105.656 5.656l1.5-1.5a1 1 0 10-1.414-1.414l-1.5 1.5a2 2 0 11-2.828-2.828l3-3z" clipRule="evenodd" />
              </svg>
            </button>
            <button
              onClick={() => { setKind("csv"); setCfg({kind:"csv", delimiter: ","} as any); }}
              className={`flex items-center justify-center w-16 h-16 rounded-lg border-2 transition-colors ${
                kind === "csv" 
                  ? "border-violet-500 bg-violet-50 text-violet-600" 
                  : "border-gray-200 hover:border-gray-300 text-gray-500"
              }`}
            >
              <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
        {kind==="url" && (
          <div>
            <label className="text-xs">Data URL</label>
            <input 
              className="mt-1 w-full border rounded-lg px-2 py-2" 
              placeholder="https://example.com/data.csv" 
              value={(cfg as any).url || ""}
              onChange={(e)=> updateCfg({ url: e.target.value } as any)} 
            />
          </div>
        )}
        {kind==="csv" && (
          <div>
            <label className="text-xs">Upload CSV File</label>
            <input 
              type="file" 
              accept=".csv" 
              className="mt-1 w-full border rounded-lg px-2 py-2 file:mr-4 file:py-1 file:px-2 file:rounded file:border-0 file:text-sm file:bg-violet-50 file:text-violet-700 hover:file:bg-violet-100" 
              onChange={(e)=> {
                const file = e.target.files?.[0];
                if (file) updateCfg({ path: file.name } as any);
              }} 
            />
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

        <div className="flex justify-end pt-4 border-t mt-4">
          <button className="px-3 py-2 rounded-lg bg-[#6250A5] text-white hover:bg-[#544691]" onClick={handleSave}>Save</button>
        </div>
      </div>
    </Modal>
  )
}

function ProcessNodeModal({ node, onClose, onSave }:{ node: Node<NodeData>; onClose:()=>void; onSave:(d:NodeData)=>void }){
  const d = node.data;
  const [transformation, setTransformation] = useState<string>(d.convo?.[0]?.content || "");

  const handleSave = () => {
    const updatedData: NodeData = {
      ...d,
      convo: transformation ? [{ role: "user", content: transformation }] : [],
      status: "configured"
    };
    onSave(updatedData);
    onClose();
  };

  return (
    <Modal title="Configure Process" onClose={onClose}>
      <div className="space-y-4 text-sm">
        <div>
          <label className="text-xs text-zinc-600 block mb-2">Data Transformation</label>
          <textarea 
            className="w-full border rounded-lg px-3 py-3 h-32 resize-none" 
            placeholder="Explain how you want your data to be transformed"
            value={transformation}
            onChange={(e) => setTransformation(e.target.value)}
          />
        </div>
        <div className="flex justify-end pt-4 mt-4">
          <button className="px-3 py-2 rounded-lg bg-[#6250A5] text-white hover:bg-[#544691]" onClick={handleSave}>Save</button>
        </div>
      </div>
    </Modal>
  )
}

function VisualizeNodeModal({ node, onClose, onSave: _onSave }:{ node: Node<NodeData>; onClose:()=>void; onSave:(d:NodeData)=>void }){
  void node; // keep param used
  const [userInput, setUserInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [chartHtml, setChartHtml] = useState("");
  const [error, setError] = useState("");
  // no local sample data needed

  const generateVisualization = async () => {
    if (!userInput.trim()) return;
    
    setIsLoading(true);
    setError("");

    try {
      const response = await fetch('http://localhost:8080/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_input: userInput,
          chart_code: ""
        })
      });

      if (!response.ok) {
        throw new Error(`Backend error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Backend response:', data);
      
      if (data.error) {
        setError(data.error);
      } else {
        console.log('Setting chart HTML:', data.chart_html ? 'HTML received' : 'No HTML');
        setChartHtml(data.chart_html);
      }
      
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      generateVisualization();
    }
  };

  // preview handled inline via iframe/chartHtml

  return (
    <Modal title="Configure Visualization" onClose={onClose} wide={true}>
      <div className="-m-4 flex flex-col h-[70vh]">
        {/* Chart Preview */}
        <div className="flex-1 w-full flex items-center justify-center min-h-0 p-4">
          {chartHtml ? (
            <div className="w-full h-full flex items-center justify-center">
              <iframe 
                srcDoc={chartHtml}
                style={{ 
                  width: '100%', 
                  height: '100%', 
                  border: 'none', 
                  display: 'block',
                  maxWidth: '900px',
                  maxHeight: '600px',
                  marginLeft: '200px'
                }}
                title="Generated Chart"
              />
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500 border-2 border-dashed border-gray-300 rounded w-full">
              {isLoading ? "Generating visualization..." : "Enter a visualization request below"}
            </div>
          )}
        </div>

        {/* User Input */}
        <div className="rounded-xl bg-white p-4 m-4 flex-shrink-0">
          {error && (
            <div className="mb-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded p-3">
              {error}
            </div>
          )}
          <div className="flex gap-3">
            <input
              type="text"
              className="flex-1 border rounded-lg px-3 py-2"
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="e.g., 'Create a scatter plot of sepal_length vs sepal_width colored by species'"
              disabled={isLoading}
            />
            <button
              onClick={generateVisualization}
              disabled={isLoading || !userInput.trim()}
              className="px-6 py-2 rounded-lg bg-violet-600 text-white hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isLoading && (
                <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
              )}
              Generate
            </button>
          </div>
        </div>
      </div>
    </Modal>
  )
}

function OutputNodeModal({ node, onClose, onSave }:{ node: Node<NodeData>; onClose:()=>void; onSave:(d:NodeData)=>void }){
  const d = node.data;
  const [kind, setKind] = useState<Destination["kind"]>(d.destination?.kind ?? "email");
  const [config, setConfig] = useState<Record<string,any>>(d.destination?.config ?? {});
  const [schedule, setSchedule] = useState<string>(d.schedule ?? "");

  const handleSave = () => {
    const updatedData: NodeData = {
      ...d,
      destination: { kind, config },
      schedule: schedule || null,
      status: "configured"
    };
    onSave(updatedData);
    onClose();
  };

  return (
    <Modal title="Configure Output" onClose={onClose}>
      <div className="space-y-3 text-sm">
        <div>
          <label className="text-xs text-zinc-600 block mb-2">Destination</label>
          <div className="flex gap-3">
            <button
              onClick={() => setKind("email")}
              className={`flex items-center justify-center w-16 h-16 rounded-lg border-2 transition-colors ${
                kind === "email" 
                  ? "border-violet-500 bg-violet-50 text-violet-600" 
                  : "border-gray-200 hover:border-gray-300 text-gray-500"
              }`}
            >
              <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
                <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
              </svg>
            </button>
            <button
              onClick={() => setKind("slack")}
              className={`flex items-center justify-center w-16 h-16 rounded-lg border-2 transition-colors ${
                kind === "slack" 
                  ? "border-violet-500 bg-violet-50 text-violet-600" 
                  : "border-gray-200 hover:border-gray-300 text-gray-500"
              }`}
            >
              <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 24 24">
                <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z"/>
              </svg>
            </button>
          </div>
        </div>

        {kind==="email" && (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs">To</label>
              <input className="mt-1 w-full border rounded-lg px-2 py-2" placeholder="ops@company.com" value={config.to || ""} onChange={(e)=> setConfig({...config, to: e.target.value})} />
            </div>
            <div>
              <label className="text-xs">Subject</label>
              <input className="mt-1 w-full border rounded-lg px-2 py-2" placeholder="Weekly KPI" value={config.subject || ""} onChange={(e)=> setConfig({...config, subject: e.target.value})} />
            </div>
          </div>
        )}
        {kind==="slack" && (
          <div>
            <label className="text-xs">Channel</label>
            <input className="mt-1 w-full border rounded-lg px-2 py-2" placeholder="#analytics" value={config.channel || ""} onChange={(e)=> setConfig({...config, channel: e.target.value})} />
          </div>
        )}
        {kind==="gdrive" && (
          <div>
            <label className="text-xs">Folder path</label>
            <input className="mt-1 w-full border rounded-lg px-2 py-2" placeholder="/Reports/Weekly" value={config.folder || ""} onChange={(e)=> setConfig({...config, folder: e.target.value})} />
          </div>
        )}

        <div>
          <label className="text-xs text-zinc-600">Schedule (optional)</label>
          <input className="mt-1 w-full border rounded-lg px-2 py-2" placeholder="e.g. Mondays 9am, and also every time an alert is set." value={schedule} onChange={(e)=> setSchedule(e.target.value)} />
          <div className="text-[11px] text-zinc-500 mt-1">Tip: Leave empty to only send on manual runs.</div>
        </div>

        <div className="flex justify-end pt-4 border-t mt-4">
          <button className="px-3 py-2 rounded-lg bg-[#6250A5] text-white hover:bg-[#544691]" onClick={handleSave}>Save</button>
        </div>
      </div>
    </Modal>
  )
}

// --------------------------- Exec Bar (top-right) ---------------------------
function ExecBar({ project }:{ project: Project }){
  const [open, setOpen] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<any>(null);

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

  const compileBlocksForExecution = () => {
    const blocks: any[] = [];
    
    // Process each node and convert to backend API format
    project.nodes.forEach(node => {
      const nodeData = node.data;
      let block: any = {
        block_id: parseInt(node.id.split('-')[1]) || Math.floor(Math.random() * 1000),
        block_type: mapNodeTypeToBlockType(nodeData.type)
      };

      // Add prerequisites based on edges
      const incomingEdges = project.edges.filter(edge => edge.target === node.id);
      if (incomingEdges.length > 0) {
        block.pre_req = incomingEdges.map(edge => {
          const sourceNode = project.nodes.find(n => n.id === edge.source);
          return parseInt(sourceNode?.id.split('-')[1] || '0') || Math.floor(Math.random() * 1000);
        });
      }

      // Add block-specific fields
      switch (nodeData.type) {
        case 'input':
          if (nodeData.input?.source?.kind === 'csv' && (nodeData.input.source as any).path) {
            block.csv_source = (nodeData.input.source as any).path;
          } else {
            block.csv_source = '/path/to/default.csv'; // fallback
          }
          break;
          
        case 'process':
          // Get the latest user message from conversation
          const userMessages = nodeData.convo?.filter(turn => turn.role === 'user') || [];
          block.prompt = userMessages.length > 0 
            ? userMessages[userMessages.length - 1].content 
            : 'Process the data';
          break;
          
        case 'visualize':
          // Get the latest user message from conversation
          const vizUserMessages = nodeData.convo?.filter(turn => turn.role === 'user') || [];
          block.prompt = vizUserMessages.length > 0 
            ? vizUserMessages[vizUserMessages.length - 1].content 
            : 'Create a visualization';
          // Map visualize to process for backend
          block.block_type = 'process';
          break;
          
        case 'output':
          if (nodeData.destination?.kind === 'email' && nodeData.destination.config?.email) {
            block.email_dest = nodeData.destination.config.email;
            block.block_type = 'destination';
          } else {
            block.init_script = 'print("Output processed")';
            block.block_type = 'output';
          }
          break;
      }

      blocks.push(block);
    });

    return blocks;
  };

  const executeWorkflow = async () => {
    setExecuting(true);
    setExecutionResult(null);
    
    try {
      const blocks = compileBlocksForExecution();
      
      // Show the compiled JSON in an alert
      alert('Compiled JSON for execution:\n\n' + JSON.stringify(blocks, null, 2));
      
      const response = await fetch('http://localhost:8080/blocks/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(blocks)
      });

      const result = await response.json();
      setExecutionResult(result);
      
      if (result.success) {
        console.log('Workflow executed successfully:', result);
      } else {
        console.error('Workflow execution failed:', result);
      }
    } catch (error) {
      console.error('Error executing workflow:', error);
      setExecutionResult({ 
        success: false, 
        error: `Network error: ${error instanceof Error ? error.message : 'Unknown error'}` 
      });
    } finally {
      setExecuting(false);
    }
  };

  const mapNodeTypeToBlockType = (nodeType: string): string => {
    switch (nodeType) {
      case 'input': return 'input_source';
      case 'process': return 'process';
      case 'visualize': return 'process'; // visualize maps to process
      case 'output': return 'output'; // will be changed to 'destination' if email
      default: return 'process';
    }
  };

  return (
    <div className="relative">
      <div className="flex items-center gap-2">
        <button 
          onClick={executeWorkflow}
          disabled={executing || project.nodes.length === 0}
          className={`px-4 py-1.5 rounded-xl text-white font-medium ${
            executing || project.nodes.length === 0
              ? 'bg-gray-400 cursor-not-allowed' 
              : 'bg-green-600 hover:bg-green-700'
          }`}
        >
          {executing ? 'Executing...' : 'Execute'}
        </button>
        <button onClick={()=>setOpen(o=>!o)} className="relative pl-3 pr-10 py-1.5 rounded-xl border bg-white hover:bg-zinc-200">
          <span>Options</span>
          <span className={`pointer-events-none absolute right-[20px] top-1/2 -translate-y-1/2 text-zinc-500 ${open?'-rotate-270':'rotate-270'}`}>⟨</span>
        </button>
      </div>
      {open && (
        <div className="absolute right-0 mt-2 w-[420px] bg-white border rounded-xl shadow-xl p-3 z-20">
          {/* Execution Results */}
          {executionResult && (
            <div className="mb-4">
              <div className="text-sm font-medium mb-2">Last Execution Result</div>
              <div className={`p-3 rounded-lg border ${executionResult.success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                <div className={`text-sm font-medium ${executionResult.success ? 'text-green-800' : 'text-red-800'}`}>
                  {executionResult.success ? '✅ Success' : '❌ Failed'}
                </div>
                <div className="text-xs mt-1 text-gray-600">
                  {executionResult.message || executionResult.error}
                </div>
                {executionResult.success && (
                  <div className="text-xs mt-1 text-gray-500">
                    Processed {executionResult.processed_blocks || 0} blocks
                  </div>
                )}
                {executionResult.errors && executionResult.errors.length > 0 && (
                  <div className="mt-2">
                    <div className="text-xs font-medium text-red-700">Errors:</div>
                    {executionResult.errors.map((error: string, idx: number) => (
                      <div key={idx} className="text-xs text-red-600 mt-1">• {error}</div>
                    ))}
                  </div>
                )}
              </div>
              <div className="h-px bg-zinc-200 my-3" />
            </div>
          )}
          
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
// sleep/dice removed
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

// topo removed

// helpers removed
function Logo({ size = 28, className = "" }: { size?: number; className?: string }){
  const [err, setErr] = useState(false);
  const [src, setSrc] = useState<string>("/logo.png");
  return (
    <div className={`inline-grid place-items-center ${className}`} style={{ width: size, height: size }}>
      {err ? (
        <div className="bg-indigo-600 w-full h-full" />
      ) : (
        <img
          src={src}
          alt="Datagent"
          style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          onError={() => { if (src !== '/logo.svg') setSrc('/logo.svg'); else setErr(true); }}
        />
      )}
    </div>
  );
}
