"use client";

import { useState } from "react";
import { downloadUrl, previewUrl } from "@/lib/api";
import type { CheckItem, GenerationResult, Style } from "@/lib/types";
import { AtsBreakdown, CoverageCompare } from "./Ats";
import { STYLES } from "./ReviewView";
import { DiffView, SuggestionList } from "./Suggestions";
import { Badge, Button, CheckIcon, Collapsible, ScoreRing, SectionTitle } from "./ui";

export function ResultView({
  sessionId,
  result,
  originalPages,
  busy,
  style,
  onStyle,
  onRegenerate,
  onDecide,
  onStartOver,
  dirty,
}: {
  sessionId: string;
  result: GenerationResult;
  originalPages: number;
  busy: boolean;
  style: Style;
  onStyle: (s: Style) => void;
  onRegenerate: (mode: "fresh" | "selections") => void;
  onDecide: (d: Record<string, "accepted" | "rejected">) => void;
  onStartOver: () => void;
  dirty: boolean;
}) {
  const cmp = result.ats.comparison;
  const applied = result.changes.filter((c) => c.status === "applied");
  const v = result.validation.summary;

  return (
    <div className="space-y-8">
      {/* Hero */}
      <div className="card relative overflow-hidden p-6 sm:p-8">
        <div className="glow" />
        <div className="relative grid gap-6 lg:grid-cols-[auto_1fr_auto] lg:items-center">
          <div className="flex items-center gap-5">
            <ScoreRing value={cmp.tailored} size={132} label="final" />
            <div>
              <div className="text-xs font-semibold uppercase tracking-wider text-violet">Tailored Resume Ready</div>
              <div className="mt-1 text-sm text-ink-2">ATS Compatibility</div>
              <div className="text-sm">
                Original <b className="tabular-nums">{cmp.original}</b> / 100
              </div>
              <Badge tone={cmp.improvement > 0 ? "good" : "neutral"} className="mt-1">
                Improvement {cmp.improvement > 0 ? "+" : ""}
                {cmp.improvement}
              </Badge>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="Keyword coverage" value={`${cmp.keyword_coverage.original}% → ${cmp.keyword_coverage.tailored}%`} />
            <Stat
              label="Pages"
              value={`${result.pages.original ?? "?"} → ${result.pages.tailored}`}
              hint={result.pages.status === "preserved" ? "Page count preserved" : result.pages.status === "longer" ? "Longer than original" : "Shorter than original"}
              tone={result.pages.status === "longer" ? "warn" : undefined}
            />
            <Stat label="Template preservation" value={result.template.level} hint={`${result.template.score}% match`} />
            <Stat label="Changes applied" value={`${applied.length}`} hint={`of ${result.changes.length} suggested`} />
          </div>
          <div className="flex flex-col gap-2">
            <a href={downloadUrl(sessionId, result.downloads.docx.file_id)} download={result.downloads.docx.name}>
              <Button variant="primary" className="w-full">Download DOCX</Button>
            </a>
            <a href={downloadUrl(sessionId, result.downloads.pdf.file_id)} download={result.downloads.pdf.name}>
              <Button className="w-full">Download PDF</Button>
            </a>
            <a href={downloadUrl(sessionId, result.downloads.both.file_id)} download={result.downloads.both.name}>
              <Button className="w-full">Download Both</Button>
            </a>
          </div>
        </div>
        <div className="relative mt-6 flex flex-wrap items-center gap-2 border-t border-line pt-4">
          <span className="text-xs font-semibold uppercase tracking-wide text-ink-3">Validation</span>
          {Object.entries(v).map(([k, ok]) => (
            <Badge key={k} tone={ok ? "good" : "bad"}>
              <CheckIcon ok={ok} className="h-3.5 w-3.5" /> {k}
            </Badge>
          ))}
          <div className="ml-auto flex flex-wrap items-center gap-2">
            <select value={style} onChange={(e) => onStyle(e.target.value as Style)} className="h-10 rounded-xl border border-line bg-surface px-2 text-sm" aria-label="Regeneration style">
              {STYLES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
            <Button variant="primary" onClick={() => onRegenerate("fresh")} loading={busy}>
              ↻ Regenerate Resume
            </Button>
            <Button onClick={() => onRegenerate("selections")} disabled={busy}>
              Regenerate with Current Selections
            </Button>
            <Button variant="ghost" onClick={onStartOver} disabled={busy}>
              Start Over
            </Button>
          </div>
        </div>
        {(result.ai_status === "failed" || result.ai_status === "weak" || result.applied_count === 0) && (
          <div className="relative mt-3 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            {result.applied_count === 0 ? (
              <>
                <b>No changes were applied</b>, so this document is the same as your original resume.{" "}
              </>
            ) : result.ai_status === "weak" ? (
              <>
                <b>The AI only made minor edits</b> (the AI service was under heavy load), so this is close to your original.{" "}
              </>
            ) : (
              <>
                <b>AI rewriting did not run</b> — only skill reordering and exact terminology swaps were applied.{" "}
              </>
            )}
            Click <b>Regenerate</b> to try AI tailoring again.
          </div>
        )}
        {(result.notes.length > 0 || result.pages.optimization.length > 0) && (
          <div className="relative mt-3 space-y-0.5 text-xs text-ink-3">
            {[...result.pages.optimization, ...result.notes].map((n, i) => (
              <p key={i}>• {n}</p>
            ))}
          </div>
        )}
      </div>

      {/* Preview + side info */}
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
        <PreviewPane key={result.generation} sessionId={sessionId} pages={result.preview.pages} generation={result.generation} originalPages={originalPages} />
        <div className="space-y-6">
          <div className="card p-5">
            <SectionTitle title="ATS Score Breakdown" desc="Expand a category to see exactly how it was calculated." />
            <AtsBreakdown score={result.ats.tailored} comparison={cmp} />
          </div>
        </div>
      </div>

      <div className="card p-6">
        <SectionTitle title="Before / After Coverage" />
        <CoverageCompare comparison={cmp} />
        {result.ats.tailored.keyword_coverage.missing_terms.length > 0 && (
          <div className="mt-4 rounded-xl bg-surface-2 p-4 text-sm">
            <div className="font-semibold">Missing / Not Evidenced</div>
            <div className="mt-2 flex flex-wrap gap-1">
              {result.ats.tailored.keyword_coverage.missing_terms.map((t) => (
                <Badge key={t} tone="bad">
                  {t}
                </Badge>
              ))}
            </div>
            <p className="mt-2 text-xs text-ink-2">
              These keywords were not found in your uploaded resume and were not added to avoid inventing experience.
            </p>
          </div>
        )}
      </div>

      <div className="card p-6">
        <SectionTitle title="What Changed?" desc={`${applied.length} change(s) applied to your original resume. Everything else is exactly as you wrote it.`} />
        {applied.length === 0 && <p className="text-sm text-ink-3">No changes applied — the documents contain your original content.</p>}
        <div className="space-y-3">
          {applied.map((c) => (
            <div key={c.change_id} className="rounded-2xl border border-line p-4">
              <div className="mb-2 flex flex-wrap items-center gap-2 text-sm font-semibold">
                {c.entry_label ? `${c.section_title} — ${c.entry_label}` : c.section_title}
                {c.jd_keywords.map((k) => (
                  <Badge key={k} tone="violet">
                    {k}
                  </Badge>
                ))}
              </div>
              <DiffView original={c.original} suggested={c.suggested} />
              <p className="mt-2 text-xs text-ink-2">
                <b>Reason:</b> {c.reason}
              </p>
              {c.source_evidence.length > 0 && (
                <p className="mt-1 text-xs text-ink-3">
                  <b>Supported by:</b> {c.source_evidence.slice(0, 2).map((e) => `“${e.slice(0, 90)}”`).join(" · ")}
                </p>
              )}
            </div>
          ))}
        </div>
        <div className="mt-6">
          <Collapsible title={<span className="text-sm font-medium">Adjust changes, then regenerate with your selections</span>} right={dirty ? <Badge tone="orange">Not regenerated yet</Badge> : null}>
            <SuggestionList changes={result.changes} onDecide={onDecide} disabled={busy} />
            <div className="mt-4 flex justify-end">
              <Button variant="primary" onClick={() => onRegenerate("selections")} loading={busy}>
                Regenerate with Current Selections
              </Button>
            </div>
          </Collapsible>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card p-6">
          <SectionTitle title="Validation Report" desc="Downloads are only enabled when every critical check passes." />
          <div className="space-y-2">
            <Collapsible title={<CheckTitle ok={result.validation.facts.passed} text="Fact check" />}>
              <p className="text-sm text-ink-2">{result.validation.facts.detail}</p>
            </Collapsible>
            <CheckGroup title="Resume completeness" data={result.validation.completeness} />
            <CheckGroup title="DOCX content" data={result.validation.docx} />
            <CheckGroup title="PDF content" data={result.validation.pdf} />
            <CheckGroup title="DOCX / PDF consistency" data={result.validation.consistency} />
            <Collapsible title={<CheckTitle ok={result.validation.visual.passed} text={`Visual layout (${result.validation.visual.pages_checked} page(s) checked)`} />}>
              {result.validation.visual.issues.length === 0 ? (
                <p className="text-sm text-ink-2">No blank pages, overlaps, clipped content, tiny text or missing images detected.</p>
              ) : (
                <ul className="space-y-1 text-sm">
                  {result.validation.visual.issues.map((i, n) => (
                    <li key={n} className={i.severity === "critical" ? "text-bad" : "text-warn"}>
                      {i.page ? `Page ${i.page}: ` : ""}
                      {i.message}
                    </li>
                  ))}
                </ul>
              )}
            </Collapsible>
            <Collapsible title={<CheckTitle ok={result.validation.identity.passed} text="Identity (your data, not sample data)" />}>
              <p className="text-sm text-ink-2">
                {result.validation.identity.passed ? "Name, employers and titles match your uploaded resume." : result.validation.identity.issues.join(" ")}
              </p>
            </Collapsible>
          </div>
        </div>
        <div className="card p-6">
          <SectionTitle title="Template Preservation" desc={`${result.template.level} · ${result.template.score}% of measured template properties preserved`} />
          <div className="grid grid-cols-2 gap-2">
            {result.template.aspects.map((a) => (
              <div key={a.aspect} className="flex items-center gap-2 rounded-xl border border-line px-3 py-2 text-sm">
                <CheckIcon ok={a.status !== "Changed"} className="h-4 w-4 shrink-0" />
                <div className="min-w-0">
                  <div className="font-medium">{a.aspect}</div>
                  <div className="truncate text-xs text-ink-3">{a.status}{a.detail ? ` · ${a.detail}` : ""}</div>
                </div>
              </div>
            ))}
          </div>
          {result.template.limitations.length > 0 && (
            <div className="mt-3 space-y-1 rounded-xl bg-amber-50 p-3 text-xs text-amber-800">
              {result.template.limitations.map((l) => (
                <p key={l}>Template limitation: {l}</p>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, hint, tone }: { label: string; value: string; hint?: string; tone?: "warn" }) {
  return (
    <div className="rounded-2xl border border-line bg-surface/80 p-3">
      <div className="text-[11px] uppercase tracking-wide text-ink-3">{label}</div>
      <div className={`mt-1 text-lg font-semibold tabular-nums ${tone === "warn" ? "text-warn" : ""}`}>{value}</div>
      {hint && <div className="text-[11px] text-ink-3">{hint}</div>}
    </div>
  );
}

function CheckTitle({ ok, text }: { ok: boolean; text: string }) {
  return (
    <span className="flex items-center gap-2 text-sm font-medium">
      <CheckIcon ok={ok} /> {text}
    </span>
  );
}

function CheckGroup({ title, data }: { title: string; data: { passed: boolean; checks: CheckItem[] } }) {
  return (
    <Collapsible title={<CheckTitle ok={data.passed} text={title} />}>
      <ul className="space-y-1">
        {data.checks.map((c) => (
          <li key={c.check} className="flex items-start gap-2 text-sm">
            <CheckIcon ok={c.passed} className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span className="flex-1 text-ink-2">{c.check}</span>
            {c.detail && <span className="text-xs text-ink-3">{c.detail}</span>}
          </li>
        ))}
      </ul>
    </Collapsible>
  );
}

function PreviewPane({ sessionId, pages, generation, originalPages }: { sessionId: string; pages: number; generation: number; originalPages: number }) {
  const [page, setPage] = useState(1);
  const [mode, setMode] = useState<"tailored" | "compare">("tailored");
  const maxPage = mode === "compare" ? Math.max(pages, originalPages) : pages;
  return (
    <div className="card p-5">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <h3 className="text-lg font-semibold">Full Resume Preview</h3>
        <span className="text-xs text-ink-3">Rendered from the exact PDF you download</span>
        <div className="ml-auto flex rounded-xl border border-line bg-surface p-0.5 text-xs">
          <button className={`rounded-lg px-3 py-1 ${mode === "tailored" ? "bg-surface-2 font-medium" : "text-ink-3"}`} onClick={() => setMode("tailored")}>
            Tailored
          </button>
          <button
            className={`rounded-lg px-3 py-1 ${mode === "compare" ? "bg-surface-2 font-medium" : "text-ink-3"}`}
            onClick={() => setMode("compare")}
            disabled={!originalPages}
          >
            Original vs Tailored
          </button>
        </div>
      </div>
      <div className={`grid gap-3 ${mode === "compare" ? "md:grid-cols-2" : ""}`}>
        {mode === "compare" && (
          <PageImage src={page <= originalPages ? previewUrl(sessionId, "original", page) : null} label={`Original · Page ${page} / ${originalPages}`} />
        )}
        <PageImage
          src={page <= pages ? previewUrl(sessionId, "tailored", page, generation) : null}
          label={`Tailored · Page ${page} / ${pages}`}
        />
      </div>
      <div className="mt-3 flex items-center justify-center gap-3">
        <Button size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
          ← Prev
        </Button>
        <span className="text-sm tabular-nums">
          Page {page} / {maxPage}
        </span>
        <Button size="sm" onClick={() => setPage((p) => Math.min(maxPage, p + 1))} disabled={page >= maxPage}>
          Next →
        </Button>
      </div>
    </div>
  );
}

function PageImage({ src, label }: { src: string | null; label: string }) {
  return (
    <figure>
      <div className="overflow-hidden rounded-xl border border-line bg-white shadow-sm">
        {src ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={src} alt={label} className="block h-auto w-full" />
        ) : (
          <div className="flex aspect-[8.5/11] items-center justify-center text-sm text-ink-3">No page</div>
        )}
      </div>
      <figcaption className="mt-1 text-center text-xs text-ink-3">{label}</figcaption>
    </figure>
  );
}
