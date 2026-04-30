import { FormEvent, useEffect, useState, type ReactNode } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { api } from '../api/client';
import type { SearchResults } from '../api/types';

// Markers wrapped around each match by the backend's snippet() call. Both
// chars are non-printable controls that never appear in legitimate text, so
// splitting on them won't split real content.
const MARK_OPEN = '\u0001';
const MARK_CLOSE = '\u0002';

// Render a marked snippet as JSX so no HTML ever flows through innerHTML;
// any stray chars from the source plaintext are inserted as text nodes,
// which the browser doesn't try to parse.
function renderSnippet(s: string): ReactNode[] {
  const out: ReactNode[] = [];
  let i = 0;
  let key = 0;
  while (i < s.length) {
    const open = s.indexOf(MARK_OPEN, i);
    if (open < 0) { out.push(s.slice(i)); break; }
    if (open > i) out.push(s.slice(i, open));
    const close = s.indexOf(MARK_CLOSE, open + 1);
    if (close < 0) { out.push(s.slice(open + 1)); break; }
    out.push(<mark key={key++}>{s.slice(open + 1, close)}</mark>);
    i = close + 1;
  }
  return out;
}

export default function SearchPage() {
  const [params, setParams] = useSearchParams();
  const q = params.get('q') ?? '';
  const [input, setInput] = useState(q);
  const [data, setData] = useState<SearchResults | null>(null);

  useEffect(() => {
    setInput(q);
    if (!q) { setData(null); return; }
    api.get<SearchResults>(`/search?q=${encodeURIComponent(q)}`).then(setData);
  }, [q]);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setParams({ q: input });
  }

  return (
    <div className="search-page">
      <form className="search-page__form" onSubmit={onSubmit}>
        <input
          type="search" value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Sök …"
        />
        <button type="submit">Sök</button>
      </form>
      {data && (
        <>
          <p className="search-page__meta">{data.total} träffar för &laquo;{data.query}&raquo;</p>
          <ul className="search-page__results">
            {data.items.map((hit) => (
              <li key={hit.url_id}>
                <Link to={`/entry/${hit.url_id}`}>
                  <strong>{hit.headword}</strong>
                </Link>
                <span className="search-page__snippet">{renderSnippet(hit.snippet)}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
