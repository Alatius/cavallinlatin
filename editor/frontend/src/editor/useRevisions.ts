import { useCallback, useEffect, useRef, useState } from 'react';

import { api, errorMessage } from '../api/client';
import type { RevisionContent, RevisionMeta } from '../api/types';

export interface UseRevisionsResult {
  list: RevisionMeta[] | null;
  loadingList: boolean;
  listError: string | null;
  /** Cached fetch — repeat calls for the same id reuse the resolved promise. */
  getContent(id: string): Promise<RevisionContent>;
}

export function useRevisions(urlId: string): UseRevisionsResult {
  const [list, setList] = useState<RevisionMeta[] | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  // Promise cache: same id → same in-flight or resolved promise. Lives in a
  // ref so the cache itself doesn't drive re-renders; consumers state-manage
  // the resolved RevisionContent on their own.
  const cacheRef = useRef<Map<string, Promise<RevisionContent>>>(new Map());

  useEffect(() => {
    let active = true;
    setLoadingList(true);
    setListError(null);
    setList(null);
    cacheRef.current = new Map();
    api.get<RevisionMeta[]>(`/entries/${urlId}/revisions`)
      .then((rows) => { if (active) setList(rows); })
      .catch((err) => {
        if (active) setListError(errorMessage(err));
      })
      .finally(() => { if (active) setLoadingList(false); });
    return () => { active = false; };
  }, [urlId]);

  const getContent = useCallback((id: string): Promise<RevisionContent> => {
    const hit = cacheRef.current.get(id);
    if (hit) return hit;
    const p = api.get<RevisionContent>(`/entries/${urlId}/revisions/${id}`)
      .catch((err) => {
        cacheRef.current.delete(id);
        throw err;
      });
    cacheRef.current.set(id, p);
    return p;
  }, [urlId]);

  return { list, loadingList, listError, getContent };
}
