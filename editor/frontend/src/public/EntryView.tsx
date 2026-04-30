import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';

import { api, ApiError } from '../api/client';
import type { Entry } from '../api/types';
import type { ColumnHighlight } from '../components/ColumnImagePanel';
import { readEntryNavState } from '../components/entryNavState';
import EntryHtml from '../components/EntryHtml';
import EntryShell from '../components/EntryShell';

export default function EntryView() {
  const { urlId = '' } = useParams<{ urlId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { targetY, clickY, targetColumn } = readEntryNavState(location.state);
  const [entry, setEntry] = useState<Entry | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [highlight, setHighlight] = useState<ColumnHighlight | null>(null);

  useEffect(() => {
    let active = true;
    setEntry(null);
    setError(null);
    setHighlight(null);
    api.get<Entry>(`/entries/${urlId}`)
      .then((e) => { if (active) setEntry(e); })
      .catch((e) => {
        if (active) setError(e instanceof ApiError ? e.message : String(e));
      });
    return () => { active = false; };
  }, [urlId]);

  if (error) return (
    <div className="entry-view--error">
      <p>{error}</p>
      <p><Link to="/">Tillbaka till förstasidan</Link></p>
    </div>
  );
  if (!entry) return <div className="loading">Laddar …</div>;

  return (
    <EntryShell
      toolbar={<h2 className="entry-view__headword">{entry.headword}</h2>}
      initialColumn={entry.starting_column}
      highlight={highlight}
      onNavigate={(id, col, y, cy) => navigate(`/entry/${id}`, { state: { targetColumn: col, targetY: y, clickY: cy } })}
    >
      <div className="entry-view__content">
        <EntryHtml xml={entry.xml_body}
                   initialColumn={entry.starting_column}
                   onHighlight={setHighlight}
                   autoHighlightKey={entry.url_id === urlId ? location.key : undefined}
                   autoHighlightY={targetY}
                   autoHighlightColumn={targetColumn}
                   autoHighlightViewportY={clickY}
                   variant="public" />
      </div>
    </EntryShell>
  );
}
