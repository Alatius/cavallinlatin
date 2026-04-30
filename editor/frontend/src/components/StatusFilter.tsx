import { useEffect, useRef, useState } from 'react';

import type { Status } from '../api/types';
import { STATUS_LABEL_SV, STATUS_VALUES } from '../api/types';

interface Props {
  value: Status | '';
  onChange(next: Status | ''): void;
}

const ALL_LABEL = 'Alla statusar';

// Custom dropdown matching the SaveButton menu so the index sidebar and the
// editor toolbar share the same visual vocabulary. The native <select>'s
// popup looks like a system widget — fine on its own, jarring next to a
// styled menu — so we render the menu ourselves with the shared
// `dropdown-menu` classes.
export default function StatusFilter({ value, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

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

  function pick(next: Status | '') {
    setOpen(false);
    onChange(next);
  }

  const label = value === '' ? ALL_LABEL : STATUS_LABEL_SV[value];

  return (
    <div className="status-filter" ref={wrapRef}>
      <button
        type="button"
        className="status-filter__trigger"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="status-filter__label">{label}</span>
        <span className="chevron-down" aria-hidden="true" />
      </button>
      {open && (
        <ul className="dropdown-menu status-filter__menu" role="listbox">
          <li role="none">
            <button
              type="button"
              role="option"
              aria-selected={value === ''}
              className={
                'dropdown-menu__item'
                + (value === '' ? ' dropdown-menu__item--current' : '')
              }
              onClick={() => pick('')}
            >
              {ALL_LABEL}
            </button>
          </li>
          {STATUS_VALUES.map((s) => (
            <li key={s} role="none">
              <button
                type="button"
                role="option"
                aria-selected={value === s}
                className={
                  'dropdown-menu__item'
                  + (value === s ? ' dropdown-menu__item--current' : '')
                }
                onClick={() => pick(s)}
              >
                {STATUS_LABEL_SV[s]}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
