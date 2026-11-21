import {apiFetch} from '../cloud'
import { Check, ChevronsLeft, ChevronsRight, FileUp, Link2, Loader2, Sparkles, X } from 'lucide-react'
import { useRef, useState, type DragEvent } from 'react'
import PdfPreview from './PdfPreview'
import { ApiError, post, upload } from '../lib/api'
import { SAMPLE_JD, SAMPLE_RESUME } from '../lib/sample'
import { useApp } from '../lib/store'
import { Button, ErrorNote } from './ui'

function count(s: string) {
  return s.replace(/\s+/g, '').length
}

export default function MaterialsPanel() {
  const { project,t, s, llm, setInputs, setMaterialsOpen, prepare, run, busy, errors, clearError, setError, inputsDirty, ready, removeSupplement } = useApp()
  const { inputs } = s
  const fileRef = useRef<HTMLInputElement>(null)
  const [preview, setPreview] = useState<Blob|null>(null)
  const [drag, setDrag] = useState(false)
  const [showUrl, setShowUrl] = useState(false)

  if (!s.materialsOpen) {
    return (
      <div className="flex h-full w-[52px] shrink-0 flex-col items-center border-r border-paper-200 bg-paper-50 py-4">
        <button
          onClick={() => setMaterialsOpen(true)}
          title={t('mat.expand')}
          aria-label={t('mat.expand')}
          className="rounded-md p-2 text-ink-500 hover:bg-paper-100 hover:text-ink-900"
        >
          <ChevronsRight className="h-4 w-4" />
        </button>
        <button onClick={() => setMaterialsOpen(true)} className="mt-4 text-[12px] font-medium tracking-[0.12em] text-ink-500 [writing-mode:vertical-rl] hover:text-ink-900">
          {t('mat.title')}
        </button>
        <span className={`mt-3 h-1.5 w-1.5 rounded-full ${inputsDirty ? 'bg-warn-500' : ready ? 'bg-ok-500' : 'bg-paper-300'}`} />
      </div>
    )
  }

  const onFile = async (f?: File | null) => {
    if (!f) return
    clearError('pdf')
    if (!/\.pdf$/i.test(f.name) && f.type !== 'application/pdf') {
      setError('pdf', 'FILE_TYPE')
      return
    }
    if (busy.pdf) return
    const out = await run('pdf', async () => {
      if (f.size > 8 * 1024 * 1024) throw new ApiError('FILE_TOO_LARGE')
      if (!((await f.slice(0, 5).text()) === '%PDF-')) throw new ApiError('PDF_UNREADABLE')
      return await upload<{text:string;pages:number;file_id:string;warning?:string}>('/api/extract/pdf',f,project.id)
    })
    if (out) {
      setInputs({ resumeText: out.text, resumeFile: { name: f.name, pages: out.pages, fileId: out.file_id } })
      if (out.warning) setError('pdf', out.warning)
    }
  }
  const onDrop = (e: DragEvent) => {
    e.preventDefault()
    setDrag(false)
    onFile(e.dataTransfer.files?.[0])
  }
  const importUrl = async () => {
    if (busy.url) return
    const sourceUrl = inputs.jdUrl.trim()
    const out = await run('url', () => post<{ text: string; title: string; url?: string }>('/api/extract/url', { url: sourceUrl }))
    if (out) {
      setInputs({ jdText: out.text, jdFromUrl: true, jdSourceUrl: out.url || sourceUrl, jobTitle: inputs.jobTitle || out.title.slice(0, 80) })
      setShowUrl(false)
    }
  }

  const empty = !inputs.resumeText.trim() && !inputs.jdText.trim()

  return (
    <section className="flex h-full w-[340px] shrink-0 flex-col border-r border-paper-200 bg-paper-50 xl:w-[360px]">
      <div className="flex h-16 shrink-0 items-center justify-between px-5">
        <div className="flex items-center gap-2">
          <h2 className="text-[14px] font-semibold text-ink-900">{t('mat.title')}</h2>
          {ready && !inputsDirty && (
            <span className="inline-flex items-center gap-1 text-[11.5px] text-ok-600">
              <Check className="h-3 w-3" />
              {t('mat.ready')}
            </span>
          )}
        </div>
        <button onClick={() => setMaterialsOpen(false)} title={t('mat.collapse')} aria-label={t('mat.collapse')} className="rounded-md p-1.5 text-ink-500 hover:bg-paper-100 hover:text-ink-900">
          <ChevronsLeft className="h-4 w-4" />
        </button>
      </div>

      <div className="scroll-thin flex-1 space-y-6 overflow-y-auto px-5 pb-6">
        {/* Resume */}
        <div>
          <div className="mb-2 flex items-center justify-between">
            <label htmlFor="resume" className="field-label">{t('mat.resume')}</label>
            <div className="flex items-center gap-3 text-xs text-accent-600">
              <button disabled={busy.pdf} onClick={() => fileRef.current?.click()}>{t('mat.uploadPdf')}</button>
              <button disabled={!inputs.resumeFile?.fileId} className="disabled:opacity-40" onClick={async()=>{
                try{
                  const response=await apiFetch('/api/documents/'+inputs.resumeFile!.fileId+'?project_id='+encodeURIComponent(project.id))
                  if(!response.ok)throw Error()
                  setPreview(await response.blob())
                }catch{setError('pdf','NETWORK')}
              }}>{t('project.preview')}</button>
            </div>
            {(inputs.resumeText || inputs.resumeFile) && (
              <button className="text-[11.5px] text-ink-500 hover:text-ink-900" onClick={async()=>{
                try{
                  if(inputs.resumeFile?.fileId){
                    const r=await apiFetch('/api/documents/'+inputs.resumeFile.fileId+'?project_id='+encodeURIComponent(project.id),{method:'DELETE'})
                    if(!r.ok&&r.status!==404)throw Error()
                  }
                  setInputs({resumeText:'',resumeFile:null})
                }catch{setError('pdf','NETWORK')}
              }}>
                {t('mat.clear')}
              </button>
            )}
          </div>
              <input ref={fileRef} type="file" accept="application/pdf,.pdf" hidden onChange={(e) => { onFile(e.target.files?.[0]); e.target.value = '' }} />
          {!inputs.resumeText && !inputs.resumeFile?.fileId && (
            <div
              onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
              onDragLeave={() => setDrag(false)}
              onDrop={onDrop}
              className={`mb-2 flex items-center gap-3 rounded-md border border-dashed px-3.5 py-3 transition-colors ${drag ? 'border-accent-400 bg-accent-50' : 'border-paper-300 bg-white'}`}
            >
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded bg-paper-100 text-ink-600">
                {busy.pdf ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileUp className="h-4 w-4" strokeWidth={1.7} />}
              </div>
              <div className="text-[12.5px] leading-snug text-ink-600">
                {busy.pdf ? t('mat.reading') : (
                  <>
                    {t('mat.dropHint')}{' '}
                    <button className="font-medium text-accent-600 underline-offset-2 hover:underline" onClick={() => fileRef.current?.click()}>
                      {t('mat.choose')}
                    </button>
                    <div className="text-[11.5px] text-ink-500">{t('mat.orPaste')}</div>
                  </>
                )}
              </div>

            </div>
          )}
          {preview && inputs.resumeFile?.fileId && <PdfPreview blob={preview} name={inputs.resumeFile.name} close={() => setPreview(null)} />}
          <ErrorNote code={errors.pdf} compact onClose={() => clearError('pdf')} />
          <textarea
            id="resume"
            value={inputs.resumeText}
            onChange={(e) => setInputs({ resumeText: e.target.value })}
            placeholder={t('mat.resumePlaceholder')}
            className={`field mt-2 resize-none font-[450] ${inputs.resumeText ? 'h-[200px]' : 'h-[96px]'}`}
          />
          <div className="mt-1 flex items-center justify-between text-[11px] text-ink-500">
            <span className="truncate">{inputs.resumeFile?.pages ? t('mat.fromFile', { name: inputs.resumeFile.name, pages: inputs.resumeFile.pages }) : inputs.resumeFile?.name}</span>
            <span className="shrink-0 tabular-nums">{inputs.resumeText ? t('mat.chars', { n: count(inputs.resumeText) }) : ''}</span>
          </div>
        </div>

        {/* Job title */}
        <div>
          <label htmlFor="jobtitle" className="field-label mb-2 block">
            {t('mat.jobTitle')} <span className="font-normal normal-case tracking-normal text-ink-500">· {t('mat.optional')}</span>
          </label>
          <input id="jobtitle" disabled={busy.url} value={inputs.jobTitle} onChange={(e) => setInputs({ jobTitle: e.target.value })} placeholder={t('mat.jobTitlePlaceholder')} className="field h-9" />
        </div>

        {/* JD */}
        <div>
          <div className="mb-2 flex items-center justify-between">
            <label htmlFor="jd" className="field-label">{t('mat.jd')}</label>
            <div className="flex items-center gap-3">
              {inputs.jdText && (
                <button className="text-[11.5px] text-ink-500 hover:text-ink-900" onClick={() => setInputs({ jdText: '', jdFromUrl: false })}>
                  {t('mat.clear')}
                </button>
              )}
              <button className="inline-flex items-center gap-1 text-[11.5px] font-medium text-accent-600 hover:text-accent-700" onClick={() => setShowUrl(!showUrl)}>
                <Link2 className="h-3 w-3" />
                {t('mat.importUrl')}
              </button>
            </div>
          </div>
          {showUrl && (
            <div className="mb-2 flex gap-1.5 animate-rise">
              <input
                disabled={busy.url}
                value={inputs.jdUrl}
                onChange={(e) => setInputs({ jdUrl: e.target.value })}
                onKeyDown={(e) => e.key === 'Enter' && !busy.url && inputs.jdUrl && importUrl()}
                placeholder={t('mat.urlPlaceholder')}
                className="field h-9 flex-1"
                autoFocus
              />
              <Button size="md" variant="secondary" loading={busy.url} disabled={!inputs.jdUrl.trim()} onClick={importUrl}>
                {busy.url ? t('mat.importing') : t('mat.import')}
              </Button>
            </div>
          )}
          <ErrorNote code={errors.url} compact onRetry={busy.url ? undefined : importUrl} onClose={() => clearError('url')} />
          <textarea
            id="jd"
            disabled={busy.url}
            value={inputs.jdText}
            onChange={(e) => setInputs({ jdText: e.target.value, jdFromUrl: e.target.value ? inputs.jdFromUrl : false })}
            placeholder={t('mat.jdPlaceholder')}
            className="field mt-2 h-[180px] resize-none"
          />
          <div className="mt-1 flex items-center justify-between text-[11px] text-ink-500">
            <span className="truncate">{inputs.jdFromUrl && inputs.jdText ? t('mat.imported') : ''}</span>
            <span className="shrink-0 tabular-nums">{inputs.jdText ? t('mat.chars', { n: count(inputs.jdText) }) : ''}</span>
          </div>
        </div>

        {/* Supplements */}
        {s.supplements.length > 0 && (
          <div>
            <div className="field-label mb-1">{t('mat.supplements')}</div>
            <p className="mb-2 text-[11.5px] text-ink-500">{t('mat.supplementsHint')}</p>
            <ul className="space-y-1.5">
              {s.supplements.map((sp) => (
                <li key={sp.id} className="group flex gap-2 rounded-md border border-paper-200 bg-white px-2.5 py-2 text-[12.5px] leading-relaxed text-ink-700">
                  <span className="mt-[2px] font-mono text-[10.5px] text-accent-600">{sp.id}</span>
                  <span className="flex-1">{sp.text}</span>
                  <button title={t('mat.removeSupplement')} onClick={() => removeSupplement(sp.id)} className="self-start rounded p-0.5 text-ink-500 opacity-0 hover:text-ink-900 group-hover:opacity-100">
                    <X className="h-3.5 w-3.5" />
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {(empty || import.meta.env.VITE_PAGES_DEMO === "1") && (
          <button
            onClick={() => setInputs({ resumeText: SAMPLE_RESUME, jdText: SAMPLE_JD, jobTitle: 'Product Operations Intern', resumeFile: null, jdFromUrl: false })}
            className="inline-flex items-center gap-1.5 text-[12px] text-ink-500 hover:text-ink-900"
          >
            <Sparkles className="h-3.5 w-3.5" />
            {t('mat.sample')}
          </button>
        )}
      </div>

      {/* footer */}
      <div className="shrink-0 space-y-2.5 border-t border-paper-200 bg-paper-50 px-5 py-4">
        {inputsDirty && <div className="text-[12px] leading-snug text-warn-600">{t('mat.dirty')}</div>}
        {ready && !inputsDirty && s.materials && (
          <div className="text-[12px] text-ink-500">
            {t('mat.lines', { r: s.materials.resume_lines.filter((l) => !l.heading).length, q: s.materials.requirements.length })}
          </div>
        )}
        <ErrorNote code={errors.prepare} compact onClose={() => clearError('prepare')} />
        <Button
          variant="primary"
          size="lg"
          className="w-full"
          loading={busy.prepare}
          onClick={prepare}
          disabled={!llm?.configured || (ready && !inputsDirty)}
        >
          {busy.prepare ? t('mat.analyzing') : ready ? t('mat.reanalyze') : t('mat.analyze')}
        </Button>
      </div>
    </section>
  )
}
