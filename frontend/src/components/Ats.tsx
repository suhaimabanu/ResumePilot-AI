"use client";

import type { AtsScore, Comparison, KeywordEvidence } from "@/lib/types";
import { Badge, Bar, CheckIcon, Collapsible } from "./ui";

export function AtsBreakdown({ score, comparison }: { score: AtsScore; comparison?: Comparison }) {
  return (
    <div className="space-y-2">
      {score.categories.map((c) => {
        const before = comparison?.categories.find((x) => x.key === c.key)?.original;
        return (
          <Collapsible
            key={c.key}
            title={
              <div>
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-sm font-medium">{c.label}</span>
                  <span className="text-sm tabular-nums">
                    {before !== undefined && before !== c.score && (
                      <span className="mr-1.5 text-xs text-ink-3 line-through">{before}</span>
                    )}
                    <span className="font-semibold">{c.score}</span>
                    <span className="text-ink-3"> / {c.max}</span>
                  </span>
                </div>
                <div className="mt-1.5">
                  <Bar value={c.score} max={c.max} />
                </div>
              </div>
            }
          >
            <p className="text-sm text-ink-2">{c.explanation}</p>
            {(c.matched?.length || c.partial?.length || c.missing?.length) ? (
              <div className="mt-3 grid gap-3 sm:grid-cols-3">
                <TermList title="Matched" tone="good" terms={c.matched ?? []} />
                <TermList title="Partial" tone="warn" terms={c.partial ?? []} />
                <TermList title="Missing / Not evidenced" tone="bad" terms={c.missing ?? []} />
              </div>
            ) : null}
            {c.stuffing && c.stuffing.length > 0 && (
              <p className="mt-2 text-xs text-warn">Repetition penalty: {c.stuffing.join(", ")}</p>
            )}
            {c.items && (
              <ul className="mt-3 space-y-1.5">
                {c.items.map((it) => (
                  <li key={it.responsibility} className="text-xs">
                    <div className="flex justify-between gap-3">
                      <span className="text-ink-2">{it.responsibility}</span>
                      <span className="tabular-nums font-medium">{it.alignment}%</span>
                    </div>
                    <Bar value={it.alignment} max={100} tone="muted" />
                  </li>
                ))}
              </ul>
            )}
            {c.checks && (
              <ul className="mt-3 space-y-1">
                {c.checks.map((ch) => (
                  <li key={ch.check} className="flex items-center gap-2 text-xs">
                    <CheckIcon ok={ch.passed} className="h-3.5 w-3.5" />
                    <span className="flex-1 text-ink-2">{ch.check}</span>
                    <span className="tabular-nums text-ink-3">{ch.passed ? `+${ch.points}` : "0"}</span>
                  </li>
                ))}
              </ul>
            )}
          </Collapsible>
        );
      })}
    </div>
  );
}

function TermList({ title, tone, terms }: { title: string; tone: "good" | "warn" | "bad"; terms: string[] }) {
  return (
    <div>
      <div className="mb-1 text-xs font-semibold text-ink-2">
        {title} ({terms.length})
      </div>
      <div className="flex flex-wrap gap-1">
        {terms.length ? terms.map((t) => <Badge key={t} tone={tone}>{t}</Badge>) : <span className="text-xs text-ink-3">—</span>}
      </div>
    </div>
  );
}

export function CoverageCompare({ comparison }: { comparison: Comparison }) {
  const kc = comparison.keyword_coverage;
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="rounded-2xl border border-line p-4">
        <div className="text-xs font-semibold uppercase tracking-wide text-ink-3">JD Keyword Coverage</div>
        <div className="mt-2 flex items-end gap-3">
          <div>
            <div className="text-xs text-ink-3">Original</div>
            <div className="text-2xl font-semibold tabular-nums">{kc.original}%</div>
          </div>
          <div className="pb-1 text-ink-3">→</div>
          <div>
            <div className="text-xs text-ink-3">Tailored</div>
            <div className="brand-text text-2xl font-semibold tabular-nums">{kc.tailored}%</div>
          </div>
          <Badge tone={kc.improvement > 0 ? "good" : "neutral"} className="mb-1 ml-auto">
            {kc.improvement > 0 ? "+" : ""}
            {kc.improvement}%
          </Badge>
        </div>
        <div className="mt-2 text-xs text-ink-2">
          Exactly matched before: <b>{kc.matched_before}</b> / {kc.total} · after: <b>{kc.matched_after}</b> / {kc.total}
        </div>
      </div>
      <div className="rounded-2xl border border-line p-4">
        <div className="text-xs font-semibold uppercase tracking-wide text-ink-3">Required Skill Coverage</div>
        <div className="mt-2 flex items-end gap-3">
          <div>
            <div className="text-xs text-ink-3">Original</div>
            <div className="text-2xl font-semibold tabular-nums">{comparison.required_coverage.original}%</div>
          </div>
          <div className="pb-1 text-ink-3">→</div>
          <div>
            <div className="text-xs text-ink-3">Tailored</div>
            <div className="brand-text text-2xl font-semibold tabular-nums">{comparison.required_coverage.tailored}%</div>
          </div>
        </div>
        <div className="mt-2 text-xs text-ink-2">Coverage is weighted: exact = 1, equivalent term = 0.75, related evidence = 0.5.</div>
      </div>
    </div>
  );
}

export function KeywordEvidencePanel({ groups }: { groups: { supported: KeywordEvidence[]; partial: KeywordEvidence[]; missing: KeywordEvidence[] } }) {
  return (
    <div className="space-y-4">
      <Group title="Supported by your resume" tone="good" items={groups.supported} />
      <Group title="Partially supported" tone="warn" items={groups.partial} />
      <div>
        <Group title="Missing / Not evidenced" tone="bad" items={groups.missing} />
        {groups.missing.length > 0 && (
          <p className="mt-2 rounded-xl bg-surface-2 p-3 text-xs text-ink-2">
            These keywords were not found in your uploaded resume and were <b>not added</b> to avoid inventing experience.
          </p>
        )}
      </div>
    </div>
  );
}

function Group({ title, tone, items }: { title: string; tone: "good" | "warn" | "bad"; items: KeywordEvidence[] }) {
  return (
    <div>
      <div className="mb-1.5 text-sm font-semibold">
        {title} <span className="font-normal text-ink-3">({items.length})</span>
      </div>
      <div className="space-y-1">
        {items.length === 0 && <div className="text-xs text-ink-3">None</div>}
        {items.map((k) => (
          <Collapsible
            key={k.term}
            title={
              <div className="flex items-center gap-2">
                <Badge tone={tone}>{k.term}</Badge>
                {k.importance === "required" && <span className="text-[10px] font-semibold uppercase text-ink-3">Required</span>}
                {k.importance === "preferred" && <span className="text-[10px] uppercase text-ink-3">Preferred</span>}
              </div>
            }
          >
            <div className="space-y-1 text-xs text-ink-2">
              <p>
                <b>Status:</b> {k.status === "supported" ? "Supported" : k.status === "partial" ? "Partially supported" : "Not evidenced"}
              </p>
              <p>
                <b>Why:</b> {k.explanation}
              </p>
              {k.evidence && (
                <p>
                  <b>Evidence:</b> “{k.evidence}”
                </p>
              )}
              <p>
                <b>Action:</b>{" "}
                {k.usable ? "May be emphasized where your resume already supports it." : "Not added to the tailored resume."}
              </p>
            </div>
          </Collapsible>
        ))}
      </div>
    </div>
  );
}
