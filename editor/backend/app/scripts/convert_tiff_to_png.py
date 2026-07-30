"""One-shot: convert columns/*.tiff to editor/data/columns/*.png.

Downsamples to 50% linear scale and keeps 1-bit bilevel encoding via
Floyd-Steinberg dithering, so files stay small while text remains crisp
at display size. Browsers antialias 1-bit PNGs when CSS-scaled.
Idempotent: skips files already present in the destination unless --force.

Existing data/columns/*.png predate the greyscale step in convert_one and
were effectively nearest-neighbour decimated; re-run with --force to replace
them (~18% larger files, noticeably cleaner text).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from PIL import Image


SCALE = 0.5


def convert_one(src: Path, dst: Path) -> int:
    with Image.open(src) as img:
        w, h = img.size
        new_size = (max(1, round(w * SCALE)), max(1, round(h * SCALE)))
        # Convert to greyscale *before* resizing. The sources are group-4
        # bilevel (mode '1'), and PIL silently falls back to NEAREST for mode
        # '1' regardless of the filter you ask for — and convert('1') on an
        # already-bilevel image has nothing to dither. So both halves of this
        # pipeline were no-ops and the whole corpus was decimated with
        # nearest-neighbour, the worst possible choice for text.
        grey = img.convert('L')
        resized = grey.resize(new_size, Image.LANCZOS)
        bilevel = resized.convert('1', dither=Image.Dither.FLOYDSTEINBERG)
        dst.parent.mkdir(parents=True, exist_ok=True)
        bilevel.save(dst, format='PNG', optimize=True)
    return dst.stat().st_size


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--src', type=Path,
                   default=Path(__file__).resolve().parents[4] / 'columns')
    p.add_argument('--dst', type=Path,
                   default=Path(__file__).resolve().parents[3] / 'data' / 'columns')
    p.add_argument('--force', action='store_true',
                   help='Re-convert even if output already exists')
    p.add_argument('--limit', type=int,
                   help='Convert at most N files (for spot-checking)')
    args = p.parse_args(argv)

    if not args.src.is_dir():
        print(f'Source not found: {args.src}', file=sys.stderr)
        return 1

    tiffs = sorted(args.src.glob('*.tiff'))
    if args.limit:
        tiffs = tiffs[:args.limit]
    if not tiffs:
        print(f'No .tiff files in {args.src}', file=sys.stderr)
        return 1

    args.dst.mkdir(parents=True, exist_ok=True)

    t0 = time.monotonic()
    converted = 0
    skipped = 0
    total_bytes = 0
    for i, src in enumerate(tiffs, 1):
        dst = args.dst / (src.stem + '.png')
        if dst.exists() and not args.force:
            skipped += 1
            continue
        size = convert_one(src, dst)
        total_bytes += size
        converted += 1
        if converted % 100 == 0 or i == len(tiffs):
            elapsed = time.monotonic() - t0
            print(f'  {i}/{len(tiffs)}  converted={converted}  '
                  f'skipped={skipped}  {elapsed:.1f}s', flush=True)

    avg_kb = total_bytes / converted / 1024 if converted else 0
    print(f'Done. converted={converted} skipped={skipped} '
          f'total={total_bytes / 1024 / 1024:.1f} MB  avg={avg_kb:.1f} KB')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
