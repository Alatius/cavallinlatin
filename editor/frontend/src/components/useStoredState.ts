import { useEffect, useState, type Dispatch, type SetStateAction } from 'react';

// Persist a state value across reloads. `parse` decides whether a stored
// raw string is acceptable (return undefined to fall back to `initial`).
// State of `null` (or empty string) clears the entry rather than writing a
// literal "null"; this lets callers model "closed/unset" cleanly.
export function useStoredState<T>(
  key: string,
  initial: T,
  parse: (raw: string) => T | undefined,
): [T, Dispatch<SetStateAction<T>>] {
  const [val, setVal] = useState<T>(() => {
    try {
      const raw = localStorage.getItem(key);
      if (raw !== null) {
        const parsed = parse(raw);
        if (parsed !== undefined) return parsed;
      }
    } catch { /* ignore */ }
    return initial;
  });
  useEffect(() => {
    try {
      if (val == null || val === '') localStorage.removeItem(key);
      else localStorage.setItem(key, String(val));
    } catch { /* ignore */ }
  }, [key, val]);
  return [val, setVal];
}
