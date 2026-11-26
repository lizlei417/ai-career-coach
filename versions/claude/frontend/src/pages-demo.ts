import { ApiError } from './api'
import strings from './demo-strings.json'
import type { Materials, Project, Lang, Status } from './types'

const original = 'Mapped visitor questions into topics and wrote a guide for a fictional museum exhibit.'
const requirement = 'Organize audience feedback and communicate findings to the exhibit team.'
export const sample = { resume: 'Demo Candidate · Fictional museum project\n' + original, jd: 'Audience Research Assistant\n' + requirement }
const status: Status = { configured: true, model: 'Demo Mode', connection: 'demo', guideFiles: [], guideCount: 0, warnings: [] }
const evidence = [{ source_id: 'R1', quote: original }]
const storageKey = 'claude.pages.fixture'
const emptyInterview = () => ({ question: null, question_number: 0, attempt: 1, guides: [], turns: [], feedback: null, ended: false, summary: null })
function newProject(materials: Materials): Project {
  if (materials.resume.trim() !== sample.resume || materials.jd.trim() !== sample.jd)
    throw new ApiError({en:'Load the fictional sample to try scripted results.', 'zh-CN':'请填入虚构示例材料，体验预设结果。', 'zh-TW':'請填入虛構範例材料，體驗預設結果。'},400)
  return { materials, context: {fingerprint:'museum-demo', resume:[{id:'R1',text:original}],jd:[{id:'J1',text:requirement}], requirements:[{id:'Q1',source_id:'J1',quote:requirement,category:'responsibility'}]}, optimization:null,matching:null,interview:emptyInterview(),decisions:{},version:1,status }
}
interface Action { kind:string; language:Lang; answer:string; id:string; choice:string; edit:string }
function act(p:Project,a:Action) {
  const iv=p.interview
  const pack = <T,>(data:T) => ({data, language:'en' as const, guides:[]})
  switch(a.kind) {
    case 'optimize':
      p.optimization=pack({revisions:[{id:'D1',title:'Audience research',requirement_ids:['Q1'],evidence,optimized:'Grouped visitor questions by topic and wrote an exhibit guide for a fictional museum.',reason:'Lead with the method and retain the original scope.'}],gaps:[]}); break
    case 'decision': p.decisions[a.id]={choice:a.choice,edit:a.edit || ''};break
    case 'match': p.matching=pack({matches:[{requirement_id:'Q1',status:'partial',evidence,assessment:'The sample describes organizing questions but does not mention sharing findings with the team.',gap_type:'unclear',suggestion:'Clarify who received the guide.',priority:'medium'}]});break
    case 'restart': p.interview=emptyInterview();break
    case 'question': case 'follow':
      iv.question={text:a.kind==='follow'?'What did visitors find difficult?':iv.question_number?'How did you choose what to include in the guide?':'How did you organize visitor questions?',kind:'behavioral',requirement_id:'Q1',evidence,guide_ids:[]}
      iv.question_number++;iv.attempt=1;iv.feedback=null;iv.questionLanguage='en';iv.feedbackLanguage=undefined;break
    case 'answer':
      if (!iv.question) break
      iv.feedback={guide_ids:[],strengths:[],missing_information:[],action:'Scripted practice tip: explain one decision and its outcome.',answer_quotes:[],follow_up:'What did visitors find difficult?'}
      iv.feedbackLanguage='en';iv.turns.push({question:iv.question,answer:a.answer,feedback:iv.feedback,attempt:iv.attempt});break
    case 'retry': iv.attempt++;iv.feedback=null;break
    case 'summary': iv.ended=true;iv.summary=pack({strengths:[],practice_priorities:['Practice describing one specific decision.'],next_steps:['Choose one example from the exhibit guide.']});break
  }
  p.version++
  return p
}
export function demoApi(path:string,method:string,body?:unknown):unknown {
  if(path==='bootstrap') return {strings:{...strings,demo:['Demo Mode','演示模式','演示模式']},status}
  if(path==='project' && method==='DELETE') {sessionStorage.removeItem(storageKey);return {}}
  if(path.startsWith('project') && ['POST','PUT'].includes(method)) {
    const p=newProject(body as Materials)
    sessionStorage.setItem(storageKey,JSON.stringify(p))
    return method==='POST'?{token:'fictional-museum',project:p}:p
  }
  if (path==='project'||path==='action') {
    const stored=sessionStorage.getItem(storageKey)
    if(!stored) throw new ApiError({},410)
    const p:Project=JSON.parse(stored)
    if(path==='action') {act(p,body as Action);sessionStorage.setItem(storageKey,JSON.stringify(p))}
    return p
  }
  throw new ApiError({en:'This action requires the local service. Paste text in the demo.', 'zh-CN':'此操作需要本地服务，演示版可粘贴文本。','zh-TW':'此操作需要本機服務，演示版可貼上文字。'},400)
}
