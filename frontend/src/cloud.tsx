import { createClient, type SupabaseClient, type Session } from '@supabase/supabase-js'
import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import './cloud.css'

const base=import.meta.env.BASE_URL
let client: SupabaseClient
let owner=''
let appId=''
let setup: Promise<void> | undefined
let revision=0
export let savedState: any=null
let queued=Promise.resolve()
export const ownerKey=(name:string)=>appId+'.'+owner+'.'+name
export async function apiFetch(path:string, options:RequestInit={}) {
  const expected=owner
  const {data}=await client.auth.getSession()
  if (!expected || data.session?.user.id!==expected || owner!==expected) throw Error('Session changed')
  const headers=new Headers(options.headers)
  headers.set('Authorization','Bearer '+data.session.access_token)
  return fetch(base+path.replace(/^\//,''),{...options,headers,cache:'no-store'})
}
export async function cloudJson(path:string,options?:RequestInit){
  const res=await apiFetch(path,options)
  if(!res.ok) throw Error('HTTP '+res.status)
  return res.json()
}
let latestWrite=0
export function saveState(state:unknown) {
  const serial=++latestWrite
  const expected=owner
  const id=appId==='claude'?'draft':'workspace'
  queued=queued.catch(()=>{}).then(async()=>{
    if(owner!==expected) throw Error('Session changed')
    if(serial!==latestWrite)return
    const result=await cloudJson('/api/workspaces/'+id,{method:'PUT',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({state,revision,name:id})})
    revision=result.revision
    savedState=state
  })
  queued.catch(()=>window.dispatchEvent(new Event('save-error')))
  return queued
}
async function configure(){
  const r=await fetch(base+'auth-config',{cache:'no-store'})
  const config=await r.json()
  if(!config.url||!config.key) throw Error('Cloud configuration missing')
  appId=config.app
  client=createClient(config.url,config.key,{auth:{storageKey:'coach.auth.'+appId,detectSessionInUrl:false}})
}
const labels=[
 ['组员登录','邮箱','密码','登录','退出登录','修改密码','新密码','登录或服务验证失败','保存失败，请保留本页并核对网络。','账号','密码已更新'],
 ['組員登入','電郵','密碼','登入','登出','修改密碼','新密碼','登入或服務驗證失敗','儲存失敗，請保留此頁並檢查網絡。','帳戶','密碼已更新'],
 ['Member sign-in','Email','Password','Sign in','Sign out','Change password','New password','Sign-in or service verification failed','Save failed. Keep this tab open and check the connection.','Account','Password updated']
]
export function AuthGate({children}:{children:ReactNode}){
  const [ready,setReady]=useState(false),[signed,setSigned]=useState(false),[error,setError]=useState(false)
  const [menu,setMenu]=useState(false),[failed,setFailed]=useState(false),[updated,setUpdated]=useState(false)
  const [language,setLanguage]=useState(0),[email,setEmail]=useState(''),[busy,setBusy]=useState(false)
  const t=labels[language]
  useEffect(()=>{
    let live=true,sub:{unsubscribe():void}|undefined
    let seq=0
    const persistError=()=>setFailed(true)
    window.addEventListener('save-error',persistError)
    async function update(session:Session|null){
      const n=++seq
      if(!live)return
      if(owner && session?.user.id!==owner){ owner=''; location.reload();return }
      if(!session){setReady(true);setSigned(false);return}
      if(owner===session.user.id)return
      try{
        const res=await fetch(base+'api/me',{headers:{Authorization:'Bearer '+session.access_token},cache:'no-store'})
        if(!res.ok) throw Error('Unauthorized')
        const me=await res.json()
        if(!live||seq!==n)return
        if(me.id!==session.user.id)throw Error('Invalid identity')
        owner=me.id
        if(appId!=='codex_v2'){
          const snapshot=await apiFetch('/api/workspaces/'+(appId==='claude'?'draft':'workspace'))
          if(snapshot.ok){const data=await snapshot.json();savedState=data.state;revision=data.revision}
          else if(snapshot.status!==404)throw Error('Load failed')
        }
        if(live){setEmail(session.user.email||'');setSigned(true);setError(false)}
      }catch{if(live){owner='';setError(true);setSigned(false)}}
      if(live)setReady(true)
    }
    ;(setup ||= configure()).then(()=>{
      if(!live)return
      sub=client.auth.onAuthStateChange((_event,session)=>{setTimeout(()=>void update(session),0)}).data.subscription
    }).catch(()=>{if(live){setError(true);setReady(true)}})
    const observe=new MutationObserver(()=>setLanguage(document.documentElement.lang==='en'?2:document.documentElement.lang==='zh-TW'?1:0))
    observe.observe(document.documentElement,{attributes:true,attributeFilter:['lang']})
    return ()=>{live=false;sub?.unsubscribe();observe.disconnect();window.removeEventListener('save-error',persistError)}
  },[])
  async function submit(e:FormEvent<HTMLFormElement>){
    e.preventDefault();const form=e.currentTarget;const fields=new FormData(form)
    setBusy(true);setError(false);setUpdated(false)
    try{
      const password=String(fields.get('password'))
      const result=signed?await client.auth.updateUser({password}):await client.auth.signInWithPassword({email:String(fields.get('email')),password})
      if(result.error)throw result.error
      form.reset();if(signed)setUpdated(true)
    }catch{setError(true)} finally{setBusy(false)}
  }
  if(!ready)return <main className="account-wait">AI Career Coach …</main>
  if(!signed)return <main className="account-enter"><form onSubmit={submit}>
    <strong>AI Career Coach</strong><select aria-label="Language" value={language} onChange={e=>setLanguage(+e.target.value)}><option value={0}>简体中文</option><option value={1}>繁體中文</option><option value={2}>English</option></select>
    <h1>{t[0]}</h1><label>{t[1]}<input name="email" type="email" autoComplete="username" required/></label>
    <label>{t[2]}<input name="password" type="password" autoComplete="current-password" required/></label>
    <button disabled={busy}>{t[3]}</button>{error&&<p role="alert">{t[7]}</p>}</form></main>
  return <><div className="account-tools"><button aria-expanded={menu} onClick={()=>setMenu(!menu)}>{t[9]}</button>
    {menu&&<section><span>{email}</span><form onSubmit={submit}><label>{t[6]}<input name="password" type="password" autoComplete="new-password" minLength={8} required/></label><button disabled={busy}>{t[5]}</button></form>
    <button onClick={async()=>{try{await queued.catch(()=>{});const r=await client.auth.signOut({scope:'local'});if(r.error)throw r.error;owner='';location.reload()}catch{setError(true)}}}>{t[4]}</button>
    {error&&<p role="alert">{t[7]}</p>}{updated&&<p role="status">{t[10]}</p>}</section>}</div>
    {failed&&<p className="cloud-error" role="alert">{t[8]}</p>}{children}</>
}
