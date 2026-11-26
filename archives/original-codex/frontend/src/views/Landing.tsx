import { ArrowRight } from 'lucide-react'
import { useApp } from '../lib/store'
import { LangSwitch } from '../components/ui'

export function Logo({ dark, size = 28 }: { dark?: boolean; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <rect width="32" height="32" rx="7" fill={dark ? '#DCE6F2' : '#111B2B'} />
      <path d="M9 22 15.5 9h1L23 22h-3l-1.4-3h-5.2L12 22H9Zm5.4-5.5h3.2L16 12.9l-1.6 3.6Z" fill={dark ? '#111B2B' : '#DCE6F2'} />
    </svg>
  )
}

export default function Landing() {
  const { t, enter } = useApp()
  const features = [
    { n: '01', title: t('landing.f1'), desc: t('landing.f1d') },
    { n: '02', title: t('landing.f2'), desc: t('landing.f2d') },
    { n: '03', title: t('landing.f3'), desc: t('landing.f3d') },
  ]
  return (
    <div className="relative flex h-screen min-h-[640px] w-full overflow-hidden bg-paper">
      {/* left column */}
      <div className="relative z-10 flex w-full flex-col px-10 lg:w-[58%] lg:px-16 xl:px-20">
        <header className="flex h-20 items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Logo />
            <span className="text-[15px] font-semibold tracking-tight text-ink-900">AI Career Coach</span>
          </div>
          <div className="lg:hidden">
            <LangSwitch />
          </div>
        </header>

        <main className="flex flex-1 flex-col justify-center pb-8">
          <div className="mb-7 flex items-center gap-3 text-[12px] font-medium uppercase tracking-[0.14em] text-accent-600 animate-rise">
            <span className="h-px w-8 bg-accent-400" />
            {t('landing.eyebrow')}
          </div>
          <h1
            className="font-serif text-[44px] font-medium leading-[1.12] tracking-[-0.02em] text-ink-900 animate-rise xl:text-[56px]"
            style={{ animationDelay: '60ms' }}
          >
            {t('landing.title1')}
            <br />
            <span className="text-ink-600">{t('landing.title2')}</span>
          </h1>
          <p className="mt-6 max-w-[520px] text-[16px] leading-[1.75] text-ink-600 animate-rise" style={{ animationDelay: '120ms' }}>
            {t('landing.lead')}
          </p>
          <div className="mt-9 flex items-center gap-5 animate-rise" style={{ animationDelay: '180ms' }}>
            <button
              onClick={enter}
              className="group inline-flex h-12 items-center gap-3 rounded-md bg-ink-900 pl-6 pr-5 text-[15px] font-medium text-white shadow-lift transition-all hover:bg-ink-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-400/60"
            >
              {t('landing.start')}
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </button>
            <span className="max-w-[260px] text-[12.5px] leading-relaxed text-ink-500">{t('landing.note')}</span>
          </div>
        </main>

        <footer className="grid grid-cols-3 gap-8 border-t border-paper-300 pb-10 pt-6 animate-fade" style={{ animationDelay: '260ms' }}>
          {features.map((f) => (
            <div key={f.n}>
              <div className="mb-2 font-mono text-[11px] text-accent-500">{f.n}</div>
              <div className="mb-1 text-[14px] font-semibold text-ink-900">{f.title}</div>
              <div className="text-[12.5px] leading-relaxed text-ink-500">{f.desc}</div>
            </div>
          ))}
        </footer>
      </div>

      {/* right photo */}
      <div className="absolute inset-y-0 right-0 hidden w-[42%] lg:block">
        <img src="/hero.jpg" alt="" className="h-full w-full object-cover" style={{ filter: 'saturate(0.7) contrast(1.02)' }} />
        <div className="absolute inset-0 bg-gradient-to-r from-paper via-paper/10 to-transparent" style={{ width: '22%' }} />
        <div className="absolute inset-0 bg-[#1A2638]/10 mix-blend-multiply" />
        <div className="absolute right-8 top-6">
          <LangSwitch />
        </div>
        <div className="absolute bottom-10 right-10 text-right">
          <div className="font-mono text-[11px] uppercase tracking-[0.18em] text-white/80">AI Career Coach</div>
          <div className="mt-1 font-serif text-[15px] text-white/90">{t('landing.caption')}</div>
        </div>
      </div>
    </div>
  )
}
