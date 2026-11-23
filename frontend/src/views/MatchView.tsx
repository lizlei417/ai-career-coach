import Discovery from '../explore/Discovery'
import { Check, Info, Plus, RefreshCw } from 'lucide-react'
import { useState } from 'react'
import { useApp } from '../lib/store'
import type { TKey } from '../lib/i18n'
import type { MatchItem, Requirement } from '../lib/types'
import { Button, ErrorNote, GuidancePanel, NeedMaterials, PageHeader, ResultBanners, SourceId, Tag, WorkingState } from '../components/ui'

export function StatusMark({ status, size = 12 }: { status: MatchItem['status']; size?: number }) {
  const c = status === 'direct' ? '#2F6449' : status === 'partial' ? '#A3742A' : '#8A93A3'
  return (
    <svg width={size} height={size} viewBox="0 0 12 12" aria-hidden className="shrink-0">
      {status === 'direct' && <circle cx="6" cy="6" r="5" fill={c} />}
      {status === 'partial' && (
        <>
          <circle cx="6" cy="6" r="4.5" fill="none" stroke={c} strokeWidth="1.2" />
          <path d="M6 1.5a4.5 4.5 0 0 1 0 9Z" fill={c} />
        </>
      )}
      {(status === 'none' || status === 'unassessed') && <circle cx="6" cy="6" r="4.5" fill="none" stroke={c} strokeWidth="1.2" strokeDasharray={status === 'unassessed' ? '2 2' : undefined} />}
    </svg>
  )
}

export default function MatchView() {
  const { t, s, ready, busy, errors, generateMatch, clearError, isStale } = useApp()
  if (!ready) return <div className="space-y-5"><PageHeader title={t('jm.title')} /><Discovery/><ErrorNote code={errors.match} onClose={()=>clearError('match')}/><NeedMaterials /></div>
  const r = s.match
  const reqs = s.materials!.requirements
  const reqMap = new Map(reqs.map((q) => [q.id, q]))
  const stale = r ? isStale(r.fingerprint) : false
  const cats = ['required', 'preferred', 'responsibility', 'unspecified'] as const
  const categoryOf = (i: MatchItem) => i.priority_code || reqMap.get(i.requirement_id)?.category

  return (
    <div className="space-y-5 animate-fade">
      <PageHeader
        title={t('jm.title')}
        meta={s.materials?.job_title}
        actions={r ? (
          <Button variant="secondary" size="sm" loading={busy.match} onClick={generateMatch} icon={<RefreshCw className="h-3.5 w-3.5" />}>
            {t('common.regenerate')}
          </Button>
        ) : null}
      />
      <Discovery/>
      <ErrorNote code={errors.match} onRetry={generateMatch} onClose={() => clearError('match')} />

      {!r && !busy.match && (
        <div className="flex items-center justify-between rounded-lg border border-paper-200 bg-white px-5 py-4">
          <div className="text-[13.5px] text-ink-600">{t('mat.lines', { r: s.materials!.resume_lines.filter((l) => !l.heading).length, q: reqs.length })}</div>
          <Button variant="primary" onClick={generateMatch}>{t('jm.generate')}</Button>
        </div>
      )}
      {busy.match && !r && <WorkingState label={t('jm.running')} rows={4} />}

      {r && (
        <>
          <ResultBanners fingerprint={r.fingerprint} supKey={r.supKey} lang={r.data.lang} onRegenerate={generateMatch} loading={busy.match} />

          {/* ledger */}
          <div className="grid grid-cols-[1.4fr_1fr] gap-5">
            <div className="rounded-lg border border-paper-200 bg-white">
              <table className="w-full text-[13px]">
                <thead>
                  <tr className="border-b border-paper-200 text-[11.5px] text-ink-500">
                    <th className="px-4 py-2.5 text-left font-medium" />
                    {(['direct', 'partial', 'none'] as const).map((st) => (
                      <th key={st} className="px-3 py-2.5 text-right font-medium">
                        <span className="inline-flex items-center gap-1.5"><StatusMark status={st} size={10} />{t(`jm.status.${st}` as TKey)}</span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {cats.map((c) => {
                    const list = r.data.items.filter((i) => categoryOf(i) === c)
                    if (!list.length) return null
                    const n = (st: string) => list.filter((i) => i.status === st).length
                    return (
                      <tr key={c} className="border-b border-paper-100 last:border-b-0">
                        <td className="px-4 py-2.5 text-ink-700">{t(`common.req.${c}` as TKey)} <span className="text-ink-500">· {list.length}</span></td>
                        {(['direct', 'partial', 'none'] as const).map((st) => (
                          <td key={st} className={`px-3 py-2.5 text-right font-serif text-[17px] tabular-nums ${n(st) ? 'text-ink-900' : 'text-paper-300'}`}>{n(st)}</td>
                        ))}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
              {r.data.overview && <p className="border-t border-paper-200 px-4 py-2.5 text-[12.5px] leading-relaxed text-ink-600">{r.data.overview}</p>}
            </div>
            <div className="rounded-lg border border-paper-200 bg-white px-4 py-3">
              <div className="mb-2 text-[11.5px] font-semibold uppercase tracking-[0.08em] text-ink-500">{t('jm.priority')}</div>
              {r.data.priority_order.length ? (
                <ol className="space-y-1.5">
                  {r.data.priority_order.map((id, i) => (
                    <li key={id}>
                      <a href={`#m-${id}`} className="flex gap-2.5 rounded px-1 py-0.5 text-[13px] leading-snug text-ink-800 hover:bg-paper-50">
                        <span className="font-serif text-[14px] text-accent-500">{i + 1}</span>
                        <span className="line-clamp-2">{reqMap.get(id)?.text}</span>
                      </a>
                    </li>
                  ))}
                </ol>
              ) : <div className="text-[13px] text-ink-500">{t('common.none')}</div>}
            </div>
          </div>

          <div className="flex items-start gap-2 text-[12.5px] leading-relaxed text-ink-500">
            <Info className="mt-[2px] h-3.5 w-3.5 shrink-0" />
            {t('jm.disclaimer')}
          </div>

          {/* report */}
          <div className="overflow-hidden rounded-lg border border-paper-200 bg-white shadow-soft">
            <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)_minmax(0,1.15fr)] border-b border-paper-200 bg-paper-50 text-[11.5px] font-semibold uppercase tracking-[0.08em] text-ink-500">
              <div className="px-5 py-2.5">{t('jm.colReq')}</div>
              <div className="border-l border-paper-200 px-5 py-2.5">{t('jm.colEvidence')}</div>
              <div className="border-l border-paper-200 px-5 py-2.5">{t('jm.colStatus')} · {t('jm.colNext')}</div>
            </div>
            {cats.map((c) => {
              const list = r.data.items.filter((i) => categoryOf(i) === c)
              if (!list.length) return null
              return (
                <div key={c}>
                  <div className="border-b border-paper-200 bg-paper-50/50 px-5 py-1.5 text-[12px] font-medium text-ink-600">{t(`common.req.${c}` as TKey)}</div>
                  {list.map((it) => <MatchRow key={it.requirement_id} it={it} req={reqMap.get(it.requirement_id)!} prio={r.data.priority_order.indexOf(it.requirement_id)} disabled={stale} />)}
                </div>
              )
            })}
          </div>
          <GuidancePanel g={r.data.guidance} />
        </>
      )}
    </div>
  )
}

function MatchRow({ it, req, prio, disabled }: { it: MatchItem; req: Requirement; prio: number; disabled: boolean }) {
  const { t, addSupplement } = useApp()
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [added, setAdded] = useState(false)
  const tone = it.status === 'direct' ? 'text-ok-600' : it.status === 'partial' ? 'text-warn-600' : 'text-miss-500'
  return (
    <div id={`m-${it.requirement_id}`} className="grid scroll-mt-4 grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)_minmax(0,1.15fr)] border-b border-paper-200 last:border-b-0">
      <div className="px-5 py-4">
        <div className="mb-1 flex items-center gap-2">
          <SourceId id={it.requirement_id} />
          {prio >= 0 && <Tag tone="accent">{t('jm.priority')} {prio + 1}</Tag>}
        </div>
        <div className="text-[14px] leading-relaxed text-ink-900">{req.text}</div>
      </div>
      <div className="border-l border-paper-200 px-5 py-4">
        {it.evidence.length ? (
          <ul className="space-y-2">
            {it.evidence.map((e) => (
              <li key={e.id} className="flex gap-2 border-l-2 border-paper-300 pl-2.5">
                <span className="pt-[3px]"><SourceId id={e.id} /></span>
                <span className="font-serif text-[14px] leading-[1.6] text-ink-700">“{e.text}”</span>
              </li>
            ))}
          </ul>
        ) : (
          <span className="text-[13px] italic text-ink-500">{t('jm.noEvidence')}</span>
        )}
      </div>
      <div className="border-l border-paper-200 px-5 py-4">
        <div className={`mb-1.5 flex items-center gap-2 text-[13px] font-semibold ${tone}`}>
          <StatusMark status={it.status} />
          {t(`jm.status.${it.status}` as TKey)}
        </div>
        {it.rationale && <p className="whitespace-pre-line text-[13px] leading-relaxed text-ink-600">{it.rationale}</p>}
        {it.verification === 'downgraded' && <p className="mt-1 text-[12px] text-warn-600">{t('jm.downgraded')}</p>}
        {it.status !== 'direct' && it.next_step.text && (
          <div className="mt-2.5 rounded-md bg-paper-50 px-3 py-2">
            <div className="mb-0.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-accent-600">{t(`jm.next.${it.next_step.type}` as TKey)}</div>
            <p className="whitespace-pre-line text-[13px] leading-relaxed text-ink-800">{it.next_step.text}</p>
          </div>
        )}
        {it.status !== 'direct' && !disabled && (
          added ? (
            <div className="mt-2 flex items-center gap-1.5 text-[12px] text-ok-600"><Check className="h-3.5 w-3.5" />{t('ro.added')}</div>
          ) : open ? (
            <div className="mt-2 animate-fade">
              <textarea value={text} onChange={(e) => setText(e.target.value)} rows={2} placeholder={t('ro.supplementPlaceholder')} className="field resize-none text-[13px]" autoFocus />
              <div className="mt-1.5 flex gap-1.5">
                <Button size="sm" variant="primary" disabled={!text.trim()} onClick={() => { addSupplement(text, it.requirement_id); setAdded(true) }}>{t('ro.addSupplement')}</Button>
                <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>{t('common.cancel')}</Button>
              </div>
            </div>
          ) : (
            <button onClick={() => setOpen(true)} className="mt-2 inline-flex items-center gap-1 text-[12px] font-medium text-accent-600 hover:text-accent-700">
              <Plus className="h-3.5 w-3.5" />{t('jm.addEvidence')}
            </button>
          )
        )}
      </div>
    </div>
  )
}
