import type { ReactNode } from 'react';

import ColumnImagePanel, { type ColumnHighlight } from './ColumnImagePanel';

export type MobileView = 'xml' | 'preview' | 'image' | 'comments';

interface Props {
  toolbar: ReactNode;
  children: ReactNode;
  initialColumn: string | null;
  highlight: ColumnHighlight | null;
  onNavigate?: (urlId: string, targetColumn: string, targetY: number, clickY: number) => void;
  /** Editor-only: which pane is showing in the stacked phone layout.
      The CSS reads `[data-mobile-view]` to hide the others; ignored on
      desktop since all three are visible side-by-side anyway. */
  mobileView?: MobileView;
}

// Shared layout for both editor + viewer: text column on the left, full-height
// image panel on the right. Keeps the banner styling (and its matching height
// on both sides) in one place.
export default function EntryShell({
  toolbar, children, initialColumn, highlight, onNavigate, mobileView,
}: Props) {
  return (
    <div className="entry-shell" data-mobile-view={mobileView}>
      <div className="entry-shell__text">
        <div className="entry-shell__toolbar">{toolbar}</div>
        {children}
      </div>
      <ColumnImagePanel
        initialColumn={initialColumn}
        highlight={highlight}
        onNavigate={onNavigate}
      />
    </div>
  );
}
