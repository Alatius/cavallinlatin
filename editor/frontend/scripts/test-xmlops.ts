// Run the case spec in src/editor/xmlOps.cases.ts against the live tagOp.
// Run from editor/frontend/:
//   node --experimental-strip-types scripts/test-xmlops.ts

import { EditorState, EditorSelection } from '@codemirror/state';
import { ensureSyntaxTree } from '@codemirror/language';
import { xml } from '@codemirror/lang-xml';

import { tagOp } from '../src/editor/xmlOps.ts';
import { cases, type Case } from '../src/editor/xmlOps.cases.ts';

// `[selected]` → { doc, from, to }. Empty selection: `[]`.
function parseInput(s: string): { doc: string; from: number; to: number } {
  const lb = s.indexOf('[');
  const rb = s.indexOf(']');
  if (lb < 0 || rb < 0 || rb < lb) throw new Error(`bad markers: ${s}`);
  const doc = s.slice(0, lb) + s.slice(lb + 1, rb) + s.slice(rb + 1);
  return { doc, from: lb, to: rb - 1 };
}

function renderOutput(doc: string, from: number, to: number): string {
  return doc.slice(0, from) + '[' + doc.slice(from, to) + ']' + doc.slice(to);
}

function runCase(c: Case): { ok: boolean; actual: string } {
  const { doc, from, to } = parseInput(c.input);
  const state = EditorState.create({
    doc,
    extensions: [xml()],
    selection: EditorSelection.range(from, to),
  });
  // Force-parse so syntaxTree returns a complete tree.
  ensureSyntaxTree(state, doc.length, 5000);
  const wrap = tagOp(state, state.selection.main, c.apply);
  let actual: string;
  if (wrap === null) {
    actual = renderOutput(doc, from, to);
  } else {
    const next = state.update({ changes: wrap.changes }).state;
    actual = renderOutput(next.doc.toString(), wrap.selection.from, wrap.selection.to);
  }
  return { ok: actual === c.expected, actual };
}

let pass = 0;
const fails: Array<{ c: Case; actual: string }> = [];
for (const c of cases) {
  const { ok, actual } = runCase(c);
  if (ok) pass++;
  else fails.push({ c, actual });
}

for (const { c, actual } of fails) {
  console.log(`FAIL ${c.name}`);
  console.log(`  input    : ${c.input}`);
  console.log(`  expected : ${c.expected}`);
  console.log(`  actual   : ${actual}`);
}
console.log(`\n${pass}/${cases.length} passed, ${fails.length} failed.`);
process.exit(fails.length === 0 ? 0 : 1);
