import { BriefcaseBusiness, FileText, Home, LayoutGrid, MessagesSquare, Settings2 } from 'lucide-react'
import { useApp } from '../lib/store'
import type { Feature } from '../lib/types'
import { LangSwitch } from './ui'
import { Logo } from '../views/Landing'

export default function Sidebar() {
  const { t, s, setFeature, leave, llm, kb, isStale } = useApp()
  const items: { key: Feature; label: string; icon: typeof FileText; dot?: 'ready' | 'stale' }[] = [
    { key: 'overview', label: t('nav.overview'), icon: LayoutGrid },
    { key: 'resume', label: t('nav.resume'), icon: FileText, dot: s.resume ? (isStale(s.resume.fingerprint) ? 'stale' : 'ready') : undefined },
    { key: 'match', label: t('nav.match'), icon: BriefcaseBusiness, dot: s.match ? (isStale(s.match.fingerprint) ? 'stale' : 'ready') : undefined },
    {
      key: 'interview', label: t('nav.interview'), icon: MessagesSquare,
      dot: s.interview.turns.length ? (isStale(s.interview.fingerprint) ? 'stale' : 'ready') : undefined,
    },
  ]
  return (
    <aside className="flex h-full w-[224px] shrink-0 flex-col bg-ink-950 text-white">
      <div className="flex h-16 items-center gap-2.5 px-5">
        <Logo dark size={26} />
        <span className="text-[14.5px] font-semibold tracking-tight">AI Career Coach</span>
      </div>

      <nav className="mt-3 flex-1 space-y-0.5 px-3">
        {items.map((it) => {
          const on = s.feature === it.key
          const Icon = it.icon
          return (
            <button
              key={it.key}
              onClick={() => setFeature(it.key)}
              className={`group relative flex h-10 w-full items-center gap-3 rounded-md px-3 text-[13.5px] transition-colors ${
                on ? 'bg-white/[0.08] text-white' : 'text-white/60 hover:bg-white/[0.04] hover:text-white'
              }`}
            >
              {on && <span className="absolute left-0 top-2.5 h-5 w-[2px] rounded-full bg-accent-200" />}
              <Icon className="h-[17px] w-[17px] shrink-0" strokeWidth={1.7} />
              <span className="flex-1 truncate text-left">{it.label}</span>
              {it.dot && <span className={`h-1.5 w-1.5 rounded-full ${it.dot === 'ready' ? 'bg-accent-200' : 'bg-warn-500'}`} />}
            </button>
          )
        })}
        <div className="!my-3 mx-3 h-px bg-white/[0.07]" />
        <button
          onClick={() => setFeature('settings')}
          className={`relative flex h-10 w-full items-center gap-3 rounded-md px-3 text-[13.5px] transition-colors ${
            s.feature === 'settings' ? 'bg-white/[0.08] text-white' : 'text-white/60 hover:bg-white/[0.04] hover:text-white'
          }`}
        >
          {s.feature === 'settings' && <span className="absolute left-0 top-2.5 h-5 w-[2px] rounded-full bg-accent-200" />}
          <Settings2 className="h-[17px] w-[17px]" strokeWidth={1.7} />
          <span className="flex-1 text-left">{t('nav.settings')}</span>
        </button>
      </nav>

      <div className="space-y-3 px-5 pb-5">
        <button onClick={() => setFeature('settings')} className="block w-full space-y-1.5 rounded-md border border-white/[0.07] px-3 py-2.5 text-left text-[11.5px] transition-colors hover:border-white/15">
          <div className="flex items-center justify-between gap-2">
            <span className="text-white/40">{t('side.model')}</span>
            <span className={`flex min-w-0 items-center gap-1.5 ${llm?.configured ? 'text-white/80' : 'text-warn-200'}`}>
              <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${llm?.connection === 'verified' ? 'bg-[#7FB89A]' : 'bg-warn-500'}`} />
              <span className="truncate">{llm?.configured ? (llm.connection ? t(llm.connection === 'verified' ? 'ds.verified' : llm.connection === 'failed' ? 'ds.failed' : 'ds.pending') : llm.model) : t('side.notConfigured')}</span>
            </span>
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="text-white/40">{t('side.kb')}</span>
            <span className="truncate text-white/60">{kb?.connected ? t('side.connected', { n: kb.files.length }) : t('side.notConnected')}</span>
          </div>
        </button>
        <div className="flex items-center justify-between">
          <LangSwitch dark />
          <button onClick={leave} title={t('nav.home')} aria-label={t('nav.home')} className="rounded-md p-2 text-white/45 hover:bg-white/[0.06] hover:text-white">
            <Home className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  )
}
