import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { api, ApiError } from '../api/client';

export default function HomePage() {
  const navigate = useNavigate();
  const [q, setQ] = useState('');

  async function onLookup(e: FormEvent) {
    e.preventDefault();
    const term = q.trim();
    if (!term) return;
    try {
      const hit = await api.get<{ url_id: string }>(`/lookup?q=${encodeURIComponent(term)}`);
      navigate(`/entry/${hit.url_id}`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        // Flag the navigation so SearchPage can show the user that we
        // fell back from a failed lookup, instead of silently swapping
        // modes mid-action.
        navigate(`/search?q=${encodeURIComponent(term)}&miss=1`);
      } else {
        throw e;
      }
    }
  }

  function onFullText() {
    const term = q.trim();
    if (!term) return;
    navigate(`/search?q=${encodeURIComponent(term)}`);
  }

  return (
    <div className="app-home">
      <p>
        Digitaliserad utgåva av <em>Latinskt lexicon</em> av Christian Cavallin (1873).
      </p>
      <form className="app-home__lookup" onSubmit={onLookup}>
        <input
          type="search" autoFocus value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Slå upp eller sök …"
        />
        <button type="submit">Slå upp</button>
        <button type="button" onClick={onFullText}>Sök i texten</button>
      </form>
      <p className="app-home__hint hide-on-mobile">
        Eller välj ett uppslagsord från listan till vänster.
      </p>
    </div>
  );
}
