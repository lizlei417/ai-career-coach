import { ArrowRight, BriefcaseBusiness, FileText, MessagesSquare } from 'lucide-react'
import {useCopy} from '../explore/shared'
import { useState } from 'react'
import { useApp } from '../lib/store'
import { LANG_LABEL, type TKey } from '../lib/i18n'
import type { Feature, Requirement } from '../lib/types'
import { PageHeader, SourceId, Tag } from '../components/ui'

export default function Overview() {
  const { t, s, setFeature, llm, isStale, busy } = useApp()
  const m = s.materials

  const {l}=useCopy()
  const discovery=<div className="explore"><div className="xgrid">{([['explorer','职业测评','Career Explorer'],['match','发现岗位方向','Discover positions'],['reviews','面经复盘','Interview Review']] as const).map(([f,z,e])=><button key={f} onClick={()=>setFeature(f)}>{l(z,e)} →</button>)}</div></div>

  if (!m) {
    const steps = [t('ov.emptyStep1'), t('ov.emptyStep2'), t('ov.emptyStep3')]
    return (
      <div className="mx-auto max-w-[640px] pt-[10vh] animate-rise">
        <h1 className="font-serif text-[30px] font-medium tracking-[-0.01em] text-ink-900">{t('ov.emptyTitle')}</h1>
        {discovery}
        <ol className="mt-8 border-t border-paper-200">
          {steps.map((st, i) => (
            <li key={i} className="flex items-center gap-5 border-b border-paper-200 py-4">
              <span className="font-mono text-[12px] text-accent-500">0{i + 1}</span>
              <span className="text-[15px] text-ink-700">{st}</span>
            </li>
          ))}
        </ol>
        {llm && !llm.configured && (
          <div className="mt-6 flex items-center justify-between rounded-md border border-warn-200 bg-warn-50 px-4 py-3 text-[13px] text-warn-600">
            <span>{t('err.LLM_NOT_CONFIGURED')}</span>
            <button className="font-medium underline-offset-2 hover:underline" onClick={() => setFeature('settings')}>
              {t('common.goSettings')}
            </button>
          </div>
        )}
      </div>
    )
  }

  const status = (fp: string | undefined, loading?: boolean) =>
    loading ? 'loading' : !fp ? 'none' : isStale(fp) ? 'stale' : 'ready'
  const features: { key: Feature; icon: typeof FileText; label: string; st: string; extra?: string }[] = [
    { key: 'resume', icon: FileText, label: t('nav.resume'), st: status(s.resume?.fingerprint, busy.resume) },
    { key: 'match', icon: BriefcaseBusiness, label: t('nav.match'), st: status(s.match?.fingerprint, busy.match) },
    {
      key: 'interview', icon: MessagesSquare, label: t('nav.interview'),
      st: s.interview.turns.length ? status(s.interview.fingerprint) : 'none',
      extra: s.interview.turns.length ? t('ov.interviewTurns', { n: s.interview.turns.length }) : undefined,
    },
  ]
  const groups: Requirement['category'][] = ['responsibility', 'required', 'preferred']
  const facts = m.resume_lines

  return (
    <div className="space-y-8 animate-fade">
      <PageHeader
        title={m.job_title || t('ov.title')}
        meta={t('mat.lines', { r: facts.filter((l) => !l.heading).length, q: m.requirements.length })}
      />

      {discovery}
      {/* features */}
      <section>
        <div className="section-label mb-3">{t('ov.features')}</div>
        <div className="grid grid-cols-3 divide-x divide-paper-200 overflow-hidden rounded-lg border border-paper-200 bg-white">
          {features.map((f) => {
            const Icon = f.icon
            return (
              <button key={f.key} onClick={() => setFeature(f.key)} className="group flex items-center gap-3.5 px-5 py-4 text-left transition-colors hover:bg-paper-50">
                <Icon className="h-[18px] w-[18px] text-ink-600" strokeWidth={1.7} />
                <div className="min-w-0 flex-1">
                  <div className="text-[14px] font-medium text-ink-900">{f.label}</div>
                  <div className="mt-0.5 flex items-center gap-1.5 text-[12px] text-ink-500">
                    <span className={`h-1.5 w-1.5 rounded-full ${f.st === 'ready' ? 'bg-ok-500' : f.st === 'stale' ? 'bg-warn-500' : f.st === 'loading' ? 'bg-accent-400 animate-pulse' : 'bg-paper-300'}`} />
                    {f.extra || t(`ov.status.${f.st}` as TKey)}
                  </div>
                </div>
                <ArrowRight className="h-4 w-4 text-ink-500 opacity-0 transition-all group-hover:translate-x-0.5 group-hover:opacity-100" />
              </button>
            )
          })}
        </div>
      </section>

      {/* shared parse */}
      <section className="grid grid-cols-1 gap-8 2xl:grid-cols-[1.1fr_1fr]">
        <div>
          <div className="mb-3 flex items-baseline justify-between">
            <div className="section-label">{t('ov.requirements')}</div>
            {m.lang !== s.lang && <span className="text-[11.5px] text-ink-500">{t('ov.relang', { lang: LANG_LABEL[m.lang] })}</span>}
          </div>
          <div className="overflow-hidden rounded-lg border border-paper-200 bg-white">
            {groups.map((g) => {
              const list = m.requirements.filter((r) => r.category === g)
              if (!list.length) return null
              return (
                <div key={g} className="border-b border-paper-200 last:border-b-0">
                  <div className="bg-paper-50 px-4 py-2 text-[11.5px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                    {t(`common.req.${g}` as TKey)} · {list.length}
                  </div>
                  <ul>
                    {list.map((r) => <ReqRow key={r.id} r={r} />)}
                  </ul>
                </div>
              )
            })}
          </div>
        </div>
        <div>
          <div className="section-label mb-3">{t('ov.resumeFacts')}</div>
          <div className="scroll-thin max-h-[520px] overflow-y-auto rounded-lg border border-paper-200 bg-white px-4 py-2">
            {facts.map((l) =>
              l.heading ? (
                <div key={l.id} className="pb-1 pt-3 text-[11.5px] font-semibold uppercase tracking-[0.08em] text-ink-500">{l.text}</div>
              ) : (
                <div key={l.id} className="flex gap-3 py-1.5 text-[13px] leading-relaxed text-ink-700">
                  <span className="w-7 shrink-0 pt-[3px]"><SourceId id={l.id} /></span>
                  <span>{l.text}</span>
                </div>
              ),
            )}
          </div>
        </div>
      </section>
    </div>
  )
}

function ReqRow({ r }: { r: Requirement }) {
  const { t, s } = useApp()
  const [open, setOpen] = useState(false)
  const src = s.materials!.jd_lines.filter((l) => r.source_ids.includes(l.id))
  return (
    <li className="border-t border-paper-100 first:border-t-0">
      <button onClick={() => setOpen(!open)} className="flex w-full items-start gap-3 px-4 py-2.5 text-left hover:bg-paper-50">
        <span className="w-7 shrink-0 pt-[3px]"><SourceId id={r.id} /></span>
        <span className="flex-1 text-[13.5px] leading-relaxed text-ink-800">{r.text}</span>
        <Tag>{t(`common.kind.${r.kind}` as TKey)}</Tag>
      </button>
      {open && (
        <div className="mb-2 ml-14 mr-4 border-l-2 border-accent-100 pl-3 text-[12.5px] leading-relaxed text-ink-500 animate-fade">
          <div className="mb-0.5 text-[11px] font-medium uppercase tracking-wide text-ink-500">{t('ov.fromJd')}</div>
          {src.map((l) => <div key={l.id}><SourceId id={l.id} /> {l.text}</div>)}
        </div>
      )}
    </li>
  )
}
