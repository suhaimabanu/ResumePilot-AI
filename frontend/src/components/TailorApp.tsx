"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, api, pollJob, type Decisions } from "@/lib/api";
import type { Analysis, AtsScore, Change, Comparison, GenerationResult, JobStatus, ResumeSummary, Style } from "@/lib/types";
import { JDCard } from "./JDCard";
import { ProgressPanel } from "./ProgressPanel";
import { ResultView } from "./ResultView";
import { ReviewView } from "./ReviewView";
import { UploadCard } from "./UploadCard";
import { Button, ErrorBox } from "./ui";

type Stage = "input" | "analyzing" | "review" | "generating" | "result";
const STORAGE_KEY = "resumepilot.session";
const MAX_MB = 10;

export default function TailorApp() {
  const [stage, setStage] = useState<Stage>("input");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [fileInfo, setFileInfo] = useState<{ name: string; type: string; size: number } | null>(null);
  const [summary, setSummary] = useState<ResumeSummary | null>(null);
  const [uploading, setUploading] = useState(false);
  const [jdText, setJdText] = useState("");
  const [jdFile, setJdFile] = useState<File | null>(null);
  const [jdSaved, setJdSaved] = useState<{ job_title: string; keywords_preview: string[] } | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [projected, setProjected] = useState<AtsScore | null>(null);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [result, setResult] = useState<GenerationResult | null>(null);
  const [dirty, setDirty] = useState(false);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [style, setStyle] = useState<Style>("balanced");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<{ gemini: boolean; converter: string | null } | null>(null);
  const cancel = useRef({ cancelled: false });

  const fail = (e: unknown) => setError(e instanceof Error ? e.message : "Something went wrong. Please try again.");

  // Restore an in-progress session after a page refresh.
  useEffect(() => {
    api.health().then((h) => setHealth({ gemini: h.gemini.configured, converter: h.pdf_converter.active })).catch(() => {});
    let saved: string | null = null;
    try {
      saved = sessionStorage.getItem(STORAGE_KEY);
    } catch {
      /* storage unavailable */
    }
    if (!saved) return;
    api
      .session(saved)
      .then((s) => {
        setSessionId(saved);
        if (s.resume) {
          setSummary(s.resume);
          setFileInfo({ name: s.resume.filename, type: s.resume.file_type, size: 0 });
        }
        if (s.analysis) {
          setAnalysis(s.analysis);
          setProjected(s.analysis.projected_ats);
          setStage("review");
        }
        if (s.result) {
          setResult(s.result as GenerationResult);
          setStage("result");
        }
      })
      .catch(() => {
        try {
          sessionStorage.removeItem(STORAGE_KEY);
        } catch {}
      });
  }, []);

  const remember = (sid: string | null) => {
    try {
      if (sid) sessionStorage.setItem(STORAGE_KEY, sid);
      else sessionStorage.removeItem(STORAGE_KEY);
    } catch {}
  };

  const resetAll = () => {
    cancel.current.cancelled = true;
    cancel.current = { cancelled: false };
    setStage("input");
    setSessionId(null);
    setFileInfo(null);
    setSummary(null);
    setJdSaved(null);
    setAnalysis(null);
    setProjected(null);
    setComparison(null);
    setResult(null);
    setJob(null);
    setDirty(false);
    setBusy(false);
    setUploading(false);
    remember(null);
  };

  const onFile = async (f: File) => {
    setError(null);
    const ext = f.name.split(".").pop()?.toLowerCase();
    if (ext !== "docx" && ext !== "pdf") return setError("Unsupported file type. Please upload a DOCX or PDF resume.");
    if (f.size > MAX_MB * 1024 * 1024) return setError(`The file is too large. Maximum size is ${MAX_MB} MB.`);
    if (sessionId) await api.startOver(sessionId).catch(() => {});
    const keepJd = jdText;
    resetAll();
    setJdText(keepJd);
    setFileInfo({ name: f.name, type: ext, size: f.size });
    setUploading(true);
    try {
      const up = await api.uploadResume(f);
      setSessionId(up.session_id);
      remember(up.session_id);
      const done = await pollJob<{ resume: ResumeSummary }>(up.job_id, setJob, cancel.current);
      setSummary(done.result!.resume);
    } catch (e) {
      if (!(e instanceof ApiError && e.message === "cancelled")) {
        fail(e);
        setFileInfo(null);
        setSessionId(null);
        remember(null);
      }
    } finally {
      setUploading(false);
      setJob(null);
    }
  };

  const onRemove = async () => {
    if (sessionId) await api.startOver(sessionId).catch(() => {});
    resetAll();
  };

  const decisionsOf = (changes: Change[]): Decisions =>
    Object.fromEntries(changes.map((c) => [c.change_id, c.status === "applied" ? "accepted" : c.status]));

  const runAnalysis = async () => {
    if (!sessionId || !summary) return;
    setError(null);
    setBusy(true);
    try {
      const saved = await api.submitJD(sessionId, jdFile ? "" : jdText, jdFile);
      setJdSaved(saved);
      setStage("analyzing");
      const { job_id } = await api.analyze(sessionId, style);
      const done = await pollJob<Analysis>(job_id, setJob, cancel.current);
      const a = done.result!;
      // Recommended changes start selected; the user can untick any of them.
      const pre = await api.applyChanges(sessionId, Object.fromEntries(a.changes.map((c) => [c.change_id, "accepted"])));
      setAnalysis({ ...a, changes: pre.changes });
      setProjected(pre.projected_ats);
      setComparison(pre.comparison);
      setStage("review");
    } catch (e) {
      if (!(e instanceof ApiError && e.message === "cancelled")) {
        fail(e);
        setStage("input");
      }
    } finally {
      setBusy(false);
      setJob(null);
    }
  };

  const onDecide = useCallback(
    async (d: Record<string, "accepted" | "rejected">) => {
      if (!sessionId) return;
      const patch = (cs: Change[]) =>
        cs.map((c) => (d[c.change_id] ? { ...c, status: d[c.change_id] === "accepted" && c.status === "applied" ? "applied" : d[c.change_id] } : c)) as Change[];
      if (stage === "result" && result) {
        setResult({ ...result, changes: patch(result.changes) });
        setDirty(true);
      }
      if (analysis) setAnalysis({ ...analysis, changes: patch(analysis.changes) });
      try {
        const r = await api.applyChanges(sessionId, d);
        setProjected(r.projected_ats);
        setComparison(r.comparison);
      } catch (e) {
        fail(e);
      }
    },
    [sessionId, stage, result, analysis],
  );

  const runGeneration = async (start: () => Promise<{ job_id: string }>) => {
    if (!sessionId) return;
    setError(null);
    setBusy(true);
    const prevStage = stage;
    setStage("generating");
    try {
      const { job_id } = await start();
      const done = await pollJob<GenerationResult>(job_id, setJob, cancel.current);
      const r = done.result!;
      setResult(r);
      setDirty(false);
      if (analysis) setAnalysis({ ...analysis, changes: r.changes });
      setStage("result");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
      if (!(e instanceof ApiError && e.message === "cancelled")) {
        fail(e);
        setStage(prevStage === "result" && result ? "result" : "review");
      }
    } finally {
      setBusy(false);
      setJob(null);
    }
  };

  const generate = () => analysis && runGeneration(() => api.tailor(sessionId!, decisionsOf(analysis.changes)));
  const regenerate = (mode: "fresh" | "selections") => {
    const changes = result?.changes ?? analysis?.changes ?? [];
    runGeneration(() => api.regenerate(sessionId!, mode, decisionsOf(changes), style));
  };

  const newSuggestions = async () => {
    if (!sessionId || !analysis) return;
    setError(null);
    setBusy(true);
    setStage("analyzing");
    try {
      const { job_id } = await api.suggest(sessionId, decisionsOf(analysis.changes), style);
      const done = await pollJob<Analysis>(job_id, setJob, cancel.current);
      const a = done.result!;
      const fresh: Decisions = Object.fromEntries(a.changes.filter((c) => c.status === "suggested").map((c) => [c.change_id, "accepted" as const]));
      const pre = await api.applyChanges(sessionId, fresh);
      setAnalysis({ ...a, changes: pre.changes });
      setProjected(pre.projected_ats);
      setComparison(pre.comparison);
    } catch (e) {
      fail(e);
    } finally {
      setStage("review");
      setBusy(false);
      setJob(null);
    }
  };

  const startOver = async () => {
    if (sessionId) await api.startOver(sessionId).catch(() => {});
    resetAll();
    setJdText("");
    setJdFile(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const canAnalyze = !!summary && !uploading && (jdFile !== null || jdText.trim().split(/\s+/).length >= 15);

  return (
    <div className="relative">
      <Header stage={stage} onStartOver={stage !== "input" ? startOver : undefined} />
      <main className="relative mx-auto w-full max-w-7xl px-4 pb-24 sm:px-6">
        {health && (!health.gemini || !health.converter) && (
          <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-800">
            {!health.gemini && "Gemini API key is not configured on the server — AI rewriting is disabled (deterministic suggestions still work). "}
            {!health.converter && "No PDF converter (LibreOffice or Microsoft Word) is available — documents cannot be generated."}
          </div>
        )}
        {error && (
          <div className="mb-4">
            <ErrorBox message={error} onDismiss={() => setError(null)} />
          </div>
        )}

        {stage === "input" && (
          <>
            <Hero />
            <div className="grid gap-6 lg:grid-cols-2">
              <UploadCard file={fileInfo} summary={summary} job={job} busy={uploading} onFile={onFile} onRemove={onRemove} />
              <JDCard text={jdText} file={jdFile} onText={setJdText} onFile={setJdFile} saved={jdSaved} />
            </div>
            <div className="mt-6 flex flex-col items-center gap-2">
              <Button variant="primary" size="lg" onClick={runAnalysis} disabled={!canAnalyze} loading={busy}>
                Analyze & Suggest Changes
              </Button>
              <p className="text-xs text-ink-3">
                {!summary ? "Upload your resume to continue." : !canAnalyze ? "Add the job description to continue." : "You'll review every change before anything is generated."}
              </p>
            </div>
          </>
        )}

        {stage === "analyzing" && <ProgressPanel title="Analyzing your resume…" job={job} />}
        {stage === "generating" && <ProgressPanel title="Building your tailored resume…" job={job} />}

        {stage === "review" && analysis && projected && (
          <ReviewView
            analysis={analysis}
            projected={projected}
            comparison={comparison}
            busy={busy}
            style={style}
            onStyle={setStyle}
            onDecide={onDecide}
            onGenerate={generate}
            onResuggest={newSuggestions}
          />
        )}

        {stage === "result" && result && sessionId && (
          <ResultView
            sessionId={sessionId}
            result={result}
            originalPages={summary?.original_preview_pages ?? analysis?.resume.original_preview_pages ?? 0}
            busy={busy}
            style={style}
            onStyle={setStyle}
            onRegenerate={regenerate}
            onDecide={onDecide}
            onStartOver={startOver}
            dirty={dirty}
          />
        )}
      </main>
      <footer className="mt-auto border-t border-line py-6 text-center text-xs text-ink-3">
        Your files are private, processed only for this session and deleted when you start over or after inactivity.
      </footer>
    </div>
  );
}

function Header({ stage, onStartOver }: { stage: Stage; onStartOver?: () => void }) {
  const steps = [
    { key: "input", label: "Upload" },
    { key: "review", label: "Review" },
    { key: "result", label: "Download" },
  ];
  const activeIdx = stage === "input" ? 0 : stage === "analyzing" || stage === "review" ? 1 : 2;
  return (
    <header className="relative z-10 mx-auto flex w-full max-w-7xl items-center gap-4 px-4 py-5 sm:px-6">
      <div className="flex items-center gap-2.5">
        <div className="brand-gradient flex h-9 w-9 items-center justify-center rounded-xl text-white shadow-md">
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M7 3h7l5 5v13H7z" strokeLinejoin="round" />
            <path d="M14 3v5h5M10 13h6M10 17h4" strokeLinecap="round" />
          </svg>
        </div>
        <div className="leading-tight">
          <div className="font-semibold tracking-tight">ResumePilot</div>
          <div className="text-[11px] text-ink-3">AI Resume Tailor</div>
        </div>
      </div>
      <nav className="mx-auto hidden items-center gap-2 sm:flex" aria-label="Progress">
        {steps.map((s, i) => (
          <div key={s.key} className="flex items-center gap-2">
            <span
              className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold ${
                i < activeIdx ? "bg-emerald-100 text-emerald-700" : i === activeIdx ? "brand-gradient text-white" : "bg-surface-2 text-ink-3"
              }`}
            >
              {i < activeIdx ? "✓" : i + 1}
            </span>
            <span className={`text-sm ${i === activeIdx ? "font-medium" : "text-ink-3"}`}>{s.label}</span>
            {i < steps.length - 1 && <span className="mx-1 h-px w-8 bg-line" />}
          </div>
        ))}
      </nav>
      {onStartOver ? (
        <Button variant="ghost" size="sm" onClick={onStartOver} className="ml-auto sm:ml-0">
          Start Over
        </Button>
      ) : (
        <span className="ml-auto w-[88px] sm:ml-0" />
      )}
    </header>
  );
}

function Hero() {
  return (
    <section className="relative mb-8 pt-4 text-center">
      <div className="glow" />
      <div className="relative">
        <h1 className="mx-auto max-w-3xl text-4xl font-semibold tracking-tight sm:text-5xl">
          Tailor <span className="brand-text">your</span> resume to any job — without inventing a thing.
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-ink-2">
          Upload your real resume and a job description. Get fact-checked suggestions you control, an explainable ATS score,
          and DOCX + PDF files that keep your original design.
        </p>
        <div className="mt-5 flex flex-wrap justify-center gap-2 text-xs text-ink-2">
          {["Your template preserved", "No fabricated skills", "Explainable ATS score", "Page count checked"].map((t) => (
            <span key={t} className="rounded-full border border-line bg-surface px-3 py-1">
              ✓ {t}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
