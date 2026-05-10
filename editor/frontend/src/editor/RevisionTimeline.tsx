import type { RevisionMeta } from '../api/types';
import { STATUS_LABEL_SV } from '../api/types';
import { formatDate } from '../components/formatDate';

interface Props {
  list: RevisionMeta[];
  beforeId: string | null;
  afterId: string | null;
  onPick(side: 'before' | 'after', id: string): void;
}

export default function RevisionTimeline({ list, beforeId, afterId, onPick }: Props) {
  // List is newest-first (index 0 = newest, index N-1 = oldest), so a row's
  // "Efter" radio is only legal when it sits *above* the current "Före"
  // selection (smaller index = newer), and "Före" only when it sits *below*
  // the current "Efter" (larger index = older). Disabling rather than
  // auto-swapping keeps the constraint visible — illegal radios are hidden
  // via CSS so the legal range reads as the contiguous run that still has
  // visible inputs.
  const beforeIdx = beforeId === null ? -1 : list.findIndex((r) => r.id === beforeId);
  const afterIdx = afterId === null ? -1 : list.findIndex((r) => r.id === afterId);

  return (
    <div className="revision-timeline">
      <div className="revision-timeline__head">
        <span className="revision-timeline__head-radio">Före</span>
        <span className="revision-timeline__head-radio">Efter</span>
        <span className="revision-timeline__head-label">Version</span>
      </div>
      <ul className="revision-timeline__list">
        {list.map((rev, i) => {
          const isBefore = rev.id === beforeId;
          const isAfter = rev.id === afterId;
          const beforeDisabled = (afterIdx !== -1 && i <= afterIdx) && !isBefore;
          const afterDisabled = (beforeIdx !== -1 && i >= beforeIdx) && !isAfter;
          const time = formatDate(rev.saved_at);
          const author = rev.saved_by;
          return (
            <li
              key={rev.id}
              className={
                'revision-timeline__row'
                + (isBefore ? ' revision-timeline__row--before' : '')
                + (isAfter ? ' revision-timeline__row--after' : '')
              }
            >
              <input
                type="radio"
                name="revision-before"
                aria-label={`Välj som före: ${time}`}
                checked={isBefore}
                disabled={beforeDisabled}
                onChange={() => onPick('before', rev.id)}
              />
              <input
                type="radio"
                name="revision-after"
                aria-label={`Välj som efter: ${time}`}
                checked={isAfter}
                disabled={afterDisabled}
                onChange={() => onPick('after', rev.id)}
              />
              <div className="revision-timeline__meta">
                <div className="revision-timeline__line revision-timeline__line--primary">
                  <span className="revision-timeline__label">{time}</span>
                </div>
                <div className="revision-timeline__line revision-timeline__line--secondary">
                  <span
                    className={`status-badge status-badge--${rev.status}`}
                    title={STATUS_LABEL_SV[rev.status]}
                  >
                    {STATUS_LABEL_SV[rev.status]}
                  </span>
                  {author !== null && (
                    <span className="revision-timeline__author">{author}</span>
                  )}
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
