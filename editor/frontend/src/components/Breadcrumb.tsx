import { Link } from 'react-router-dom';

interface Props {
  /** The group's head headword, or null when the entry stands alone. */
  head: string | null;
  /** The headword to label as the current focus. */
  current: string;
  /** Router path for the head, if it should be a link. */
  headTo?: string | null;
  /** Router path for the current entry, if it should be a link. */
  currentTo?: string | null;
}

// Toolbar headword display shared by editor + public. When `head` is provided
// and differs from `current`, renders "Head › Current"; otherwise just
// "Current". Suppressing the head when it equals current avoids "Cano › Cano"
// for primaries that have their own page open.
export default function Breadcrumb({ head, current, headTo, currentTo }: Props) {
  const showHead = head !== null && head !== current;
  return (
    <h2 className="entry-breadcrumb">
      {showHead && (
        <>
          {headTo
            ? <Link className="entry-breadcrumb__head" to={headTo}>{head}</Link>
            : <span className="entry-breadcrumb__head">{head}</span>}
          <span className="entry-breadcrumb__sep" aria-hidden="true">›</span>
        </>
      )}
      {currentTo
        ? <Link className="entry-breadcrumb__current" to={currentTo}>{current}</Link>
        : <span className="entry-breadcrumb__current">{current}</span>}
    </h2>
  );
}
