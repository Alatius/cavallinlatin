import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { api, ApiError } from '../api/client';

export default function HomePage() {
  const navigate = useNavigate();
  const [q, setQ] = useState('');

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const term = q.trim();
    if (!term) return;
    try {
      const hit = await api.get<{ url_id: string }>(`/lookup?q=${encodeURIComponent(term)}`);
      navigate(`/entry/${hit.url_id}`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        navigate(`/search?q=${encodeURIComponent(term)}`);
      }
    }
  }

  return (
    <div className="app-home">
      <p>
        Digitaliserad utgåva av <em>Latinskt lexicon</em> av Christian Cavallin (1873).
      </p>
      <form className="app-home__lookup" onSubmit={onSubmit}>
        <input
          type="search" autoFocus value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Slå upp ett ord …"
        />
        <button type="submit">Sök</button>
      </form>
      <p className="app-home__hint">
        Eller välj ett uppslagsord från listan till vänster.
      </p>
    </div>
  );
}
