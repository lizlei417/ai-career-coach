import { AlertTriangle, Check, CornerDownRight, PenLine, RefreshCw, RotateCcw, ShieldCheck, Undo2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import FinalResume from '../components/FinalResume'
import { confirmAction } from '../ProductDialog'
import { diffTokens, newNumbers } from '../lib/diff'
import { useApp } from '../lib/store'
import type { TKey } from '../lib/i18n'
import type { Decision, MissingItem, OptimizeItem } from '../lib/types'
import { Button, ErrorNote, GuidancePanel, NeedMaterials, PageHeader, ResultBanners, SourceId, Tag, WorkingState } from '../components/ui'

type Filter = 'all' | 'pending' | 'done'

export default function ResumeView() {
  const { t, s, ready, busy, errors, generateResume, clearError, isStale } = useApp()
  const [filter, setFilter] = useState<Filter>('all')
  const r = s.resume
  const stale = r ? isStale(r.fingerprint) : false
  const regenerate = async () => {
    if (r && Object.values(r.decisions).some(d => d.state !== 'pending')) {
      const ok = await confirmAction(s.lang === 'en' ? 'Regenerating replaces these suggestions and review decisions. Continue?' : s.lang === 'zh-TW' ? '重新生成將替換目前建議及審核決定，是否繼續？' : '重新生成将替换当前建议和审核决定，是否继续？')
      if (!ok) return
    }
    await generateResume()
  }

  if (!ready) return <NeedMaterials />

  const items = r?.data.items ?? []
  const decided = items.filter((i) => (r?.decisions[i.id]?.state ?? 'pending') !== 'pending').length
  const shown = items.filter((i) => {
    const st = r?.decisions[i.id]?.state ?? 'pending'
    return filter === 'all' || (filter === 'pending' ? st === 'pending' : st !== 'pending')
  })


  return (
    <div className="space-y-5 animate-fade">
      <PageHeader
        title={t('ro.title')}
        meta={r ? <>{t('ro.count', { n: items.length, m: r.data.missing.length })}{items.length > 0 && <> · {t('ro.progress', { d: decided, n: items.length })}</>}</> : s.materials?.job_title}
        actions={
          r ? (
            <>
              <Button variant="secondary" size="sm" loading={busy.resume} onClick={regenerate} icon={<RefreshCw className="h-3.5 w-3.5" />}>
                {t('common.regenerate')}
              </Button>
            </>
          ) : null
        }
      />

      <ErrorNote code={errors.resume} onRetry={generateResume} onClose={() => clearError('resume')} />

      {!r && !busy.resume && (
        <div className="flex items-center justify-between rounded-lg border border-paper-200 bg-white px-5 py-4">
          <div className="text-[13.5px] text-ink-600">{t('mat.lines', { r: s.materials!.resume_lines.filter((l) => !l.heading).length, q: s.materials!.requirements.length })}</div>
          <Button variant="primary" onClick={generateResume}>{t('ro.generate')}</Button>
        </div>
      )}

      {busy.resume && !r && <WorkingState label={t('ro.running')} rows={3} />}

      {r && (
        <>
          <ResultBanners fingerprint={r.fingerprint} supKey={r.supKey} lang={r.data.lang} onRegenerate={regenerate} loading={busy.resume} />
          <FinalResume />
          {busy.resume && <WorkingState label={t('ro.running')} rows={1} />}

          {items.length > 0 ? (
            <>
              <div className="flex items-center justify-between">
                <div className="inline-flex rounded-md bg-paper-100 p-0.5 text-[12.5px]">
                  {(['all', 'pending', 'done'] as Filter[]).map((f) => (
                    <button key={f} onClick={() => setFilter(f)} className={`h-7 rounded px-3 font-medium transition-colors ${filter === f ? 'bg-white text-ink-900 shadow-hair' : 'text-ink-500 hover:text-ink-900'}`}>
                      {t(`ro.filter.${f}` as TKey)}
                    </button>
                  ))}
                </div>
                {r.data.hidden_count > 0 && <span className="text-[12px] text-ink-500">{t('ro.hidden', { n: r.data.hidden_count })}</span>}
              </div>

              <div className="overflow-hidden rounded-lg border border-paper-200 bg-white shadow-soft">
                <div className="grid grid-cols-2 border-b border-paper-200 bg-paper-50 text-[11.5px] font-semibold uppercase tracking-[0.08em] text-ink-500">
                  <div className="px-5 py-2.5">{t('ro.original')}</div>
                  <div className="border-l border-paper-200 px-5 py-2.5">{t('ro.rewrite')}</div>
                </div>
                {shown.map((it) => (
                  <RewriteRow key={`${r.fingerprint}:${it.id}:${it.rewrite}`} it={it} index={items.indexOf(it) + 1} decision={r.decisions[it.id]} disabled={stale || !!busy.resume} />
                ))}
              </div>
            </>
          ) : (
            <p className="rounded-lg border border-paper-200 bg-white px-5 py-6 text-[13.5px] text-ink-600">{t('ro.noItems')}</p>
          )}

          {r.data.missing.length > 0 && <MissingSection list={r.data.missing} />}
          <GuidancePanel g={r.data.guidance} />
        </>
      )}
    </div>
  )
}

/* ---------------------------------------------------------------- row */

function RewriteRow({ it, index, decision, disabled }: { it: OptimizeItem; index: number; decision?: Decision; disabled: boolean }) {
  const { t, s, setDecision } = useApp()
  const st = decision?.state ?? 'pending'
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(decision?.text ?? it.rewrite)
  useEffect(() => { if (!editing) setDraft(decision?.text ?? it.rewrite) }, [decision?.text, it.rewrite, editing])
  const flagged = it.verification.status === 'needs_review'
  const parts = useMemo(() => diffTokens(it.original, it.rewrite), [it.original, it.rewrite])
  const reqMap = new Map((s.materials?.requirements ?? []).map((q) => [q.id, q]))
  const factMap = new Map<string, string>([
    ...(s.materials?.resume_lines ?? []).map((l) => [l.id, l.text] as [string, string]),
    ...s.supplements.map((x) => [x.id, x.text] as [string, string]),
  ])
  const evidenceText = it.evidence_ids.map((e) => factMap.get(e) ?? '').join(' ')
  const editIssues = editing ? newNumbers(draft, evidenceText) : []
  const unsupported = [...it.verification.unsupported_numbers, ...it.verification.unsupported_terms]

  const shownText = st === 'edited' ? decision?.text ?? it.rewrite : it.rewrite
  const dim = st === 'kept'

  return (
    <div data-testid={`rewrite-${it.id}`} className={`border-b border-paper-200 last:border-b-0 ${st !== 'pending' ? 'bg-paper-50/60' : ''}`}>
      <div className="grid grid-cols-2">
        {/* original */}
        <div className="px-5 pb-4 pt-4">
          <div className="mb-2 flex items-center gap-2">
            <span className="font-mono text-[11px] text-ink-500">{String(index).padStart(2, '0')}</span>
            <SourceId id={it.source_id} />
            {it.section && <span className="truncate text-[11.5px] text-ink-500">· {it.section}</span>}
          </div>
          <p className={`font-serif text-[15px] leading-[1.7] ${st === 'kept' ? 'text-ink-900' : 'text-ink-600'}`}>{it.original}</p>
        </div>
        {/* rewrite */}
        <div className="border-l border-paper-200 px-5 pb-4 pt-4">
          <div className="mb-2 flex items-center gap-2">
            {flagged ? (
              <Tag tone="warn"><AlertTriangle className="h-3 w-3" />{t('ro.needsReview')}</Tag>
            ) : (
              <Tag tone="ok"><ShieldCheck className="h-3 w-3" />{t('ro.verified')}</Tag>
            )}
            {st !== 'pending' && (
              <Tag tone={st === 'kept' ? 'plain' : 'dark'}>
                <Check className="h-3 w-3" />
                {t(st === 'adopted' ? 'ro.adopted' : st === 'edited' ? 'ro.edited' : 'ro.kept')}
              </Tag>
            )}
          </div>
          {editing ? (
            <div className="animate-fade">
              <textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={4} className="field font-serif text-[15px] leading-[1.7]" autoFocus />
              <div className="mt-1 text-[11.5px] text-ink-500">{t('ro.editHint')}</div>
              {editIssues.length > 0 && <div className="mt-1.5 text-[12px] text-warn-600">{t('ro.editStillFlagged', { items: editIssues.join('、') })}</div>}
              <div className="mt-2.5 flex gap-2">
                <Button size="sm" variant="primary" disabled={disabled || !draft.trim()} onClick={() => { setDecision(it.id, { state: 'edited', text: draft.trim() }); setEditing(false) }}>
                  {s.lang === 'en' ? 'Save edit' : s.lang === 'zh-TW' ? '儲存修改' : '保存修改'}
                </Button>
                <Button size="sm" variant="ghost" onClick={() => { setEditing(false); setDraft(decision?.text ?? it.rewrite) }}>{t('common.cancel')}</Button>
              </div>
            </div>
          ) : (
            <p className={`font-serif text-[15px] leading-[1.7] ${dim ? 'text-ink-500 line-through decoration-ink-500/30' : 'text-ink-900'}`}>
              {st === 'edited'
                ? shownText
                : parts.filter((p) => p.type !== 'del').map((p, i) =>
                    p.type === 'add' ? <mark key={i} className="rounded-[2px] bg-accent-100/80 px-[1px] text-ink-900">{p.text}</mark> : <span key={i}>{p.text}</span>,
                  )}
            </p>
          )}
        </div>
      </div>

      {/* rationale strip */}
      <div className="grid grid-cols-2 gap-0 border-t border-dashed border-paper-200">
        <div className="space-y-2 px-5 py-3">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="mr-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">{t('ro.evidence')}</span>
            {it.evidence_ids.map((e) => (
              <span key={e} title={factMap.get(e) ?? ''} className={`cursor-help rounded border px-1.5 py-[1px] font-mono text-[10.5px] ${e.startsWith('S') ? 'border-accent-200 bg-accent-50 text-accent-700' : 'border-paper-300 text-ink-600'}`}>
                {e}
              </span>
            ))}
          </div>
          {it.requirement_ids.length > 0 && (
            <div className="flex flex-wrap items-start gap-1.5">
              <span className="mr-1 pt-[2px] text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">{t('ro.addresses')}</span>
              {it.requirement_ids.map((q) => (
                <span key={q} className="text-[12px] text-ink-600">
                  <SourceId id={q} /> {reqMap.get(q)?.text}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="border-l border-paper-200 px-5 py-3">
          <div className="flex gap-2 text-[13px] leading-relaxed text-ink-600">
            <CornerDownRight className="mt-[3px] h-3.5 w-3.5 shrink-0 text-accent-400" />
            <div>
              <span className="font-medium text-ink-800">{t('ro.reason')}　</span>
              {it.reason}
              {it.changes.length > 0 && (
                <span className="ml-2 inline-flex gap-1 align-middle">
                  {it.changes.map((c) => <Tag key={c}>{t(`ro.change.${c}` as TKey) || c}</Tag>)}
                </span>
              )}
            </div>
          </div>
          {flagged && <div className="mt-2 rounded border border-warn-200 bg-warn-50 px-2.5 py-1.5 text-[12px] leading-relaxed text-warn-600">{t('ro.needsReviewDetail', { items: unsupported.join('、') })}</div>}

          {!editing && (
            <div className="mt-3 flex items-center gap-1.5">
              {st === 'pending' ? (
                <>
                  {!flagged && (
                    <Button size="sm" variant="primary" disabled={disabled} onClick={() => setDecision(it.id, { state: 'adopted' })} icon={<Check className="h-3.5 w-3.5" />}>
                      {t('ro.adopt')}
                    </Button>
                  )}
                  <Button size="sm" variant={flagged ? 'primary' : 'secondary'} disabled={disabled} onClick={() => setEditing(true)} icon={<PenLine className="h-3.5 w-3.5" />}>
                    {flagged ? t('ro.editAdopt') : t('ro.edit')}
                  </Button>
                  <Button size="sm" variant="ghost" disabled={disabled} onClick={() => setDecision(it.id, { state: 'kept' })} icon={<RotateCcw className="h-3.5 w-3.5" />}>
                    {t('ro.keep')}
                  </Button>
                </>
              ) : (
                <>
                <Button size="sm" variant="secondary" disabled={disabled} onClick={() => setEditing(true)} icon={<PenLine className="h-3.5 w-3.5" />}>{t('ro.edit')}</Button>
                <Button size="sm" variant="ghost" onClick={() => setDecision(it.id, { state: 'pending' })} icon={<Undo2 className="h-3.5 w-3.5" />}>
                  {t('ro.undo')}
                </Button>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/* ---------------------------------------------------------------- missing evidence */

function MissingSection({ list }: { list: MissingItem[] }) {
  const { t } = useApp()
  return (
    <section className="pt-2">
      <div className="mb-1 font-serif text-[18px] font-medium text-ink-900">{t('ro.missingTitle')}</div>
      <p className="mb-3 max-w-[720px] text-[13px] leading-relaxed text-ink-500">{t('ro.missingLead')}</p>
      <div className="divide-y divide-paper-200 overflow-hidden rounded-lg border border-paper-200 bg-white">
        {list.map((m) => <MissingRow key={m.requirement_id} m={m} />)}
      </div>
    </section>
  )
}

export function MissingRow({ m }: { m: MissingItem }) {
  const { t, s, addSupplement } = useApp()
  const [text, setText] = useState('')
  const [added, setAdded] = useState(false)
  const req = s.materials?.requirements.find((q) => q.id === m.requirement_id)
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] gap-6 px-5 py-4">
      <div>
        <div className="mb-1.5 flex items-center gap-2">
          <SourceId id={m.requirement_id} />
          {req && <Tag>{t(`common.req.${req.category}` as TKey)}</Tag>}
          <Tag tone={m.kind === 'unclear' ? 'warn' : 'miss'}>{t(m.kind === 'unclear' ? 'ro.kind.unclear' : 'ro.kind.absent')}</Tag>
        </div>
        <div className="text-[14px] font-medium leading-relaxed text-ink-900">{req?.text}</div>
        {m.note && <p className="mt-1 text-[13px] leading-relaxed text-ink-600">{m.note}</p>}
      </div>
      <div>
        {m.ask && <p className="mb-2 text-[13px] leading-relaxed text-ink-800">{m.ask}</p>}
        {added ? (
          <div className="flex items-center gap-1.5 text-[12.5px] text-ok-600"><Check className="h-3.5 w-3.5" />{t('ro.added')}</div>
        ) : (
          <div className="flex items-end gap-2">
            <textarea value={text} onChange={(e) => setText(e.target.value)} rows={2} placeholder={t('ro.supplementPlaceholder')} className="field flex-1 resize-none text-[13px]" />
            <Button size="sm" variant="secondary" disabled={!text.trim()} onClick={() => { addSupplement(text, m.requirement_id); setAdded(true) }}>
              {t('ro.addSupplement')}
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
