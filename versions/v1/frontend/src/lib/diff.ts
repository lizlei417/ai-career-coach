// Token-level diff (LCS) used to highlight what a rewrite changed.
// CJK characters are individual tokens; Latin words stay whole.
const TOKEN_RE = /[\u3400-\u9fff\uf900-\ufaff]|[A-Za-z0-9+#.'’-]+|\s+|[^\sA-Za-z0-9\u3400-\u9fff]/g

export type DiffPart = { text: string; type: 'same' | 'add' | 'del' }

export function diffTokens(a: string, b: string): DiffPart[] {
  const A = a.match(TOKEN_RE) || []
  const B = b.match(TOKEN_RE) || []
  if (A.length * B.length > 250000) return [{ text: b, type: 'add' }]
  const n = A.length, m = B.length
  const dp: Uint16Array[] = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1))
  for (let i = n - 1; i >= 0; i--)
    for (let j = m - 1; j >= 0; j--)
      dp[i][j] = norm(A[i]) === norm(B[j]) ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1])
  const out: DiffPart[] = []
  const push = (text: string, type: DiffPart['type']) => {
    const last = out[out.length - 1]
    if (last && last.type === type) last.text += text
    else out.push({ text, type })
  }
  let i = 0, j = 0
  while (i < n && j < m) {
    if (norm(A[i]) === norm(B[j])) { push(B[j], 'same'); i++; j++ }
    else if (dp[i + 1][j] >= dp[i][j + 1]) { push(A[i], 'del'); i++ }
    else { push(B[j], 'add'); j++ }
  }
  while (i < n) push(A[i++], 'del')
  while (j < m) push(B[j++], 'add')
  return out
}

function norm(t: string) {
  return /^\s+$/.test(t) ? ' ' : t.toLowerCase()
}

// light client-side check for student edits: numbers not present in evidence
export function newNumbers(text: string, evidence: string): string[] {
  const nums = (s: string) => new Set((s.normalize('NFKC').match(/\d+(?:[.,]\d+)?%?/g) || []).map((x) => x.replace(/,/g, '')))
  const ev = nums(evidence)
  return [...nums(text)].filter((x) => !ev.has(x) && !ev.has(x.replace('%', '')))
}
