import { useEffect, useRef } from 'react'
import MaterialsPanel from './components/MaterialsPanel'
import Sidebar from './components/Sidebar'
import { useApp } from './lib/store'
import InterviewView from './views/InterviewView'
import Landing from './views/Landing'
import MatchView from './views/MatchView'
import Overview from './views/Overview'
import ResumeView from './views/ResumeView'
import SettingsView from './views/SettingsView'

export default function App() {
  const { s } = useApp()
  if (!s.entered) return <Landing />
  return <Workspace />
}

function Workspace() {
  const { s } = useApp()
  const main = useRef<HTMLDivElement>(null)
  useEffect(() => {
    main.current?.scrollTo({ top: 0 })
  }, [s.feature])
  const showMaterials = s.feature !== 'settings'
  const View = { overview: Overview, resume: ResumeView, match: MatchView, interview: InterviewView, settings: SettingsView }[s.feature]
  return (
    <div className="flex h-screen w-full overflow-hidden bg-paper animate-fade">
      <Sidebar />
      {showMaterials && <MaterialsPanel />}
      <main ref={main} className="scroll-thin min-w-0 flex-1 overflow-y-auto">
        <div className={`mx-auto h-full px-8 py-7 xl:px-10 ${s.feature === 'interview' ? 'max-w-[1180px]' : 'max-w-[1240px]'}`}>
          <View />
        </div>
      </main>
    </div>
  )
}
