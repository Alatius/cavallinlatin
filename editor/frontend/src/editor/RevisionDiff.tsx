import { useEffect, useRef } from 'react';
import { MergeView } from '@codemirror/merge';
import { EditorState } from '@codemirror/state';
import { EditorView } from '@codemirror/view';
import { xml as xmlLang } from '@codemirror/lang-xml';

interface Props {
  beforeXml: string;
  afterXml: string;
  beforeLabel: string;
  afterLabel: string;
}

const COMMON_EXT = [
  xmlLang(),
  EditorState.readOnly.of(true),
  EditorView.editable.of(false),
  EditorView.lineWrapping,
];

export default function RevisionDiff({
  beforeXml, afterXml, beforeLabel, afterLabel,
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const viewRef = useRef<MergeView | null>(null);

  useEffect(() => {
    const parent = containerRef.current;
    if (!parent) return;
    if (viewRef.current) {
      // Reuse the mounted MergeView — dispatching updates avoids the full
      // DOM teardown + collapseUnchanged recompute that switching revisions
      // would otherwise pay each click.
      const v = viewRef.current;
      v.a.dispatch({ changes: { from: 0, to: v.a.state.doc.length, insert: beforeXml } });
      v.b.dispatch({ changes: { from: 0, to: v.b.state.doc.length, insert: afterXml } });
      return;
    }
    viewRef.current = new MergeView({
      a: { doc: beforeXml, extensions: COMMON_EXT },
      b: { doc: afterXml, extensions: COMMON_EXT },
      parent,
      orientation: 'a-b',
      highlightChanges: true,
      gutter: true,
      collapseUnchanged: { margin: 3, minSize: 6 },
    });
  }, [beforeXml, afterXml]);

  useEffect(() => () => {
    viewRef.current?.destroy();
    viewRef.current = null;
  }, []);

  return (
    <div className="revision-diff">
      <div className="revision-diff__header">
        <span className="revision-diff__header-cell">
          <span className="revision-diff__header-side">Före</span>
          <span className="revision-diff__header-detail">{beforeLabel}</span>
        </span>
        <span className="revision-diff__header-cell">
          <span className="revision-diff__header-side">Efter</span>
          <span className="revision-diff__header-detail">{afterLabel}</span>
        </span>
      </div>
      <div ref={containerRef} className="revision-diff__merge" />
    </div>
  );
}
