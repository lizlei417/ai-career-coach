import PersonalQuota from '../PersonalQuota'
import {confirmAction,showNotice} from '../ProductDialog'
import { eraseProjects } from '../lib/projects'
import { Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { ApiError, get, post } from '../lib/api'
import { errorKey, LANG_LABEL } from '../lib/i18n'
import { useApp } from '../lib/store'
import type { KBStatus, Lang, LLMPublic } from '../lib/types'
import { Button, ErrorNote, PageHeader, Tag } from '../components/ui'

function Section({ title, lead, children, aside }: { title: string; lead?: string; children: React.ReactNode; aside?: React.ReactNode }) {
  return (
    <section className="grid grid-cols-[240px_minmax(0,1fr)] gap-10 border-b border-paper-200 py-8 last:border-b-0">
      <div>
        <h2 className="text-[14.5px] font-semibold text-ink-900">{title}</h2>
        {lead && <p className="mt-1.5 text-[12.5px] leading-relaxed text-ink-500">{lead}</p>}
        {aside}
      </div>
      <div className="min-w-0">{children}</div>
    </section>
  )
}

export default function SettingsView() {
  const { t, s, setLang, llm, kb, refreshStatus } = useApp()
  return (
    <div className="max-w-[960px] animate-fade">
      <PageHeader title={t('st.title')} />
      <Section title={t('st.language')}>
        <div className="inline-flex rounded-md bg-paper-100 p-0.5">
          {(['zh-CN', 'zh-TW', 'en'] as Lang[]).map((l) => (
            <button key={l} onClick={() => setLang(l)} className={`h-8 rounded px-4 text-[13px] font-medium ${s.lang === l ? 'bg-white text-ink-900 shadow-hair' : 'text-ink-500 hover:text-ink-900'}`}>
              {LANG_LABEL[l]}
            </button>
          ))}
        </div>
      </Section>
      <ModelSection llm={llm} onChange={refreshStatus} />
      <KBSection kb={kb} />
      <PromptSection />
      <PrivacySection />
    </div>
  )
}

function ModelSection({ llm, onChange }: { llm: LLMPublic | null; onChange: () => void }) {
  const { t } = useApp()
  const [err, setErr] = useState<string>()
  const [testing, setTesting] = useState(false)
  async function test() {
    setTesting(true)
    setErr(undefined)
    try { await post('/api/settings/test', {}) }
    catch (e) { setErr(e instanceof ApiError ? e.code : 'unknown') }
    finally { await onChange(); setTesting(false) }
  }
  return <Section title={t('st.model')} lead="DeepSeek · DEEPSEEK_API_KEY">
    <p>{llm?.model} · {llm === null ? t('side.statusUnknown') : llm.configured ? t(llm.connection === 'verified' ? 'ds.verified' : llm.connection === 'failed' ? (llm.last_error === 'LLM_AUTH' ? 'ds.authFailed' : 'ds.unavailable') : 'ds.pending') : t('st.status.off')}</p>
    <Button disabled={llm?.configured === false || testing} onClick={test}>{t('st.test')}</Button>
    <ErrorNote code={err} onClose={() => setErr(undefined)} />
  </Section>
}

function KBSection({ kb }: { kb: KBStatus | null }) {
  const { t } = useApp()
  const [q, setQ] = useState('')
  const [hits, setHits] = useState<{chunk_id:string;page_title:string;source_url:string;text:string}[] | null>(null)
  const [err, setErr] = useState<string>()
  const [busy, setBusy] = useState(false)
  async function search() {
    if (!q.trim() || busy) return
    setBusy(true);setErr(undefined)
    try { const r = await post<{results: NonNullable<typeof hits>}>('/api/kb/search', { query: q, k: 4 }); setHits(r.results) }
    catch (e) { setErr(e instanceof ApiError ? e.code : 'unknown') }
    finally { setBusy(false) }
  }
  return <Section title={t('st.kb')} lead={t('st.kbFixed')}>
    <p className="mb-3 text-sm">{kb?.version} · {kb === null ? t('side.statusUnknown') : kb.connected ? t('side.connected', {n: kb.files.length}) : t(kb?.error ? 'side.kbError' : 'side.notConnected')}</p>
    <ul className="mb-4 divide-y divide-paper-200 rounded-md border border-paper-200 bg-white">{kb?.files.map(f =>
      <li key={f.name} className="px-3 py-2 text-[13px]">{f.name} · {t('st.kbChunks', {n:f.chunks})}</li>)}</ul>
    <div className="flex gap-2">
      <input aria-label={t('st.kbSearch')} className="field h-9 flex-1" value={q} onChange={e => setQ(e.target.value)} onKeyDown={e => e.key === 'Enter' && search()} />
      <Button variant="secondary" loading={busy} onClick={search} icon={<Search className="h-4 w-4" />}>{t('st.kbSearch')}</Button>
    </div>
    <ErrorNote code={err} onClose={() => setErr(undefined)} />
    {hits?.length === 0 && <p>{t('st.kbNoHit')}</p>}
    {hits?.map(h => <div key={h.chunk_id} className="mt-3 rounded-md border border-paper-200 p-3 text-[12.5px]">
      <a className="text-accent-600 underline" href={h.source_url} target="_blank" rel="noopener noreferrer">{h.chunk_id} · {h.page_title}</a><p>{h.text}</p>
    </div>)}
  </Section>
}

function PromptSection() {
  const { t } = useApp()
  const [list, setList] = useState<{ name: string; custom: boolean }[]>([])
  const [err, setErr] = useState<string>()
  useEffect(() => {
    get<{ prompts: { name: string; custom: boolean }[] }>('/api/health').then((h) => setList(h.prompts)).catch((e) => setErr(e.code))
  }, [])
  return (
    <Section title={t('st.prompts')} lead={t('st.promptsLead')}>
      {err && <p className="text-[13px] text-ink-500">{t(errorKey(err))}</p>}
      <ul className="grid grid-cols-2 gap-x-6">
        {list.map((p) => (
          <li key={p.name} className="flex items-center justify-between border-b border-paper-200 py-2 text-[13px]">
            <span className="font-mono text-[12.5px] text-ink-700">{p.name}.md</span>
            <Tag tone={p.custom ? 'accent' : 'plain'}>{p.custom ? t('st.promptCustom') : t('st.promptDefault')}</Tag>
          </li>
        ))}
      </ul>
    </Section>
  )
}

function PrivacySection(){
  const {s,busy,saving,reloadProjects}=useApp()
  const text=s.lang==='en'
    ? ['Delete my data','Delete all your V3 projects, PDFs, résumé text, job descriptions, analyses and interview records?','Permanently delete these data now?','Deletion incomplete. Retry.','Deleted projects / PDFs']
    : s.lang==='zh-TW'
    ? ['清除我的資料','刪除你在 V3 的全部專案、PDF、履歷、職位描述、分析與面試記錄？','再次確認永久刪除？','未完成刪除，請重試。','已刪除專案 / PDF']
    : ['清除我的数据','删除你在 V3 的全部项目、PDF、简历文本、JD、分析结果与面试记录？','再次确认永久删除这些数据？','未完成删除，请重试。','已删除项目 / PDF']
  const [working,setWorking]=useState(false),[failed,setFailed]=useState(false)
  return <><PersonalQuota lang={s.lang}/>
    <Section title={text[0]}><Button variant="danger" disabled={working||saving||Object.values(busy).some(Boolean)} onClick={async()=>{
      if(!await confirmAction(text[1])||!await confirmAction(text[2]))return
      setWorking(true);setFailed(false)
      try{const r=await eraseProjects();await showNotice(text[4]+' · '+r.deletedProjects+' / '+r.deletedDocuments);await reloadProjects()}
      catch{setFailed(true);setWorking(false)}
    }}>{text[0]}</Button>{failed&&<p role="alert">{text[3]}</p>}</Section></>
}
