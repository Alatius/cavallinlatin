import { useEffect, useState } from 'react';

/** Returns a value that trails `value` by `ms` milliseconds: each new
 *  `value` resets the timer, and the returned value only updates when the
 *  timer fires. Useful to throttle expensive renders driven by typing.
 *
 *  When `resetKey` changes the new `value` is flushed *synchronously* in
 *  the same render. Doing it in a useEffect would leak one frame of the
 *  previous value, and downstream effects that read the DOM (e.g. an
 *  auto-highlight that walks the rendered preview) would run against a
 *  DOM still showing yesterday's entry. */
export function useDebounce<T>(value: T, ms: number, resetKey?: unknown): T {
  const [debounced, setDebounced] = useState(value);
  const [prevResetKey, setPrevResetKey] = useState(resetKey);

  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);

  // setState during render is the React-supported pattern for resetting
  // state derived from props: React discards the rendered output and
  // re-renders with the new state, so consumers never see the stale value.
  // Must come AFTER any other hook calls to keep hook order consistent
  // between the discarded render and the re-render.
  if (resetKey !== undefined && resetKey !== prevResetKey) {
    setPrevResetKey(resetKey);
    setDebounced(value);
    return value;
  }

  return debounced;
}
