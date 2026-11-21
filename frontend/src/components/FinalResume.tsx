import { useState } from 'react'
import { Download, Eye } from 'lucide-react'
import { apiFetch } from '../cloud'
import { useApp } from '../lib/store'
import { Button } from './ui'
import { errorKey } from '../lib/i18n'

type Final = { text: string; applied: number; pending: number }
export default function FinalResume() {
  const { s, t, project, flushSave, isStale, busy } = useApp()
  const [result, setResult] = useState<Final>()
  const [version, setVersion] = useState('')
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')
  const en = s.lang === 'en', tw = s.lang === 'zh-TW'
  const words = en ? {
    title: 'Complete resume', preview: 'Preview complete resume', hint: 'Your original stays unchanged. Only accepted or saved edits are applied. Pending and kept suggestions use the original text.',
    changed: 'Your materials or decisions changed. Refresh the preview before exporting.', failed: 'Could not save or export. Check the connection and retry.', close: 'Close preview', pending: 'Pending suggestions use original text. Review the full resume before applying.', applied: 'Applied changes', save: 'Saving and preparing…',
  } : tw ? {
    title: '完整履歷', preview: '預覽完整履歷', hint: '保留原始履歷，僅套用已採納或已儲存的編輯；待審核與保留原文的項目維持原文。',
    changed: '材料或審核決定已變更，請重新預覽後匯出。', failed: '未能儲存或匯出，請檢查網絡後重試。', close: '關閉預覽', pending: '未審核項目保留原文。投遞前請核對完整履歷。', applied: '已套用修改', save: '正在儲存並準備…',
  } : {
    title: '完整简历', preview: '预览完整简历', hint: '保留原始简历，仅应用已采纳或已保存的编辑；待审核与保留原文的项目维持原文。',
    changed: '材料或审核决定已变更，请重新预览后导出。', failed: '无法保存或导出，请检查网络后重试。', close: '关闭预览', pending: '未审核项目保留原文。投递前请核对完整简历。', applied: '已应用修改', save: '正在保存并准备…',
  }
  const current = JSON.stringify([s.resume, s.inputs, s.inputsKey, s.materials?.fingerprint])
  const outdated = version !== current
  const stale = isStale(s.resume?.fingerprint)
  async function request(format?: 'pdf' | 'docx') {
    if (working) return
    setWorking(true); setError('')
    try {
      // The server always reads the persisted, owner-scoped project. A failed
      // write blocks export instead of silently exporting older decisions.
      await flushSave()
      const response = await apiFetch(`/api/workspaces/${encodeURIComponent(project.id)}/resume/${format ? 'export?format=' + format : 'final'}`)
      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        const code = body?.error?.code
        throw Error(code ? t(errorKey(code)) : words.failed)
      }
      if (!format) { setResult(await response.json()); setVersion(current) }
      else {
        const url = URL.createObjectURL(await response.blob())
        const a = document.createElement('a'); a.href = url
        a.download = `${project.name.replace(/[^\p{L}\p{N} _-]/gu, '').slice(0, 80) || 'Resume'}.${format}`
        document.body.append(a); a.click(); a.remove()
        setTimeout(() => URL.revokeObjectURL(url), 1000)
      }
    } catch (e) { setError(e instanceof Error && !e.message.startsWith('HTTP') ? e.message : words.failed) }
    finally { setWorking(false) }
  }
  return <section className="rounded-lg border border-paper-200 bg-white p-5" aria-label={words.title}>
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><h2 className="font-serif text-[20px] text-ink-900">{words.title}</h2><p className="mt-1 max-w-2xl text-[13px] leading-relaxed text-ink-500">{words.hint}</p></div>
      <Button icon={<Eye className="h-4 w-4" />} loading={working} disabled={stale || busy.resume} onClick={() => request()}>{words.preview}</Button>
    </div>
    {error && <p role="alert" className="mt-3 text-sm text-[#7A2E2E]">{error}</p>}
    {result && <div className="mt-4">
      {outdated && <p role="status" className="mb-3 text-sm text-warn-600">{words.changed}</p>}
      <div className="mb-3 flex flex-wrap items-center gap-2 text-xs text-ink-500"><span>{words.applied}: {result.applied} · {words.pending}</span></div>
      <pre data-testid="final-resume-text" className="max-h-[65vh] overflow-y-auto whitespace-pre-wrap break-words rounded border border-paper-200 bg-paper-50 p-6 font-serif text-[15px] leading-relaxed text-ink-900">{result.text}</pre>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button variant="primary" disabled={working || outdated || stale || busy.resume} icon={<Download className="h-4 w-4" />} onClick={() => request('pdf')}>PDF</Button>
        <Button disabled={working || outdated || stale || busy.resume} icon={<Download className="h-4 w-4" />} onClick={() => request('docx')}>DOCX</Button>
        <Button variant="ghost" onClick={() => setResult(undefined)}>{words.close}</Button>
      </div>
    </div>}
  </section>
}
