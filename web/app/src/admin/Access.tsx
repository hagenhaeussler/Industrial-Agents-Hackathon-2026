import { LoaderCircle, ShieldCheck } from 'lucide-react';
import { useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError } from '../api/client';

export const adminAccessError = (error: unknown) => error instanceof ApiError && error.status === 403
  ? 'Access denied. Check the admin code and try again.'
  : 'Admin access could not be verified. Check your connection and try again.';

export function AdminAccess({ onUnlock, error }: { onUnlock: (code: string) => Promise<void>; error?: string | null }) {
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!code.trim() || busy) return;
    const entered = code.trim();
    setCode(''); setFailure(null); setBusy(true);
    try { await onUnlock(entered); } catch (reason) { setFailure(adminAccessError(reason)); }
    finally { setBusy(false); }
  };
  return <main className="desk-message"><form className="surface notice admin-access" onSubmit={event => void submit(event)} aria-labelledby="admin-access-title">
    <ShieldCheck size={28} aria-hidden="true"/>
    <h1 id="admin-access-title">Admin access</h1>
    <p>Enter the code supplied by the team to manage building changes.</p>
    <label htmlFor="admin-access-code">Admin code</label>
    <input id="admin-access-code" type="password" value={code} onChange={event => setCode(event.target.value)} autoComplete="off" spellCheck={false} maxLength={512} required autoFocus disabled={busy}/>
    {(failure || error) && <p role="alert">{failure || error}</p>}
    <button className="primary-button" type="submit" disabled={busy || !code.trim()}>{busy ? <><LoaderCircle className="spin" size={18}/>Checking access…</> : 'Unlock admin view'}</button>
    <p className="fineprint">Access stays in this browser tab. Closing the tab clears the saved code.</p>
  </form></main>;
}
