import { useEffect, useRef, useState } from 'react'
import { useApp } from '../lib/store'

export default function PdfPreview({ blob, name, close }: { blob: Blob; name: string; close: () => void }) {
  const { t } = useApp()
  const dialog = useRef<HTMLDialogElement>(null)
  const [url, setUrl] = useState('')
  useEffect(() => {
    const source = URL.createObjectURL(blob)
    setUrl(source)
    const element = dialog.current!
    element.showModal()
    return () => { element.close(); URL.revokeObjectURL(source) }
  }, [blob])
  return <dialog ref={dialog} aria-label={t('project.preview')} className="pdf-reader" onCancel={close}>
    <header className="flex items-center justify-between gap-4 px-5 py-3">
      <strong className="truncate">{name}</strong><button autoFocus onClick={close}>{t('project.close')}</button>
    </header>
    {url && <iframe title={name} src={url + '#view=FitH&toolbar=1'} />}
  </dialog>
}
