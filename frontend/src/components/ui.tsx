"use client";

import { useState, type ButtonHTMLAttributes, type ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";

export function Button({
  variant = "secondary",
  size = "md",
  loading,
  className = "",
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: "sm" | "md" | "lg"; loading?: boolean }) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-xl font-medium transition disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap";
  const sizes = { sm: "h-8 px-3 text-sm", md: "h-10 px-4 text-sm", lg: "h-12 px-6 text-base" };
  const variants: Record<Variant, string> = {
    primary: "brand-gradient text-white shadow-[0_6px_20px_-8px_rgba(124,92,255,0.7)] hover:brightness-105 active:brightness-95",
    secondary: "bg-surface border border-line text-ink hover:bg-surface-2",
    ghost: "text-ink-2 hover:bg-surface-2",
    danger: "bg-surface border border-line text-bad hover:bg-red-50",
  };
  return (
    <button className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} disabled={loading || rest.disabled} {...rest}>
      {loading && <Spinner />}
      {children}
    </button>
  );
}

export function Spinner({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function Badge({ tone = "neutral", children, className = "" }: { tone?: "neutral" | "good" | "warn" | "bad" | "violet" | "orange" | "pink"; children: ReactNode; className?: string }) {
  const tones = {
    neutral: "bg-surface-2 text-ink-2 border-line",
    good: "bg-emerald-50 text-emerald-700 border-emerald-200",
    warn: "bg-amber-50 text-amber-700 border-amber-200",
    bad: "bg-red-50 text-red-700 border-red-200",
    violet: "bg-violet-50 text-violet-700 border-violet-200",
    orange: "bg-orange-50 text-orange-700 border-orange-200",
    pink: "bg-pink-50 text-pink-700 border-pink-200",
  };
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${tones[tone]} ${className}`}>
      {children}
    </span>
  );
}

export function ScoreRing({ value, max = 100, size = 120, label }: { value: number; max?: number; size?: number; label?: string }) {
  const r = (size - 14) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(1, value / max));
  const id = `ring-${size}-${label ?? "x"}`.replace(/\s/g, "");
  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--violet)" />
            <stop offset="60%" stopColor="var(--pink)" />
            <stop offset="100%" stopColor="var(--orange)" />
          </linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={r} stroke="var(--surface-2)" strokeWidth="10" fill="none" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke={`url(#${id})`}
          strokeWidth="10"
          strokeLinecap="round"
          fill="none"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - pct)}
          style={{ transition: "stroke-dashoffset 600ms ease" }}
        />
      </svg>
      <div className="absolute text-center">
        <div className="text-3xl font-semibold tracking-tight">{Math.round(value)}</div>
        <div className="text-[11px] text-ink-3">/ {max}</div>
      </div>
    </div>
  );
}

export function Bar({ value, max, tone = "brand" }: { value: number; max: number; tone?: "brand" | "muted" }) {
  const pct = max ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
  return (
    <div className="h-2 w-full rounded-full bg-surface-2 overflow-hidden">
      <div
        className={`h-full rounded-full ${tone === "brand" ? "brand-gradient" : "bg-ink-3/40"}`}
        style={{ width: `${pct}%`, transition: "width 500ms ease" }}
      />
    </div>
  );
}

export function CheckIcon({ ok, className = "h-4 w-4" }: { ok: boolean; className?: string }) {
  return ok ? (
    <svg viewBox="0 0 20 20" className={`${className} text-good`} fill="currentColor" aria-label="passed">
      <path fillRule="evenodd" d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm3.7-9.3a1 1 0 0 0-1.4-1.4L9 10.6 7.7 9.3a1 1 0 0 0-1.4 1.4l2 2a1 1 0 0 0 1.4 0l4-4Z" clipRule="evenodd" />
    </svg>
  ) : (
    <svg viewBox="0 0 20 20" className={`${className} text-bad`} fill="currentColor" aria-label="failed">
      <path fillRule="evenodd" d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16ZM8.7 7.3a1 1 0 0 0-1.4 1.4L8.6 10l-1.3 1.3a1 1 0 1 0 1.4 1.4l1.3-1.3 1.3 1.3a1 1 0 0 0 1.4-1.4L11.4 10l1.3-1.3a1 1 0 0 0-1.4-1.4L10 8.6 8.7 7.3Z" clipRule="evenodd" />
    </svg>
  );
}

export function Collapsible({ title, right, children, defaultOpen = false }: { title: ReactNode; right?: ReactNode; children: ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-xl border border-line bg-surface">
      <button className="flex w-full items-center gap-3 px-4 py-3 text-left" onClick={() => setOpen(!open)} aria-expanded={open}>
        <svg className={`h-4 w-4 shrink-0 text-ink-3 transition ${open ? "rotate-90" : ""}`} viewBox="0 0 20 20" fill="currentColor">
          <path d="M7.3 4.3a1 1 0 0 1 1.4 0l5 5a1 1 0 0 1 0 1.4l-5 5a1 1 0 0 1-1.4-1.4L11.6 10 7.3 5.7a1 1 0 0 1 0-1.4Z" />
        </svg>
        <div className="flex-1 min-w-0">{title}</div>
        {right}
      </button>
      {open && <div className="border-t border-line px-4 py-3">{children}</div>}
    </div>
  );
}

export function SectionTitle({ eyebrow, title, desc }: { eyebrow?: string; title: string; desc?: ReactNode }) {
  return (
    <div className="mb-4">
      {eyebrow && <div className="text-xs font-semibold uppercase tracking-wider text-violet">{eyebrow}</div>}
      <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
      {desc && <p className="mt-1 text-sm text-ink-2">{desc}</p>}
    </div>
  );
}

export function ErrorBox({ message, onDismiss }: { message: string; onDismiss?: () => void }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
      <CheckIcon ok={false} className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="flex-1">{message}</div>
      {onDismiss && (
        <button onClick={onDismiss} className="text-red-700/70 hover:text-red-900" aria-label="Dismiss">
          ✕
        </button>
      )}
    </div>
  );
}
