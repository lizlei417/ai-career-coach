export type Lang = 'zh-CN' | 'zh-TW' | 'en'
export type Feature = 'overview' | 'resume' | 'match' | 'interview' | 'settings'

export interface SourceLine {
  id: string
  text: string
  section: string
  heading: boolean
}

export interface Requirement {
  id: string
  category: 'responsibility' | 'required' | 'preferred'
  text: string
  source_ids: string[]
  kind: 'behavioral' | 'technical'
}

export interface Supplement {
  id: string
  text: string
  note?: string // which requirement prompted it
}

export interface Materials {
  pipeline_version?: string
  fingerprint: string
  job_title: string
  resume_lines: SourceLine[]
  jd_lines: SourceLine[]
  requirements: Requirement[]
  lang: Lang
}

export interface GuidanceSource {
  id: string
  source: string
  section: string
  excerpt: string
  used: boolean
  source_url?: string
  evidence_type?: string
  claims?: string[]
}
export interface Guidance {
  connected: boolean
  sources: GuidanceSource[]
}

export interface OptimizeItem {
  id: string
  source_id: string
  original: string
  section: string
  rewrite: string
  reason: string
  evidence_ids: string[]
  requirement_ids: string[]
  changes: string[]
  verification: { status: 'grounded' | 'needs_review'; unsupported_numbers: string[]; unsupported_terms: string[] }
}
export interface MissingItem {
  requirement_id: string
  kind: 'unclear' | 'absent'
  note: string
  ask: string
  related_ids: string[]
}
export interface OptimizeResult {
  questions_to_student?: string[]
  items: OptimizeItem[]
  missing: MissingItem[]
  hidden_count: number
  guidance: Guidance
  lang: Lang
}
export type Decision = { state: 'pending' | 'adopted' | 'kept' | 'edited'; text?: string }

export interface MatchItem {
  requirement_id: string
  status: 'direct' | 'partial' | 'none' | 'unassessed'
  evidence: { id: string; text: string }[]
  rationale: string
  next_step: { type: 'clarify' | 'supplement' | 'learn' | 'none'; text: string }
  priority: number
  verification: string
}
export interface MatchResult {
  items: MatchItem[]
  priority_order: string[]
  overview: string
  guidance: Guidance
  lang: Lang
}

export interface Question {
  guidance?: Guidance
  question: string
  type: 'behavioral' | 'technical'
  requirement_id: string
  resume_refs: { id: string; text: string }[]
  focus: string
  is_follow_up?: boolean
}
export interface Feedback {
  next_question?: Question | null
  session_summary?: string
  guidance?: Guidance
  on_topic: { quote: string; why: string }[]
  missing: string[]
  action: string
  structure: { situation: boolean; task: boolean; action: boolean; result: boolean } | null
  reasoning_note: string
  follow_up: { needed: boolean; question: string; reason: string }
  unverified_quotes_removed: number
  lang: Lang
}
export interface Attempt {
  answer: string
  feedback?: Feedback
}
export interface Turn {
  id: string
  question: Question
  attempts: Attempt[]
}
export interface Summary {
  guidance?: Guidance
  strengths: { text: string; turn: number | null }[]
  priorities: { text: string; turn: number | null }[]
  next_session: string
  lang: Lang
}

export interface LLMPublic {
  last_error?: string
  verified_at?: number | null
  connection?: 'verified' | 'failed' | 'unverified' | 'offline'
  provider: 'deepseek' | 'openai' | 'anthropic'
  model: string
  base_url: string
  timeout: number
  configured: boolean
  api_key_masked: string
  allow_runtime_config: boolean
}
export interface KBStatus {
  integrity?: boolean
  error?: string
  version?: string
  rejected?: number
  connected: boolean
  files: { name: string; chunks: number }[]
  chunks: number
}
