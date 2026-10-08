"use client";

import type { JobStatus } from "@/lib/types";
import { Spinner } from "./ui";

/** Shows the real backend job steps — nothing here is simulated. */
export function ProgressPanel({ title, job }: { title: string; job: JobStatus | null }) {
  const progress = job?.progress ?? 0;
  return (
    <div className="card mx-auto max-w-xl p-8">
      <div className="flex items-center gap-3">
        <Spinner className="h-5 w-5 text-violet" />
        <h2 className="text-lg font-semibold">{title}</h2>
      </div>
      <div className="mt-5 h-2 w-full overflow-hidden rounded-full bg-surface-2">
        <div className="brand-gradient h-full rounded-full transition-all duration-500" style={{ width: `${progress}%` }} />
      </div>
      <div className="mt-1 text-right text-xs text-ink-3">{progress}%</div>
      <ul className="mt-4 space-y-2.5">
        {(job?.steps ?? []).map((s) => (
          <li key={s.key} className="flex items-center gap-3 text-sm">
            {s.state === "done" ? (
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-100 text-xs text-emerald-700">✓</span>
            ) : s.state === "active" ? (
              <span className="flex h-5 w-5 items-center justify-center">
                <span className="pulse-dot h-2.5 w-2.5 rounded-full bg-violet" />
              </span>
            ) : (
              <span className="flex h-5 w-5 items-center justify-center rounded-full border border-line text-xs text-ink-3">○</span>
            )}
            <span className={s.state === "pending" ? "text-ink-3" : s.state === "active" ? "font-medium" : "text-ink-2"}>
              {s.label}
            </span>
          </li>
        ))}
      </ul>
      {job?.notes?.length ? (
        <div className="mt-5 space-y-1 border-t border-line pt-4 text-xs text-ink-3">
          {job.notes.map((n, i) => (
            <p key={i}>• {n}</p>
          ))}
        </div>
      ) : null}
    </div>
  );
}
