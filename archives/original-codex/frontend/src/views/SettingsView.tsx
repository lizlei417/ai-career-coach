import { Check, FileUp, Search, Trash2 } from 'lucide-react'
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
  const { t, s, setLang, llm, kb, refreshStatus, clearAll } = useApp()
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
      <Section title={t('st.local')} lead={t('st.localLead')}>
        <Button variant="danger" icon={<Trash2 className="h-4 w-4" />} onClick={() => { if (confirm(t('st.clearConfirm'))) clearAll() }}>
          {t('st.clearLocal')}
        </Button>
      </Section>
    </div>
  )
}

function ModelSection({ llm, onChange }: { llm: LLMPublic | null; onChange: () => void }) {
  const { t } = useApp()
  const [provider, setProvider] = useState<'openai' | 'anthropic'>('openai')
  const [model, setModel] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [key, setKey] = useState('')
  const [timeout, setTimeoutV] = useState(90)
  const [busy, setBusy] = useState<'' | 'save' | 'test'>('')
  const [err, setErr] = useState<string>()
  const [ok, setOk] = useState<'' | 'saved' | 'tested'>('')

  useEffect(() => {
    if (!llm) return
    setProvider(llm.provider)
    setModel(llm.model)
    setBaseUrl(llm.base_url)
    setTimeoutV(llm.timeout)
  }, [llm])

  const allow = llm?.allow_runtime_config !== false
  const act = async (kind: 'save' | 'test') => {
    setBusy(kind); setErr(undefined); setOk('')
    try {
      if (kind === 'save' || key) {
        await post('/api/settings', { provider, model, base_url: baseUrl, api_key: key, timeout })
        setKey('')
      }
      if (kind === 'test') await post('/api/settings/test', {})
      setOk(kind === 'save' ? 'saved' : 'tested')
      onChange()
    } catch (e) {
      setErr(e instanceof ApiError ? e.code : 'unknown')
      onChange()
    } finally {
      setBusy('')
    }
  }

  return (
    <Section
      title={t('st.model')}
      lead={t('st.modelLead')}
      aside={
        <div className={`mt-3 inline-flex items-center gap-1.5 text-[12px] ${llm?.configured ? 'text-ok-600' : 'text-warn-600'}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${llm?.configured ? 'bg-ok-500' : 'bg-warn-500'}`} />
          {llm?.configured ? t('st.status.on') : t('st.status.off')}
        </div>
      }
    >
      {!allow && <p className="mb-4 text-[13px] text-warn-600">{t('st.runtimeDisabled')}</p>}
      <fieldset disabled={!allow} className="grid grid-cols-2 gap-x-5 gap-y-4">
        <label className="col-span-2">
          <span className="field-label mb-1.5 block">{t('st.provider')}</span>
          <div className="inline-flex rounded-md bg-paper-100 p-0.5">
            {(['openai', 'anthropic'] as const).map((p) => (
              <button type="button" key={p} onClick={() => setProvider(p)} className={`h-8 rounded px-4 text-[13px] font-medium ${provider === p ? 'bg-white text-ink-900 shadow-hair' : 'text-ink-500 hover:text-ink-900'}`}>
                {t(`st.provider.${p}`)}
              </button>
            ))}
          </div>
        </label>
        <label>
          <span className="field-label mb-1.5 block">{t('st.modelName')}</span>
          <input className="field h-9 font-mono text-[13px]" value={model} onChange={(e) => setModel(e.target.value)} placeholder={provider === 'anthropic' ? 'claude-sonnet-4-5' : 'gpt-4o-mini'} />
        </label>
        <label>
          <span className="field-label mb-1.5 block">{t('st.baseUrl')}</span>
          <input className="field h-9 font-mono text-[13px]" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder={t('st.baseUrlHint')} />
        </label>
        <label>
          <span className="field-label mb-1.5 block">{t('st.apiKey')}</span>
          <input
            className="field h-9 font-mono text-[13px]"
            type="password"
            autoComplete="off"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder={llm?.api_key_masked ? t('st.apiKeyKeep', { mask: llm.api_key_masked }) : 'sk-…'}
          />
        </label>
        <label>
          <span className="field-label mb-1.5 block">{t('st.timeout')}</span>
          <input className="field h-9 w-28 tabular-nums" type="number" min={10} max={300} value={timeout} onChange={(e) => setTimeoutV(Number(e.target.value) || 90)} />
        </label>
      </fieldset>
      <div className="mt-5 flex items-center gap-2">
        <Button variant="primary" disabled={!allow} loading={busy === 'save'} onClick={() => act('save')}>{t('st.saveModel')}</Button>
        <Button variant="secondary" loading={busy === 'test'} onClick={() => act('test')}>{busy === 'test' ? t('st.testing') : t('st.test')}</Button>
        {llm?.api_key_masked && allow && (
          <Button variant="ghost" onClick={async () => { await del('/api/settings/key').catch(() => null); onChange() }}>{t('st.clearKey')}</Button>
        )}
        {ok && <span className="ml-2 inline-flex items-center gap-1 text-[12.5px] text-ok-600"><Check className="h-3.5 w-3.5" />{ok === 'saved' ? t('st.saved') : t('st.testOk')}</span>}
      </div>
      {err && <div className="mt-3"><ErrorNote code={err} onClose={() => setErr(undefined)} /></div>}
    </Section>
  )
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
