import { useState } from 'react'
import { createRoot } from 'react-dom/client'
import { ProductDialog } from '../ProductDialog'
import { translate } from './i18n'
import type { Inputs } from './store'
import type { Lang } from './types'

export type CareerProfile = { lang: Lang; userStage: NonNullable<Inputs['userStage']>; jobGoal: NonNullable<Inputs['jobGoal']> }

export function requestCareerProfile(lang: Lang, inputs: Inputs): Promise<CareerProfile | null> {
  return new Promise(resolve => {
    const node = document.createElement('div')
    document.body.append(node)
    const root = createRoot(node)
    const finish = (value: CareerProfile | null) => { root.unmount(); node.remove(); resolve(value) }
    root.render(<ProfileForm lang={lang} inputs={inputs} finish={finish} />)
  })
}

function ProfileForm({ lang, inputs, finish }: { lang: Lang; inputs: Inputs; finish: (value: CareerProfile | null) => void }) {
  const [language, setLanguage] = useState(lang)
  const [stage, setStage] = useState(inputs.userStage || '')
  const [goal, setGoal] = useState(inputs.jobGoal || '')
  const t = (key: Parameters<typeof translate>[1]) => translate(language, key)
  const words = language === 'en' ? ['Confirm coaching preferences', 'Confirm the language shown below and complete the missing choices. Your materials stay unchanged.', 'Confirm and continue', 'Cancel']
    : language === 'zh-TW' ? ['確認求職選項', '請確認目前語言並補齊選項。你的履歷和 JD 會保留。', '確認並繼續', '取消']
      : ['确认求职选项', '请确认当前语言并补齐选项。你的简历和 JD 会保留。', '确认并继续', '取消']
  return <ProductDialog title={words[0]} onClose={() => finish(null)}>
    <form onSubmit={e => { e.preventDefault(); if (stage && goal) finish({ lang: language, userStage: stage as CareerProfile['userStage'], jobGoal: goal as CareerProfile['jobGoal'] }) }}>
      <p className="mb-4 text-sm text-ink-600">{words[1]}</p>
      <div className="space-y-4">
        <label className="block text-sm">简体中文 · 繁體中文 · English
          <select autoFocus id="analysis-language" className="field mt-1 h-10" value={language} onChange={e => setLanguage(e.target.value as Lang)}>
            <option value="zh-CN">简体中文</option><option value="zh-TW">繁體中文</option><option value="en">English</option>
          </select>
        </label>
        <label className="block text-sm">{t('profile.stage')}
          <select id="analysis-stage" required className="field mt-1 h-10" value={stage} onChange={e => setStage(e.target.value as typeof stage)}>
            <option value="">{t('profile.select')}</option><option value="no_experience">{t('profile.noExperience')}</option><option value="current_student">{t('profile.student')}</option><option value="recent_graduate">{t('profile.graduate')}</option>
          </select>
        </label>
        <label className="block text-sm">{t('profile.goal')}
          <select id="analysis-goal" required className="field mt-1 h-10" value={goal} onChange={e => setGoal(e.target.value as typeof goal)}>
            <option value="">{t('profile.select')}</option><option value="internship">{t('profile.internship')}</option><option value="job">{t('profile.job')}</option>
          </select>
        </label>
      </div>
      <footer><button type="button" onClick={() => finish(null)}>{words[3]}</button><button type="submit" className="dialog-primary" disabled={!stage || !goal}>{words[2]}</button></footer>
    </form>
  </ProductDialog>
}
