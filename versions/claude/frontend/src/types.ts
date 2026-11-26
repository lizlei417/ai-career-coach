export type Lang = "en" | "zh-CN" | "zh-TW";
export type Strings = Record<string, string[]>;
export type Trans = (
  key: string,
  params?: Record<string, string | number>,
) => string;
export type View = "optimize" | "match" | "interview";
export type Materials = {
  name: string;
  role: string;
  direction: string;
  resume: string;
  jd: string;
  filename: string;
  link: string;
  language: Lang;
};
export type Source = { id: string; text: string };
export type Requirement = {
  id: string;
  source_id: string;
  quote: string;
  category: string;
};
export type Evidence = { source_id: string; quote: string };
export type Guide = { id: string; filename: string; text: string };
export type Pack<T> = {
  data: T;
  language: Lang;
  guides: Guide[];
  blocked?: number;
};
export type Revision = {
  title?: string;
  id: string;
  requirement_ids: string[];
  evidence: Evidence[];
  optimized: string;
  reason: string;
};
export type Match = {
  requirement_id: string;
  status: string;
  evidence: Evidence[];
  assessment: string;
  gap_type: string;
  suggestion: string;
  priority: string;
};
export type Question = {
  guide_ids: string[];
  text: string;
  kind: string;
  requirement_id: string;
  evidence: Evidence[];
};
export type Feedback = {
  guide_ids: string[];
  strengths: string[];
  missing_information: string[];
  action: string;
  answer_quotes: string[];
  follow_up: string | null;
};
export type Turn = {
  question: Question;
  feedback: Feedback;
  answer: string;
  attempt: number;
};
export type Status = {
  configured: boolean;
  model: string;
  connection: string;
  guideCount: number;
  guideFiles: string[];
  warnings: Record<Lang, string>[];
};
export type Project = {
  materials: Materials;
  context: {
    fingerprint: string;
    resume: Source[];
    jd: Source[];
    requirements: Requirement[];
  } | null;
  optimization: Pack<{
    revisions: Revision[];
    gaps: { requirement_id: string; explanation: string; suggestion: string }[];
  }> | null;
  matching: Pack<{ matches: Match[] }> | null;
  interview: {
    question: Question | null;
    question_number: number;
    attempt: number;
    guides: Guide[];
    sourceArchive?: Record<string, Guide>;
    questionLanguage?: Lang;
    feedback: Feedback | null;
    feedbackGuides?: Guide[];
    feedbackLanguage?: Lang;
    turns: Turn[];
    ended: boolean;
    summary: Pack<{
      strengths: string[];
      practice_priorities: string[];
      next_steps: string[];
    }> | null;
  };
  decisions: Record<string, { choice: string; edit: string }>;
  version: number;
  status: Status;
};
export type Act = (
  kind: string,
  extra?: Record<string, string>,
) => Promise<boolean>;
export type TaskProps = {
  project: Project;
  t: Trans;
  lang: Lang;
  act: Act;
  busy: boolean;
};
export const emptyMaterials: Materials = {
  name: "",
  role: "",
  direction: "",
  resume: "",
  jd: "",
  filename: "",
  link: "",
  language: "en",
};
