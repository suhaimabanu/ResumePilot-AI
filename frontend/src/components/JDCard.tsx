"use client";

import { useRef } from "react";
import { StepDot } from "./UploadCard";
import { Badge, Button } from "./ui";

export function JDCard({
  text,
  file,
  onText,
  onFile,
  saved,
}: {
  text: string;
  file: File | null;
  onText: (t: string) => void;
  onFile: (f: File | null) => void;
  saved: { job_title: string; keywords_preview: string[] } | null;
}) {
  const input = useRef<HTMLInputElement>(null);
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  return (
    <div className="card flex flex-col p-6">
      <div className="flex items-center gap-3">
        <StepDot n={2} done={!!saved} />
        <div>
          <h2 className="text-lg font-semibold">Add the Job Description</h2>
          <p className="text-sm text-ink-2">Paste the posting or upload it as TXT, DOCX or PDF.</p>
        </div>
      </div>
      {file ? (
        <div className="mt-5 flex items-center gap-3 rounded-2xl border border-line bg-surface-2/40 p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-ink text-xs font-bold text-white">JD</div>
          <div className="min-w-0 flex-1 truncate font-medium">{file.name}</div>
          <Button size="sm" variant="ghost" onClick={() => onFile(null)}>
            Remove
          </Button>
        </div>
      ) : (
        <textarea
          value={text}
          onChange={(e) => onText(e.target.value)}
          placeholder="Paste the full job description here — title, responsibilities, requirements, nice-to-haves…"
          className="mt-5 min-h-[260px] flex-1 resize-y rounded-2xl border border-line bg-surface-2/40 p-4 text-sm leading-relaxed outline-none transition focus:border-violet focus:bg-surface"
        />
      )}
      <div className="mt-3 flex items-center justify-between text-xs text-ink-3">
        <span>{file ? "File will be parsed on analysis" : `${words} words`}</span>
        {!file && (
          <>
            <button className="font-medium text-violet hover:underline" onClick={() => input.current?.click()}>
              Upload JD file instead
            </button>
            <input
              ref={input}
              type="file"
              accept=".txt,.docx,.pdf"
              className="hidden"
              onChange={(e) => onFile(e.target.files?.[0] ?? null)}
            />
          </>
        )}
      </div>
      {saved && (
        <div className="mt-3">
          <div className="text-xs text-ink-3">
            Detected: <span className="font-medium text-ink">{saved.job_title || "Job description"}</span>
          </div>
          <div className="mt-1.5 flex flex-wrap gap-1">
            {saved.keywords_preview.slice(0, 14).map((k) => (
              <Badge key={k}>{k}</Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
