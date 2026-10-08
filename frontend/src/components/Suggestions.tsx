"use client";

import { useState } from "react";
import { wordDiff } from "@/lib/diff";
import type { Change } from "@/lib/types";
import { Badge, Button } from "./ui";

const IMPACT_TONE = { high: "violet", medium: "orange", low: "neutral" } as const;

export const isOn = (c: Change) => c.status === "accepted" || c.status === "applied";

export function DiffView({ original, suggested }: { original: string; suggested: string }) {
  return (
    <p className="text-sm leading-relaxed">
      {wordDiff(original, suggested).map((p, i) =>
        p.type === "same" ? (
          <span key={i}>{p.text}</span>
        ) : (
          <span key={i} className={p.type === "del" ? "diff-del" : "diff-ins"}>
            {p.text}
          </span>
        ),
      )}
    </p>
  );
}

export function SuggestionCard({ change, onToggle, disabled }: { change: Change; onToggle: (on: boolean) => void; disabled?: boolean }) {
  const [view, setView] = useState<"diff" | "side">("diff");
  const on = isOn(change);
  const title = change.entry_label ? `${change.section_title} — ${change.entry_label}` : change.section_title;
  return (
    <div className={`rounded-2xl border p-4 transition ${on ? "border-violet/40 bg-violet-50/30" : "border-line bg-surface"}`}>
      <div className="flex items-start gap-3">
        <label className="mt-0.5 flex cursor-pointer items-center">
          <input
            type="checkbox"
            checked={on}
            disabled={disabled}
            onChange={(e) => onToggle(e.target.checked)}
            className="h-4.5 w-4.5 accent-[var(--violet)]"
            aria-label={`Apply ${change.change_id}`}
          />
        </label>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold">{title}</span>
            <Badge tone={IMPACT_TONE[change.impact]}>ATS impact: {change.impact[0].toUpperCase() + change.impact.slice(1)}</Badge>
            {change.kind === "reorder_skills" && <Badge>Reorder only</Badge>}
            {change.status === "applied" && <Badge tone="good">Applied</Badge>}
            {change.status === "rejected" && <Badge tone="bad">Rejected</Badge>}
            <span className="ml-auto text-[11px] text-ink-3">{change.change_id}</span>
          </div>

          <div className="mt-3">
            <div className="mb-1 flex gap-1 text-[11px]">
              <button className={`rounded-md px-2 py-0.5 ${view === "diff" ? "bg-surface-2 font-medium" : "text-ink-3"}`} onClick={() => setView("diff")}>
                Changes
              </button>
              <button className={`rounded-md px-2 py-0.5 ${view === "side" ? "bg-surface-2 font-medium" : "text-ink-3"}`} onClick={() => setView("side")}>
                Before / After
              </button>
            </div>
            {view === "diff" ? (
              <DiffView original={change.original} suggested={change.suggested} />
            ) : (
              <div className="grid gap-2 sm:grid-cols-2">
                <div className="rounded-xl bg-surface-2/70 p-3">
                  <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-ink-3">Before</div>
                  <p className="text-sm">{change.original}</p>
                </div>
                <div className="rounded-xl bg-emerald-50/70 p-3">
                  <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-emerald-700">Suggested</div>
                  <p className="text-sm">{change.suggested}</p>
                </div>
              </div>
            )}
          </div>

          <div className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
            <div>
              <div className="font-semibold text-ink-2">Why</div>
              <p className="text-ink-2">{change.reason}</p>
            </div>
            <div>
              <div className="font-semibold text-ink-2">Supported by your resume</div>
              {change.source_evidence.length ? (
                <ul className="space-y-0.5 text-ink-2">
                  {change.source_evidence.slice(0, 2).map((e, i) => (
                    <li key={i} className="line-clamp-2">“{e}”</li>
                  ))}
                </ul>
              ) : (
                <p className="text-ink-3">Same facts as the original paragraph.</p>
              )}
              {change.source_claims.length > 0 && (
                <p className="mt-0.5 text-[10px] text-ink-3">Source claims: {change.source_claims.join(", ")}</p>
              )}
            </div>
          </div>
          {change.jd_keywords.length > 0 && (
            <div className="mt-2 flex flex-wrap items-center gap-1">
              <span className="text-xs text-ink-3">JD keywords addressed:</span>
              {change.jd_keywords.map((k) => (
                <Badge key={k} tone="violet">
                  {k}
                </Badge>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function SuggestionList({
  changes,
  onDecide,
  disabled,
}: {
  changes: Change[];
  onDecide: (d: Record<string, "accepted" | "rejected">) => void;
  disabled?: boolean;
}) {
  const [filter, setFilter] = useState<"all" | "on" | "off">("all");
  const onCount = changes.filter(isOn).length;
  const shown = changes.filter((c) => (filter === "all" ? true : filter === "on" ? isOn(c) : !isOn(c)));
  const all = (status: "accepted" | "rejected") => onDecide(Object.fromEntries(changes.map((c) => [c.change_id, status])));

  if (!changes.length) {
    return (
      <div className="rounded-2xl border border-dashed border-line p-8 text-center text-sm text-ink-2">
        No changes were suggested. Your resume already aligns with the supported keywords, or the AI could not find fact-safe improvements.
      </div>
    );
  }
  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="flex rounded-xl border border-line bg-surface p-0.5 text-xs">
          {(["all", "on", "off"] as const).map((f) => (
            <button key={f} onClick={() => setFilter(f)} className={`rounded-lg px-3 py-1 ${filter === f ? "bg-surface-2 font-medium" : "text-ink-3"}`}>
              {f === "all" ? `All (${changes.length})` : f === "on" ? `Applied (${onCount})` : `Not applied (${changes.length - onCount})`}
            </button>
          ))}
        </div>
        <div className="ml-auto flex gap-2">
          <Button size="sm" onClick={() => all("accepted")} disabled={disabled}>
            Apply All Suggested Changes
          </Button>
          <Button size="sm" variant="ghost" onClick={() => all("rejected")} disabled={disabled}>
            Reject All
          </Button>
        </div>
      </div>
      <div className="space-y-3">
        {shown.map((c) => (
          <SuggestionCard
            key={c.change_id}
            change={c}
            disabled={disabled}
            onToggle={(on) => onDecide({ [c.change_id]: on ? "accepted" : "rejected" })}
          />
        ))}
      </div>
    </div>
  );
}
