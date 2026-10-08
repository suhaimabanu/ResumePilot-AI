export type ChangeStatus = "suggested" | "accepted" | "rejected" | "applied";

export interface Change {
  change_id: string;
  block_id: string;
  section: string;
  section_title: string;
  entry_label: string;
  kind: "rewrite" | "reorder_skills";
  original: string;
  suggested: string;
  reason: string;
  source_claims: string[];
  source_evidence: string[];
  jd_keywords: string[];
  impact: "high" | "medium" | "low";
  status: ChangeStatus;
  validation: { passed: boolean; issues: string[] };
}

export interface ResumeSummary {
  filename: string;
  file_type: "docx" | "pdf";
  page_count: number | null;
  counts: {
    pages: number | null;
    sections: number;
    experience_entries: number;
    skills: number;
    projects: number;
    education_entries: number;
    certifications: number;
    paragraphs: number;
  };
  name: string;
  headline: string;
  sections: { key: string; title: string }[];
  experience: { title: string; organization: string; dates: string; bullets: number }[];
  skills: string[];
  certifications: string[];
  warnings: string[];
  ocr_used: boolean;
  profile_photo: boolean;
  template: { tables: number; images: number; fonts: string[]; page_size: string | null };
  structuring: string;
  original_preview_pages: number;
}

export interface KeywordEvidence {
  term: string;
  category: string;
  importance: "required" | "preferred" | "general";
  status: "supported" | "partial" | "missing";
  match_type: string;
  evidence: string;
  explanation: string;
  usable: boolean;
}

export interface ScoreCategory {
  key: string;
  label: string;
  max: number;
  score: number;
  explanation: string;
  matched?: string[];
  partial?: string[];
  missing?: string[];
  stuffing?: string[];
  items?: { responsibility: string; alignment: number }[];
  checks?: { check: string; passed: boolean; points: number }[];
  years?: number;
  required_years?: number | null;
  title_similarity?: number;
}

export interface Coverage {
  total: number;
  matched: number;
  partial: number;
  missing: number;
  percent: number;
  matched_terms: string[];
  partial_terms: string[];
  missing_terms: string[];
}

export interface AtsScore {
  total: number;
  categories: ScoreCategory[];
  keyword_coverage: Coverage;
  required_coverage: { percent: number; matched: number; total: number };
  keywords: { term: string; importance: string; status: string; match_type: string; count: number }[];
}

export interface Comparison {
  original: number;
  tailored: number;
  improvement: number;
  keyword_coverage: {
    original: number;
    tailored: number;
    improvement: number;
    matched_before: number;
    matched_after: number;
    total: number;
  };
  required_coverage: { original: number; tailored: number };
  categories: { key: string; label: string; max: number; original: number; tailored: number }[];
}

export interface Analysis {
  jd: {
    job_title: string;
    company: string;
    years_experience: number | null;
    required_skills: string[];
    preferred_skills: string[];
    responsibilities: string[];
    keywords: { term: string; category: string; importance: string }[];
    source: string;
  };
  keyword_evidence: KeywordEvidence[];
  keyword_groups: { supported: KeywordEvidence[]; partial: KeywordEvidence[]; missing: KeywordEvidence[] };
  original_ats: AtsScore;
  projected_ats: AtsScore;
  changes: Change[];
  blocked_count: number;
  blocked: { block_id: string; section: string; suggested: string; issues: string[] }[];
  resume: ResumeSummary;
  ai_enabled: boolean;
  ai_status: AiStatus;
}

/** Outcome of the last AI tailoring call ("" before any). */
export type AiStatus = "ok" | "weak" | "failed" | "disabled" | "";

export interface CheckItem {
  check: string;
  passed: boolean;
  detail?: string;
}

export interface GenerationResult {
  generation: number;
  ats: { original: AtsScore; tailored: AtsScore; comparison: Comparison };
  ats_score: number;
  page_count: number;
  pages: {
    original: number | null;
    tailored: number;
    preserved: boolean;
    status: "preserved" | "shorter" | "longer";
    optimization: string[];
  };
  template: {
    score: number;
    level: "High" | "Medium" | "Low";
    aspects: { aspect: string; score: number; status: string; detail: string }[];
    limitations: string[];
  };
  validation: {
    summary: Record<string, boolean>;
    facts: { passed: boolean; detail: string };
    completeness: { passed: boolean; checks: CheckItem[] };
    docx: { passed: boolean; checks: CheckItem[] };
    pdf: { passed: boolean; checks: CheckItem[] };
    consistency: { passed: boolean; checks: CheckItem[] };
    visual: {
      passed: boolean;
      pages_checked: number;
      issues: { severity: string; code: string; message: string; page: number | null }[];
    };
    identity: { passed: boolean; issues: string[] };
  };
  downloads: Record<"docx" | "pdf" | "both", { file_id: string; name: string }>;
  preview: { pages: number; generation: number };
  changes: Change[];
  applied_count: number;
  converter: string;
  notes: string[];
  ai_status: AiStatus;
}

export interface JobStep {
  key: string;
  label: string;
  state: "done" | "active" | "pending";
}

export interface JobStatus<T = unknown> {
  job_id: string;
  kind: string;
  status: "queued" | "processing" | "waiting_for_user" | "completed" | "failed";
  step: string;
  step_label: string;
  progress: number;
  steps: JobStep[];
  notes: string[];
  error: string | null;
  result: T | null;
}

export type Style = "balanced" | "ats" | "concise" | "achievement" | "conservative";
