import { useEffect, useRef, useState } from 'react'
import MaterialsPanel from './components/MaterialsPanel'
import Explorer from './explore/Explorer'
import Reviews from './explore/Reviews'
import './explore/explore.css'
import Sidebar from './components/Sidebar'
import { useApp } from './lib/store'
import type { Feature } from './lib/types'
import InterviewView from './views/InterviewView'
import MatchView from './views/MatchView'
import Overview from './views/Overview'
import ResumeView from './views/ResumeView'
import SettingsView from './views/SettingsView'

const navItems = [
  { key: 'explorer', en: 'Career Explorer', tw: '職業測評', cn: '职业测评' },
  { key: 'reviews', en: 'Interview Review', tw: '面經復盤', cn: '面经复盘' },
  { key: 'resume', en: 'Resume', tw: '履歷優化', cn: '简历优化' },
  { key: 'match', en: 'Job match', tw: '職位匹配', cn: '岗位匹配' },
  { key: 'interview', en: 'Interview', tw: '模擬面試', cn: '模拟面试' },
] as const

const usesMaterials = (feature: Feature) => !['settings', 'explorer', 'reviews'].includes(feature)

export default function App() {
  return <Workspace />
}

function Workspace() {
  const { s } = useApp()
  const { t, project, saving, saveFailed, switching, retrySave, setFeature, resumeDirty } = useApp()
  const main = useRef<HTMLDivElement>(null)
  const materialsSlot = useRef<HTMLDivElement>(null)
  const showMaterials = usesMaterials(s.feature)
  const [displayFeature, setDisplayFeature] = useState<Feature>(s.feature)
  const [viewPhase, setViewPhase] = useState<'idle' | 'out' | 'in'>('idle')
  const previousPage = useRef({ feature: s.feature, projectId: project.id })

  // Keep the panel mounted while its width animates, preserving inputs and scroll position.
  // The inert flag prevents keyboard focus on controls while the panel is visually hidden.
  useEffect(() => {
    if (materialsSlot.current) materialsSlot.current.inert = !showMaterials || switching
  }, [showMaterials, switching])

  // Cross-fade the content at the midpoint of the panel's horizontal movement.
  // Only the five-function layout boundary needs the longer transition.
  useEffect(() => {
    const previous = previousPage.current
    previousPage.current = { feature: s.feature, projectId: project.id }
    if (previous.feature === s.feature && previous.projectId === project.id) return
    if (
      previous.projectId !== project.id ||
      usesMaterials(previous.feature) === showMaterials ||
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    ) {
      setDisplayFeature(s.feature)
      setViewPhase('idle')
      return
    }
    setViewPhase('out')
    let firstFrame = 0
    let secondFrame = 0
    const exitTimer = window.setTimeout(() => {
      setDisplayFeature(s.feature)
      setViewPhase('in')
      firstFrame = window.requestAnimationFrame(() => {
        secondFrame = window.requestAnimationFrame(() => setViewPhase('idle'))
      })
    }, 160)
    return () => {
      window.clearTimeout(exitTimer)
      if (firstFrame) window.cancelAnimationFrame(firstFrame)
      if (secondFrame) window.cancelAnimationFrame(secondFrame)
    }
  }, [s.feature, project.id, showMaterials])

  useEffect(() => {
    main.current?.scrollTo({ top: 0 })
  }, [s.feature])
  const View = { explorer: Explorer, reviews: Reviews, overview: Overview, resume: ResumeView, match: MatchView, interview: InterviewView, settings: SettingsView }[displayFeature]
  return (
    <div className="workspace flex h-screen w-full overflow-hidden bg-paper">
      <Sidebar />
      <div
        ref={materialsSlot}
        className="workspace-materials-slot"
        data-visible={showMaterials && !!project.id ? 'true' : 'false'}
        data-folded={!s.materialsOpen ? 'true' : 'false'}
        style={{ visibility: switching ? 'hidden' : 'visible' }}
        aria-hidden={!showMaterials || switching}
      >
        {project.id && <MaterialsPanel key={project.id} />}
      </div>
      <main ref={main} className="scroll-thin min-w-0 flex-1 overflow-y-auto">
        {switching ? <p role="status" className="p-8 text-sm text-ink-500">{s.lang==='en'?'Loading project…':s.lang==='zh-TW'?'正在載入專案…':'正在加载项目…'}</p> : !project.id && !['overview','match','settings','explorer','reviews'].includes(s.feature) ? <p className="p-8 text-sm text-ink-500">{s.lang==='en'?'No projects yet. Choose New project to begin.':s.lang==='zh-TW'?'尚無專案，請點擊「新增專案」開始。':'暂无项目，点击「新建项目」开始。'}</p> : <div className={`mx-auto min-h-full px-8 py-7 xl:px-10 max-w-[1240px]`}>
          {import.meta.env.VITE_PAGES_DEMO === '1' && <p className="mb-4 text-xs text-accent-600">{s.lang === 'en' ? 'Demo Mode · Load the fictional sample for scripted results in English.' : s.lang === 'zh-TW' ? '演示模式 · 填入虛構範例可體驗英文預設結果。' : '演示模式 · 填入虚构示例可体验英文预设结果。'}</p>}
          <header className="sticky top-0 z-10 bg-paper mb-4 flex items-baseline justify-between gap-3 border-b border-paper-200 pb-3">
            <nav aria-label={s.lang === 'en' ? 'Career tools' : s.lang === 'zh-TW' ? '求職工具' : '求职工具'} className="flex flex-wrap items-center gap-x-4 gap-y-2 sm:gap-x-5">
              {navItems.map((item) => <button key={item.key} aria-current={s.feature === item.key ? 'page' : undefined} onClick={() => setFeature(item.key)} className={`whitespace-nowrap border-b-2 pb-3 -mb-[13px] text-sm ${s.feature === item.key ? 'border-ink-900 font-semibold text-ink-900' : 'border-transparent text-ink-500 hover:text-ink-900'}`}>{s.lang === 'en' ? item.en : s.lang === 'zh-TW' ? item.tw : item.cn}</button>)}
            </nav>
            {!['reviews','explorer'].includes(s.feature) && <span className="shrink-0 text-xs text-ink-500" data-saved={!saving && !saveFailed && !resumeDirty}>
              {!saveFailed && (saving ? t('project.saving') : resumeDirty ? (s.lang === 'en' ? 'Unsaved edits' : s.lang === 'zh-TW' ? '尚未儲存' : '尚未保存') : t('project.saved'))}
            </span>}
          </header>
          {saveFailed && <p role="alert">{s.lang === 'en' ? 'Changes could not be saved. Check storage or reload if another tab edited this project.' : '项目保存失败。请检查存储空间；若其他标签页已修改此项目，请先复制草稿再刷新。'} <button disabled={saving} className="underline" onClick={retrySave}>{t('common.retry')}</button></p>}
          <div className="workspace-view-swap" data-phase={viewPhase} data-direction={showMaterials ? 'expand' : 'collapse'}>
            <View key={project.id} />
          </div>
        </div>}
      </main>
    </div>
  )
}
