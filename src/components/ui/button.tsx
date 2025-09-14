import * as React from "react";
export function Button({
  className = "",
  size = "md",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { size?: "sm"|"md"|"lg" }) {
  const sz = size==="sm" ? "px-2 py-1 text-sm" : size==="lg" ? "px-4 py-2" : "px-3 py-1.5";
  return (
    <button
      className={`rounded-xl bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 ${sz} ${className}`}
      {...props}
    />
  );
}
