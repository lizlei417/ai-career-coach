import { ApiError } from './api'
import { SAMPLE_JD, SAMPLE_RESUME } from './sample'
import type { Lang } from './types'

interface Input {
  resume_text?: string
  jd_text?: string
  lang?: Lang
  asked?: unknown[]
}
const guidance = { connected: false, sources: [] }
const lines = (text: string, prefix: string) => text.split('\n').map((text, index) => ({
  id: prefix + (index + 1), text, section: '', heading: index === 0,
}))
const resume = lines(SAMPLE_RESUME, 'R')
const jd = lines(SAMPLE_JD, 'J')
const requirements = jd.slice(1).map((line, i) => ({
  id: 'Q' + (i + 1), category: 'responsibility', text: line.text, source_ids: [line.id], kind: 'behavioral',
}))
export function demo(path: string, data: Input = {}): unknown {
  const lang = data.lang || 'zh-CN'
  const reason = 'Example: lead with the research method and keep the original scope.'
  const action = 'Practice prompt: describe one finding and the decision it informed.'
  switch (path) {
    case '/api/health':
      return { llm: { provider: 'openai', model: 'Demo Mode', base_url: '', timeout: 90, configured: true, api_key_masked: '', allow_runtime_config: false }, kb: { connected: false, files: [], chunks: 0 }, prompts: [] }
    case '/api/materials/prepare':
      if (data.resume_text?.trim() !== SAMPLE_RESUME || data.jd_text?.trim() !== SAMPLE_JD) throw new ApiError('DEMO_SAMPLE')
      return { fingerprint: 'fictional-campus-app', job_title: jd[0].text, resume_lines: resume, jd_lines: jd, requirements, lang }
    case '/api/resume/optimize':
      return { items: [{ id: 'D1', source_id: 'R2', original: resume[1].text, section: '', rewrite: 'Interviewed students to collect feedback on a fictional campus app.', reason, evidence_ids: ['R2'], requirement_ids: ['Q1'], changes: [], verification: { status: 'grounded', unsupported_numbers: [], unsupported_terms: [] } }], missing: [], hidden_count: 0, guidance, lang }
    case '/api/match':
      return { items: requirements.map((r,i) => ({ requirement_id: r.id, status: i ? 'none' : 'direct', evidence: i ? [] : [resume[1]], rationale: i ? 'The sample contains no SQL experience.' : 'The sample describes student interviews.', next_step: { type: i ? 'learn' : 'none', text: i ? 'Practice preparing a usage report in SQL.' : '' }, priority: i ? 1 : 2, verification: '' })), priority_order: ['Q2'], overview: 'Fictional campus app case', guidance, lang }
    case '/api/interview/question':
      return { question: data.asked?.length ? 'How did you share the findings with the team?' : 'How did you gather feedback on the campus app?', type: 'behavioral', requirement_id: 'Q1', resume_refs: [resume[1]], focus: 'User research' }
    case '/api/interview/feedback':
      return { on_topic: [], missing: [action], action, structure: null, reasoning_note: 'Scripted example feedback.', follow_up: { needed: true, question: 'What decision changed after the interviews?', reason: 'Practice explaining impact.' }, unverified_quotes_removed: 0, lang }
    case '/api/interview/summary':
      return { strengths: [], priorities: [{ text: action, turn: null }], next_session: 'Practice describing one concrete decision.', lang }
    default: throw new ApiError('DEMO_ONLY')
  }
}
