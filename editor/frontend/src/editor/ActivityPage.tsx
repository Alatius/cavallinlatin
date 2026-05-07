import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { api, ApiError } from '../api/client';
import type { ActivityItem } from '../api/types';
import { useStoredState } from '../components/useStoredState';

type Tab = 'comments' | 'edits';
const isTab = (s: string): Tab | undefined =>
  s === 'comments' || s === 'edits' ? s : undefined;

function formatDate(unix: number): string {
  return new Date(unix * 1000).toLocaleString('sv-SE', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  });
}

export default function ActivityPage() {
  const [tab, setTab] = useStoredState<Tab>('activityPage.tab', 'comments', isTab);
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    setItems([]);
    api.get<ActivityItem[]>(`/activity/${tab}`)
      .then((rows) => { if (active) setItems(rows); })
      .catch((err) => {
        if (active) setError(err instanceof ApiError ? err.message : String(err));
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [tab]);

  return (
    <div className="activity-page">
      <h1 className="activity-page__title">Senaste aktivitet</h1>
      <div className="activity-page__tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'comments'}
          className={
            'activity-page__tab'
            + (tab === 'comments' ? ' activity-page__tab--active' : '')
          }
          onClick={() => setTab('comments')}
        >
          Senast kommenterade
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'edits'}
          className={
            'activity-page__tab'
            + (tab === 'edits' ? ' activity-page__tab--active' : '')
          }
          onClick={() => setTab('edits')}
        >
          Senast redigerade
        </button>
      </div>
      {error && <div className="activity-page__error">{error}</div>}
      {loading && <p className="activity-page__empty">Laddar …</p>}
      {!loading && items.length === 0 && !error && (
        <p className="activity-page__empty">Inget att visa än.</p>
      )}
      <ul className="activity-page__list">
        {items.map((it) => (
          <li key={it.url_id} className="activity-page__item">
            <div className="activity-page__row">
              <Link
                to={`/editor/entry/${it.url_id}`}
                state={tab === 'comments' ? { openComments: true } : undefined}
                className="activity-page__headword"
              >
                {it.headword}
              </Link>
              <span className="activity-page__meta">
                {it.display_name && <span>{it.display_name}</span>}
                <span className="activity-page__time">{formatDate(it.at)}</span>
                {tab === 'comments' && it.count > 1 && (
                  <span className="activity-page__count">({it.count})</span>
                )}
                {tab === 'edits' && (
                  <span className="activity-page__count">
                    {it.count} {it.count === 1 ? 'revision' : 'revisioner'}
                  </span>
                )}
              </span>
            </div>
            {it.snippet && (
              <div className="activity-page__snippet">{it.snippet}</div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
