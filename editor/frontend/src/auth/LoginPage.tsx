import { FormEvent, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

import { ApiError } from '../api/client';
import { useAuth } from './AuthContext';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setPending(true);
    setError(null);
    try {
      await login(email, password);
      const dest = (location.state as { from?: { pathname: string } } | null)?.from?.pathname
        ?? '/editor';
      navigate(dest, { replace: true });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Inloggning misslyckades');
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="auth-page">
      <h1>Cavallins lexikon – redigerarinloggning</h1>
      <form onSubmit={onSubmit}>
        <label>
          E-post
          <input
            type="email" required autoComplete="username"
            value={email} onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label>
          Lösenord
          <input
            type="password" required autoComplete="current-password"
            value={password} onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error && <div className="error">{error}</div>}
        <button type="submit" disabled={pending}>Logga in</button>
      </form>
      <p className="auth-page__note">
        Vill du bli registrerad användare och hjälpa till att korrekturläsa och redigera
        lexikonet? Skicka ett mejl med en kort presentation till{' '}
        <a href="mailto:johan.winge@gmail.com">johan.winge@gmail.com</a>.
      </p>
      <p><Link to="/">Tillbaka till lexikonet</Link></p>
    </div>
  );
}
