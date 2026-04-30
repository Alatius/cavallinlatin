import { useCallback, useEffect, useRef, useState } from 'react';

import { api, ApiError } from '../api/client';
import { useHorizontalResize } from './useHorizontalResize';

const DEFAULT_WIDTH = 410;
const BASE_MARKER_HEIGHT = 18;
const COLUMNS_ROOT = `${import.meta.env.BASE_URL}columns`;

// Number of columns per volume in the source book. Used for input validation
// and to cap ▶/◀ navigation at the last page.
const VOLUME_MAX: Record<number, number> = { 1: 1160, 2: 1448 };

export interface ColumnHighlight {
  column: string;
  y: number;
}

interface Props {
  initialColumn: string | null;
  highlight: ColumnHighlight | null;
  onNavigate?: (urlId: string, targetColumn: string, targetY: number, clickY: number) => void;
}

function parseImageName(name: string): { vol: number; num: number } | null {
  const m = name.match(/^cavlat-(\d+)-(\d+)\.png$/);
  return m ? { vol: Number(m[1]), num: Number(m[2]) } : null;
}

function formatImageName(vol: number, num: number): string {
  return `cavlat-${vol}-${String(num).padStart(4, '0')}.png`;
}

function nextImage(name: string): string | null {
  const p = parseImageName(name);
  if (!p) return null;
  const max = VOLUME_MAX[p.vol];
  if (!max) return null;
  if (p.num >= max) return p.vol === 1 ? formatImageName(2, 1) : null;
  return formatImageName(p.vol, p.num + 1);
}

function prevImage(name: string): string | null {
  const p = parseImageName(name);
  if (!p) return null;
  if (p.num < 2) return p.vol === 2 ? formatImageName(1, 1160) : null;
  return formatImageName(p.vol, p.num - 1);
}

function labelFor(name: string | null): string {
  if (!name) return '—';
  const p = parseImageName(name);
  return p ? `${p.vol}-${p.num}` : name;
}

function parseLabel(label: string): string | null {
  const m = label.trim().match(/^(\d+)-(\d+)$/);
  if (!m) return null;
  const vol = Number(m[1]);
  const num = Number(m[2]);
  const max = VOLUME_MAX[vol];
  if (!max || num < 1 || num > max) return null;
  return formatImageName(vol, num);
}

export default function ColumnImagePanel({ initialColumn, highlight, onNavigate }: Props) {
  const { width, handleRef, onPointerDown } = useHorizontalResize({
    storageKey: 'image-panel-width',
    initial: DEFAULT_WIDTH,
    min: 150,
    side: 'left',
  });
  const [currentImage, setCurrentImage] = useState<string | null>(
    initialColumn ? `cavlat-${initialColumn}.png` : null,
  );
  const [markerY, setMarkerY] = useState(0);
  const [showMarker, setShowMarker] = useState(false);
  const [imgHeight, setImgHeight] = useState(0);
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState('');
  const [editInvalid, setEditInvalid] = useState(false);

  const imgRef = useRef<HTMLImageElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const labelInputRef = useRef<HTMLInputElement>(null);

  function startEdit() {
    setEditValue(labelFor(currentImage));
    setEditInvalid(false);
    setEditing(true);
  }

  function closeEdit() {
    setEditing(false);
    setEditInvalid(false);
  }

  function commitEdit() {
    const name = parseLabel(editValue);
    if (name) {
      setCurrentImage(name);
      setShowMarker(false);
      setMarkerY(0);
      closeEdit();
    } else {
      setEditInvalid(true);
    }
  }

  useEffect(() => {
    if (editing && labelInputRef.current) {
      labelInputRef.current.focus();
      labelInputRef.current.select();
    }
  }, [editing]);

  useEffect(() => {
    if (!highlight) return;
    setCurrentImage(`cavlat-${highlight.column}.png`);
    setMarkerY(highlight.y);
    setShowMarker(true);
  }, [highlight]);

  useEffect(() => {
    if (!initialColumn) return;
    setCurrentImage(`cavlat-${initialColumn}.png`);
    setShowMarker(false);
    setMarkerY(0);
  }, [initialColumn]);

  // Position the freshly-loaded image. When there's no marker (◀/▶ paged us
  // to a new column) we land at the top, or the bottom when paging backward
  // (markerY===100 is the caller's signal for that). When we do have a
  // marker, drop it about a quarter of the way down so context above it is
  // visible.
  const onImageLoad = useCallback(() => {
    const img = imgRef.current;
    const container = containerRef.current;
    if (!img || !container) return;
    setImgHeight(img.offsetHeight);
    if (showMarker) {
      const targetPx = (markerY / 100) * img.offsetHeight;
      container.scrollTop = targetPx - container.clientHeight / 4;
    } else {
      container.scrollTop = markerY === 100 ? img.offsetHeight : 0;
    }
  }, [markerY, showMarker]);

  // Marker moved on an already-loaded image (e.g. user clicked another sense
  // in the same column). Bring it back into view only if it has gone off the
  // visible band — leaves manually-scrolled positions alone.
  useEffect(() => {
    if (!showMarker) return;
    const img = imgRef.current;
    const container = containerRef.current;
    if (!img || !container || img.offsetHeight === 0) return;
    const targetPx = (markerY / 100) * img.offsetHeight;
    const { scrollTop, clientHeight } = container;
    const margin = 40;
    if (targetPx < scrollTop + margin || targetPx > scrollTop + clientHeight - margin) {
      container.scrollTop = targetPx - clientHeight / 4;
    }
  }, [markerY, showMarker]);

  useEffect(() => {
    if (imgRef.current) setImgHeight(imgRef.current.offsetHeight);
  }, [width]);

  async function onImageClick(e: React.MouseEvent<HTMLImageElement>) {
    if (!onNavigate || !currentImage) return;
    const p = parseImageName(currentImage);
    if (!p) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const yPct = Math.max(0, Math.min(100, ((e.clientY - rect.top) / rect.height) * 100));
    const column = `${p.vol}-${String(p.num).padStart(4, '0')}`;
    try {
      const res = await api.get<{ url_id: string }>(
        `/entry-at?column=${encodeURIComponent(column)}&y=${yPct.toFixed(2)}`,
      );
      onNavigate(res.url_id, column, yPct, e.clientY);
    } catch (err) {
      // 404 = click above the first entry on column 1-0001; ignore.
      if (!(err instanceof ApiError) || err.status !== 404) throw err;
    }
  }

  const markerScale = width / DEFAULT_WIDTH;
  const markerTop = (markerY / 100) * imgHeight;

  return (
    <>
      <div ref={handleRef} className="resize-handle" onPointerDown={onPointerDown} />
      <div className="column-panel" style={{ width }}>
        <div className="column-panel__header">
          <button
            type="button" className="column-panel__nav"
            onClick={() => {
              if (!currentImage) return;
              const p = prevImage(currentImage);
              if (p) { setCurrentImage(p); setMarkerY(100); setShowMarker(false); }
            }}
          >◀</button>
          {editing ? (
            <input
              ref={labelInputRef}
              className={
                'column-panel__label-input'
                + (editInvalid ? ' column-panel__label-input--invalid' : '')
              }
              value={editValue}
              aria-invalid={editInvalid}
              onChange={(e) => { setEditValue(e.target.value); setEditInvalid(false); }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') { e.preventDefault(); commitEdit(); }
                else if (e.key === 'Escape') { e.preventDefault(); closeEdit(); }
              }}
              onBlur={() => {
                // On blur: accept if valid, silently cancel otherwise — user's
                // click probably went somewhere useful.
                if (parseLabel(editValue)) commitEdit();
                else closeEdit();
              }}
              placeholder={`1-1…${VOLUME_MAX[1]} el. 2-1…${VOLUME_MAX[2]}`}
            />
          ) : (
            <button
              type="button"
              className="column-panel__label column-panel__label--button"
              onClick={startEdit}
              title="Klicka för att gå till annan kolumn"
            >
              {labelFor(currentImage)}
            </button>
          )}
          <button
            type="button" className="column-panel__nav"
            onClick={() => {
              if (!currentImage) return;
              const n = nextImage(currentImage);
              if (n) { setCurrentImage(n); setMarkerY(0); setShowMarker(false); }
            }}
          >▶</button>
        </div>
        <div className="column-panel__img-container" ref={containerRef}>
          {currentImage && (
            <img
              className={
                'column-panel__img'
                + (onNavigate ? ' column-panel__img--clickable' : '')
              }
              ref={imgRef}
              src={`${COLUMNS_ROOT}/${currentImage}`}
              alt={currentImage}
              draggable={false}
              onLoad={onImageLoad}
              onClick={onNavigate ? onImageClick : undefined}
            />
          )}
          {showMarker && (
            <div
              className="column-panel__marker"
              style={{ top: `${markerTop}px`, height: `${BASE_MARKER_HEIGHT * markerScale}px` }}
            />
          )}
        </div>
      </div>
    </>
  );
}
