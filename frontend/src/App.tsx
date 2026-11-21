import { useEffect, useRef } from 'react'
import MaterialsPanel from './components/MaterialsPanel'
import Sidebar from './components/Sidebar'
import { useApp } from './lib/store'
import InterviewView from './views/InterviewView'
import MatchView from './views/MatchView'
import Overview from './views/Overview'
import ResumeView from './views/ResumeView'
import SettingsView from './views/SettingsView'

export default function App() {
  return <Workspace />
}

function Workspace() {
  const { s } = useApp()
  const { t, project, saving, saveFailed, switching } = useApp()
  const main = useRef<HTMLDivElement>(null)
  useEffect(() => {
    main.current?.scrollTo({ top: 0 })
  }, [s.feature])
  const showMaterials = s.feature !== 'settings'
  const View = { overview: Overview, resume: ResumeView, match: MatchView, interview: InterviewView, settings: SettingsView }[s.feature]
  return (
    <div className="workspace flex h-screen w-full overflow-hidden bg-paper">
      <Sidebar />
      {showMaterials && project.id && <div className="flex shrink-0" style={{visibility:switching?'hidden':'visible'}} aria-hidden={switching}><MaterialsPanel key={project.id}/></div>}
      <main ref={main} className="scroll-thin min-w-0 flex-1 overflow-y-auto">
        {switching ? <p role="status" className="p-8 text-sm text-ink-500">{s.lang==='en'?'Loading project…':s.lang==='zh-TW'?'正在載入專案…':'正在加载项目…'}</p> : !project.id && s.feature!=='settings' ? <p className="p-8 text-sm text-ink-500">{s.lang==='en'?'No projects yet. Choose New project to begin.':s.lang==='zh-TW'?'尚無專案，請點擊「新增專案」開始。':'暂无项目，点击「新建项目」开始。'}</p> : <div className={`mx-auto h-full px-8 py-7 xl:px-10 ${s.feature === 'interview' ? 'max-w-[1180px]' : 'max-w-[1240px]'}`}>
          {import.meta.env.VITE_PAGES_DEMO === '1' && <p className="mb-4 text-xs text-accent-600">{s.lang === 'en' ? 'Demo Mode · Load the fictional sample for scripted results in English.' : s.lang === 'zh-TW' ? '演示模式 · 填入虛構範例可體驗英文預設結果。' : '演示模式 · 填入虚构示例可体验英文预设结果。'}</p>}
          <header className="mb-4 flex items-baseline justify-between gap-3 border-b border-paper-200 pb-3">
            <strong className="min-w-0 break-words">{project.name}</strong>
            <span className="shrink-0 text-xs text-ink-500" data-saved={!saving && !saveFailed}>
              {!saveFailed && (saving ? t('project.saving') : t('project.saved'))}
            </span>
          </header>
          {saveFailed && <p role="alert">{s.lang === 'en' ? 'Changes could not be saved. Check storage or reload if another tab edited this project.' : '项目保存失败。请检查存储空间；若其他标签页已修改此项目，请先复制草稿再刷新。'}</p>}
          <View key={project.id}/>
        </div>}
      </main>
    </div>
  )
}
