import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { fold, useHeadwords, type FoldedEntry } from '../components/HeadwordsContext';
import { useDebounce } from '../components/useDebounce';

interface Hit {
  entry: FoldedEntry;
  display: string;
  isAlt: boolean;
}

const MAX_RESULTS = 40;

interface Props {
  basePath: string;
}

// Mobile-only search affordance shown above the entry view: a permanent
// input that, when focused, drops a result list below it. Reuses the same
// folding/prefix-match logic as IndexPanel; we avoid pulling in IndexPanel
// itself because its Virtuoso layout doesn't fit a dropdown.
export default function MobileSearchBar({ basePath }: Props) {
  const { items: all, loaded, error } = useHeadwords();
  const [q, setQ] = useState('');
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const wrapRef = useRef<HTMLDivElement>(null);

  const qDebounced = useDebounce(q, 120);
  const qFold = useMemo(() => fold(qDebounced.trim()), [qDebounced]);
  const hasQuery = qFold.length > 0;

  const hits: Hit[] = useMemo(() => {
    if (!hasQuery) return [];
    const cap = MAX_RESULTS + 1;
    const out: Hit[] = [];
    outer: for (const e of all) {
      if (e.fold.startsWith(qFold)) {
        out.push({ entry: e, display: e.headword, isAlt: false });
        if (out.length >= cap) break;
      }
      for (let i = 0; i < e.alt_folds.length; i += 1) {
        if (e.alt_folds[i].startsWith(qFold)) {
          out.push({ entry: e, display: e.alt_headwords[i], isAlt: true });
          if (out.length >= cap) break outer;
        }
      }
    }
    return out;
  }, [all, qFold, hasQuery]);

  // Close the dropdown when focus or pointer leaves the bar.
  useEffect(() => {
    if (!open) return;
    function onDocPointer(e: PointerEvent) {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('pointerdown', onDocPointer);
    return () => document.removeEventListener('pointerdown', onDocPointer);
  }, [open]);

  function onPick(urlId: string) {
    setOpen(false);
    setQ('');
    navigate(`${basePath}/${urlId}`);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && hits.length > 0) {
      e.preventDefault();
      onPick(hits[0].entry.url_id);
    } else if (e.key === 'Escape') {
      setOpen(false);
      (e.target as HTMLInputElement).blur();
    }
  }

  const showDropdown = open && hasQuery;
  const shown = hits.slice(0, MAX_RESULTS);
  const overflow = hits.length > MAX_RESULTS;

  return (
    <div className="mobile-search" ref={wrapRef}>
      <input
        type="search"
        className="mobile-search__input"
        placeholder={
          error ? 'Registret kunde inte laddas'
            : loaded ? 'Sök uppslagsord …' : 'Laddar …'
        }
        value={q}
        onChange={(e) => { setQ(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        autoComplete="off"
        aria-autocomplete="list"
        aria-expanded={showDropdown}
      />
      {showDropdown && (
        <ul className="dropdown-menu mobile-search__results" role="listbox">
          {shown.length === 0 && (
            // Distinguish a failed index fetch from a genuine miss, so a
            // network error doesn't masquerade as "no such headword".
            <li className="mobile-search__empty">
              {error ? `Kunde inte ladda registret: ${error}` : 'Inga träffar'}
            </li>
          )}
          {shown.map((h, i) => (
            <li
              key={`${h.entry.url_id}:${h.isAlt ? 'a' + i : 'p'}`}
              className={
                'mobile-search__item' +
                (h.isAlt ? ' mobile-search__item--alt' : '')
              }
            >
              <Link
                to={`${basePath}/${h.entry.url_id}`}
                onClick={() => onPick(h.entry.url_id)}
              >
                {h.display}
              </Link>
            </li>
          ))}
          {overflow && (
            <li className="mobile-search__overflow">
              … fler träffar – förfina sökningen
            </li>
          )}
        </ul>
      )}
    </div>
  );
}
