import { AlertCircle, ArrowUpRight, BookMarked, Loader2, RefreshCw, X } from 'lucide-react'
import { useState, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { useApp } from '../lib/store'
import { errorKey, LANG_LABEL, LANG_SHORT } from '../lib/i18n'
import type { Guidance, Lang } from '../lib/types'

/* ---------------------------------------------------------------- Button */

type Variant = 'primary' | 'secondary' | 'ghost' | 'quiet' | 'danger'
const VARIANTS: Record<Variant, string> = {
  primary: 'bg-ink-900 text-white hover:bg-ink-800 active:bg-ink-950 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]',
  secondary: 'bg-white text-ink-900 ring-1 ring-inset ring-paper-300 hover:ring-ink-500/40 hover:bg-paper-50',
  ghost: 'text-ink-700 hover:bg-paper-100 hover:text-ink-900',
  quiet: 'text-accent-600 hover:text-accent-700 hover:bg-accent-50',
  danger: 'text-[#9B3B3B] hover:bg-[#F8EDED]',
}

export function Button({
  variant = 'secondary', size = 'md', loading, icon, children, className = '', ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: 'sm' | 'md' | 'lg'; loading?: boolean; icon?: ReactNode }) {
  const sz = size === 'sm' ? 'h-8 px-3 text-[13px] gap-1.5' : size === 'lg' ? 'h-11 px-5 text-[15px] gap-2' : 'h-9 px-3.5 text-[13.5px] gap-2'
  return (
    <button
      {...rest}
      disabled={rest.disabled || loading}
      className={`inline-flex select-none items-center justify-center whitespace-nowrap rounded-md font-medium transition-all duration-150 disabled:cursor-not-allowed disabled:opacity-45 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-400/50 ${sz} ${VARIANTS[variant]} ${className}`}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : icon}
      {children}
    </button>
  )
}

/* ---------------------------------------------------------------- Error note */

export function ErrorNote({ code, onRetry, onClose, compact }: { code?: string; onRetry?: () => void; onClose?: () => void; compact?: boolean }) {
  const { t, setFeature } = useApp()
  if (!code) return null
  const cfg = code === 'LLM_NOT_CONFIGURED' || code === 'LLM_AUTH'
  return (
    <div role="alert" className={`flex items-start gap-2.5 rounded-md border border-[#E9CFCF] bg-[#FBF3F3] text-[13px] leading-relaxed text-[#7A2E2E] animate-rise ${compact ? 'px-3 py-2' : 'px-3.5 py-2.5'}`}>
      <AlertCircle className="mt-[2px] h-4 w-4 shrink-0" />
      <div className="flex-1">{t(errorKey(code))}</div>
      <div className="flex shrink-0 items-center gap-1">
        {cfg && (
          <button className="rounded px-1.5 py-0.5 font-medium underline-offset-2 hover:underline" onClick={() => setFeature('settings')}>
            {t('common.goSettings')}
          </button>
        )}
        {onRetry && !cfg && (
          <button className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-medium hover:underline" onClick={onRetry}>
            <RefreshCw className="h-3.5 w-3.5" />
            {t('common.retry')}
          </button>
        )}
        {onClose && (
          <button aria-label={t('common.close')} className="rounded p-0.5 opacity-60 hover:opacity-100" onClick={onClose}>
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
    </div>
  )
}

/* ---------------------------------------------------------------- Notice */

export function Notice({ tone = 'info', children, action }: { tone?: 'info' | 'warn'; children: ReactNode; action?: ReactNode }) {
  const cls = tone === 'warn' ? 'border-warn-200 bg-warn-50 text-warn-600' : 'border-accent-100 bg-accent-50 text-accent-700'
  return (
    <div className={`flex items-center gap-3 rounded-md border px-3.5 py-2 text-[13px] animate-fade ${cls}`}>
      <div className="flex-1 leading-relaxed">{children}</div>
      {action}
    </div>
  )
}

/* ---------------------------------------------------------------- Loading skeleton */

export function WorkingState({ label, rows = 3 }: { label: string; rows?: number }) {
  return (
    <div className="animate-fade" aria-live="polite">
      <div className="mb-5 flex items-center gap-2.5 text-[13.5px] text-ink-600">
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent-400 opacity-60" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-accent-500" />
        </span>
        {label}
      </div>
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="rounded-lg border border-paper-200 bg-white p-5" style={{ opacity: 1 - i * 0.22 }}>
            <div className="skeleton mb-3 h-3 w-1/4 rounded" />
            <div className="skeleton mb-2 h-3 w-11/12 rounded" />
            <div className="skeleton h-3 w-2/3 rounded" />
          </div>
        ))}
      </div>
    </div>
  )
}

/* ---------------------------------------------------------------- Page header */

export function PageHeader({ title, meta, actions }: { title: string; meta?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3 border-b border-paper-200 pb-4">
      <div className="min-w-0">
        <h1 className="font-serif text-[26px] font-medium leading-tight tracking-[-0.01em] text-ink-900">{title}</h1>
        {meta && <div className="mt-1.5 text-[13px] text-ink-500">{meta}</div>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  )
}

/* ---------------------------------------------------------------- Need materials */

export function NeedMaterials() {
  const { t, setMaterialsOpen, s } = useApp()
  return (
    <div className="mx-auto mt-16 max-w-md text-center animate-rise">
      <div className="mx-auto mb-4 flex h-11 w-11 items-center justify-center rounded-full bg-paper-100 text-ink-500">
        <BookMarked className="h-5 w-5" />
      </div>
      <p className="text-[14px] leading-relaxed text-ink-600">{t('common.needMaterials')}</p>
      {!s.materialsOpen && (
        <Button className="mt-4" variant="secondary" onClick={() => setMaterialsOpen(true)}>
          {t('common.openMaterials')}
        </Button>
      )}
    </div>
  )
}

/* ---------------------------------------------------------------- Result banners */

export function ResultBanners({ fingerprint, supKey, lang, onRegenerate, loading }: { fingerprint: string; supKey: string; lang: Lang; onRegenerate: () => void; loading?: boolean }) {
  const { t, s, isStale, supKey: curSup } = useApp()
  const stale = isStale(fingerprint)
  const supChanged = !stale && supKey !== curSup
  const langDiff = lang !== s.lang
  if (!stale && !supChanged && !langDiff) return null
  const msg = stale ? t('common.staleResult') : supChanged ? t('common.supplementChanged') : t('common.langMismatch', { lang: LANG_LABEL[lang] })
  return (
    <Notice
      tone={stale ? 'warn' : 'info'}
      action={
        stale ? null : (
          <Button size="sm" variant="secondary" loading={loading} onClick={onRegenerate} icon={<RefreshCw className="h-3.5 w-3.5" />}>
            {langDiff && !supChanged ? t('common.regenInLang') : t('common.regenerate')}
          </Button>
        )
      }
    >
      {msg}
    </Notice>
  )
}

/* ---------------------------------------------------------------- Guidance */

export function GuidancePanel({ g }: { g?: Guidance }) {
  const { t } = useApp()
  const [open, setOpen] = useState(false)
  if (!g) return null
  if (!g.connected || g.sources.length === 0) {
    return (
      <div className="flex items-center gap-2 text-[12.5px] text-ink-500">
        <BookMarked className="h-3.5 w-3.5" />
        {t('common.guidanceNone')}
      </div>
    )
  }
  return (
    <div className="rounded-md border border-paper-200 bg-paper-50">
      <button className="flex w-full items-center gap-2 px-3.5 py-2.5 text-left text-[12.5px] text-ink-600 hover:text-ink-900" onClick={() => setOpen(!open)}>
        <BookMarked className="h-3.5 w-3.5" />
        <span className="flex-1">{t('common.guidanceRetrieved')}</span>
        <span className="font-mono text-[11px] text-ink-500">{g.sources.length}</span>
        <ArrowUpRight className={`h-3.5 w-3.5 transition-transform ${open ? 'rotate-90' : ''}`} />
      </button>
      {open && (
        <ul className="divide-y divide-paper-200 border-t border-paper-200">
          {g.sources.map((src) => (
            <li key={src.id} className="px-3.5 py-2.5 text-[12.5px]">
              <div className="mb-1 flex items-center gap-2 text-ink-700">
                <span className="font-mono text-[11px] text-accent-600">{src.id}</span>
                <span className="font-medium">{src.source}</span>
                {src.section && <span className="text-ink-500">› {src.section}</span>}
                {src.used && <span className="ml-auto rounded bg-accent-50 px-1.5 text-[11px] text-accent-700">{t('common.guidanceUsed')}</span>}
              </div>
              <p className="line-clamp-3 leading-relaxed text-ink-500">{src.excerpt}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/* ---------------------------------------------------------------- Language switch */

export function LangSwitch({ dark }: { dark?: boolean }) {
  const { s, setLang } = useApp()
  const langs: Lang[] = ['zh-CN', 'zh-TW', 'en']
  return (
    <div role="radiogroup" aria-label="Language" className={`inline-flex items-center rounded-md p-0.5 text-[12px] ${dark ? 'bg-white/[0.06] ring-1 ring-white/10' : 'bg-white/70 ring-1 ring-paper-300 backdrop-blur'}`}>
      {langs.map((l) => {
        const on = s.lang === l
        return (
          <button
            key={l}
            role="radio"
            aria-checked={on}
            title={LANG_LABEL[l]}
            onClick={() => setLang(l)}
            className={`h-7 min-w-[34px] rounded px-2 font-medium transition-colors ${
              on ? (dark ? 'bg-white/[0.14] text-white' : 'bg-ink-900 text-white') : dark ? 'text-white/55 hover:text-white' : 'text-ink-600 hover:text-ink-900'
            }`}
          >
            {LANG_SHORT[l]}
          </button>
        )
      })}
    </div>
  )
}

/* ---------------------------------------------------------------- Tag */

export function Tag({ children, tone = 'plain' }: { children: ReactNode; tone?: 'plain' | 'accent' | 'ok' | 'warn' | 'miss' | 'dark' }) {
  const map = {
    plain: 'bg-paper-100 text-ink-600',
    accent: 'bg-accent-50 text-accent-700',
    ok: 'bg-ok-50 text-ok-600',
    warn: 'bg-warn-50 text-warn-600',
    miss: 'bg-miss-50 text-miss-500',
    dark: 'bg-ink-900 text-white',
  }
  return <span className={`inline-flex h-[22px] items-center gap-1 rounded px-1.5 text-[11.5px] font-medium ${map[tone]}`}>{children}</span>
}

export function SourceId({ id }: { id: string }) {
  return <span className="font-mono text-[10.5px] tracking-tight text-ink-500">{id}</span>
}
