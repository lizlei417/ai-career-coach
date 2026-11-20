import { Folder, Plus } from 'lucide-react'
import { useRef, useState } from 'react'
import { useApp } from '../lib/store'

export default function ProjectList() {
  const { t, project, projects, busy, switching, changeProject } = useApp()
  const [name, setName] = useState('')
  const dialog = useRef<HTMLDialogElement>(null)
  const locked = switching || Object.values(busy).some(Boolean)
  return <section className="project-list mx-3 mt-4 min-h-0 border-b border-white/10 pb-3">
    <h2 className="px-2 pb-1 text-xs text-white/60">{t('project.list')}</h2>
    <div className="max-h-[23vh] overflow-y-auto">
      {projects.map(p => <button key={p.id} disabled={locked} aria-current={project.id === p.id ? 'true' : undefined}
        className={'flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm ' + (project.id === p.id ? 'bg-white/10 text-white' : 'text-white/65')}
        onClick={() => p.id !== project.id && changeProject(p.id)}>
        <Folder size={15} className="shrink-0"/><span className="truncate" title={p.name}>{p.name}</span>
      </button>)}
    </div>
    <button disabled={locked} className="flex items-center gap-2 px-2 pt-2 text-xs text-white/75" onClick={() => { setName(''); dialog.current?.showModal() }}>
      <Plus size={14}/>{t('project.new')}
    </button>
    <dialog className="project-dialog rounded-lg border border-paper-200 p-6 text-ink-900" ref={dialog} aria-labelledby="new-project-title">
      <form onSubmit={async e => { e.preventDefault(); if (name.trim()) { dialog.current?.close(); await changeProject(name.trim(), true) } }}>
        <h2 id="new-project-title" className="mb-4 font-semibold">{t('project.new')}</h2>
        <label className="field-label">{t('project.name')}<input autoFocus required maxLength={100} className="field mt-2" value={name} onChange={e => setName(e.target.value)}/></label>
        <div className="mt-5 flex justify-end gap-4"><button type="button" onClick={() => dialog.current?.close()}>{t('project.cancel')}</button>
          <button className="rounded bg-ink-900 px-4 py-2 text-white disabled:opacity-50" disabled={!name.trim()}>{t('project.create')}</button></div>
      </form>
    </dialog>
  </section>
}
