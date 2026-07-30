import { useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';

import { api, errorMessage } from '../api/client';
import type { Entry, RevisionContent, RevisionMeta } from '../api/types';
import Breadcrumb from '../components/Breadcrumb';
import { formatDate } from '../components/formatDate';
import RevisionDiff from './RevisionDiff';
import RevisionTimeline from './RevisionTimeline';
import { useRevisions } from './useRevisions';

interface Pair {
  beforeId: string;
  afterId: string;
}

function defaultPair(list: RevisionMeta[]): Pair | null {
  if (list.length < 2) return null;
  return { beforeId: list[1].id, afterId: list[0].id };
}

function labelFor(rev: RevisionMeta): string {
  const t = formatDate(rev.saved_at);
  if (rev.is_current) return `${t} (nuvarande)`;
  return rev.saved_by ? `${t} av ${rev.saved_by}` : t;
}

export default function EntryHistory() {
  const { urlId = '' } = useParams<{ urlId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const { list, loadingList, listError, getContent } = useRevisions(urlId);

  const [entry, setEntry] = useState<Entry | null>(null);
  useEffect(() => {
    let active = true;
    api.get<Entry>(`/entries/${urlId}`)
      .then((e) => { if (active) setEntry(e); })
      .catch(() => { /* the revisions list error covers this case */ });
    return () => { active = false; };
  }, [urlId]);

  const [pair, setPair] = useState<Pair | null>(null);

  useEffect(() => {
    if (!list) return;
    const idx = (id: string) => list.findIndex((r) => r.id === id);
    const qBefore = searchParams.get('before');
    const qAfter = searchParams.get('after');
    if (qBefore && qAfter && qBefore !== qAfter) {
      const bi = idx(qBefore);
      const ai = idx(qAfter);
      if (bi !== -1 && ai !== -1 && bi > ai) {
        setPair({ beforeId: qBefore, afterId: qAfter });
        return;
      }
    }
    setPair(defaultPair(list));
  }, [list, searchParams]);

  useEffect(() => {
    if (!pair) return;
    const next = new URLSearchParams(searchParams);
    next.set('before', pair.beforeId);
    next.set('after', pair.afterId);
    if (
      next.get('before') !== searchParams.get('before')
      || next.get('after') !== searchParams.get('after')
    ) {
      setSearchParams(next, { replace: true });
    }
  }, [pair, searchParams, setSearchParams]);

  const [beforeRev, setBeforeRev] = useState<RevisionContent | null>(null);
  const [afterRev, setAfterRev] = useState<RevisionContent | null>(null);
  const [contentError, setContentError] = useState<string | null>(null);
  useEffect(() => {
    if (!pair) return;
    let active = true;
    setContentError(null);
    Promise.all([getContent(pair.beforeId), getContent(pair.afterId)])
      .then(([b, a]) => {
        if (!active) return;
        setBeforeRev(b);
        setAfterRev(a);
      })
      .catch((err) => {
        if (active) setContentError(errorMessage(err));
      });
    return () => { active = false; };
  }, [pair, getContent]);

  const beforeMeta = useMemo(
    () => list?.find((r) => r.id === pair?.beforeId) ?? null,
    [list, pair],
  );
  const afterMeta = useMemo(
    () => list?.find((r) => r.id === pair?.afterId) ?? null,
    [list, pair],
  );

  function handlePick(side: 'before' | 'after', id: string) {
    setPair((prev) => {
      if (!prev) return prev;
      return side === 'before'
        ? { ...prev, beforeId: id }
        : { ...prev, afterId: id };
    });
  }

  if (loadingList) {
    return <div className="loading">Laddar historik …</div>;
  }
  if (listError) {
    return <div className="entry-history__error">{listError}</div>;
  }
  if (!list) return null;

  const headTo = entry?.root_url_id ? `/editor/entry/${entry.root_url_id}` : null;
  const head = entry?.root_headword ?? null;
  const current = entry?.headword ?? urlId;

  // Match the displayed pair to the loaded content to avoid showing the
  // previous diff with the new selection's labels for one tick.
  const showDiff = pair && beforeRev?.id === pair.beforeId && afterRev?.id === pair.afterId
    && beforeMeta && afterMeta;

  return (
    <div className="entry-history">
      <div className="entry-history__toolbar">
        <Breadcrumb
          head={head}
          current={current}
          headTo={headTo}
          currentTo={`/editor/entry/${urlId}`}
        />
        <span className="entry-history__title">Historik</span>
        <div className="entry-history__spacer" />
        <Link to={`/editor/entry/${urlId}`} className="entry-history__back">
          ← Tillbaka till redigering
        </Link>
      </div>
      <div className="entry-history__body">
        <RevisionTimeline
          list={list}
          beforeId={pair?.beforeId ?? null}
          afterId={pair?.afterId ?? null}
          onPick={handlePick}
        />
        <div className="entry-history__diff">
          {list.length < 2 && (
            <div className="entry-history__empty">
              Endast en version finns – inget att jämföra ännu.
            </div>
          )}
          {list.length >= 2 && contentError && (
            <div className="entry-history__error">{contentError}</div>
          )}
          {list.length >= 2 && !contentError && showDiff && (
            <RevisionDiff
              beforeXml={beforeRev!.xml_body}
              afterXml={afterRev!.xml_body}
              beforeLabel={labelFor(beforeMeta!)}
              afterLabel={labelFor(afterMeta!)}
            />
          )}
          {list.length >= 2 && !contentError && !showDiff && (
            <div className="entry-history__loading">Laddar versioner …</div>
          )}
        </div>
      </div>
    </div>
  );
}
