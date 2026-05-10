import { syntaxTree } from '@codemirror/language';
import { linter, type Diagnostic } from '@codemirror/lint';
import type { EditorState } from '@codemirror/state';
import type { AttrSpec, ElementSpec } from '@codemirror/lang-xml';
import type { SyntaxNode } from '@lezer/common';

import { REQUIRED_ATTRS, TEI_ATTRS, TEI_ELEMENTS } from './teiSchema';

const elementByName = new Map<string, ElementSpec>(
  TEI_ELEMENTS.map((e) => [e.name, e]),
);
const namedAttrs = new Map<string, AttrSpec>(
  TEI_ATTRS.map((a) => [a.name, a]),
);
const globalAttrs = new Map<string, AttrSpec>(
  TEI_ATTRS.filter((a) => a.global).map((a) => [a.name, a]),
);

// Lezer-XML surfaces well-formedness problems in two ways: generic error
// nodes (anything the grammar couldn't parse) and the explicit
// Mismatched/Missing close-tag tokens emitted by its context tracker. We
// catch both — the latter is what flags `<a></b>` and `<a>` with no closer.
const WF_ERROR_MESSAGES: Record<string, string> = {
  MismatchedCloseTag: 'Stängningstaggen matchar inte öppningstaggen.',
  MissingCloseTag: 'Stängningstagg saknas.',
};

type TagInfo = { name: string; from: number; to: number };

function tagInfo(elementNode: SyntaxNode, state: EditorState): TagInfo | null {
  const tag = elementNode.firstChild;
  if (!tag) return null;
  if (tag.name !== 'OpenTag' && tag.name !== 'SelfClosingTag') return null;
  const tn = tag.getChild('TagName');
  if (!tn) return null;
  return { name: state.sliceDoc(tn.from, tn.to), from: tn.from, to: tn.to };
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

export const teiLinter = linter((view) => {
  const diagnostics: Diagnostic[] = [];
  const state = view.state;
  const tree = syntaxTree(state);

  tree.iterate({
    enter(ref) {
      if (ref.type.isError || ref.name in WF_ERROR_MESSAGES) {
        diagnostics.push({
          from: ref.from,
          to: Math.max(ref.to, ref.from + 1),
          severity: 'error',
          message: WF_ERROR_MESSAGES[ref.name] ?? 'XML-syntaxfel.',
        });
        return;
      }

      if (ref.name !== 'Element') return;

      const node = ref.node;
      const t = tagInfo(node, state);
      if (!t) return;

      const spec = elementByName.get(t.name);
      if (!spec) {
        diagnostics.push({
          from: t.from,
          to: t.to,
          severity: 'error',
          message: `Okänt element <${t.name}>.`,
        });
        // An unknown element has no schema, so attribute-checking it would
        // flare on every attribute — bail out instead.
        return;
      }

      // ElementSpec without a `children` array means "anything goes" per
      // lang-xml's contract — only flag against specs that explicitly enumerate.
      const parent = node.parent;
      if (parent && parent.name === 'Element') {
        const pt = tagInfo(parent, state);
        if (pt) {
          const pSpec = elementByName.get(pt.name);
          if (pSpec && pSpec.children && !pSpec.children.includes(t.name)) {
            diagnostics.push({
              from: t.from,
              to: t.to,
              severity: 'error',
              message: `<${t.name}> är inte tillåtet inuti <${pt.name}>.`,
            });
          }
        }
      }

      const tag = node.firstChild;
      if (!tag) return;
      const required = REQUIRED_ATTRS[t.name];
      const present = required ? new Map<string, string>() : null;
      for (const attr of tag.getChildren('Attribute')) {
        const nameNode = attr.getChild('AttributeName');
        if (!nameNode) continue;
        const aname = state.sliceDoc(nameNode.from, nameNode.to);
        const valueNode = attr.getChild('AttributeValue');
        const value = valueNode
          ? unquote(state.sliceDoc(valueNode.from, valueNode.to))
          : '';
        present?.set(aname, value);
        const aspec = attrSpecFor(spec, aname);
        if (!aspec) {
          diagnostics.push({
            from: nameNode.from,
            to: nameNode.to,
            severity: 'warning',
            message: `Attributet "${aname}" är inte deklarerat på <${t.name}>.`,
          });
          continue;
        }
        if (aspec.values && aspec.values.length > 0 && valueNode) {
          const allowed = aspec.values.map((v) =>
            typeof v === 'string' ? v : v.label,
          );
          if (!allowed.includes(value)) {
            diagnostics.push({
              from: valueNode.from,
              to: valueNode.to,
              severity: 'warning',
              message: `Värdet "${value}" är inte i listan: ${allowed.join(', ')}.`,
            });
          }
        }
      }

      for (const name of required ?? []) {
        const value = present!.get(name);
        let message: string | null = null;
        if (value === undefined) {
          message = `Attributet "${name}" är obligatoriskt på <${t.name}>.`;
        } else if (value.trim() === '') {
          message = `Attributet "${name}" på <${t.name}> får inte vara tomt.`;
        }
        if (message !== null) {
          diagnostics.push({ from: t.from, to: t.to, severity: 'error', message });
        }
      }
    },
  });

  return diagnostics;
});
