"use client";

import { useState } from "react";
import type { Analysis, AtsScore, Comparison, Style } from "@/lib/types";
import { AtsBreakdown, KeywordEvidencePanel } from "./Ats";
import { SuggestionList, isOn } from "./Suggestions";
import { Badge, Button, Collapsible, ScoreRing } from "./ui";

export const STYLES: { value: Style; label: string }[] = [
  { value: "balanced", label: "Balanced" },
  { value: "ats", label: "More ATS-focused" },
  { value: "concise", label: "More concise" },
  { value: "achievement", label: "More achievement-focused" },
  { value: "conservative", label: "More conservative" },
];

export function ReviewView({
  analysis,
  projected,
  comparison,
  busy,
  style,
  onStyle,
  onDecide,
  onGenerate,
  onResuggest,
}: {
  analysis: Analysis;
  projected: AtsScore;
  comparison: Comparison | null;
  busy: boolean;
  style: Style;
  onStyle: (s: Style) => void;
  onDecide: (d: Record<string, "accepted" | "rejected">) => void;
  onGenerate: () => void;
  onResuggest: () => void;
}) {
  const [tab, setTab] = useState<"changes" | "keywords" | "score">("changes");
  const selected = analysis.changes.filter(isOn).length;
  const original = analysis.original_ats.total;
  const delta = projected.total - original;
  const g = analysis.keyword_groups;

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
      <div className="min-w-0">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider text-violet">Step 2 · Review</div>
            <h2 className="text-2xl font-semibold tracking-tight">Suggested Changes</h2>
            <p className="mt-1 text-sm text-ink-2">
              Tailoring <b>{analysis.resume.name || analysis.resume.filename}</b> for{" "}
              <b>{analysis.jd.job_title || "this role"}</b>
              {analysis.jd.company ? ` at ${analysis.jd.company}` : ""}. Every suggestion was fact-checked against your resume — choose which to apply.
            </p>
          </div>
        </div>

        <div className="mb-4 flex gap-1 rounded-xl border border-line bg-surface p-1 text-sm">
          {(
            [
              ["changes", `Suggestions (${analysis.changes.length})`],
              ["keywords", `JD Keywords (${analysis.keyword_evidence.length})`],
              ["score", "Score details"],
            ] as const
          ).map(([k, label]) => (
            <button key={k} onClick={() => setTab(k)} className={`flex-1 rounded-lg px-3 py-1.5 ${tab === k ? "bg-surface-2 font-medium" : "text-ink-3"}`}>
              {label}
            </button>
          ))}
        </div>

        {tab === "changes" && (
          <>
            {!analysis.ai_enabled && (
              <div className="mb-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
                Gemini is not configured on the server, so only deterministic suggestions (skill ordering and exact terminology) are shown.
              </div>
            )}
            {analysis.ai_enabled && (analysis.ai_status === "failed" || analysis.ai_status === "weak") && (
              <div className="mb-3 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                <p className="min-w-0 flex-1">
                  {analysis.ai_status === "failed" ? (
                    <>
                      <b>AI rewriting did not run.</b> The AI service is busy or unreachable, so your content has not been rewritten for
                      this job — only skill reordering and exact terminology swaps are shown.
                    </>
                  ) : (
                    <>
                      <b>The AI only made minor edits this time</b> (the AI service is under heavy load).
                    </>
                  )}{" "}
                  Generating now would give you a resume very close to your original.
                </p>
                <Button size="sm" className="shrink-0" onClick={onResuggest} loading={busy}>
                  Retry AI tailoring
                </Button>
              </div>
            )}
            <SuggestionList changes={analysis.changes} onDecide={onDecide} disabled={busy} />
            {analysis.blocked_count > 0 && (
              <div className="mt-4">
                <Collapsible title={<span className="text-sm text-ink-2">{analysis.blocked_count} AI suggestion(s) were blocked by fact-checking</span>}>
                  <ul className="space-y-2">
                    {analysis.blocked.map((b, i) => (
                      <li key={i} className="text-xs">
                        <p className="text-ink-2 line-through">{b.suggested}</p>
                        <p className="text-bad">{b.issues.join(" ")}</p>
                      </li>
                    ))}
                  </ul>
                </Collapsible>
              </div>
            )}
          </>
        )}
        {tab === "keywords" && <KeywordEvidencePanel groups={g} />}
        {tab === "score" && <AtsBreakdown score={projected} comparison={comparison ?? undefined} />}
      </div>

      <aside className="lg:sticky lg:top-6 h-fit space-y-4">
        <div className="card p-5">
          <div className="text-xs font-semibold uppercase tracking-wide text-ink-3">ATS Compatibility (projected)</div>
          <div className="mt-3 flex items-center gap-4">
            <ScoreRing value={projected.total} size={104} label="proj" />
            <div className="space-y-1 text-sm">
              <div>
                Original: <b className="tabular-nums">{original}</b> / 100
              </div>
              <div>
                With selections: <b className="tabular-nums">{projected.total}</b> / 100
              </div>
              <Badge tone={delta > 0 ? "good" : "neutral"}>
                {delta > 0 ? "+" : ""}
                {delta} points
              </Badge>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
            <div className="rounded-xl bg-emerald-50 p-2">
              <div className="text-lg font-semibold text-emerald-700">{g.supported.length}</div>supported
            </div>
            <div className="rounded-xl bg-amber-50 p-2">
              <div className="text-lg font-semibold text-amber-700">{g.partial.length}</div>partial
            </div>
            <div className="rounded-xl bg-red-50 p-2">
              <div className="text-lg font-semibold text-red-700">{g.missing.length}</div>missing
            </div>
          </div>
          <p className="mt-3 text-[11px] leading-snug text-ink-3">
            Deterministic score calculated by ResumePilot, not by the AI. Different ATS products score differently.
          </p>
        </div>

        <div className="card space-y-3 p-5">
          <div className="text-sm">
            <b>{selected}</b> of {analysis.changes.length} changes selected
          </div>
          <Button variant="primary" size="lg" className="w-full" onClick={onGenerate} loading={busy}>
            Generate With My Selections
          </Button>
          <div className="flex items-center gap-2">
            <select
              value={style}
              onChange={(e) => onStyle(e.target.value as Style)}
              className="h-9 min-w-0 flex-1 rounded-xl border border-line bg-surface px-2 text-sm"
              aria-label="Tailoring style"
            >
              {STYLES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
            <Button size="sm" className="shrink-0" onClick={onResuggest} disabled={busy}>
              New suggestions
            </Button>
          </div>
          <p className="text-[11px] text-ink-3">New suggestions keep the changes you already applied or rejected.</p>
        </div>
      </aside>
    </div>
  );
}
