// Render a single <entry>…</entry> XML fragment into a styled HTML fragment.
// Single-pass scan: each wrapper carries data-xml-start (the offset of its
// open tag in the XML) so the preview can jump the XML editor's cursor back
// to the source on click.
//
// Security: the output goes to dangerouslySetInnerHTML, so nothing may reach
// it as live markup unless this file emitted it. Three things enforce that:
// tags outside ALLOWED_TAGS are escaped rather than passed through,
// attributes outside ALLOWED_ATTRS are dropped (and the rest escaped, with
// ref targets confined to a fixed path prefix via encodeURIComponent), and
// every '<' in a text run is escaped — see emitText for why that last one is
// load-bearing rather than redundant.

const TEI_SPAN_TAGS = new Set([
  'pos', 'gen', 'subc', 'case', 'mood', 'tns', 'number',
  'iType', 'gram', 'lbl', 'hom',
]);

// Every tag that legitimately appears in source XML. Unknown tags are
// rendered as escaped text rather than executable markup.
const ALLOWED_TAGS: ReadonlySet<string> = new Set([
  'entry', 'sense', 'orth', 'foreign', 'form', 'cb', 'ref',
  ...TEI_SPAN_TAGS,
  'b', 'i', 'u', 'br',
]);

// Per-tag attribute allowlist. Names not listed are dropped — including
// any on*, style, class, href, src, etc. so the rules also block reflective
// attacks on the inline tags (b/i/u/br) that the browser styles natively.
// 'y' is renamed to 'data-y' on the way out.
const ALLOWED_ATTRS: Record<string, ReadonlySet<string>> = {
  entry: new Set(['id', 'type', 'root']),
  sense: new Set(['n', 'y']),
  orth: new Set(['y']),
  cb: new Set(['n']),
  gram: new Set(['type']),
  ref: new Set(['target']),
};

// The body alternation skips over quoted attribute values so a literal `>`
// inside a value (legal in XML attributes — only `<` MUST be escaped) can't
// terminate the tag prematurely. Non-greedy so the trailing `(\/?)` still
// catches self-close slashes that would otherwise be eaten by the body.
const TAG_RE = /<(\/?)([A-Za-z][A-Za-z0-9]*)\b((?:[^>"']|"[^"]*"|'[^']*')*?)(\/?)>/g;
// Single-quoted values are legal XML. TAG_RE already skips over them, so
// matching only double quotes here silently dropped the attribute: <orth y='5'>
// lost its data-y (breaking the column-image sync) and <ref target='x'> became
// a link with no href.
const ATTR_RE = /\b([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*(?:"([^"]*)"|'([^']*)')/g;

// HTML elements with no closing tag. `br` is the only one in ALLOWED_TAGS.
const VOID_TAGS: ReadonlySet<string> = new Set(['br']);

function escapeText(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

export function escapeAttr(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
}

// Attribute values in the source are XML-encoded, so decode to the actual
// value before either re-escaping it for HTML or using it as an identifier.
// Skipping this escaped everything twice: target="#a&amp;b" came out as
// href=".../a%26amp%3Bb", a link that 404s.
function xmlDecodeAttr(s: string): string {
  if (!s.includes('&')) return s;
  return s.replace(/&(#\d+|#[xX][0-9a-fA-F]+|amp|lt|gt|quot|apos);/g, (whole, ref: string) => {
    switch (ref) {
      case 'amp': return '&';
      case 'lt': return '<';
      case 'gt': return '>';
      case 'quot': return '"';
      case 'apos': return "'";
      default: {
        const code = ref[1] === 'x' || ref[1] === 'X'
          ? parseInt(ref.slice(2), 16)
          : parseInt(ref.slice(1), 10);
        return Number.isFinite(code) && code >= 0 && code <= 0x10ffff
          ? String.fromCodePoint(code)
          : whole;
      }
    }
  });
}

type SafeAttrs = {
  /** Ready-to-emit HTML, allowlisted and escaped. */
  html: string;
  /** Raw (unescaped) values, for callers that need the value itself rather
   *  than markup — re-parsing them out of `html` double-escaped them. */
  values: Record<string, string>;
};

function safeAttrs(tag: string, raw: string): SafeAttrs {
  const allowed = ALLOWED_ATTRS[tag];
  const values: Record<string, string> = {};
  if (!allowed) return { html: '', values };
  let html = '';
  for (const m of raw.matchAll(ATTR_RE)) {
    if (!allowed.has(m[1])) continue;
    const value = xmlDecodeAttr(m[2] ?? m[3] ?? '');
    values[m[1]] = value;
    const name = m[1] === 'y' ? 'data-y' : m[1];
    html += ` ${name}="${escapeAttr(value)}"`;
  }
  return { html, values };
}

// Closing markup for an allowed tag. Shared by the close-tag branch and the
// self-closing case, so the two can't drift.
function closeHtmlFor(tag: string): string {
  if (tag === 'entry' || tag === 'sense') return '</div>';
  if (tag === 'foreign' || tag === 'form' || TEI_SPAN_TAGS.has(tag)) return '</span>';
  if (tag === 'ref') return '</a>';
  return `</${tag}>`;
}

export interface RenderOptions {
  /** URL prefix for cross-reference links, e.g. "/entry/" (public view) or
   *  "/editor/entry/" (editor view). When omitted, <ref> targets resolve
   *  to "/entry/<id>". */
  entryHrefPrefix?: string;
}

export function entryXmlToHtml(xml: string, opts: RenderOptions = {}): string {
  const hrefPrefix = opts.entryHrefPrefix ?? '/entry/';
  let out = '';
  let last = 0;

  for (const m of xml.matchAll(TAG_RE)) {
    const offset = m.index!;
    out += emitText(xml, last, offset);
    last = offset + m[0].length;

    const isClose = m[1] === '/';
    const tag = m[2];
    const selfClose = m[4] === '/';

    if (!ALLOWED_TAGS.has(tag)) {
      // Unknown / disallowed tag: show literally so the editor can spot it.
      out += escapeText(m[0]);
      continue;
    }

    if (isClose) {
      // cb opens are force-closed below, so a paired </cb> must not emit a
      // second (stray) close tag.
      if (tag !== 'cb') out += closeHtmlFor(tag);
      continue;
    }

    const attrs = safeAttrs(tag, m[3]);
    let openHtml: string;

    if (tag === 'entry') {
      // A div, not a p: HTML5 auto-closes an open <p> as soon as a <div>
      // start tag arrives, and <sense> renders as a div. As a p, every one of
      // the 7,347 sense-bearing entries parsed into three siblings — the
      // entry attributes stopped applying at the first sense, and a stray
      // empty <p> picked up a real margin.
      openHtml = `<div class="entry" data-xml-start="${offset}"${attrs.html}>`;
    } else if (tag === 'sense') {
      // Pull n out so it can render as the leading sense-num span.
      const nVal = attrs.values.n ?? '';
      const rest = attrs.html.replace(/ n="[^"]*"/, '');
      const num = nVal ? `<span class="sense-num">${escapeText(nVal)}.</span> ` : '';
      openHtml = `<div class="sense" data-xml-start="${offset}"${rest}>${num}`;
    } else if (tag === 'foreign') {
      openHtml = `<span class="foreign" data-xml-start="${offset}">`;
    } else if (tag === 'form') {
      openHtml = `<span class="form" data-xml-start="${offset}"${attrs.html}>`;
    } else if (TEI_SPAN_TAGS.has(tag)) {
      openHtml = `<span class="${tag}" data-xml-start="${offset}"${attrs.html}>`;
    } else if (tag === 'ref') {
      // EntryHtml intercepts clicks on a.ref and routes via react-router so
      // navigation stays in-SPA.
      const raw = attrs.values.target ?? '';
      const id = raw.startsWith('#') ? raw.slice(1) : raw;
      const href = id ? `${hrefPrefix}${encodeURIComponent(id)}` : '';
      const hrefAttr = href ? ` href="${escapeAttr(href)}"` : '';
      openHtml = `<a class="ref"${hrefAttr}>`;
    } else {
      openHtml = `<${tag} data-xml-start="${offset}"${attrs.html}>`;
    }

    out += openHtml;
    // A self-closing non-void tag has to be closed right here. Only the
    // final branch used to honour selfClose, so <ref target="#x"/> — legal
    // XML, and a natural thing to type — swallowed the entire rest of the
    // entry into one link. Same for <foreign/>, <b/> and <sense n="1"/>.
    // cb is a milestone: force-close it even when typed as a bare <cb>, or
    // the rest of the entry ends up inside the unclosed element.
    if ((selfClose || tag === 'cb') && !VOID_TAGS.has(tag)) out += closeHtmlFor(tag);
  }

  out += emitText(xml, last, xml.length);
  return out;
}

// Walk xml[start..end) and wrap every whitespace-delimited run in a span
// carrying data-xml-start = absolute XML offset of that run's first char.
// Whitespace is passed through verbatim so text layout is unchanged.
//
// `&` is deliberately left alone: in valid XML the text is already
// entity-encoded, and the browser decodes those the same way HTML does.
// `<` is escaped, though. It cannot appear raw in valid XML text, so this
// never touches legitimate content — but it is exactly the set of `<`
// characters TAG_RE declined to consume, and those reached the DOM as live
// markup. A tag with an unpaired quote defeats TAG_RE's quote-skipping
// alternation and matches nothing at all, and CDATA sections and processing
// instructions can carry such a thing through the parser verbatim:
//
//     <![CDATA[ <img/src="x"/onerror="alert(1)"/' ]]>
//
// went straight into dangerouslySetInnerHTML as a live <img>. The production
// CSP (script-src 'self') blocks the handler, but style-src allows inline, so
// an injected <style> restyles the whole public page — and the dev server
// sends no CSP at all.
//
// Hyphens are remapped to U+2011 NON-BREAKING HYPHEN so word-initial
// suffixes like "-us" can never be orphaned by a line break.
function emitText(xml: string, start: number, end: number): string {
  let out = '';
  let i = start;
  while (i < end) {
    const wsStart = i;
    while (i < end && isWs(xml.charCodeAt(i))) i++;
    if (i > wsStart) out += xml.slice(wsStart, i);
    const wordStart = i;
    while (i < end && !isWs(xml.charCodeAt(i))) i++;
    if (i > wordStart) {
      // Render every "-" as U+2011 NON-BREAKING HYPHEN so the browser
      // never breaks a line at a hyphen.
      const word = xml.slice(wordStart, i).replace(/-/g, '‑').replace(/</g, '&lt;');
      out += `<span class="w" data-xml-start="${wordStart}">${word}</span>`;
    }
  }
  return out;
}

function isWs(c: number): boolean {
  return c === 0x20 || c === 0x09 || c === 0x0a || c === 0x0d;
}
