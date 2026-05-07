import { useCallback, useEffect, useRef, useState } from 'react';

interface Options {
  storageKey: string;
  initial: number;
  min?: number;
  max?: number;
  side: 'right' | 'left';
  // When true, preserves the pane's fraction of its container when the
  // container itself resizes (window resize, sibling pane collapse, etc.).
  proportional?: boolean;
}

interface Result {
  width: number;
  // Callback ref rather than a RefObject so the proportional effect can react
  // to the handle actually mounting — the panes are gated behind a "Laddar …"
  // placeholder, so the element isn't in the DOM on first commit.
  handleRef: (el: HTMLDivElement | null) => void;
  onPointerDown: (e: React.PointerEvent<HTMLDivElement>) => void;
}

function readStored(key: string, fallback: number): number {
  if (typeof localStorage === 'undefined') return fallback;
  const s = localStorage.getItem(key);
  const n = s ? Number.parseInt(s, 10) : Number.NaN;
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

export function useHorizontalResize(opts: Options): Result {
  const { storageKey, initial, min = 100, max, side, proportional = false } = opts;
  const [width, setWidth] = useState(() => readStored(storageKey, initial));
  const widthRef = useRef(width);
  widthRef.current = width;
  const [handleEl, handleRef] = useState<HTMLDivElement | null>(null);
  const dragCleanupRef = useRef<(() => void) | null>(null);
  // Pane-as-fraction-of-container, captured at user actions (drag end, first
  // observe). Tracked separately from `width` because reading widthRef from
  // the ResizeObserver would drift: React batches the setWidth calls and a
  // burst of resize fires (e.g. window-edge drag) reads stale widthRef and
  // recomputes a different ratio each time.
  const ratioRef = useRef<number | null>(null);

  const onPointerDown = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    e.preventDefault();
    const startX = e.clientX;
    const startW = widthRef.current;
    const h = e.currentTarget;
    h.classList.add('resize-handle--dragging');
    document.body.style.cursor = 'col-resize';

    // Capture-phase window listeners so CodeMirror's stopPropagation
    // on bubbling can't swallow our drag events.
    const onMove = (ev: PointerEvent) => {
      const dx = ev.clientX - startX;
      let w = side === 'right' ? startW + dx : startW - dx;
      if (w < min) w = min;
      if (max != null && w > max) w = max;
      setWidth(w);
    };
    const stop = () => {
      window.removeEventListener('pointermove', onMove, true);
      window.removeEventListener('pointerup', stop, true);
      window.removeEventListener('pointercancel', stop, true);
      h.classList.remove('resize-handle--dragging');
      document.body.style.cursor = '';
      localStorage.setItem(storageKey, String(widthRef.current));
      // Container width is fixed during a handle drag, so it's safe to read
      // straight from the DOM here.
      const cw = h.parentElement?.clientWidth ?? 0;
      if (cw > 0) ratioRef.current = widthRef.current / cw;
      dragCleanupRef.current = null;
    };
    dragCleanupRef.current = stop;

    window.addEventListener('pointermove', onMove, true);
    window.addEventListener('pointerup', stop, true);
    window.addEventListener('pointercancel', stop, true);
  }, [min, max, side, storageKey]);

  // If the component unmounts mid-drag, remove the window listeners so they
  // don't call setWidth on an unmounted component.
  useEffect(() => () => { dragCleanupRef.current?.(); }, []);

  useEffect(() => {
    if (!proportional) return;
    const container = handleEl?.parentElement;
    if (!container || typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(() => {
      const cw = container.clientWidth;
      if (cw <= 0) return;
      if (ratioRef.current === null) {
        ratioRef.current = widthRef.current / cw;
        return;
      }
      let w = ratioRef.current * cw;
      if (w < min) w = min;
      if (max != null && w > max) w = max;
      // Leave at least `min` for the sibling pane. There's no per-pane info
      // here, so we assume the same min.
      if (w > cw - min) w = Math.max(min, cw - min);
      if (Math.abs(w - widthRef.current) > 0.5) setWidth(w);
    });
    ro.observe(container);
    return () => ro.disconnect();
  }, [proportional, min, max, handleEl]);

  return { width, handleRef, onPointerDown };
}
