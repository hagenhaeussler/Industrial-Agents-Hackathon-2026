/** An explicitly entered admin code is kept for this tab only. */
const CODE_KEY = 'tyb.admin.access-code';

export function readAdminCode(): string | null {
  try { return sessionStorage.getItem(CODE_KEY); } catch { return null; }
}

export function rememberAdminCode(code: string): void {
  try { sessionStorage.setItem(CODE_KEY, code); } catch { /* access still works for this page */ }
}

export function forgetAdminCode(): void {
  try { sessionStorage.removeItem(CODE_KEY); } catch { /* storage can be unavailable */ }
}
