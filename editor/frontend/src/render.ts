// Render a single <entry>…</entry> XML fragment into a styled HTML fragment.
// Single-pass scan: each wrapper carries data-xml-start (the offset of its
// open tag in the XML) so the preview can jump the XML editor's cursor back
// to the source on click.
//
// Security: tags outside ALLOWED_TAGS and attributes outside ALLOWED_ATTRS
// are HTML-escaped, so an editor can't smuggle <script>, <img onerror=…>,
// on*-handlers, javascript: URLs, etc. through the preview or public view.

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
const ATTR_RE = /\b([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*"([^"]*)"/g;
const REF_TARGET_RE = / target="([^"]*)"/;

function escapeText(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function escapeAttr(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
}

function safeAttrs(tag: string, raw: string): string {
  const allowed = ALLOWED_ATTRS[tag];
  if (!allowed) return '';
  let out = '';
  for (const m of raw.matchAll(ATTR_RE)) {
    if (!allowed.has(m[1])) continue;
    const name = m[1] === 'y' ? 'data-y' : m[1];
    out += ` ${name}="${escapeAttr(m[2])}"`;
  }
  return out;
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
      if (tag === 'entry') out += '</p>';
      else if (tag === 'sense') out += '</div>';
      else if (tag === 'foreign' || tag === 'form' || TEI_SPAN_TAGS.has(tag)) out += '</span>';
      else if (tag === 'ref') out += '</a>';
      else out += `</${tag}>`;
      continue;
    }

    const attrs = safeAttrs(tag, m[3]);

    if (tag === 'entry') {
      out += `<p data-xml-start="${offset}"${attrs}>`;
    } else if (tag === 'sense') {
      // Pull n out so it can render as the leading sense-num span.
      const nMatch = / n="([^"]*)"/.exec(attrs);
      const nVal = nMatch ? nMatch[1] : '';
      const rest = attrs.replace(/ n="[^"]*"/, '');
      out += `<div class="sense" data-xml-start="${offset}"${rest}><span class="sense-num">${nVal}.</span> `;
    } else if (tag === 'foreign') {
      out += `<span class="foreign" data-xml-start="${offset}">`;
    } else if (tag === 'form') {
      out += `<span class="form" data-xml-start="${offset}"${attrs}>`;
    } else if (TEI_SPAN_TAGS.has(tag)) {
      out += `<span class="${tag}" data-xml-start="${offset}"${attrs}>`;
    } else if (tag === 'ref') {
      // EntryHtml intercepts clicks on a.ref and routes via react-router so
      // navigation stays in-SPA.
      const tgtMatch = REF_TARGET_RE.exec(attrs);
      const raw = tgtMatch ? tgtMatch[1] : '';
      const id = raw.startsWith('#') ? raw.slice(1) : raw;
      const href = id ? `${hrefPrefix}${encodeURIComponent(id)}` : '';
      const hrefAttr = href ? ` href="${escapeAttr(href)}"` : '';
      out += `<a class="ref"${hrefAttr}>`;
    } else if (tag === 'cb') {
      // HTML5 ignores /> on custom elements; emit an explicit close tag.
      out += `<cb data-xml-start="${offset}"${attrs}></cb>`;
    } else if (selfClose) {
      out += `<${tag} data-xml-start="${offset}"${attrs}/>`;
    } else {
      out += `<${tag} data-xml-start="${offset}"${attrs}>`;
    }
  }

  out += emitText(xml, last, xml.length);
  return out;
}

// Walk xml[start..end) and wrap every whitespace-delimited run in a span
// carrying data-xml-start = absolute XML offset of that run's first char.
// Whitespace is passed through verbatim so text layout is unchanged. Text
// content is emitted as-is: in valid XML it is already entity-encoded
// (&amp;, &lt;, …) so the browser decodes it the same way HTML expects.
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
      const word = xml.slice(wordStart, i).replace(/-/g, '‑');
      out += `<span class="w" data-xml-start="${wordStart}">${word}</span>`;
    }
  }
  return out;
}

function isWs(c: number): boolean {
  return c === 0x20 || c === 0x09 || c === 0x0a || c === 0x0d;
}
