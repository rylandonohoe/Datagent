import * as React from "react";
export function Dialog({ open, onOpenChange, children }:{ open:boolean; onOpenChange:(v:boolean)=>void; children:React.ReactNode }) {
  if (!open) return null;
  return <div className="fixed inset-0 z-50" onClick={()=>onOpenChange(false)}>{children}</div>;
}
export function DialogContent({ className="", children }:{ className?:string; children:React.ReactNode }) {
  return (
    <>
      <div className="absolute inset-0 bg-black/30" />
      <div className={`absolute left-1/2 top-16 -translate-x-1/2 w-[640px] max-w-[94vw] rounded-2xl border bg-white shadow-xl ${className}`}
           onClick={(e)=>e.stopPropagation()}>
        {children}
      </div>
    </>
  );
}
export function DialogHeader({ children }:{ children:React.ReactNode }) { return <div className="border-b px-5 py-3">{children}</div>; }
export function DialogTitle({ children }:{ children:React.ReactNode }) { return <div className="text-base font-semibold">{children}</div>; }
export function DialogDescription({ children }:{ children:React.ReactNode }) { return <div className="text-xs text-zinc-500">{children}</div>; }
