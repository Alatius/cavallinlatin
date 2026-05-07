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

// Preserve ä, ö, å as distinct (so 'bar' doesn't match 'bär'), but
// fold every other diacritic — macrons and breves so 'abavus' matches
// 'ăbāvus', and ordinary diaereses so 'coepi' matches 'coëpi'. We
// stash ä/ö/å in PUA codepoints before NFKD strips combining marks,
// then restore them. Then w↔v, ß↔ss, æ↔ae and œ↔oe are folded because
// the dictionary treats them as orthographic equivalents; the backend
// /search expansion and the Python text.fold() mirror this.
// (Regex inlined rather than hoisted to a module const so the
// test_contract.py contract test can extract this function body and
// run it under node without external bindings.)
export function fold(s: string): string {
  return s
    .toLowerCase()
    .normalize('NFC')
    .replace(/ä/g, '\uE000')
    .replace(/ö/g, '\uE001')
    .replace(/å/g, '\uE002')
    .normalize('NFKD')
    .replace(/\p{M}/gu, '')
    .replace(/\uE000/g, 'ä')
    .replace(/\uE001/g, 'ö')
    .replace(/\uE002/g, 'å')
    .replace(/w/g, 'v')
    .replace(/ß/g, 'ss')
    .replace(/æ/g, 'ae')
    .replace(/œ/g, 'oe');
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
