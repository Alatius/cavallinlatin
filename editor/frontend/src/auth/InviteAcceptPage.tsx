import { FormEvent, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { api, ApiError } from '../api/client';
import type { InviteInfo, User } from '../api/types';
import { useAuth } from './AuthContext';

export default function InviteAcceptPage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { refresh } = useAuth();

  const [info, setInfo] = useState<InviteInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (!token) return;
    api.get<InviteInfo>(`/auth/invite/${token}`)
      .then((i) => {
        setInfo(i);
        if (i.display_name) setDisplayName(i.display_name);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : 'Ogiltig inbjudan'));
  }, [token]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setPending(true);
    setError(null);
    try {
      await api.post<User>(`/auth/invite/${token}`, {
        password, display_name: displayName,
      });
      await refresh();
      navigate('/editor', { replace: true });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Kunde inte spara');
    } finally {
      setPending(false);
    }
  }

  if (error && !info) return <div className="auth-page"><h1>Inbjudan</h1><div className="error">{error}</div></div>;
  if (!info) return <div className="auth-page">Laddar …</div>;

  return (
    <div className="auth-page">
      <h1>Acceptera inbjudan</h1>
      <p>Välkommen. Sätt ett lösenord för {info.email ?? 'ditt konto'}.</p>
      <form onSubmit={onSubmit}>
        <label>
          Namn
          <input
            type="text" required value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
          />
        </label>
        <label>
          Lösenord (minst 8 tecken)
          <input
            type="password" required minLength={8} value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error && <div className="error">{error}</div>}
        <button type="submit" disabled={pending}>Spara och logga in</button>
      </form>
    </div>
  );
}
