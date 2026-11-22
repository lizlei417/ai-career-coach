import { useEffect, useRef, useState } from 'react'
import { Check, Download, Eye, Pencil } from 'lucide-react'
import { apiFetch, ownerKey } from '../cloud'
import { useApp } from '../lib/store'
import { Button } from './ui'
import { errorKey } from '../lib/i18n'
import { confirmAction, ProductDialog } from '../ProductDialog'
import { registerResumeGuard } from '../lib/resume-navigation'
import { renderWordPreview } from '../lib/document-preview'

type Final = { text: string; applied: number; pending: number; manual?: boolean; version?: number }
export default function FinalResume() {
  const { s, t, project, flushSave, saveFinalResume, busy, setResumeDirty } = useApp()
  const [result, setResult] = useState<Final>()
  const [working, setWorking] = useState(false), [saving, setSaving] = useState(false)
  const [error, setError] = useState(''), [saved, setSaved] = useState(false)
  const [choose, setChoose] = useState(false), [editing, setEditing] = useState(false), [draft, setDraft] = useState('')
  const savingNow = useRef(false), preparingNow = useRef(false)
  const cacheKey = ownerKey('final-resume-draft.' + project.id)
  const latest = useRef({ editing, draft, result });latest.current = { editing, draft, result }
  const en = s.lang === 'en', tw = s.lang === 'zh-TW'
  const w = en ? {
    title: 'Complete resume', preview: 'Preview complete resume', edit: 'Edit', done: 'Done', hint: 'Your original stays unchanged. Accepted suggestions and saved edits form this complete resume.',
    failed: 'Could not save or prepare the document. Your draft is retained. Check the connection and retry.', pdf: 'PDF preview', word: 'Word (DOCX) preview', saved: 'Resume saved', manual: 'Using your saved complete resume. New AI suggestions do not overwrite it. Edit this version to apply further changes.',
    unsaved: 'Your complete resume has unsaved edits. Continue and keep a recovery draft on this device? Choose Cancel to finish saving first.', finish: 'Finish saving your edits before opening a file preview.', restore: 'Recovered an unfinished draft. Choose Done to save it to this project.', empty: 'The complete resume cannot be empty.',
  } : tw ? {
    title: '完整履歷', preview: '預覽完整履歷', edit: '編輯', done: '完成', hint: '保留原始履歷，整合已採納的建議與已儲存的編輯，形成完整履歷。',
    failed: '未能儲存或準備文件，草稿已保留，請檢查網絡後重試。', pdf: 'PDF 預覽', word: 'Word（DOCX）預覽', saved: '履歷已儲存', manual: '正在使用已儲存的完整履歷。新的 AI 建議不會覆蓋它，請編輯此版本套用後續修改。',
    unsaved: '完整履歷有尚未儲存的修改。是否繼續並在此裝置保留恢復草稿？選擇取消可先完成儲存。', finish: '請先完成儲存編輯，再預覽文件。', restore: '已恢復未完成的草稿，點擊完成可儲存至此專案。', empty: '完整履歷不能為空。',
  } : {
    title: '完整简历', preview: '预览完整简历', edit: '编辑', done: '完成', hint: '保留原始简历，整合已采纳的建议与已保存的编辑，形成完整简历。',
    failed: '无法保存或准备文件，草稿已保留，请检查网络后重试。', pdf: 'PDF 预览', word: 'Word（DOCX）预览', saved: '简历已保存', manual: '正在使用已保存的完整简历。新的 AI 建议不会覆盖它，请编辑此版本应用后续修改。',
    unsaved: '完整简历有尚未保存的修改。是否继续并在此设备保留恢复草稿？选择取消可先完成保存。', finish: '请先完成保存编辑，再预览文件。', restore: '已恢复未完成的草稿，点击完成可保存至当前项目。', empty: '完整简历不能为空。',
  }
  const current = JSON.stringify([s.resume, s.inputs, s.inputsKey, s.materials?.fingerprint, s.finalResume])
  async function readFinal() {
    await flushSave()
    const r = await apiFetch(`/api/workspaces/${encodeURIComponent(project.id)}/resume/final`)
    if (!r.ok) { const b = await r.json().catch(() => ({}));throw Error(b.error?.code ? t(errorKey(b.error.code)) : w.failed) }
    return await r.json() as Final
  }
  useEffect(() => {
    let active = true
    readFinal().then(value => { if (active) {setResult(value);setError('')} }).catch(e => { if (active && !latest.current.editing) setError(e.message?.startsWith('HTTP') ? w.failed : e.message) })
    return () => { active = false }
  }, [current])
  useEffect(() => {
    try { const value = localStorage.getItem(cacheKey);if (value !== null) { setDraft(value);setEditing(true);setError(w.restore) } } catch { /* storage may be disabled */ }
  }, [cacheKey])
  useEffect(() => registerResumeGuard(async () => {
    const v = latest.current
    if (!v.editing || v.draft === v.result?.text) return true
    return await confirmAction(w.unsaved)
  }), [w.unsaved])
  useEffect(() => {
    setResumeDirty(editing && draft !== result?.text)
    return () => setResumeDirty(false)
  }, [editing, draft, result?.text, setResumeDirty])
  function updateDraft(text: string) {
    setDraft(text);setSaved(false)
    try { localStorage.setItem(cacheKey, text) } catch { setError(en ? 'Recovery storage unavailable; save before leaving.' : tw ? '恢復儲存不可用，請先完成儲存再離開。' : '恢复存储不可用，请先完成保存再离开。') }
  }
  async function finish() {
    if (savingNow.current) return
    if (!draft.trim()) {setError(w.empty);return}
    savingNow.current = true;setSaving(true);setError('')
    try {
      await saveFinalResume(draft, result?.text || '')
      setResult({ text: draft, applied: result?.applied || 0, pending: 0, manual: true })
      setEditing(false);setSaved(true)
      try { localStorage.removeItem(cacheKey) } catch { /* saved on server */ }
    } catch { setError(w.failed) } finally { savingNow.current = false;setSaving(false) }
  }
  async function file(format: 'pdf' | 'docx', preview = true) {
    if (preparingNow.current) return
    if (editing) {setError(w.finish);setChoose(false);return}
    // Open synchronously within the click gesture, before network awaits.
    const win = preview ? window.open('', '_blank') : null
    if (preview && !win) {setError(en ? 'Allow pop-ups to preview this document.' : tw ? '請允許新分頁以預覽文件。' : '请允许新标签页以预览文件。');return}
    if (win) {win.opener = null;win.document.body.textContent = en ? 'Preparing document…' : tw ? '正在準備文件…' : '正在准备文件…'}
    preparingNow.current = true;setChoose(false);setWorking(true);setError('')
    try {
      await flushSave()
      const r = await apiFetch(`/api/workspaces/${encodeURIComponent(project.id)}/resume/export?format=${format}`)
      if (!r.ok) {const b = await r.json().catch(() => ({}));throw Error(b.error?.code ? t(errorKey(b.error.code)) : w.failed)}
      const blob = await r.blob(), name = project.name.replace(/[^\p{L}\p{N} _-]/gu, '').slice(0, 80) || 'Resume'
      if (preview && format === 'docx' && win) await renderWordPreview(win, blob, name, s.lang)
      else {
        const url = URL.createObjectURL(blob)
        if (win) {win.location.replace(url);setTimeout(() => URL.revokeObjectURL(url), 600000)}
        else {const a = document.createElement('a');a.href = url;a.download = `${name}.${format}`;a.click();setTimeout(() => URL.revokeObjectURL(url), 10000)}
      }
    } catch (e) {const message = e instanceof Error && !e.message.startsWith('HTTP') ? e.message : w.failed;setError(message);if (win && !win.closed) win.document.body.textContent = message}
    finally {preparingNow.current = false;setWorking(false)}
  }
  return <section className="rounded-lg border border-paper-200 bg-white p-5" aria-label={w.title}>
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0 flex-1"><h2 className="font-serif text-[20px] text-ink-900">{w.title}</h2><p className="mt-1 max-w-2xl text-[13px] leading-relaxed text-ink-500">{w.hint}</p></div>
      <div className="flex shrink-0 flex-col items-end gap-2">
        <Button icon={<Eye className="h-4 w-4" />} loading={working} disabled={saving || busy.resume || !result} onClick={() => editing ? setError(w.finish) : setChoose(true)}>{w.preview}</Button>
        <Button data-testid="edit-complete-resume" className="!w-[96px] !bg-[#111827] !text-white" variant="primary" icon={editing ? <Check className="h-4 w-4" /> : <Pencil className="h-4 w-4" />} loading={saving} disabled={working || busy.resume || !result} onClick={() => editing ? finish() : (setDraft(result!.text), setEditing(true), setSaved(false))}>{editing ? w.done : w.edit}</Button>
      </div>
    </div>
    {error && <p role="alert" className="mt-3 text-sm text-[#7A2E2E]">{error}</p>}
    {saved && <p role="status" className="mt-3 text-sm text-[#276749]">{w.saved}</p>}
    {result && <div className="mt-4">
      <p className="mb-3 text-xs leading-relaxed text-ink-500">{result.manual ? w.manual : `${en ? 'Applied changes' : tw ? '已套用修改' : '已应用修改'}: ${result.applied}`}</p>
      {editing ? <textarea aria-label={w.title} data-testid="final-resume-editor" value={draft} disabled={saving} onChange={e => updateDraft(e.target.value)} className="h-[65vh] w-full resize-none overflow-y-auto whitespace-pre-wrap break-words rounded border border-paper-300 bg-paper-50 p-6 font-serif text-[15px] leading-relaxed text-ink-900 focus:outline-none focus:ring-1 focus:ring-ink-500" /> : <pre data-testid="final-resume-text" className="h-[65vh] overflow-y-auto whitespace-pre-wrap break-words rounded border border-paper-200 bg-paper-50 p-6 font-serif text-[15px] leading-relaxed text-ink-900">{result.text}</pre>}
      <div className="mt-4 flex gap-2"><Button disabled={working || editing || busy.resume} icon={<Download className="h-4 w-4" />} onClick={() => file('pdf', false)}>PDF</Button><Button disabled={working || editing || busy.resume} icon={<Download className="h-4 w-4" />} onClick={() => file('docx', false)}>DOCX</Button></div>
    </div>}
    {choose && <ProductDialog title={w.preview} onClose={() => setChoose(false)}><div className="flex gap-3 py-5"><Button onClick={() => file('pdf')}>{w.pdf}</Button><Button onClick={() => file('docx')}>{w.word}</Button></div></ProductDialog>}
  </section>
}
