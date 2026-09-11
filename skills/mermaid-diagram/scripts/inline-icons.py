#!/usr/bin/env python3
"""
Make an mmdc-exported SVG self-contained.

mmdc writes image shapes as <image href="/absolute/path/icon.png"
preserveAspectRatio="none">. That breaks two ways: the absolute filesystem
path does not survive moving or sharing the SVG (and markdown previews
generally refuse to load it), and preserveAspectRatio="none" stretches the
icon to the node box, which is sized from the label rather than the image.

This rewrites each referenced PNG as an inline base64 data URI and restores
proportional scaling.

Usage:
    inline-icons.py <svg-path> [<svg-path> ...]

Edits in place. Exits non-zero if a referenced icon is missing.
"""

import base64
import pathlib
import re
import sys

HREF = re.compile(r'href="([^"]+\.(?:png|jpg|jpeg|svg))"')

MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
}


def inline(svg_path: pathlib.Path) -> tuple[int, list[str]]:
    """Inline every local image reference. Returns (count, missing_paths)."""
    text = svg_path.read_text()
    missing: list[str] = []
    count = 0

    def replace(match: re.Match) -> str:
        nonlocal count
        raw = match.group(1)
        if raw.startswith("data:"):
            return match.group(0)

        candidate = pathlib.Path(raw)
        if not candidate.is_absolute():
            candidate = (svg_path.parent / candidate).resolve()

        if not candidate.is_file():
            missing.append(raw)
            return match.group(0)

        mime = MIME.get(candidate.suffix.lower(), "application/octet-stream")
        encoded = base64.b64encode(candidate.read_bytes()).decode("ascii")
        count += 1
        return f'href="data:{mime};base64,{encoded}"'

    text = HREF.sub(replace, text)

    # mmdc hardcodes preserveAspectRatio="none" on image shapes, which distorts
    # the icon because the node box width comes from the label, not the image.
    text = text.replace(
        'preserveAspectRatio="none"',
        'preserveAspectRatio="xMidYMid meet"',
    )

    svg_path.write_text(text)
    return count, missing


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip(), file=sys.stderr)
        return 2

    failed = False
    for arg in argv:
        path = pathlib.Path(arg)
        if not path.is_file():
            print(f"error: not a file: {arg}", file=sys.stderr)
            failed = True
            continue

        count, missing = inline(path)
        print(f"{path.name}: inlined {count} image(s)")
        for ref in missing:
            print(f"  error: referenced icon not found: {ref}", file=sys.stderr)
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
