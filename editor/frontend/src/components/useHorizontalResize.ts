import { useCallback, useEffect, useRef, useState, type RefObject } from 'react';

interface Options {
  storageKey: string;
  initial: number;
  min?: number;
  max?: number;
  side: 'right' | 'left';
}

interface Result {
  width: number;
  handleRef: RefObject<HTMLDivElement>;
  onPointerDown: (e: React.PointerEvent<HTMLDivElement>) => void;
}

function readStored(key: string, fallback: number): number {
  if (typeof localStorage === 'undefined') return fallback;
  const s = localStorage.getItem(key);
  const n = s ? Number.parseInt(s, 10) : Number.NaN;
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

export function useHorizontalResize(opts: Options): Result {
  const { storageKey, initial, min = 100, max, side } = opts;
  const [width, setWidth] = useState(() => readStored(storageKey, initial));
  const widthRef = useRef(width);
  widthRef.current = width;
  const handleRef = useRef<HTMLDivElement>(null);
  const dragCleanupRef = useRef<(() => void) | null>(null);

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

  return { width, handleRef, onPointerDown };
}
