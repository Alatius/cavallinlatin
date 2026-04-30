import { useEffect, useRef, useState } from 'react';

import type { Status } from '../api/types';

interface Props {
  dirty: boolean;
  saving: boolean;
  currentStatus: Status;
  onSave(): void;
  onSaveWithStatus(next: Status): void;
}

// `null` is the "plain" variant: save without changing status (the backend
// auto-bumps untouched → in_progress, but everything else is preserved).
// `shortLabel` is shown when the entry is clean: nothing to "save", so the
// "Spara & " prefix would be misleading — the action is just the status flip.
type Variant = { status: Status | null; label: string; shortLabel: string };

const VARIANTS: Variant[] = [
  { status: null,          label: 'Spara',                    shortLabel: 'Spara' },
  { status: 'in_progress', label: 'Spara & markera pågående', shortLabel: 'Markera pågående' },
  { status: 'approved',    label: 'Spara & markera godkänd',  shortLabel: 'Markera godkänd' },
];

function labelOf(v: Variant, dirty: boolean): string {
  return dirty ? v.label : v.shortLabel;
}

const STORAGE_KEY = 'save-variant';

// A variant is applicable only when it would actually change something:
//   - plain "Spara" (status=null) is always applicable
//   - "markera pågående" is the walk-back, so only from `approved`
//   - "markera godkänd" is the forward step, so only when not yet approved
// Variants that fail this test are hidden from the menu *and* skipped as
// the primary fallback, so the user only ever sees moves that move.
function applicable(v: Variant, current: Status): boolean {
  if (v.status === null) return true;
  if (v.status === 'in_progress') return current === 'approved';
  if (v.status === 'approved')    return current !== 'approved';
  return false;
}

function loadStored(): Variant {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored !== null) {
      const hit = VARIANTS.find((v) => (v.status ?? '') === stored);
      if (hit) return hit;
    }
  } catch { /* ignore */ }
  return VARIANTS[0];
}

export default function SaveButton({
  dirty, saving, currentStatus, onSave, onSaveWithStatus,
}: Props) {
  // The user's last manually-picked variant. Persists across entries; on
  // entries where it isn't applicable we fall back to plain "Spara" without
  // overwriting localStorage, so the preference pops back when relevant.
  const [stored, setStored] = useState<Variant>(loadStored);
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  // Outside-click closes the menu; pointerdown so it fires before the
  // menu-item's click handler when the user picks something.
  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    window.addEventListener('pointerdown', onDown);
    return () => window.removeEventListener('pointerdown', onDown);
  }, [open]);

  // Effective primary: the stored choice if it's applicable to this entry's
  // current status, otherwise plain "Spara".
  const primary: Variant = applicable(stored, currentStatus) ? stored : VARIANTS[0];

  function fire(v: Variant) {
    if (v.status === null) onSave();
    else onSaveWithStatus(v.status);
  }

  function pick(v: Variant) {
    setOpen(false);
    setStored(v);
    try { localStorage.setItem(STORAGE_KEY, v.status ?? ''); } catch { /* ignore */ }
    fire(v);
  }

  // Menu shows applicable variants except the one currently shown as primary.
  const others = VARIANTS.filter(
    (v) => applicable(v, currentStatus) && v.status !== primary.status,
  );
  // Plain "Spara" is gated on dirty (nothing to save); the status-changing
  // variants are enabled even when clean, so an editor can mark an unedited
  // entry's status without first making a fake edit.
  const primaryDisabled = saving || (primary.status === null && !dirty);

  return (
    <div className="save-button" ref={wrapRef}>
      <button
        type="button"
        className="save-button__primary"
        onClick={() => fire(primary)}
        disabled={primaryDisabled}
        title="Ctrl+S"
      >
        {labelOf(primary, dirty)}
      </button>
      <button
        type="button"
        className="save-button__caret"
        onClick={() => setOpen((v) => !v)}
        disabled={saving || others.length === 0}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Fler sparalternativ"
      >
        <span className="chevron-down" aria-hidden="true" />
      </button>
      {open && others.length > 0 && (
        <ul className="dropdown-menu save-button__menu" role="menu">
          {others.map((v) => (
            <li key={v.status ?? 'plain'} role="none">
              <button
                type="button"
                role="menuitem"
                className="dropdown-menu__item"
                onClick={() => pick(v)}
                disabled={saving || (v.status === null && !dirty)}
              >
                {labelOf(v, dirty)}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
