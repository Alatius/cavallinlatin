import { FormEvent, useEffect, useMemo, useState, type ReactNode } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';

import { api, ApiError } from '../api/client';
import type { SearchHit, SearchResults } from '../api/types';
import { fold } from '../components/HeadwordsContext';
import { plural } from '../components/plural';

// Markers wrapped around each match by the backend's snippet() call. Both
// chars are non-printable controls that never appear in legitimate text, so
// splitting on them won't split real content.
const MARK_OPEN = '\u0001';
const MARK_CLOSE = '\u0002';
const TOKEN_RE = /[\p{L}\p{N}]+/gu;

// FTS5's tokenizer (`remove_diacritics 2`) treats Swedish ä/ö/å as plain
// a/o, so a search for 'kara' matches 'kära' and the snippet marks it.
// Our `fold()` is stricter, so callers re-check each marked chunk and
// emit the spurious ones as plain text.
type Chunk = { mark: boolean; text: string };

function* parseSnippet(s: string): Generator<Chunk> {
  let i = 0;
  while (i < s.length) {
    const open = s.indexOf(MARK_OPEN, i);
    if (open < 0) { yield { mark: false, text: s.slice(i) }; return; }
    if (open > i) yield { mark: false, text: s.slice(i, open) };
    const close = s.indexOf(MARK_CLOSE, open + 1);
    if (close < 0) { yield { mark: false, text: s.slice(open + 1) }; return; }
    yield { mark: true, text: s.slice(open + 1, close) };
    i = close + 1;
  }
}

function isStrictPrefix(fragment: string, queryWords: string[]): boolean {
  const f = fold(fragment);
  return queryWords.some((w) => f.startsWith(w));
}

function isRealHit(hit: SearchHit, queryWords: string[]): boolean {
  if (queryWords.length === 0) return true;
  // FTS5 may match in the headword field even if no marked fragment shows
  // up in the plaintext snippet, so check headword tokens too.
  const headTokens = fold(hit.headword).match(TOKEN_RE) ?? [];
  if (headTokens.some((t) => isStrictPrefix(t, queryWords))) return true;
  for (const c of parseSnippet(hit.snippet)) {
    if (c.mark && isStrictPrefix(c.text, queryWords)) return true;
  }
  return false;
}

// Render the snippet as JSX so no HTML flows through innerHTML; spurious
// marks (failing the strict fold check) become plain text — context stays
// readable but isn't falsely highlighted.
function renderSnippet(s: string, queryWords: string[]): ReactNode[] {
  const out: ReactNode[] = [];
  let key = 0;
  for (const c of parseSnippet(s)) {
    if (c.mark && queryWords.length > 0 && isStrictPrefix(c.text, queryWords)) {
      out.push(<mark key={key++}>{c.text}</mark>);
    } else {
      out.push(c.text);
    }
  }
  return out;
}

export default function SearchPage() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
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

  async function onLookup() {
    const term = input.trim();
    if (!term) return;
    try {
      const hit = await api.get<{ url_id: string }>(`/lookup?q=${encodeURIComponent(term)}`);
      navigate(`/entry/${hit.url_id}`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        // No exact headword match — fall through to full-text search and
        // flag the miss so the user sees an explanation instead of a
        // silent mode switch. The flag drops off automatically when they
        // submit a fresh search via onSubmit (setParams replaces all).
        setParams({ q: term, miss: '1' });
      } else {
        throw e;
      }
    }
  }

  const lookupMissed = params.get('miss') === '1';

  const queryWords = useMemo(
    () => (fold(q).match(TOKEN_RE) ?? []),
    [q],
  );
  const realHits = useMemo(
    () => data ? data.items.filter((h) => isRealHit(h, queryWords)) : [],
    [data, queryWords],
  );

  return (
    <div className="search-page">
      <form className="search-page__form" onSubmit={onSubmit}>
        <input
          type="search" value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Sök i texten …"
        />
        <button type="button" onClick={onLookup}>Slå upp</button>
        <button type="submit">Sök i texten</button>
      </form>
      {data && (
        <>
          {lookupMissed && (
            <p className="search-page__notice">
              Inget uppslagsord matchar &rdquo;{data.query}&rdquo;. Visar textträffar:
            </p>
          )}
          <p className="search-page__meta">
            {realHits.length} {plural(realHits.length, 'träff', 'träffar')} för &rdquo;{data.query}&rdquo;
          </p>
          <ul className="search-page__results">
            {realHits.map((hit) => (
              <li key={hit.url_id}>
                <Link to={`/entry/${hit.url_id}`}>
                  <strong>{hit.headword}</strong>
                </Link>
                <span className="search-page__snippet">{renderSnippet(hit.snippet, queryWords)}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
