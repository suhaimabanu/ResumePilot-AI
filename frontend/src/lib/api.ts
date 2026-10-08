import type { Analysis, Change, Comparison, AtsScore, JobStatus, ResumeSummary, Style } from "./types";

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, init);
  } catch {
    throw new ApiError("Can't reach the server. Please check that the backend is running and try again.");
  }
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    /* non-JSON */
  }
  if (!res.ok) {
    const detail = (body as { detail?: unknown } | null)?.detail;
    throw new ApiError(typeof detail === "string" ? detail : "Something went wrong. Please try again.");
  }
  return body as T;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export type Decisions = Record<string, "accepted" | "rejected" | "suggested">;

export const api = {
  health: () =>
    request<{ gemini: { configured: boolean; model: string }; pdf_converter: { active: string | null }; ocr: boolean; max_upload_mb: number }>(
      "/api/health",
    ),

  uploadResume: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<{ session_id: string; job_id: string; file: { name: string; type: string; size: number } }>(
      "/api/resume/upload",
      { method: "POST", body: fd },
    );
  },

  submitJD: (sessionId: string, text: string, file?: File | null) => {
    const fd = new FormData();
    fd.append("session_id", sessionId);
    if (text) fd.append("jd_text", text);
    if (file) fd.append("file", file);
    return request<{ characters: number; words: number; job_title: string; keywords_preview: string[]; source: string }>(
      "/api/jd/analyze",
      { method: "POST", body: fd },
    );
  },

  analyze: (sessionId: string, style: Style) =>
    request<{ job_id: string }>("/api/resume/analyze", json({ session_id: sessionId, style })),

  applyChanges: (sessionId: string, decisions: Decisions) =>
    request<{ projected_ats: AtsScore; comparison: Comparison; changes: Change[] }>(
      "/api/resume/apply-changes",
      json({ session_id: sessionId, decisions }),
    ),

  tailor: (sessionId: string, decisions: Decisions) =>
    request<{ job_id: string }>("/api/resume/tailor", json({ session_id: sessionId, decisions })),

  regenerate: (sessionId: string, mode: "fresh" | "selections", decisions: Decisions, style?: Style) =>
    request<{ job_id: string }>("/api/resume/regenerate", json({ session_id: sessionId, mode, decisions, style })),

  suggest: (sessionId: string, decisions: Decisions, style?: Style) =>
    request<{ job_id: string }>("/api/resume/regenerate", json({ session_id: sessionId, mode: "suggestions", decisions, style })),

  session: (sessionId: string) =>
    request<{ resume: ResumeSummary | null; has_jd: boolean; analyzed: boolean; analysis?: Analysis; result: unknown }>(
      `/api/sessions/${encodeURIComponent(sessionId)}`,
    ),

  startOver: (sessionId: string) =>
    request<{ deleted: boolean }>(`/api/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" }),

  job: <T>(jobId: string) => request<JobStatus<T>>(`/api/jobs/${encodeURIComponent(jobId)}/status`),
};

export const downloadUrl = (sessionId: string, fileId: string) =>
  `/api/download/${encodeURIComponent(fileId)}?s=${encodeURIComponent(sessionId)}`;

export const previewUrl = (sessionId: string, which: "original" | "tailored", page: number, generation = 0) =>
  `/api/preview/${which}/${page}?s=${encodeURIComponent(sessionId)}&g=${generation}`;

/** Poll a job until it finishes, reporting real backend status on every tick. */
export async function pollJob<T>(
  jobId: string,
  onUpdate: (s: JobStatus<T>) => void,
  signal?: { cancelled: boolean },
): Promise<JobStatus<T>> {
  let failures = 0;
  for (;;) {
    if (signal?.cancelled) throw new ApiError("cancelled");
    try {
      const status = await api.job<T>(jobId);
      failures = 0;
      onUpdate(status);
      if (status.status === "completed" || status.status === "waiting_for_user") return status;
      if (status.status === "failed") throw new ApiError(status.error || "Processing failed. Please try again.");
    } catch (e) {
      if (e instanceof ApiError && !e.message.startsWith("Can't reach")) throw e;
      failures += 1;
      if (failures > 8) throw e;
    }
    await new Promise((r) => setTimeout(r, 700));
  }
}

export function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(2)} MB`;
}
