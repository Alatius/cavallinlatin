import { syntaxTree } from '@codemirror/language';
import { xmlLanguage } from '@codemirror/lang-xml';
import { EditorSelection } from '@codemirror/state';
import { EditorView } from '@codemirror/view';

// Auto-fill the closing tag when the user types `/` to start a close tag.
// We can't use `xmlLang({ autoCloseTags: true })` because that *also* auto-
// inserts `</tag>` after a typed `>`, which fights the "mark up existing
// text" workflow (the inserted close tag lands before the content the user
// wants to wrap). This extension is the slash-only half — lifted from
// lang-xml's autoCloseTags source.
export const closeTagOnSlash = EditorView.inputHandler.of(
  (view, from, to, text, insertTransaction) => {
    if (
      view.composing
      || view.state.readOnly
      || from !== to
      || text !== '/'
      || !xmlLanguage.isActiveAt(view.state, from, -1)
    ) return false;

    const base = insertTransaction();
    const { state } = base;
    const result = state.changeByRange((range) => {
      const { head } = range;
      if (state.doc.sliceString(head - 1, head) !== '/') return { range };
      const after = syntaxTree(state).resolveInner(head, -1);
      if (after.name !== 'StartCloseTag' || after.from !== head - 2) return { range };
      const elt = after.parent;
      if (!elt || elt.lastChild?.name === 'CloseTag') return { range };
      const tagNode = elt.firstChild?.getChild('TagName');
      if (!tagNode) return { range };
      const name = state.doc.sliceString(tagNode.from, tagNode.to);
      if (!name) return { range };
      const closingTo = head + (state.doc.sliceString(head, head + 1) === '>' ? 1 : 0);
      const insert = `${name}>`;
      return {
        range: EditorSelection.cursor(head + insert.length, -1),
        changes: { from: head, to: closingTo, insert },
      };
    });
    if (result.changes.empty) return false;
    view.dispatch([
      base,
      state.update(result, { userEvent: 'input.complete', scrollIntoView: true }),
    ]);
    return true;
  },
);
