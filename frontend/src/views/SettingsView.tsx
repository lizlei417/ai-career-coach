import { eraseProjects } from '../lib/projects'
import { cloudJson } from '../cloud'
import { FileUp, Search, Trash2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { ApiError, del, get, post, upload } from '../lib/api'
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
      <KBSection kb={kb} onChange={refreshStatus} />
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
    <p>{llm?.model} · {llm?.configured ? t(llm.connection === 'verified' ? 'ds.verified' : llm.connection === 'failed' ? 'ds.failed' : 'ds.pending') : t('st.status.off')}</p>
    <Button disabled={!llm?.configured || testing} onClick={test}>{t('st.test')}</Button>
    <ErrorNote code={err} onClose={() => setErr(undefined)} />
  </Section>
}

function KBSection({ kb, onChange }: { kb: KBStatus | null; onChange: () => void }) {
  const { t } = useApp()
  const ref = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string>()
  const [q, setQ] = useState('')
  const [hits, setHits] = useState<{ id: string; source: string; section: string; text: string }[] | null>(null)

  const onFiles = async (files: FileList | null) => {
    if (!files?.length) return
    setBusy(true); setErr(undefined)
    try {
      for (const f of Array.from(files)) await upload('/api/kb/upload', f)
    } catch (e) {
      setErr(e instanceof ApiError ? e.code : 'unknown')
    }
    setBusy(false)
    onChange()
  }
  const search = async () => {
    if (!q.trim()) return
    try {
      const r = await post<{ results: any[] }>('/api/kb/search', { query: q, k: 4 })
      setHits(r.results)
    } catch (e) {
      setErr(e instanceof ApiError ? e.code : 'unknown')
    }
  }

  return (
    <Section title={t('st.kb')} lead={t('st.kbLead')}>
      {kb?.connected ? (
        <ul className="mb-4 divide-y divide-paper-200 rounded-md border border-paper-200 bg-white">
          {kb.files.map((f) => (
            <li key={f.name} className="flex items-center gap-3 px-3.5 py-2.5 text-[13px]">
              <span className="flex-1 truncate text-ink-800">{f.name}</span>
              <span className="text-[12px] text-ink-500">{t('st.kbChunks', { n: f.chunks })}</span>
              <button className="rounded p-1 text-ink-500 hover:bg-paper-100 hover:text-[#9B3B3B]" onClick={async () => { await del(`/api/kb/${encodeURIComponent(f.name)}`).catch(() => null); onChange() }}>
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mb-4 rounded-md border border-dashed border-paper-300 px-3.5 py-3 text-[13px] text-ink-500">{t('st.kbNone')}</p>
      )}
      <Button variant="secondary" loading={busy} onClick={() => ref.current?.click()} icon={<FileUp className="h-4 w-4" />}>{t('st.kbUpload')}</Button>
      <input ref={ref} type="file" multiple accept=".md,.txt,.pdf" hidden onChange={(e) => { onFiles(e.target.files); e.target.value = '' }} />
      {err && <div className="mt-3"><ErrorNote code={err} onClose={() => setErr(undefined)} /></div>}

      {kb?.connected && (
        <div className="mt-6">
          <div className="field-label mb-1.5">{t('st.kbSearch')}</div>
          <div className="flex gap-2">
            <input className="field h-9 flex-1" value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && search()} placeholder={t('st.kbSearchPlaceholder')} />
            <Button variant="secondary" onClick={search} icon={<Search className="h-4 w-4" />}>{t('st.kbSearch')}</Button>
          </div>
          {hits && (
            <ul className="mt-3 space-y-2">
              {hits.length === 0 && <li className="text-[13px] text-ink-500">{t('st.kbNoHit')}</li>}
              {hits.map((h) => (
                <li key={h.id} className="rounded-md border border-paper-200 bg-white px-3.5 py-2.5 text-[12.5px]">
                  <div className="mb-1 font-medium text-ink-800">{h.source}{h.section && <span className="font-normal text-ink-500"> › {h.section}</span>}</div>
                  <p className="line-clamp-3 leading-relaxed text-ink-600">{h.text}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Section>
  )
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
  const {s,busy,saving}=useApp()
  const text=s.lang==='en'
    ? ['Delete my data','Delete all your V2 projects, PDFs, résumé text, job descriptions, analyses and interview records?','Permanently delete these data now?','Deletion incomplete. Retry.','Deleted projects / PDFs','Daily AI calls remaining','Site remaining','Billing paused']
    : s.lang==='zh-TW'
    ? ['清除我的資料','刪除你在 V2 的全部專案、PDF、履歷、職位描述、分析與面試記錄？','再次確認永久刪除？','未完成刪除，請重試。','已刪除專案 / PDF','今日剩餘 AI 次數','全站剩餘','付費請求已暫停']
    : ['清除我的数据','删除你在 V2 的全部项目、PDF、简历文本、JD、分析结果与面试记录？','再次确认永久删除这些数据？','未完成删除，请重试。','已删除项目 / PDF','今日剩余 AI 次数','全站剩余','付费请求已暂停']
  const [q,setQ]=useState<{remaining:number;limit:number;siteRemaining:number;blocked:boolean}>()
  const [working,setWorking]=useState(false),[failed,setFailed]=useState(false)
  useEffect(()=>{
    let active=true
    const update=()=>{cloudJson('/api/quota').then(v=>{if(active)setQ(v)}).catch(()=>{if(active)setQ(undefined)})}
    update();window.addEventListener('quota-update',update)
    return ()=>{active=false;window.removeEventListener('quota-update',update)}
  },[])
  return <><Section title={text[5]}><p>{q? q.remaining+' / '+q.limit+' · '+text[6]+' '+q.siteRemaining:'—'} {q?.blocked&&text[7]}</p></Section>
    <Section title={text[0]}><Button variant="danger" disabled={working||saving||Object.values(busy).some(Boolean)} onClick={async()=>{
      if(!confirm(text[1])||!confirm(text[2]))return
      setWorking(true);setFailed(false)
      try{const r=await eraseProjects();alert(text[4]+' · '+r.deletedProjects+' / '+r.deletedDocuments);location.reload()}
      catch{setFailed(true);setWorking(false)}
    }}>{text[0]}</Button>{failed&&<p role="alert">{text[3]}</p>}</Section></>
}
