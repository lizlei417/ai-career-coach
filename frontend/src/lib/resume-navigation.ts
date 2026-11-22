// One shared guard for existing routes, projects, AI actions and account logout.
let guard: (() => Promise<boolean>) | undefined
export function registerResumeGuard(next: () => Promise<boolean>) {
  guard = next
  return () => { if (guard === next) guard = undefined }
}
export async function guardResumeNavigation() { return guard ? guard() : true }
