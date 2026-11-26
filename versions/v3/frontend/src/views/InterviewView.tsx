import {confirmAction} from '../ProductDialog'
import { ArrowRight, CircleStop, CornerDownRight, FileText, MessageSquareReply, Play, RotateCcw, Undo2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useApp } from '../lib/store'
import type { TKey } from '../lib/i18n'
import type { Attempt, Feedback, Turn } from '../lib/types'
import { Button, ErrorNote, NeedMaterials, Notice, PageHeader, SourceId, Tag, WorkingState, GuidancePanel } from '../components/ui'

export default function InterviewView() {
  const { t, s, ready, busy, errors, clearError, askQuestion, isStale, resetInterview, endInterview, resumeInterview, loadSummary } = useApp()
  const iv = s.interview
  const [target, setTarget] = useState('')
  const [viewId, setViewId] = useState<string | null>(null)
  const stale = iv.turns.length > 0 && isStale(iv.fingerprint)

  useEffect(() => setViewId(null), [iv.turns.length])

  if (!ready) return <NeedMaterials />
  const reqs = s.materials!.requirements

  /* ---------------- start screen */
  if (iv.status === 'idle' || iv.turns.length === 0) {
    return (
      <div className="space-y-5 animate-fade">
        <PageHeader title={t('iv.title')} meta={s.materials?.job_title} />
        <ErrorNote code={errors.question} onRetry={() => askQuestion(target)} onClose={() => clearError('question')} />
        {busy.question ? (
          <div className="mx-auto max-w-[720px] pt-6"><WorkingState label={t('iv.asking')} rows={1} /></div>
        ) : (
          <div className="mx-auto max-w-[720px] pt-[6vh]">
            <div className="rounded-xl bg-ink-900 px-10 py-10 text-white shadow-lift">
              <div className="mb-3 font-mono text-[11px] uppercase tracking-[0.18em] text-accent-200/70">Interview room</div>
              <h2 className="font-serif text-[28px] font-medium leading-snug">{t('iv.startTitle')}</h2>
              <p className="mt-3 max-w-[520px] text-[14px] leading-relaxed text-white/65">{t('iv.startLead')}</p>
              <div className="mt-8 flex items-end gap-3">
                <label className="flex-1">
                  <span className="mb-1.5 block text-[11.5px] font-medium uppercase tracking-[0.08em] text-white/45">{t('iv.focusLabel')}</span>
                  <select value={target} onChange={(e) => setTarget(e.target.value)} className="h-10 w-full rounded-md border border-white/10 bg-white/[0.06] px-3 text-[13.5px] text-white outline-none focus:border-accent-200/50">
                    <option value="" className="text-ink-900">{t('iv.focusAuto')}</option>
                    {reqs.map((q) => (
                      <option key={q.id} value={q.id} className="text-ink-900">{q.id} · {q.text}</option>
                    ))}
                  </select>
                </label>
                <button onClick={() => askQuestion(target)} className="inline-flex h-10 items-center gap-2 rounded-md bg-white px-5 text-[14px] font-medium text-ink-900 transition-colors hover:bg-accent-50">
                  <Play className="h-3.5 w-3.5" />{t('iv.start')}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }

  const current = iv.turns[iv.turns.length - 1]
  const viewing = viewId ? iv.turns.find((x) => x.id === viewId) ?? current : current
  const isCurrent = viewing.id === current.id
  const answered = iv.turns.filter((x) => x.attempts.length).length

  return (
    <div className="flex h-full flex-col animate-fade">
      <PageHeader
        title={t('iv.title')}
        meta={s.materials?.job_title}
        actions={
          <>
            <Button size="sm" variant="ghost" onClick={async () => { if (await confirmAction(t('iv.resetConfirm'))) resetInterview() }} icon={<RotateCcw className="h-3.5 w-3.5" />}>{t('iv.reset')}</Button>
            {iv.status === 'active' ? (
              <Button size="sm" variant="secondary" disabled={!answered} onClick={endInterview} icon={<CircleStop className="h-3.5 w-3.5" />}>{t('iv.end')}</Button>
            ) : (
              <Button size="sm" variant="secondary" disabled={stale} onClick={resumeInterview} icon={<Undo2 className="h-3.5 w-3.5" />}>{t('iv.continue')}</Button>
            )}
          </>
        }
      />
      {stale && <div className="mt-4"><Notice tone="warn">{t('common.staleResult')}</Notice></div>}

      <div className="mt-5 grid min-h-0 flex-1 grid-cols-[200px_minmax(0,1fr)] gap-6">
        {/* session rail */}
        <aside className="min-w-0">
          <div className="mb-2 text-[11.5px] font-semibold uppercase tracking-[0.08em] text-ink-500">{t('iv.session')}</div>
          <ol className="space-y-0.5">
            {iv.turns.map((turn, i) => {
              const on = viewing.id === turn.id && iv.status !== 'ended'
              const done = turn.attempts.length > 0
              return (
                <li key={turn.id}>
                  <button
                    onClick={() => { setViewId(turn.id); if (iv.status === 'ended') resumeInterview() }}
                    className={`flex w-full items-start gap-2.5 rounded-md px-2.5 py-2 text-left transition-colors ${on ? 'bg-white shadow-hair' : 'hover:bg-paper-100'}`}
                  >
                    <span className={`mt-[1px] flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10.5px] font-semibold ${done ? 'bg-ink-900 text-white' : 'border border-paper-300 text-ink-500'}`}>
                      {turn.question.is_follow_up ? '↳' : i + 1}
                    </span>
                    <span className="min-w-0">
                      <span className="block truncate text-[12.5px] font-medium text-ink-800">{turn.question.focus || t(`iv.type.${turn.question.type}` as TKey)}</span>
                      <span className="block text-[11px] text-ink-500">
                        {turn.question.is_follow_up ? t('iv.followUp') : t(`iv.type.${turn.question.type}` as TKey)}
                        {turn.attempts.length > 1 && ` · ×${turn.attempts.length}`}
                      </span>
                    </span>
                  </button>
                </li>
              )
            })}
          </ol>
          {(iv.status === 'ended' || answered > 0) && (
            <button
              onClick={() => { if (iv.status !== 'ended') endInterview(); else if (!iv.summary) loadSummary() }}
              className={`mt-3 w-full rounded-md px-2.5 py-2 text-left text-[12.5px] font-medium transition-colors ${iv.status === 'ended' ? 'bg-white text-ink-900 shadow-hair' : 'text-accent-600 hover:bg-paper-100'}`}
            >
              {t('iv.viewSummary')}
            </button>
          )}
        </aside>

        {/* stage */}
        <div className="min-w-0 pb-10">
          {iv.status === 'ended' ? (
            <SummaryPanel />
          ) : (
            <TurnStage key={viewing.id} turn={viewing} index={iv.turns.indexOf(viewing) + 1} isCurrent={isCurrent} disabled={stale} />
          )}
        </div>
      </div>
    </div>
  )
}

/* ---------------------------------------------------------------- one question */

function TurnStage({ turn, index, isCurrent, disabled }: { turn: Turn; index: number; isCurrent: boolean; disabled: boolean }) {
  const { t, busy, errors, clearError, submitAnswer, askQuestion, takeFollowUp, endInterview } = useApp()
  const last = turn.attempts[turn.attempts.length - 1]
  const { s, setDraft: saveDraft } = useApp()
  const draft = s.drafts[turn.id] || ''
  const setDraft = (value: string) => saveDraft(turn.id, value)
  const ref = useRef<HTMLTextAreaElement>(null)
  const [answering, setAnswering] = useState(!last || !!draft)
  const q = turn.question

  useEffect(() => {
    if (!last) setAnswering(true)
  }, [last])

  const submit = async () => {
    if (!draft.trim()) return
    await submitAnswer(draft) // draft is cleared only once the attempt is stored (see effect below)
  }

  // when a new attempt arrives, leave answering mode
  const attempts = turn.attempts.length
  const prevAttempts = useRef(attempts)
  useEffect(() => {
    if (attempts > prevAttempts.current) {
      setAnswering(false)
      setDraft('')
    }
    prevAttempts.current = attempts
  }, [attempts])

  return (
    <div className="space-y-5">
      {/* question card */}
      <div className="rounded-xl bg-ink-900 px-8 py-7 text-white shadow-lift animate-rise">
        <div className="mb-4 flex flex-wrap items-center gap-2 text-[12px]">
          <span className="font-mono uppercase tracking-[0.16em] text-accent-200/70">{q.is_follow_up ? t('iv.followUp') : t('iv.question', { n: index })}</span>
          <span className="text-white/25">/</span>
          <span className="text-white/60">{t(`iv.type.${q.type}` as TKey)}</span>
          {q.focus && (<><span className="text-white/25">/</span><span className="text-white/60">{t('iv.assesses')} · {q.focus}</span></>)}
        </div>
        <p className="font-serif text-[21px] leading-[1.55] text-white">{q.question}</p>
        {q.resume_refs.length > 0 && (
          <div className="mt-5 border-t border-white/10 pt-3.5">
            <div className="mb-1.5 flex items-center gap-1.5 text-[11px] uppercase tracking-[0.1em] text-white/40"><FileText className="h-3 w-3" />{t('iv.anchor')}</div>
            {q.resume_refs.map((r) => (
              <div key={r.id} className="text-[12.5px] leading-relaxed text-white/60"><span className="font-mono text-[10.5px] text-white/35">{r.id}</span> {r.text}</div>
            ))}
          </div>
        )}
      </div>

      <GuidancePanel g={q.guidance} />
      {/* earlier attempts */}
      {turn.attempts.map((a, i) => (
        <AttemptBlock key={i} a={a} n={i + 1} total={turn.attempts.length} type={q.type} />
      ))}

      {/* answer box */}
      {isCurrent && answering && (
        <div className="rounded-xl border border-paper-200 bg-white shadow-soft animate-rise">
          <textarea
            ref={ref}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => { if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') submit() }}
            disabled={busy.feedback || disabled}
            placeholder={t('iv.answerPlaceholder')}
            rows={7}
            autoFocus
            className="block w-full resize-none rounded-t-xl bg-transparent px-6 py-5 text-[15px] leading-[1.75] text-ink-900 outline-none placeholder:text-ink-500/70"
          />
          <div className="flex items-center justify-between border-t border-paper-200 px-4 py-2.5">
            <span className="text-[12px] text-ink-500">{q.type === 'behavioral' ? t('iv.starHint') : t('iv.techHint')}</span>
            <div className="flex items-center gap-3">
              <span className="hidden text-[11.5px] text-ink-500 xl:inline">{t('iv.shortcut')}</span>
              {last && <Button size="sm" variant="ghost" onClick={() => setAnswering(false)}>{t('common.cancel')}</Button>}
              <Button size="sm" variant="primary" loading={busy.feedback} disabled={!draft.trim() || disabled} onClick={submit}>
                {busy.feedback ? t('iv.evaluating') : t('iv.submit')}
              </Button>
            </div>
          </div>
        </div>
      )}
      <ErrorNote code={errors.feedback} onRetry={submit} onClose={() => clearError('feedback')} />
      {busy.feedback && <WorkingState label={t('iv.evaluating')} rows={1} />}
      <ErrorNote code={errors.question} onRetry={() => askQuestion()} onClose={() => clearError('question')} />

      <GuidancePanel g={last?.feedback?.guidance} />
      {/* next actions */}
      {isCurrent && !answering && last?.feedback && !disabled && (
        <div className="flex flex-wrap items-center gap-2 border-t border-paper-200 pt-4 animate-fade">
          <Button variant="secondary" onClick={() => setAnswering(true)} icon={<RotateCcw className="h-4 w-4" />}>{t('iv.reanswer')}</Button>
          {last.feedback.follow_up.needed && (
            <Button variant="secondary" onClick={takeFollowUp} icon={<MessageSquareReply className="h-4 w-4" />}>{t('iv.acceptFollowUp')}</Button>
          )}
          {!last.feedback.follow_up.needed && <Button variant="primary" disabled={s.interview.turns.filter(t => !t.question.is_follow_up).length >= 2} loading={busy.question} onClick={() => askQuestion()} icon={<ArrowRight className="h-4 w-4" />}>{t('iv.next')}</Button>}
          <div className="flex-1" />
          <Button variant="ghost" onClick={endInterview} icon={<CircleStop className="h-4 w-4" />}>{t('iv.end')}</Button>
        </div>
      )}
      {busy.question && <WorkingState label={t('iv.asking')} rows={1} />}
    </div>
  )
}

function AttemptBlock({ a, n, total, type }: { a: Attempt; n: number; total: number; type: 'behavioral' | 'technical' }) {
  const { t } = useApp()
  const [open, setOpen] = useState(n === total)
  return (
    <div className="animate-rise">
      <button onClick={() => setOpen(!open)} className="mb-2 flex w-full items-center gap-2 text-left text-[11.5px] font-semibold uppercase tracking-[0.08em] text-ink-500 hover:text-ink-800">
        {total > 1 ? t('iv.attempt', { n }) : t('iv.yourAnswer')}
        <span className="h-px flex-1 bg-paper-200" />
        {!open && <span className="normal-case tracking-normal">…</span>}
      </button>
      {open && (
        <div className="space-y-3">
          <div className="border-l-2 border-paper-300 pl-4 text-[14px] leading-[1.75] text-ink-700 whitespace-pre-wrap">{a.answer}</div>
          {a.feedback && <FeedbackBlock fb={a.feedback} type={type} />}
        </div>
      )}
    </div>
  )
}

function FeedbackBlock({ fb, type }: { fb: Feedback; type: 'behavioral' | 'technical' }) {
  const { t } = useApp()
  const star = fb.structure
  return (
    <div className="overflow-hidden rounded-xl border border-paper-200 bg-white shadow-soft">
      <div className="grid grid-cols-2 divide-x divide-paper-200">
        <div className="px-5 py-4">
          <div className="mb-2.5 flex items-center justify-between">
            <span className="text-[11.5px] font-semibold uppercase tracking-[0.08em] text-ok-600">{t('iv.onTopic')}</span>
            {type === 'behavioral' && star && (
              <span className="flex gap-1">
                {(['situation', 'task', 'action', 'result'] as const).map((k) => (
                  <span key={k} title={t(`iv.star.${k}` as TKey)} className={`flex h-5 min-w-5 items-center justify-center rounded px-1 text-[10.5px] font-semibold ${star[k] ? 'bg-ink-900 text-white' : 'border border-dashed border-paper-300 text-ink-500'}`}>
                    {t(`iv.star.${k}` as TKey).slice(0, 1)}
                  </span>
                ))}
              </span>
            )}
          </div>
          {fb.on_topic.length ? (
            <ul className="space-y-2.5">
              {fb.on_topic.map((o, i) => (
                <li key={i}>
                  <div className="font-serif text-[14px] leading-relaxed text-ink-900">“{o.quote}”</div>
                  <div className="mt-0.5 text-[12.5px] leading-relaxed text-ink-500">{o.why}</div>
                </li>
              ))}
            </ul>
          ) : <p className="text-[13px] text-ink-500">{t('iv.noOnTopic')}</p>}
          {fb.unverified_quotes_removed > 0 && <p className="mt-2 text-[11.5px] text-ink-500">{t('iv.removedQuotes', { n: fb.unverified_quotes_removed })}</p>}
        </div>
        <div className="px-5 py-4">
          <div className="mb-2.5 text-[11.5px] font-semibold uppercase tracking-[0.08em] text-warn-600">{t('iv.missing')}</div>
          <ul className="space-y-1.5">
            {fb.missing.map((m, i) => (
              <li key={i} className="flex gap-2 text-[13.5px] leading-relaxed text-ink-700">
                <span className="mt-[9px] h-1 w-1 shrink-0 rounded-full bg-warn-500" />{m}
              </li>
            ))}
          </ul>
          {type === 'technical' && fb.reasoning_note && (
            <div className="mt-3 border-t border-paper-100 pt-2.5">
              <div className="mb-0.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-500">{t('iv.reasoning')}</div>
              <p className="text-[13px] leading-relaxed text-ink-600">{fb.reasoning_note}</p>
            </div>
          )}
        </div>
      </div>
      {fb.action && (
        <div className="flex gap-3 border-t border-paper-200 bg-accent-50/60 px-5 py-3.5">
          <CornerDownRight className="mt-[3px] h-4 w-4 shrink-0 text-accent-500" />
          <div>
            <div className="text-[11.5px] font-semibold uppercase tracking-[0.08em] text-accent-700">{t('iv.action')}</div>
            <p className="mt-0.5 text-[14px] leading-relaxed text-ink-900">{fb.action}</p>
          </div>
        </div>
      )}
      {fb.follow_up.needed && (
        <div className="border-t border-paper-200 px-5 py-3.5">
          <div className="text-[11.5px] font-semibold uppercase tracking-[0.08em] text-ink-500">{t('iv.followUpTitle')}</div>
          <p className="mt-1 font-serif text-[15px] leading-relaxed text-ink-900">{fb.follow_up.question}</p>
          {fb.follow_up.reason && <p className="mt-0.5 text-[12.5px] text-ink-500">{fb.follow_up.reason}</p>}
        </div>
      )}
    </div>
  )
}

/* ---------------------------------------------------------------- summary */

function SummaryPanel() {
  const { t, s, busy, errors, loadSummary, clearError } = useApp()
  const sum = s.interview.summary
  return (
    <div className="space-y-5 animate-rise">
      <div className="flex items-baseline justify-between">
        <h2 className="font-serif text-[22px] font-medium text-ink-900">{t('iv.summary')}</h2>
        <span className="text-[12.5px] text-ink-500">{t('iv.ended')} · {t('ov.interviewTurns', { n: s.interview.turns.filter((x) => x.attempts.length).length })}</span>
      </div>
      <ErrorNote code={errors.summary} onRetry={loadSummary} onClose={() => clearError('summary')} />
      {busy.summary && <WorkingState label={t('iv.summarizing')} rows={2} />}
      {sum && !busy.summary && (
        <>
          <div className="grid grid-cols-2 gap-5">
            <div className="rounded-xl border border-paper-200 bg-white px-6 py-5">
              <div className="mb-3 text-[11.5px] font-semibold uppercase tracking-[0.08em] text-ok-600">{t('iv.strengths')}</div>
              <ul className="space-y-3">
                {sum.strengths.map((x, i) => (
                  <li key={i} className="text-[14px] leading-relaxed text-ink-800">
                    {x.text}{x.turn && <span className="ml-1.5"><Tag>{t('iv.turnRef', { n: x.turn })}</Tag></span>}
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-xl border border-paper-200 bg-white px-6 py-5">
              <div className="mb-3 text-[11.5px] font-semibold uppercase tracking-[0.08em] text-warn-600">{t('iv.priorities')}</div>
              <ol className="space-y-3">
                {sum.priorities.map((x, i) => (
                  <li key={i} className="flex gap-3 text-[14px] leading-relaxed text-ink-800">
                    <span className="font-serif text-[16px] text-accent-500">{i + 1}</span>
                    <span>{x.text}{x.turn && <span className="ml-1.5"><Tag>{t('iv.turnRef', { n: x.turn })}</Tag></span>}</span>
                  </li>
                ))}
              </ol>
            </div>
          </div>
          {sum.next_session && (
            <div className="flex gap-3 rounded-xl bg-ink-900 px-6 py-4 text-white">
              <ArrowRight className="mt-[3px] h-4 w-4 shrink-0 text-accent-200" />
              <div>
                <div className="text-[11.5px] font-semibold uppercase tracking-[0.08em] text-white/50">{t('iv.nextSession')}</div>
                <p className="mt-0.5 text-[14px] leading-relaxed">{sum.next_session}</p>
              </div>
            </div>
          )}
        </>
      )}
      <GuidancePanel g={sum?.guidance} />
      {/* question list for review */}
      <div className="divide-y divide-paper-200 rounded-xl border border-paper-200 bg-white">
        {s.interview.turns.filter((x) => x.attempts.length).map((turn, i) => (
          <div key={turn.id} className="flex gap-4 px-5 py-3">
            <span className="w-8 shrink-0 font-mono text-[11px] text-ink-500">{t('iv.turnRef', { n: i + 1 })}</span>
            <div className="min-w-0 flex-1">
              <div className="text-[13.5px] text-ink-800">{turn.question.question}</div>
              {turn.attempts[turn.attempts.length - 1].feedback?.action && (
                <div className="mt-0.5 text-[12.5px] text-ink-500">→ {turn.attempts[turn.attempts.length - 1].feedback!.action}</div>
              )}
            </div>
            <SourceId id={turn.question.requirement_id} />
          </div>
        ))}
      </div>
    </div>
  )
}
