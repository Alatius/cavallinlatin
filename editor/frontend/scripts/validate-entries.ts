// Validate every entry's xml_body against the TEI schema used by the editor.
// Imports teiSchema.ts directly so this stays in lockstep with the in-editor
// linter (teiLint.ts), which applies the same rules.
//
// Run from editor/frontend/:
//   node --experimental-strip-types scripts/validate-entries.ts
//   node --experimental-strip-types scripts/validate-entries.ts --summary
//   node --experimental-strip-types scripts/validate-entries.ts --errors-only

import { DatabaseSync } from 'node:sqlite';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { parser } from '@lezer/xml';
import type { ElementSpec, AttrSpec } from '@codemirror/lang-xml';

import { TEI_ATTRS, TEI_ELEMENTS } from '../src/editor/teiSchema.ts';

const elementByName = new Map<string, ElementSpec>(
  TEI_ELEMENTS.map((e) => [e.name, e]),
);
const namedAttrs = new Map<string, AttrSpec>(
  TEI_ATTRS.map((a) => [a.name, a]),
);
const globalAttrs = new Map<string, AttrSpec>(
  TEI_ATTRS.filter((a) => a.global).map((a) => [a.name, a]),
);

const WF_ERROR_MESSAGES: Record<string, string> = {
  MismatchedCloseTag: 'Mismatched close tag',
  MissingCloseTag: 'Missing close tag',
};

type Severity = 'error' | 'warning';
interface Issue {
  severity: Severity;
  message: string;
  offset: number;
}

function attrSpecFor(spec: ElementSpec, name: string): AttrSpec | undefined {
  if (spec.attributes) {
    for (const a of spec.attributes) {
      if (typeof a === 'string') {
        if (a === name) return namedAttrs.get(a);
      } else if (a.name === name) {
        return a;
      }
    }
  }
  return globalAttrs.get(name);
}

function unquote(raw: string): string {
  if (
    raw.length >= 2
    && (raw[0] === '"' || raw[0] === "'")
    && raw[raw.length - 1] === raw[0]
  ) {
    return raw.slice(1, -1);
  }
  return raw;
}

function lintXml(xml: string): Issue[] {
  const issues: Issue[] = [];
  const tree = parser.parse(xml);
  const slice = (from: number, to: number) => xml.slice(from, to);

  tree.iterate({
    enter(ref) {
      if (ref.type.isError || ref.name in WF_ERROR_MESSAGES) {
        issues.push({
          severity: 'error',
          message: WF_ERROR_MESSAGES[ref.name] ?? 'XML syntax error',
          offset: ref.from,
        });
        return;
      }

      if (ref.name !== 'Element') return;

      const node = ref.node;
      const tag = node.firstChild;
      if (!tag) return;
      if (tag.name !== 'OpenTag' && tag.name !== 'SelfClosingTag') return;
      const tn = tag.getChild('TagName');
      if (!tn) return;
      const tagName = slice(tn.from, tn.to);

      const spec = elementByName.get(tagName);
      if (!spec) {
        issues.push({
          severity: 'error',
          message: `Unknown element <${tagName}>`,
          offset: tn.from,
        });
        return;
      }

      const parent = node.parent;
      if (parent && parent.name === 'Element') {
        const ptag = parent.firstChild;
        const ptn = ptag?.getChild('TagName');
        if (ptn) {
          const parentName = slice(ptn.from, ptn.to);
          const pSpec = elementByName.get(parentName);
          if (pSpec && pSpec.children && !pSpec.children.includes(tagName)) {
            issues.push({
              severity: 'error',
              message: `<${tagName}> not allowed inside <${parentName}>`,
              offset: tn.from,
            });
          }
        }
      }

      for (const attr of tag.getChildren('Attribute')) {
        const nameNode = attr.getChild('AttributeName');
        if (!nameNode) continue;
        const aname = slice(nameNode.from, nameNode.to);
        const aspec = attrSpecFor(spec, aname);
        if (!aspec) {
          issues.push({
            severity: 'warning',
            message: `Attribute "${aname}" not declared on <${tagName}>`,
            offset: nameNode.from,
          });
          continue;
        }
        if (aspec.values && aspec.values.length > 0) {
          const valueNode = attr.getChild('AttributeValue');
          if (valueNode) {
            const value = unquote(slice(valueNode.from, valueNode.to));
            const allowed = aspec.values.map((v) =>
              typeof v === 'string' ? v : v.label,
            );
            if (!allowed.includes(value)) {
              issues.push({
                severity: 'warning',
                message: `Value "${value}" not in allowed list for ${aname}: ${allowed.join(', ')}`,
                offset: valueNode.from,
              });
            }
          }
        }
      }
    },
  });

  return issues;
}

function offsetToLineCol(text: string, offset: number): [number, number] {
  let line = 1;
  let col = 1;
  const upTo = Math.min(offset, text.length);
  for (let i = 0; i < upTo; i++) {
    if (text.charCodeAt(i) === 10) {
      line++;
      col = 1;
    } else {
      col++;
    }
  }
  return [line, col];
}

const __dirname = dirname(fileURLToPath(import.meta.url));
const dbPath = resolve(__dirname, '../../data/cavallin.db');

const args = new Set(process.argv.slice(2));
const summaryOnly = args.has('--summary');
const errorsOnly = args.has('--errors-only');

const db = new DatabaseSync(dbPath, { readOnly: true });
const rows = db
  .prepare('SELECT url_id, headword, xml_body FROM entries ORDER BY sort_key')
  .all() as Array<{ url_id: string; headword: string; xml_body: string }>;

let totalErrors = 0;
let totalWarnings = 0;
let entriesWithIssues = 0;
const messageCounts = new Map<string, number>();

for (const row of rows) {
  const issues = lintXml(row.xml_body);
  const filtered = errorsOnly ? issues.filter((i) => i.severity === 'error') : issues;
  if (!filtered.length) continue;

  entriesWithIssues++;
  for (const i of issues) {
    if (i.severity === 'error') totalErrors++;
    else totalWarnings++;
    // Bucket by message text (without offset) for the summary.
    messageCounts.set(i.message, (messageCounts.get(i.message) ?? 0) + 1);
  }

  if (summaryOnly) continue;

  console.log(`\n${row.url_id} (${row.headword})`);
  for (const i of filtered) {
    const [line, col] = offsetToLineCol(row.xml_body, i.offset);
    console.log(`  ${i.severity.padEnd(7)} ${line}:${col}  ${i.message}`);
  }
}

if (summaryOnly && messageCounts.size) {
  console.log('\nIssue counts by message:');
  const sorted = [...messageCounts.entries()].sort((a, b) => b[1] - a[1]);
  for (const [msg, n] of sorted) {
    console.log(`  ${String(n).padStart(5)}  ${msg}`);
  }
}

console.log(
  `\n=== ${rows.length} entries scanned, ${entriesWithIssues} with issues `
  + `(${totalErrors} errors, ${totalWarnings} warnings) ===`,
);

db.close();
