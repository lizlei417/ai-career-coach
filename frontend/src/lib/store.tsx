import { createContext, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { saveProject, type Project, type SavedProject } from './projects'
import { ApiError, get, post } from './api'
import { errorKey, translate, type TKey } from './i18n'
import type {
  Attempt, Decision, Feature, Feedback, KBStatus, Lang, LLMPublic, MatchResult, Materials,
  OptimizeResult, Question, Summary, Supplement, Turn,
} from './types'

/* ------------------------------------------------------------------ state */

export interface Inputs {
  resumeText: string
  resumeFile: { name: string; pages: number; blob?: Blob } | null
  jobTitle: string
  jdText: string
  jdUrl: string
  jdFromUrl: boolean
}

interface Stamped<T> {
  data: T
  fingerprint: string
  supKey: string
}

export interface InterviewState {
  status: 'idle' | 'active' | 'ended'
  turns: Turn[]
  summary: Summary | null
  fingerprint: string
}

export interface Persisted {
  drafts: Record<string,string>
  lang: Lang
  entered: boolean
  feature: Feature
  materialsOpen: boolean
  inputs: Inputs
  inputsKey: string // key of inputs at the time materials were prepared
  materials: Materials | null
  supplements: Supplement[]
  resume: (Stamped<OptimizeResult> & { decisions: Record<string, Decision> }) | null
  match: Stamped<MatchResult> | null
  interview: InterviewState
}

const STORAGE = import.meta.env.VITE_PAGES_DEMO === '1' ? 'pages.codex.v1' : 'aicc.v1'
const storage = import.meta.env.VITE_PAGES_DEMO === '1' ? sessionStorage : localStorage
const emptyInputs: Inputs = { resumeText: '', resumeFile: null, jobTitle: '', jdText: '', jdUrl: '', jdFromUrl: false }
const emptyInterview: InterviewState = { status: 'idle', turns: [], summary: null, fingerprint: '' }

export const initial: Persisted = {
  drafts: {},
  lang: 'zh-CN',
  entered: false,
  feature: 'overview',
  materialsOpen: true,
  inputs: emptyInputs,
  inputsKey: '',
  materials: null,
  supplements: [],
  resume: null,
  match: null,
  interview: emptyInterview,
}

export function loadLegacy(): Persisted {
  try {
    const raw = storage.getItem(STORAGE)
    if (!raw) return initial
    const p = JSON.parse(raw)
    return { ...initial, ...p, inputs: { ...emptyInputs, ...(p.inputs || {}) }, interview: { ...emptyInterview, ...(p.interview || {}) } }
  } catch {
    return initial
  }
}

export function keyOf(i: Pick<Inputs, 'resumeText' | 'jdText' | 'jobTitle'>): string {
  // small non-cryptographic hash, only for change detection
  const s = `${i.resumeText.trim()}\u0000${i.jdText.trim()}\u0000${i.jobTitle.trim()}`
  let h1 = 0x811c9dc5, h2 = 0
  for (let k = 0; k < s.length; k++) {
    const c = s.charCodeAt(k)
    h1 = Math.imul(h1 ^ c, 16777619)
    h2 = (h2 * 31 + c) | 0
  }
  return `${(h1 >>> 0).toString(36)}${(h2 >>> 0).toString(36)}${s.length}`
}
const supKeyOf = (s: Supplement[]) => s.map((x) => x.id + ':' + x.text.length).join('|')

/* ------------------------------------------------------------------ busy / errors */

export type BusyKey = 'prepare' | 'pdf' | 'url' | 'resume' | 'match' | 'question' | 'feedback' | 'summary'
export type ErrKey = BusyKey

interface Ctx {
  project: Project
  projects: Project[]
  changeProject: (value: string, create?: boolean) => Promise<void>
  switching: boolean
  saving: boolean
  saveFailed: boolean
  setDraft: (id: string, value: string) => void
  s: Persisted
  t: (k: TKey, v?: Record<string, string | number>) => string
  busy: Partial<Record<BusyKey, boolean>>
  errors: Partial<Record<ErrKey, string>>
  llm: LLMPublic | null
  kb: KBStatus | null
  // derived
  inputsDirty: boolean
  ready: boolean
  isStale: (fp?: string) => boolean
  supKey: string
  // actions
  setLang: (l: Lang) => void
  enter: () => void
  leave: () => void
  setFeature: (f: Feature) => void
  setMaterialsOpen: (v: boolean) => void
  setInputs: (p: Partial<Inputs>) => void
  clearError: (k: ErrKey) => void
  setError: (k: ErrKey, code: string) => void
  run: <T>(k: BusyKey, fn: () => Promise<T>) => Promise<T | undefined>
  prepare: () => Promise<boolean>
  addSupplement: (text: string, note?: string) => void
  removeSupplement: (id: string) => void
  generateResume: () => Promise<void>
  setDecision: (id: string, d: Decision) => void
  generateMatch: () => Promise<void>
  askQuestion: (target?: string) => Promise<void>
  submitAnswer: (answer: string) => Promise<void>
  takeFollowUp: () => void
  endInterview: () => Promise<void>
  loadSummary: () => Promise<void>
  resetInterview: () => void
  resumeInterview: () => void
  refreshStatus: () => Promise<void>
  clearAll: () => void
}

const AppCtx = createContext<Ctx | null>(null)

type ProjectAction = (value: string, lang: Lang) => Promise<void>
export function AppProvider({ children, project, projects, select, create }: {
  children: ReactNode; project: SavedProject; projects: Project[]; select: ProjectAction; create: ProjectAction
}) {
  const [s, setS] = useState<Persisted>(project.state)
  const [switching, setSwitching] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveFailed, setSaveFailed] = useState(false)
  const [busy, setBusy] = useState<Partial<Record<BusyKey, boolean>>>({})
  const [errors, setErrors] = useState<Partial<Record<ErrKey, string>>>({})
  const [llm, setLlm] = useState<LLMPublic | null>(null)
  const [kb, setKb] = useState<KBStatus | null>(null)
  const sRef = useRef(s)
  sRef.current = s

  const revision = useRef(project.revision)
  const pendingSave = useRef(Promise.resolve())
  useLayoutEffect(() => {
    let current = true
    setSaving(true)
    const guard = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', guard)
    const write = pendingSave.current.catch(() => {}).then(async () => {
      revision.current = await saveProject({ id: project.id, name: project.name, revision: revision.current, state: s })
    })
    pendingSave.current = write
    function finish(failed: boolean) {
      if (!current) return
      setSaveFailed(failed)
      setSaving(false)
      if (!failed) window.removeEventListener('beforeunload', guard)
    }
    write.then(() => finish(false), () => finish(true))
    return () => { current = false; window.removeEventListener('beforeunload', guard) }
  }, [project.id, project.name, s])

  async function changeProject(value: string, isNew = false) {
    if (switching || Object.values(busy).some(Boolean)) return
    setSwitching(true)
    try {
      await pendingSave.current
      await (isNew ? create : select)(value, s.lang)
    } catch {
      setSaveFailed(true)
    } finally {
      setSwitching(false)
    }
  }

  useEffect(() => {
    document.documentElement.lang = s.lang
  }, [s.lang])

  const t = useCallback((k: TKey, v?: Record<string, string | number>) => translate(s.lang, k, v), [s.lang])

  const refreshStatus = useCallback(async () => {
    try {
      const h = await get<{ llm: LLMPublic; kb: KBStatus }>('/api/health')
      setLlm(h.llm)
      setKb(h.kb)
    } catch {
      setLlm(null)
      setKb(null)
    }
  }, [])
  useEffect(() => {
    refreshStatus()
  }, [refreshStatus])

  const setError = useCallback((k: ErrKey, code: string) => setErrors((e) => ({ ...e, [k]: code })), [])
  const clearError = useCallback((k: ErrKey) => setErrors((e) => ({ ...e, [k]: undefined })), [])

  const run = useCallback(async <T,>(k: BusyKey, fn: () => Promise<T>) => {
    setBusy((b) => ({ ...b, [k]: true }))
    setErrors((e) => ({ ...e, [k]: undefined }))
    try {
      return await fn()
    } catch (e) {
      const code = e instanceof ApiError ? e.code : 'unknown'
      if (code !== 'ABORTED') setErrors((er) => ({ ...er, [k]: code }))
      if (code === 'LLM_NOT_CONFIGURED' || code === 'LLM_AUTH') refreshStatus()
      return undefined
    } finally {
      setBusy((b) => ({ ...b, [k]: false }))
    }
  }, [refreshStatus])

  const patch = useCallback((p: Partial<Persisted> | ((s: Persisted) => Partial<Persisted>)) => {
    setS((cur) => ({ ...cur, ...(typeof p === 'function' ? p(cur) : p) }))
  }, [])

  const inputsDirty = !!s.materials && keyOf(s.inputs) !== s.inputsKey
  const ready = !!s.materials
  const supKey = supKeyOf(s.supplements)
  const isStale = useCallback((fp?: string) => !!fp && (!s.materials || fp !== s.materials.fingerprint || inputsDirty), [s.materials, inputsDirty])

  const bundle = () => {
    const cur = sRef.current
    return { ...cur.materials!, supplements: cur.supplements }
  }

  /* ---------------- materials */
  const prepare = useCallback(async () => {
    const cur = sRef.current
    const { resumeText, jdText, jobTitle } = cur.inputs
    if (!resumeText.trim()) {
      setError('prepare', 'RESUME_EMPTY')
      return false
    }
    if (!jdText.trim()) {
      setError('prepare', 'JD_EMPTY')
      return false
    }
    const out = await run('prepare', () =>
      post<Materials>('/api/materials/prepare', { resume_text: resumeText, jd_text: jdText, job_title: jobTitle, lang: cur.lang }),
    )
    if (!out) return false
    // Results tied to an older fingerprint are kept but shown as stale until regenerated.
    // Supplements are student-provided facts and stay valid across re-analysis.
    patch((c) => ({
      materials: out,
      inputsKey: keyOf(c.inputs),
      feature: c.feature === 'settings' ? 'overview' : c.feature,
    }))
    return true
  }, [run, patch, setError])

  const addSupplement = useCallback((text: string, note?: string) => {
    const v = text.trim()
    if (!v) return
    patch((c) => {
      const n = c.supplements.reduce((m, x) => Math.max(m, Number(x.id.slice(1)) || 0), 0) + 1
      return { supplements: [...c.supplements, { id: `S${n}`, text: v.slice(0, 1200), note }] }
    })
  }, [patch])
  const removeSupplement = useCallback((id: string) => patch((c) => ({ supplements: c.supplements.filter((x) => x.id !== id) })), [patch])

  /* ---------------- resume */
  const generateResume = useCallback(async () => {
    const cur = sRef.current
    if (!cur.materials) return
    const out = await run('resume', () => post<OptimizeResult>('/api/resume/optimize', { materials: bundle(), lang: cur.lang }))
    if (!out) return
    patch((c) => ({
      resume: { data: out, fingerprint: c.materials!.fingerprint, supKey: supKeyOf(c.supplements), decisions: {} },
    }))
  }, [run, patch])

  const setDecision = useCallback((id: string, d: Decision) => {
    patch((c) => (c.resume ? { resume: { ...c.resume, decisions: { ...c.resume.decisions, [id]: d } } } : {}))
  }, [patch])

  /* ---------------- match */
  const generateMatch = useCallback(async () => {
    const cur = sRef.current
    if (!cur.materials) return
    const out = await run('match', () => post<MatchResult>('/api/match', { materials: bundle(), lang: cur.lang }))
    if (!out) return
    patch((c) => ({ match: { data: out, fingerprint: c.materials!.fingerprint, supKey: supKeyOf(c.supplements) } }))
  }, [run, patch])

  /* ---------------- interview */
  const askQuestion = useCallback(async (target?: string) => {
    const cur = sRef.current
    if (!cur.materials) return
    const asked = cur.interview.fingerprint === cur.materials.fingerprint
      ? cur.interview.turns.map((x) => ({ question: x.question.question, requirement_id: x.question.requirement_id }))
      : []
    const q = await run('question', () =>
      post<Question>('/api/interview/question', { materials: bundle(), lang: cur.lang, asked, target_requirement: target || null }),
    )
    if (!q) return
    patch((c) => {
      const base = c.interview.fingerprint === c.materials!.fingerprint ? c.interview : emptyInterview
      return {
        interview: {
          ...base,
          status: 'active',
          summary: null,
          fingerprint: c.materials!.fingerprint,
          turns: [...base.turns, { id: crypto.randomUUID?.() ?? String(Date.now()), question: q, attempts: [] }],
        },
      }
    })
  }, [run, patch])

  const submitAnswer = useCallback(async (answer: string) => {
    const cur = sRef.current
    const turn = cur.interview.turns[cur.interview.turns.length - 1]
    if (!cur.materials || !turn) return
    if (!answer.trim()) {
      setError('feedback', 'ANSWER_EMPTY')
      return
    }
    const history = turn.attempts.filter((a) => a.feedback).map((a) => ({ question: turn.question.question, answer: a.answer }))
    const fb = await run('feedback', () =>
      post<Feedback>('/api/interview/feedback', { materials: bundle(), lang: cur.lang, question: turn.question, answer, history }),
    )
    if (!fb) return
    patch((c) => {
      const turns = [...c.interview.turns]
      const last = turns[turns.length - 1]
      turns[turns.length - 1] = { ...last, attempts: [...last.attempts, { answer, feedback: fb } as Attempt] }
      return { interview: { ...c.interview, turns } }
    })
  }, [run, patch, setError])

  const takeFollowUp = useCallback(() => {
    patch((c) => {
      const last = c.interview.turns[c.interview.turns.length - 1]
      const fb = last?.attempts[last.attempts.length - 1]?.feedback
      if (!fb?.follow_up.needed) return {}
      const q: Question = {
        question: fb.follow_up.question,
        type: last.question.type,
        requirement_id: last.question.requirement_id,
        resume_refs: last.question.resume_refs,
        focus: last.question.focus,
        is_follow_up: true,
      }
      return {
        interview: {
          ...c.interview,
          turns: [...c.interview.turns, { id: crypto.randomUUID?.() ?? String(Date.now()), question: q, attempts: [] }],
        },
      }
    })
  }, [patch])

  const summaryTurns = () =>
    sRef.current.interview.turns
      .filter((x) => x.attempts.length)
      .map((x) => {
        const a = x.attempts[x.attempts.length - 1]
        return { question: x.question.question, answer: a.answer, feedback: a.feedback }
      })

  const loadSummary = useCallback(async () => {
    const turns = summaryTurns()
    if (!turns.length) return
    const out = await run('summary', () => post<Summary>('/api/interview/summary', { lang: sRef.current.lang, turns }))
    if (out) patch((c) => ({ interview: { ...c.interview, summary: out } }))
  }, [run, patch])

  const endInterview = useCallback(async () => {
    patch((c) => ({ interview: { ...c.interview, status: 'ended' } }))
    await loadSummary()
  }, [patch, loadSummary])

  const resumeInterview = useCallback(() => patch((c) => ({ interview: { ...c.interview, status: 'active' } })), [patch])
  const resetInterview = useCallback(() => {
    patch({ interview: emptyInterview })
    setErrors((e) => ({ ...e, question: undefined, feedback: undefined, summary: undefined }))
  }, [patch])

  const clearAll = useCallback(() => {
    setS({ ...initial, lang: sRef.current.lang, entered: true })
    setErrors({})
  }, [])

  const value: Ctx = {
    project, projects, switching, changeProject, saving, saveFailed,
    setDraft: (id, value) => patch(c => ({ drafts: { ...c.drafts, [id]: value } })),
    s, t, busy, errors, llm, kb, inputsDirty, ready, isStale, supKey,
    setLang: (l) => patch({ lang: l }),
    enter: () => patch({ entered: true }),
    leave: () => patch({ entered: false }),
    setFeature: (f) => patch({ feature: f }),
    setMaterialsOpen: (v) => patch({ materialsOpen: v }),
    setInputs: (p) => patch((c) => ({ inputs: { ...c.inputs, ...p } })),
    clearError, setError, run, prepare, addSupplement, removeSupplement,
    generateResume, setDecision, generateMatch,
    askQuestion, submitAnswer, takeFollowUp, endInterview, loadSummary, resetInterview, resumeInterview,
    refreshStatus, clearAll,
  }
  return <AppCtx.Provider value={value}>{children}</AppCtx.Provider>
}

export function useApp() {
  const c = useContext(AppCtx)
  if (!c) throw new Error('AppProvider missing')
  return c
}

export function useErrorText(code?: string) {
  const { t } = useApp()
  return useMemo(() => (code ? t(errorKey(code)) : ''), [code, t])
}
