import type { ReactNode } from 'react';

import ColumnImagePanel, { type ColumnHighlight } from './ColumnImagePanel';

interface Props {
  toolbar: ReactNode;
  children: ReactNode;
  initialColumn: string | null;
  highlight: ColumnHighlight | null;
  onNavigate?: (urlId: string, targetColumn: string, targetY: number, clickY: number) => void;
}

// Shared layout for both editor + viewer: text column on the left, full-height
// image panel on the right. Keeps the banner styling (and its matching height
// on both sides) in one place.
export default function EntryShell({
  toolbar, children, initialColumn, highlight, onNavigate,
}: Props) {
  return (
    <div className="entry-shell">
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
