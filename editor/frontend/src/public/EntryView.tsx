import { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';

import { api, ApiError } from '../api/client';
import type { EntryGroup, EntryGroupItem } from '../api/types';
import Breadcrumb from '../components/Breadcrumb';
import type { ColumnHighlight } from '../components/ColumnImagePanel';
import { readEntryNavState } from '../components/entryNavState';
import EntryHtml, { findScrollableAncestor, scrollAncestorToViewportY } from '../components/EntryHtml';
import EntryShell from '../components/EntryShell';

export default function EntryView() {
  const { urlId = '' } = useParams<{ urlId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { targetY, clickY, targetColumn } = readEntryNavState(location.state);
  const [group, setGroup] = useState<EntryGroup | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [highlight, setHighlight] = useState<ColumnHighlight | null>(null);

  const memberRefs = useRef<Map<string, HTMLElement>>(new Map());

  useEffect(() => {
    let active = true;
    setGroup(null);
    setError(null);
    setHighlight(null);
    api.get<EntryGroup>(`/entries/${urlId}/group`)
      .then((g) => { if (active) setGroup(g); })
      .catch((e) => {
        if (active) setError(e instanceof ApiError ? e.message : String(e));
      });
    return () => { active = false; };
  }, [urlId]);

  // Align the focus member's top with the scroll container's content-box
  // top, so a primary focus lands at scrollTop = 0 and any subentry lands
  // at the same visual offset. We use scrollAncestorToViewportY rather than
  // scrollIntoView because the latter walks every scrollable ancestor
  // including overflow: hidden ones, which shifts the toolbar inside
  // .entry-shell__text. Re-runs when focus_url_id changes (clicking a
  // sibling in the IndexPanel re-fetches the same group with a new focus).
  useEffect(() => {
    if (!group) return;
    const el = memberRefs.current.get(group.focus_url_id);
    if (!el) return;
    const container = findScrollableAncestor(el);
    if (!container) return;
    const paddingTop = parseFloat(getComputedStyle(container).paddingTop) || 0;
    scrollAncestorToViewportY(el, container.getBoundingClientRect().top + paddingTop);
  }, [group]);

  if (error) return (
    <div className="entry-view--error">
      <p>{error}</p>
      <p><Link to="/">Tillbaka till förstasidan</Link></p>
    </div>
  );
  if (!group) return <div className="loading">Laddar …</div>;

  const focus: EntryGroupItem =
    group.items.find((i) => i.url_id === group.focus_url_id) ?? group.items[0];
  const head: EntryGroupItem | null =
    group.head_url_id !== null
      ? group.items.find((i) => i.url_id === group.head_url_id) ?? null
      : null;

  return (
    <EntryShell
      toolbar={<Breadcrumb head={head?.headword ?? null} current={focus.headword} />}
      initialColumn={focus.starting_column}
      highlight={highlight}
      onNavigate={(id, col, y, cy) => navigate(`/entry/${id}`, { state: { targetColumn: col, targetY: y, clickY: cy } })}
    >
      <div className="entry-view__content">
        {group.items.map((m) => {
          const isFocus = m.url_id === group.focus_url_id;
          // Only auto-highlight inside the focus member, and only when the
          // URL still matches the group's focus (avoids running against a
          // stale group that's about to be replaced).
          const autoKey = isFocus && m.url_id === urlId ? location.key : undefined;
          return (
            <section
              key={m.url_id}
              ref={(el) => {
                if (el) memberRefs.current.set(m.url_id, el);
                else memberRefs.current.delete(m.url_id);
              }}
              className="entry-group__member"
              data-url-id={m.url_id}
            >
              <EntryHtml xml={m.xml_body}
                         initialColumn={m.starting_column}
                         onHighlight={setHighlight}
                         autoHighlightKey={autoKey}
                         autoHighlightY={isFocus ? targetY : undefined}
                         autoHighlightColumn={isFocus ? targetColumn : undefined}
                         autoHighlightViewportY={isFocus ? clickY : undefined}
                         variant="public" />
            </section>
          );
        })}
        <div className="entry-view__bottom-spacer" aria-hidden="true" />
      </div>
    </EntryShell>
  );
}
