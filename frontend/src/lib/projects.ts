import { cloudJson, ownerKey } from '../cloud'
import type { Persisted } from './store'

export interface Project { id:string; name:string }
export interface SavedProject extends Project { state:Persisted; revision:number }

let clearing=false
const writes=new Set<Promise<number>>()
export function saveProject(project:SavedProject):Promise<number>{
  if(clearing)return Promise.reject(Error('Deleting workspace'))
  const write=cloudJson('/api/workspaces/'+encodeURIComponent(project.id),{
    method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(project)
  }).then(({revision})=>revision as number)
  writes.add(write)
  write.then(()=>writes.delete(write),()=>writes.delete(write))
  return write
}
export const readProject=(id:string):Promise<SavedProject>=>cloudJson('/api/workspaces/'+encodeURIComponent(id))
export const listProjects=():Promise<Project[]>=>cloudJson('/api/workspaces')
export const lastProject=()=>sessionStorage.getItem(ownerKey('active'))
export const rememberProject=(id:string)=>sessionStorage.setItem(ownerKey('active'),id)
export async function eraseProjects(){
  clearing=true
  try{
    await Promise.allSettled(Array.from(writes))
    const result=await cloudJson('/api/my-data',{method:'DELETE'})
    if((await listProjects()).length)throw Error('Deletion incomplete')
    sessionStorage.removeItem(ownerKey('active'))
    return result as {deletedProjects:number;deletedDocuments:number}
  }catch(e){clearing=false;throw e}
}
