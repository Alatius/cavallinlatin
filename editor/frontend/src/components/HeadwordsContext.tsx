import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';

import { api } from '../api/client';
import type { EntrySummary } from '../api/types';

export interface FoldedEntry extends EntrySummary {
  fold: string;        // primary headword folded
  alt_folds: string[]; // same length as alt_headwords
}

export function fold(s: string): string {
  return s.normalize('NFKD').replace(/\p{M}/gu, '').toLowerCase();
}

interface HeadwordsContextValue {
  items: FoldedEntry[];
  loaded: boolean;
  patch: (urlId: string, changes: Partial<EntrySummary>) => void;
}

const Ctx = createContext<HeadwordsContextValue | null>(null);

function enrich(it: EntrySummary): FoldedEntry {
  return {
    ...it,
    fold: fold(it.headword),
    alt_folds: (it.alt_headwords ?? []).map(fold),
  };
}

const altsEqual = (a: readonly string[], b: readonly string[]): boolean =>
  a.length === b.length && a.every((v, i) => v === b[i]);

export function HeadwordsProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<FoldedEntry[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;
    api.get<EntrySummary[]>('/headwords').then((raw) => {
      if (!active) return;
      setItems(raw.map(enrich));
      setLoaded(true);
    });
    return () => { active = false; };
  }, []);

  const patch = useCallback((urlId: string, changes: Partial<EntrySummary>) => {
    setItems((prev) => {
      let changed = false;
      const next = prev.map((it) => {
        if (it.url_id !== urlId) return it;
        const headwordDiff = changes.headword !== undefined && changes.headword !== it.headword;
        const statusDiff = changes.status !== undefined && changes.status !== it.status;
        const typeDiff = changes.type !== undefined && changes.type !== it.type;
        const altDiff = changes.alt_headwords !== undefined
          && !altsEqual(changes.alt_headwords, it.alt_headwords);
        const commentDiff = changes.comment_count !== undefined
          && changes.comment_count !== it.comment_count;
        if (!headwordDiff && !statusDiff && !typeDiff && !altDiff && !commentDiff) return it;
        changed = true;
        return {
          ...it,
          ...changes,
          fold: headwordDiff ? fold(changes.headword!) : it.fold,
          alt_folds: altDiff ? changes.alt_headwords!.map(fold) : it.alt_folds,
        };
      });
      return changed ? next : prev;
    });
  }, []);

  return <Ctx.Provider value={{ items, loaded, patch }}>{children}</Ctx.Provider>;
}

export function useHeadwords(): HeadwordsContextValue {
  const v = useContext(Ctx);
  if (!v) throw new Error('useHeadwords must be used within HeadwordsProvider');
  return v;
}
