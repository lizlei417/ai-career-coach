import { flushSync } from 'react-dom'
import { guardResumeNavigation } from './resume-navigation'
import { requestCareerProfile } from './career-profile'
import {publicHome,entryFeature,changeFeature,rememberLanguage} from '../cloud'
import { createContext, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { renameProject as renameSaved, deleteProject as deleteSaved,readProject,saveProject, type Project, type SavedProject } from './projects'
import { ApiError, get, post } from './api'
import { errorKey, translate, type TKey } from './i18n'
import type {
  Attempt, Decision, Feature, Feedback, KBStatus, Lang, LLMPublic, MatchResult, Materials,
  OptimizeResult, Question, Summary, Supplement, Turn,
} from './types'

/* ------------------------------------------------------------------ state */

export interface Inputs {
  resumeText: string
  resumeFile: { name: string; pages: number; fileId?: string } | null
  jobTitle: string
  jdText: string
  jdUrl: string
  jdFromUrl: boolean
  jdSourceUrl?: string
  languageConfirmed?: boolean
  userStage?: "no_experience" | "current_student" | "recent_graduate"
  jobGoal?: "internship" | "job"
}

interface Stamped<T> {
  data: T
  fingerprint: string
  supKey: string
  source?: { text: string; lines: Materials['resume_lines'] }
}

export interface InterviewState {
  status: 'idle' | 'active' | 'ended'
  turns: Turn[]
  summary: Summary | null
  fingerprint: string
}

export interface FinalResumeVersion { text: string; savedAt: string; version: number; baseText: string }

export interface Persisted {
  finalResume?: FinalResumeVersion
  finalResumeHistory?: FinalResumeVersion[]
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

export function keyOf(i: Pick<Inputs, 'resumeText' | 'jdText' | 'jobTitle' | 'userStage' | 'jobGoal'>): string {
  // small non-cryptographic hash, only for change detection
  const profile = i.userStage || i.jobGoal ? `\u0000${i.userStage || ""}\u0000${i.jobGoal || ""}` : ""
  const s = `${i.resumeText.trim()}\u0000${i.jdText.trim()}\u0000${i.jobTitle.trim()}${profile}`
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
  renameProject: (id:string,name:string)=>Promise<void>
  deleteProject: (id:string)=>Promise<void>
  reloadProjects:()=>Promise<void>
  pendingProject:string
  switching: boolean
  saving: boolean
  saveFailed: boolean
  resumeDirty: boolean
  setResumeDirty: (dirty: boolean) => void
  saveFinalResume: (text: string, baseText: string) => Promise<void>
  flushSave: () => Promise<void>
  retrySave: () => Promise<void>
  setDraft: (id: string, value: string) => void
  s: Persisted
  t: (k: TKey, v?: Record<string, string | number>) => string
  busy: Partial<Record<BusyKey, boolean>>
  errors: Partial<Record<ErrKey, string>>
  llm: LLMPublic | null
  kb: KBStatus | null
  // derived
  materialsOutdated: boolean
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
  configureProfile: () => Promise<boolean>
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
export function AppProvider({ children, project, projects, select, create, renamed, removed, reload }: {
  children: ReactNode; project: SavedProject; projects: Project[]; select: ProjectAction; create: ProjectAction;renamed:(id:string,name:string,revision:number)=>void;removed:ProjectAction;reload:()=>Promise<void>
}) {
  const [s, setS] = useState<Persisted>({...project.state,feature:entryFeature(project.state.feature)})
  const [activeId,setActiveId]=useState(project.id)
  const [pendingProject,setPendingProject]=useState('')
  const [switching, setSwitching] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveFailed, setSaveFailed] = useState(false)
  const [resumeDirty, setResumeDirty] = useState(false)
  const [busy, setBusy] = useState<Partial<Record<BusyKey, boolean>>>({})
  const running = useRef(new Set<BusyKey>())
  const [errors, setErrors] = useState<Partial<Record<ErrKey, string>>>({})
  const [llm, setLlm] = useState<LLMPublic | null>(null)
  const [kb, setKb] = useState<KBStatus | null>(null)
  const sRef = useRef(s)
  sRef.current = s

  const confirmedResume = useRef({ current: s.finalResume, history: s.finalResumeHistory || [] })
  const lastSaved=useRef(s)
  const revision = useRef(project.revision)
  const pendingSave = useRef(Promise.resolve())
  const projectName=useRef(project.name)
  projectName.current=project.name
  useEffect(() => {
    if (!saving && !saveFailed) return
    const guard = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', guard)
    return () => window.removeEventListener('beforeunload', guard)
  }, [saving, saveFailed])
  if(activeId!==project.id){
    setActiveId(project.id)
    const next={...project.state,feature:entryFeature(s.feature)}
    lastSaved.current=next
    confirmedResume.current={current:next.finalResume,history:next.finalResumeHistory || []}
    setS(next)
    revision.current=project.revision
    setErrors({});setSaveFailed(false);setSaving(false)
  }
  useLayoutEffect(() => {
    if(!project.id||lastSaved.current===s)return
    lastSaved.current=s
    let current = true
    setSaving(true)
    const name=projectName.current
    const write = pendingSave.current.catch(() => {}).then(async () => {
      revision.current = await saveProject({ id: project.id, name, revision: revision.current, state: s })
      confirmedResume.current={current:s.finalResume,history:s.finalResumeHistory || []}
    })
    pendingSave.current = write
    function finish(failed: boolean) {
      if (!current) return
      setSaveFailed(failed)
      setSaving(false)
    }
    write.then(() => finish(false), () => finish(true))
    return () => { current = false }
  }, [project.id, s])

  async function changeProject(value: string, isNew = false) {
    if (switching || Object.values(busy).some(Boolean)) return
    if (!await guardResumeNavigation()) return
    setSwitching(true)
    setPendingProject(isNew?'':value)
    try {
      await pendingSave.current
      await (isNew ? create : select)(value, s.lang)
    } catch {
      setSaveFailed(true)
      throw Error('Project operation failed')
    } finally {
      setPendingProject('')
      setSwitching(false)
    }
  }

  async function renameProject(id:string,name:string){
    if(switching||Object.values(busy).some(Boolean))throw Error('Busy')
    await pendingSave.current
    const record=id===project.id?{revision:revision.current}:await readProject(id)
    const result=await renameSaved(id,name.trim(),record.revision)
    if(id===project.id)revision.current=result.revision
    renamed(id,result.name,result.revision)
  }
  async function deleteProject(id:string){
    if (!await guardResumeNavigation()) return
    if(switching||Object.values(busy).some(Boolean))throw Error('Busy')
    await pendingSave.current
    await deleteSaved(id)
    await removed(id,s.lang)
  }

  useEffect(()=>{const update=async()=>{if(await guardResumeNavigation())setS(cur=>({...cur,feature:entryFeature(cur.feature)}));else changeFeature(sRef.current.feature)};window.addEventListener('popstate',update);return ()=>window.removeEventListener('popstate',update)},[])

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

  const profileRequest = useRef<Promise<boolean> | null>(null)
  const profileProject = useRef(project.id)
  profileProject.current = project.id
  const ensureProfile = useCallback(async (force = false): Promise<boolean> => {
    if (profileRequest.current) return profileRequest.current
    const cur = sRef.current
    if (!force && cur.inputs.languageConfirmed && cur.inputs.userStage && cur.inputs.jobGoal) return true
    const id = profileProject.current
    const pending = (async () => {
      const choice = await requestCareerProfile(cur.lang, cur.inputs)
      if (!choice || profileProject.current !== id) return false
      rememberLanguage(choice.lang)
      const next = { ...sRef.current, lang: choice.lang, inputs: { ...sRef.current.inputs, languageConfirmed: true,
        userStage: choice.userStage, jobGoal: choice.jobGoal } }
      sRef.current = next
      setS(next)
      setErrors(e => Object.fromEntries(Object.entries(e).filter(([, code]) => code !== 'LANGUAGE_REQUIRED' && code !== 'PROFILE_REQUIRED')))
      return true
    })()
    profileRequest.current = pending
    try { return await pending } finally { profileRequest.current = null }
  }, [])

  const run = useCallback(async <T,>(k: BusyKey, fn: () => Promise<T>) => {
    if (running.current.has(k)) return undefined
    if (llm?.configured === false && k !== 'pdf' && k !== 'url') {
      setErrors(e => ({ ...e, [k]: 'LLM_NOT_CONFIGURED' }))
      return undefined
    }
    if (k !== 'pdf' && k !== 'url' && !await ensureProfile()) return undefined
    if (running.current.has(k)) return undefined
    running.current.add(k)
    setBusy((b) => ({ ...b, [k]: true }))
    setErrors((e) => ({ ...e, [k]: undefined }))
    try {
      return await fn()
    } catch (e) {
      const code = e instanceof ApiError ? e.code : 'unknown'
      if (code !== 'ABORTED') setErrors((er) => ({ ...er, [k]: code }))
      return undefined
    } finally {
      running.current.delete(k)
      void refreshStatus()
      setBusy((b) => ({ ...b, [k]: false }))
    }
  }, [refreshStatus, llm, ensureProfile])

  const patch = useCallback((p: Partial<Persisted> | ((s: Persisted) => Partial<Persisted>)) => {
    setS((cur) => ({ ...cur, ...(typeof p === 'function' ? p(cur) : p) }))
  }, [])

  const materialsOutdated = !!s.materials && s.materials.pipeline_version !== "m3-jd-sentences-v1"
  const inputsDirty = !!s.materials && keyOf(s.inputs) !== s.inputsKey
  const ready = !!s.materials
  const supKey = supKeyOf(s.supplements)
  const isStale = useCallback((fp?: string) => !!fp && (!s.materials || fp !== s.materials.fingerprint || inputsDirty), [s.materials, inputsDirty])

  const bundle = () => {
    const cur = sRef.current
    return { ...cur.materials!, supplements: cur.supplements, user_stage: cur.inputs.userStage, job_goal: cur.inputs.jobGoal }
  }

  /* ---------------- materials */
  const prepare = useCallback(async () => {
    if (!await guardResumeNavigation()) return false
    if (!await ensureProfile()) return false
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
      post<Materials>('/api/materials/prepare', { resume_text: resumeText, jd_text: jdText, job_title: jobTitle, lang: cur.lang, user_stage: cur.inputs.userStage, job_goal: cur.inputs.jobGoal, resume_format: cur.inputs.resumeFile ? "pdf" : "text" }),
    )
    if (!out) return false
    // Results tied to an older fingerprint are kept but shown as stale until regenerated.
    // Supplements are student-provided facts and stay valid across re-analysis.
    patch((c) => ({
      materials: out,
      inputsKey: keyOf(cur.inputs),
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
    if (!await guardResumeNavigation()) return
    if (!await ensureProfile()) return
    const cur = sRef.current
    if (!cur.inputs.resumeText.trim()) { setError('resume', 'RESUME_EMPTY'); return }
    if (!cur.inputs.jdText.trim()) { setError('resume', 'JD_EMPTY'); return }
    const result = await run('resume', async () => {
      const materials = !cur.materials || cur.materials.pipeline_version !== "m3-jd-sentences-v1" || keyOf(cur.inputs) !== cur.inputsKey
        ? await post<Materials>('/api/materials/prepare', { resume_text: cur.inputs.resumeText, jd_text: cur.inputs.jdText, job_title: cur.inputs.jobTitle, lang: cur.lang, user_stage: cur.inputs.userStage, job_goal: cur.inputs.jobGoal, resume_format: cur.inputs.resumeFile ? "pdf" : "text" })
        : cur.materials
      const out = await post<OptimizeResult>('/api/resume/optimize', { materials: { ...materials, supplements: cur.supplements, user_stage: cur.inputs.userStage, job_goal: cur.inputs.jobGoal }, lang: cur.lang, user_stage: cur.inputs.userStage, job_goal: cur.inputs.jobGoal, resume_format: cur.inputs.resumeFile ? "pdf" : "text" })
      return { materials, out }
    })
    if (!result) return
    patch({ materials: result.materials, inputsKey: keyOf(cur.inputs),
      resume: { data: result.out, fingerprint: result.materials.fingerprint, supKey: supKeyOf(cur.supplements), decisions: {},
        source: { text: cur.inputs.resumeText, lines: result.materials.resume_lines } } })
  }, [run, patch])

  const setDecision = useCallback((id: string, d: Decision) => {
    patch((c) => {
      if (!c.resume || !c.resume.data.items.some(it => it.id === id)) return {}
      if (d.state !== 'pending' && (keyOf(c.inputs) !== c.inputsKey || c.resume.fingerprint !== c.materials?.fingerprint || running.current.has('resume'))) return {}
      return { resume: { ...c.resume, decisions: { ...c.resume.decisions, [id]: d } } }
    })
  }, [patch])

  /* ---------------- match */
  const generateMatch = useCallback(async () => {
    if (!await ensureProfile()) return
    const cur = sRef.current
    if (!cur.inputs.resumeText.trim()) { setError('match', 'RESUME_EMPTY'); return }
    if (!cur.inputs.jdText.trim()) { setError('match', 'JD_EMPTY'); return }
    const result = await run('match', async () => {
      const materials = !cur.materials || cur.materials.pipeline_version !== "m3-jd-sentences-v1" || keyOf(cur.inputs) !== cur.inputsKey
        ? await post<Materials>('/api/materials/prepare', { resume_text: cur.inputs.resumeText, jd_text: cur.inputs.jdText, job_title: cur.inputs.jobTitle, lang: cur.lang, user_stage: cur.inputs.userStage, job_goal: cur.inputs.jobGoal, resume_format: cur.inputs.resumeFile ? "pdf" : "text" })
        : cur.materials
      const out = await post<MatchResult>('/api/match', { materials: { ...materials, supplements: cur.supplements, user_stage: cur.inputs.userStage, job_goal: cur.inputs.jobGoal }, lang: cur.lang, user_stage: cur.inputs.userStage, job_goal: cur.inputs.jobGoal, resume_format: cur.inputs.resumeFile ? "pdf" : "text" })
      return { materials, out }
    })
    if (!result) return
    patch({ materials: result.materials, inputsKey: keyOf(cur.inputs), match: { data: result.out, fingerprint: result.materials.fingerprint, supKey: supKeyOf(cur.supplements) } })
  }, [run, patch])

  /* ---------------- interview */
  const askQuestion = useCallback(async (target?: string) => {
    if (!await ensureProfile()) return
    const cur = sRef.current
    if (!cur.materials) return
    const asked = cur.interview.fingerprint === cur.materials.fingerprint
      ? cur.interview.turns.slice(-8).map(turn => {
          const last = turn.attempts[turn.attempts.length - 1]
          return { question: turn.question.question, requirement_id: turn.question.requirement_id,
            is_follow_up: !!turn.question.is_follow_up, answer: last?.answer.slice(0, 600), feedback: last?.feedback?.action.slice(0, 240) }
        })
      : []
    const last = cur.interview.turns[cur.interview.turns.length - 1]
    const cached = last?.attempts[last.attempts.length - 1]?.feedback?.next_question
    if (cur.interview.turns.filter(t => !t.question.is_follow_up).length >= 2 && cur.interview.fingerprint === cur.materials.fingerprint) {
      setError('question', 'INTERVIEW_COMPLETE'); return
    }
    const q = cached && cur.interview.fingerprint === cur.materials.fingerprint ? cached : await run('question', () =>
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
    if (!await ensureProfile()) return
    const cur = sRef.current
    const turn = cur.interview.turns[cur.interview.turns.length - 1]
    if (!cur.materials || !turn) return
    if (!answer.trim()) {
      setError('feedback', 'ANSWER_EMPTY')
      return
    }
    const history = turn.attempts.filter((a) => a.feedback).map((a) => ({ question: turn.question.question, answer: a.answer }))
    const fb = await run('feedback', () =>
      post<Feedback>('/api/interview/feedback', { materials: bundle(), lang: cur.lang, question: turn.question, answer, history, turns: cur.interview.turns.slice(0, -1).map(t => ({ question: t.question.question, answer: t.attempts[t.attempts.length - 1]?.answer || "" })) }),
    )
    if (!fb) return
    patch((c) => {
      const turns = [...c.interview.turns]
      const last = turns[turns.length - 1]
      turns[turns.length - 1] = { ...last, attempts: [...last.attempts, { answer, feedback: fb } as Attempt] }
      const summary = fb.session_summary ? { strengths: [], priorities: [], next_session: fb.session_summary, lang: c.lang, guidance: fb.guidance } : null
      return { interview: { ...c.interview, turns, ...(summary ? { status: 'ended' as const, summary } : {}) } }
    })
  }, [run, patch, setError])

  const takeFollowUp = useCallback(() => {
    patch((c) => {
      const last = c.interview.turns[c.interview.turns.length - 1]
      const fb = last?.attempts[last.attempts.length - 1]?.feedback
      if (!fb?.follow_up.needed || last.question.is_follow_up) return {}
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
    if (!await ensureProfile()) return
    const turns = summaryTurns()
    if (!turns.length) return
    const out = await run('summary', () => post<Summary>('/api/interview/summary', { lang: sRef.current.lang, turns, materials: bundle() }))
    if (out) patch((c) => ({ interview: { ...c.interview, summary: out } }))
  }, [run, patch])

  const endInterview = useCallback(async () => {
    if (!await ensureProfile()) return
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
    project, projects, switching, changeProject, saving, saveFailed,resumeDirty,setResumeDirty,renameProject,deleteProject,reloadProjects:reload,pendingProject,
    saveFinalResume: async (text, baseText) => {
      if (!text.trim()) throw Error('Empty resume')
      // Commit to the existing revision-checked write queue before reporting success.
      flushSync(() => patch(() => ({
        finalResume: { text, baseText, savedAt: new Date().toISOString(), version: (confirmedResume.current.current?.version || 0) + 1 },
        finalResumeHistory: [...confirmedResume.current.history, ...(confirmedResume.current.current ? [confirmedResume.current.current] : [])].slice(-3),
      })))
      await pendingSave.current
    },
    flushSave: async () => { await pendingSave.current },
    retrySave: async () => {
      setSaving(true)
      const write = pendingSave.current.catch(() => {}).then(async () => {
        const state = sRef.current
        revision.current = await saveProject({ id: project.id, name: projectName.current, revision: revision.current, state })
        confirmedResume.current={current:state.finalResume,history:state.finalResumeHistory || []}
      })
      pendingSave.current = write
      try { await write; setSaveFailed(false) } catch { setSaveFailed(true) } finally { setSaving(false) }
    },
    setDraft: (id, value) => patch(c => ({ drafts: { ...c.drafts, [id]: value } })),
    s, t, busy, errors, llm, kb, materialsOutdated, inputsDirty, ready, isStale, supKey,
    setLang: (l) => { rememberLanguage(l); patch(c => ({ lang: l, inputs: { ...c.inputs, languageConfirmed: true } })) },
    enter: () => patch({ entered: true }),
    leave: async () => { if (await guardResumeNavigation()) publicHome() },
    setFeature: async (f) => {if (f !== sRef.current.feature && !await guardResumeNavigation()) return;changeFeature(f);patch({feature:f})},
    setMaterialsOpen: (v) => patch({ materialsOpen: v }),
    setInputs: (p) => patch((c) => ({ inputs: { ...c.inputs, ...p } })),
    clearError, setError, run, prepare, addSupplement, removeSupplement,
    configureProfile: () => ensureProfile(true),
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
