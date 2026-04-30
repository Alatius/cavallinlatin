"""Cross-language drift checks (M5, tier 1).

Doesn't unify the implementations — just catches divergence in CI before it
ships:

  * Status / EntryType / STATUS_VALUES — parse types.ts and compare to the
    Python Literal members.
  * fold() — extract the TS body from HeadwordsContext.tsx, run it via
    `node -e` over a representative input set, assert byte-equal output
    with the Python fold().
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import get_args

import pytest

from app import models, text


_FRONTEND = Path(__file__).resolve().parents[2] / 'frontend' / 'src'
TYPES_TS = _FRONTEND / 'api' / 'types.ts'
HEADWORDS_TSX = _FRONTEND / 'components' / 'HeadwordsContext.tsx'


def _parse_union(ts_source: str, name: str) -> set[str]:
    m = re.search(rf'export type {name}\s*=\s*([^;]+);', ts_source)
    if not m:
        raise AssertionError(f'TS union {name!r} not found in types.ts')
    return set(re.findall(r"'([^']+)'", m.group(1)))


def _parse_array_const(ts_source: str, name: str) -> list[str]:
    m = re.search(rf'export const {name}[^=]*=\s*\[(.*?)\];', ts_source, re.DOTALL)
    if not m:
        raise AssertionError(f'TS const {name!r} not found in types.ts')
    return re.findall(r"'([^']+)'", m.group(1))


def _parse_fold_body(tsx_source: str) -> str:
    # Match from the open brace's trailing newline to a `}` at the start of
    # a line — that's the function's closing brace, not the `}` inside the
    # `\p{M}` regex literal in the body.
    m = re.search(
        r'export function fold\(\s*s\s*:\s*string\s*\)\s*:\s*string\s*\{\n(.*?)\n\}',
        tsx_source, re.DOTALL,
    )
    if not m:
        raise AssertionError('fold() not found in HeadwordsContext.tsx')
    return m.group(1)


# ----- Status / EntryType ------------------------------------------------

def test_status_union_matches_python_literal():
    ts_values = _parse_union(TYPES_TS.read_text(), 'Status')
    py_values = set(get_args(models.Status))
    assert ts_values == py_values, (
        f'Status drift: TS has {ts_values - py_values}, Python has {py_values - ts_values}'
    )


def test_entry_type_union_matches_python_literal():
    ts_values = _parse_union(TYPES_TS.read_text(), 'EntryType')
    py_values = set(get_args(models.EntryType))
    assert ts_values == py_values, (
        f'EntryType drift: TS has {ts_values - py_values}, Python has {py_values - ts_values}'
    )


def test_status_values_array_matches_union():
    src = TYPES_TS.read_text()
    arr = _parse_array_const(src, 'STATUS_VALUES')
    union = _parse_union(src, 'Status')
    assert set(arr) == union, (
        f'STATUS_VALUES has drifted from Status union: array={arr}, union={union}'
    )


# ----- fold() -----------------------------------------------------------

# Inputs span the cases the function actually encounters: ordinary ASCII,
# uppercase, Latin macrons / breves the dictionary uses for vowel quantity,
# Greek (a few etymology entries cite Greek), ligatures, mixed punctuation.
FOLD_SAMPLES = [
    'Abacus',
    'ĂBĂVUS',
    'ăbăvus',
    'Caesar',
    'plērusque',
    'Ămō',
    'Hīc, illīc',
    'COEPI',
    'Æquus',
    'Διός',
    '',
    '  spaced  ',
    'A B C',
    "It's",
]


@pytest.mark.skipif(shutil.which('node') is None, reason='node not on PATH')
def test_ts_fold_matches_python_fold():
    body = _parse_fold_body(HEADWORDS_TSX.read_text())
    js = (
        f'function fold(s) {{\n{body}\n}}\n'
        'const inputs = JSON.parse(process.argv[1]);\n'
        'process.stdout.write(JSON.stringify(inputs.map(fold)));\n'
    )
    proc = subprocess.run(
        ['node', '-e', js, json.dumps(FOLD_SAMPLES)],
        check=True, capture_output=True, text=True,
    )
    js_out = json.loads(proc.stdout)
    py_out = [text.fold(s) for s in FOLD_SAMPLES]
    mismatches = [
        (s, j, p) for s, j, p in zip(FOLD_SAMPLES, js_out, py_out) if j != p
    ]
    assert not mismatches, f'fold() diverges: {mismatches}'
