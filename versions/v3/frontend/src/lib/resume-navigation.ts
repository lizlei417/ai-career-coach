// One shared guard for existing routes, projects, AI actions and account logout.
let guard: (() => Promise<boolean>) | undefined
export function registerResumeGuard(next: () => Promise<boolean>) {
  guard = next
  return () => { if (guard === next) guard = undefined }
}
let pending: Promise<boolean> | undefined
export async function guardResumeNavigation() {
  if (!guard) return true
  if (!pending) pending = guard().finally(() => { pending = undefined })
  return pending
}
