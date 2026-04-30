// Shape of router-state passed when navigating between entries. Centralised
// here so writers (image clicks, activity-page links) and readers (EntryEditor,
// EntryView) can't drift on field names or types.

export interface EntryNavState {
  targetColumn?: string;
  targetY?: number;
  clickY?: number;
  openComments?: boolean;
}

export function readEntryNavState(state: unknown): EntryNavState {
  if (!state || typeof state !== 'object') return {};
  const s = state as Record<string, unknown>;
  const out: EntryNavState = {};
  if (typeof s.targetColumn === 'string') out.targetColumn = s.targetColumn;
  if (typeof s.targetY === 'number') out.targetY = s.targetY;
  if (typeof s.clickY === 'number') out.clickY = s.clickY;
  if (typeof s.openComments === 'boolean') out.openComments = s.openComments;
  return out;
}
