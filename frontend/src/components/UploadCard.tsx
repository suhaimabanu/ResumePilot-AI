"use client";

import { useRef, useState } from "react";
import { formatBytes } from "@/lib/api";
import type { JobStatus, ResumeSummary } from "@/lib/types";
import { Badge, Button, CheckIcon, Spinner } from "./ui";

const ACCEPT = ".docx,.pdf";

export function UploadCard({
  file,
  summary,
  job,
  busy,
  onFile,
  onRemove,
}: {
  file: { name: string; type: string; size: number } | null;
  summary: ResumeSummary | null;
  job: JobStatus | null;
  busy: boolean;
  onFile: (f: File) => void;
  onRemove: () => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);

  const pick = (files: FileList | null) => {
    const f = files?.[0];
    if (f) onFile(f);
  };

  return (
    <div className="card p-6">
      <div className="flex items-center gap-3">
        <StepDot n={1} done={!!summary} />
        <div>
          <h2 className="text-lg font-semibold">Upload Your Resume</h2>
          <p className="text-sm text-ink-2">We tailor your actual resume and keep its design.</p>
        </div>
      </div>

      {!file && (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            pick(e.dataTransfer.files);
          }}
          className={`mt-5 flex flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-10 text-center transition ${
            drag ? "border-violet bg-violet-50/60" : "border-line bg-surface-2/50 hover:border-violet/50"
          }`}
        >
          <div className="brand-gradient mb-3 flex h-12 w-12 items-center justify-center rounded-2xl text-white shadow-lg">
            <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 16V4m0 0-4 4m4-4 4 4M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <p className="font-medium">Drag & drop your resume here</p>
          <p className="my-2 text-sm text-ink-3">or</p>
          <Button variant="secondary" onClick={() => input.current?.click()}>
            Browse Files
          </Button>
          <p className="mt-3 text-xs text-ink-3">Supported: DOCX, PDF · DOCX gives the best template preservation</p>
          <input ref={input} type="file" accept={ACCEPT} className="hidden" onChange={(e) => pick(e.target.files)} />
        </div>
      )}

      {file && (
        <div className="mt-5 rounded-2xl border border-line bg-surface-2/40 p-4">
          <div className="flex items-center gap-3">
            <div className={`flex h-10 w-10 items-center justify-center rounded-xl text-xs font-bold text-white ${file.type === "pdf" ? "bg-red-500" : "bg-blue-600"}`}>
              {file.type.toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate font-medium">{file.name}</div>
              <div className="text-xs text-ink-3">
                {file.type.toUpperCase()} · {formatBytes(file.size)}
                {summary?.page_count ? ` · ${summary.page_count} page${summary.page_count > 1 ? "s" : ""}` : ""}
              </div>
            </div>
            {busy ? (
              <span className="flex items-center gap-2 text-sm text-ink-2">
                <Spinner /> {job?.step_label ?? "Uploading"}…
              </span>
            ) : summary ? (
              <Badge tone="good">
                <CheckIcon ok className="h-3.5 w-3.5" /> Parsed
              </Badge>
            ) : null}
          </div>
          <div className="mt-3 flex gap-2">
            <Button size="sm" variant="ghost" onClick={() => input.current?.click()} disabled={busy}>
              Replace
            </Button>
            <Button size="sm" variant="ghost" onClick={onRemove} disabled={busy}>
              Remove
            </Button>
            <input ref={input} type="file" accept={ACCEPT} className="hidden" onChange={(e) => pick(e.target.files)} />
          </div>
        </div>
      )}

      {summary && <ResumeDetected summary={summary} />}
    </div>
  );
}

function ResumeDetected({ summary }: { summary: ResumeSummary }) {
  const c = summary.counts;
  const stats: [string, number | null][] = [
    ["pages", summary.page_count],
    ["experience entries", c.experience_entries],
    ["skills", c.skills],
    ["projects", c.projects],
    ["education", c.education_entries],
    ["certifications", c.certifications],
  ];
  return (
    <div className="mt-4">
      <div className="text-sm font-semibold">
        Resume detected{summary.name ? <span className="font-normal text-ink-2"> — {summary.name}</span> : null}
      </div>
      <div className="mt-2 grid grid-cols-3 gap-2">
        {stats.map(([label, v]) => (
          <div key={label} className="rounded-xl border border-line bg-surface px-3 py-2">
            <div className="text-lg font-semibold">{v ?? "—"}</div>
            <div className="text-[11px] leading-tight text-ink-3">{label}</div>
          </div>
        ))}
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {summary.sections.map((s) => (
          <Badge key={s.title}>{s.title}</Badge>
        ))}
        {summary.profile_photo && <Badge tone="violet">Profile photo</Badge>}
        {summary.template.tables > 0 && <Badge tone="violet">{summary.template.tables} table(s)</Badge>}
      </div>
      {summary.warnings.map((w) => (
        <p key={w} className="mt-2 text-xs text-warn">
          ⚠ {w}
        </p>
      ))}
      {summary.file_type === "pdf" && (
        <p className="mt-2 text-xs text-ink-3">
          PDFs have no editable template, so the layout will be rebuilt from measured fonts and spacing. Upload a DOCX for maximum fidelity.
        </p>
      )}
    </div>
  );
}

export function StepDot({ n, done }: { n: number; done?: boolean }) {
  return (
    <div
      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-semibold ${
        done ? "bg-emerald-100 text-emerald-700" : "brand-gradient text-white"
      }`}
    >
      {done ? "✓" : n}
    </div>
  );
}
