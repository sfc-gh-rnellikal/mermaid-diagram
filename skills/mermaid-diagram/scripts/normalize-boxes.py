#!/usr/bin/env python3
"""
Normalize box geometry in a Mermaid-generated SVG.

Mermaid sizes every node to its own text and exposes no node-width property, so
peer nodes doing the same job render at different widths (measured spread up to
25px on a 5-stage diagram, giving box aspect ratios from 2.61 to 2.93). Group
rects inherit the same raggedness. Author-side label tuning reduces this but
cannot eliminate it.

This pass rewrites the geometry attributes after `mmdc` has run:

  1. Every node rect is set to a single width, centred on its node origin.
  2. Node columns are squared up -- but only for nodes no edge attaches to, so
     baked edge paths are never left dangling.
  3. Group rects are set to a common x and width, with their titles re-centred.

Attributes are edited directly rather than via `themeCSS`, because themeCSS is
applied to the live DOM only: it affects a rasterized PNG but never reaches the
exported SVG, and Mermaid strips it from frontmatter config as unsafe.

Usage:
    python3 normalize-boxes.py DIAGRAM.svg [--pad 28] [--dry-run]
"""

import argparse
import re
import sys
import xml.etree.ElementTree as ET

NODE_RE = re.compile(
    r'(<g class="node[^"]*" id="flowchart-(?P<name>[^-]+)-\d+"[^>]*'
    r'transform="translate\((?P<cx>[-\d.]+),\s*(?P<cy>[-\d.]+)\)"[^>]*>)'
    r'(?P<mid>.*?)'
    r'(?P<rect><rect[^>]*class="basic label-container"[^>]*/>)',
    re.S,
)
RECT_ATTR_RE = re.compile(r'(?P<key>\bx|\bwidth)="(?P<val>[-\d.]+)"')
CLUSTER_RE = re.compile(
    r'<g class="cluster" id="(?P<id>[^"]+)"[^>]*>'
    r'<rect(?P<rattrs>[^>]*)/>'
    r'<g class="cluster-label" transform="translate\((?P<lx>[-\d.]+),\s*(?P<ly>[-\d.]+)\)"',
    re.S,
)
EDGE_PT_RE = re.compile(r'<path[^>]*class="[^"]*flowchart-link[^"]*"[^>]*d="([^"]+)"')
TRANSLATE_RE = re.compile(r'translate\(\s*([-\d.]+)(?:[ ,]+([-\d.]+))?\s*\)')


def tag_name(tag):
    return tag.rsplit('}', 1)[-1]


def translate_xy(transform):
    if not transform:
        return 0.0, 0.0
    m = TRANSLATE_RE.search(transform)
    if not m:
        return 0.0, 0.0
    return float(m.group(1)), float(m.group(2) or 0.0)


def edge_endpoints(svg):
    """Start and end coordinates of every drawn edge path."""
    pts = []
    for d in EDGE_PT_RE.findall(svg):
        nums = re.findall(r'(-?\d+(?:\.\d+)?)[, ](-?\d+(?:\.\d+)?)', d)
        if nums:
            pts.append(tuple(map(float, nums[0])))
            pts.append(tuple(map(float, nums[-1])))
    return pts


def collect_nodes(svg):
    out = []
    for m in NODE_RE.finditer(svg):
        attrs = dict(
            (a.group('key'), float(a.group('val')))
            for a in RECT_ATTR_RE.finditer(m.group('rect'))
        )
        if 'width' not in attrs:
            continue
        out.append(
            {
                'name': m.group('name'),
                'cx': float(m.group('cx')),
                'cy': float(m.group('cy')),
                'w': attrs['width'],
                'span': m.span(),
            }
        )
    return out


def group_columns(nodes, tol=60.0):
    """Cluster node centres into columns by x proximity."""
    cols = []
    for n in sorted(nodes, key=lambda n: n['cx']):
        if cols and n['cx'] - cols[-1][-1]['cx'] <= tol:
            cols[-1].append(n)
        else:
            cols.append([n])
    return cols


def collect_cluster_boxes(svg):
    """Cluster rects in absolute SVG coordinates."""
    root = ET.fromstring(svg)
    boxes = []

    def walk(elem, dx=0.0, dy=0.0):
        tx, ty = translate_xy(elem.get('transform'))
        abs_dx, abs_dy = dx + tx, dy + ty

        if tag_name(elem.tag) == 'g' and 'cluster' in (elem.get('class') or '').split():
            rect = next((child for child in elem if tag_name(child.tag) == 'rect'), None)
            if rect is not None:
                boxes.append(
                    {
                        'id': elem.get('id'),
                        'x': float(rect.get('x', '0')) + abs_dx,
                        'y': float(rect.get('y', '0')) + abs_dy,
                        'width': float(rect.get('width', '0')),
                        'height': float(rect.get('height', '0')),
                    }
                )

        for child in elem:
            walk(child, abs_dx, abs_dy)

    walk(root)
    return boxes


def nested_cluster_ids(boxes, tol=0.01):
    nested = set()
    for box in boxes:
        x1 = box['x']
        y1 = box['y']
        x2 = x1 + box['width']
        y2 = y1 + box['height']
        for other in boxes:
            if other['id'] == box['id']:
                continue
            ox1 = other['x']
            oy1 = other['y']
            ox2 = ox1 + other['width']
            oy2 = oy1 + other['height']
            contains = ox1 <= x1 + tol and oy1 <= y1 + tol and ox2 >= x2 - tol and oy2 >= y2 - tol
            strictly_larger = (
                ox1 < x1 - tol or oy1 < y1 - tol or ox2 > x2 + tol or oy2 > y2 + tol
            )
            if contains and strictly_larger:
                nested.add(box['id'])
                break
    return nested


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('svg')
    ap.add_argument('--pad', type=float, default=28.0,
                    help='horizontal padding between group border and node edge')
    ap.add_argument('--square-columns', action='store_true',
                    help='also snap node columns to a common x. Only safe when '
                         'the diagram has clean, well-separated columns; column '
                         'detection is by x-proximity and can merge distinct '
                         'columns in wide multi-column graphs.')
    ap.add_argument('--strict', action='store_true',
                    help='exit non-zero when the pass would leave the SVG unchanged')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    original_svg = open(args.svg, encoding='utf-8').read()
    svg = original_svg
    nodes = collect_nodes(svg)
    if not nodes:
        print('normalize-boxes: no flowchart nodes found; nothing to do')
        if args.strict:
            print('normalize-boxes: --strict, exiting 2 because the SVG was unchanged')
            return 2
        return 0

    target_w = max(n['w'] for n in nodes)
    if len({n['w'] for n in nodes}) > 1:
        # Round up to an even number with a little breathing room. Skipped when
        # the widths already agree, so re-running the pass is idempotent rather
        # than inflating every box by 4px each time.
        target_w = float(int(target_w) + (int(target_w) % 2) + 4)
    half = target_w / 2.0

    # Only reposition nodes that no edge terminates on.
    endpoints = edge_endpoints(svg)
    def anchored(n):
        return any(abs(px - n['cx']) < half and abs(py - n['cy']) < 60
                   for px, py in endpoints)

    moves = {}
    for col in group_columns(nodes):
        anchored_xs = [n['cx'] for n in col if anchored(n)]
        # An anchored column must keep its x or the baked edge paths break.
        target_cx = anchored_xs[0] if anchored_xs else max(n['cx'] for n in col)
        for n in col:
            movable = args.square_columns and not anchored(n)
            if movable and abs(n['cx'] - target_cx) > 0.01:
                moves[n['name']] = target_cx
            n['new_cx'] = target_cx if movable else n['cx']

    # Rewrite node rects (and transforms for movable nodes), right to left.
    for n in sorted(nodes, key=lambda n: -n['span'][0]):
        s, e = n['span']
        block = svg[s:e]
        block = RECT_ATTR_RE.sub(
            lambda m: f'{m.group("key")}="{-half if m.group("key") == "x" else target_w}"',
            block,
        )
        if n['name'] in moves:
            # Rewrite only the x component of the existing transform. Do not
            # reconstruct the whole string: the source may carry "72" where
            # Python would render "72.0", and the replacement would silently
            # not match.
            block = re.sub(
                r'(transform="translate\()([-\d.]+)(,)',
                lambda m: f'{m.group(1)}{moves[n["name"]]:.6g}{m.group(3)}',
                block,
                count=1,
            )
        svg = svg[:s] + block + svg[e:]

    # Square up the group rects and re-centre their titles.
    left = min(n['new_cx'] for n in nodes) - half - args.pad
    right = max(n['new_cx'] for n in nodes) + half + args.pad
    cl_w, cl_x = right - left, left

    cluster_boxes = collect_cluster_boxes(svg)
    nested_ids = nested_cluster_ids(cluster_boxes)

    # Groups that are alone in their vertical band. Sibling groups laid out side
    # by side share a y range, and giving them a common x and width would slam
    # them on top of each other -- they would render as a single box with one
    # border hidden entirely. Keyed by id, because siblings can have byte
    # identical y and height and so cannot be told apart by geometry alone.
    solo_ids = {
        box['id']
        for box in cluster_boxes
        if not any(
            other['id'] != box['id']
            and box['y'] < other['y'] + other['height']
            and other['y'] < box['y'] + box['height']
            for other in cluster_boxes
        )
    }

    widened = []

    def fix_cluster(m):
        old_x = float(re.search(r'\bx="([-\d.]+)"', m.group('rattrs')).group(1))
        old_w = float(re.search(r'\bwidth="([-\d.]+)"', m.group('rattrs')).group(1))

        if nested_ids or m.group('id') not in solo_ids:
            return m.group(0)

        widened.append(m.group('id'))
        rattrs = RECT_ATTR_RE.sub(
            lambda a: f'{a.group("key")}="{cl_x if a.group("key") == "x" else cl_w}"',
            m.group('rattrs'),
        )
        # Shift the title by the same delta as the group centre. This avoids
        # needing the label's own width, which is only exposed on the HTML-label
        # path -- with htmlLabels: false the title is <text>/<tspan> instead.
        delta = (cl_x + cl_w / 2.0) - (old_x + old_w / 2.0)
        new_lx = float(m.group('lx')) + delta
        return (
            m.group(0)
            .replace(m.group('rattrs'), rattrs, 1)
            .replace(
                f'translate({m.group("lx")}, {m.group("ly")})',
                f'translate({new_lx:.4f}, {m.group("ly")})',
                1,
            )
        )

    svg, n_matched = CLUSTER_RE.subn(fix_cluster, svg)
    # Report groups actually widened, not groups matched. subn counts every match
    # even though fix_cluster returns side-by-side siblings untouched, so the
    # match count would claim a merge that did not happen -- and would equally
    # hide one that did.
    skipped = n_matched - len(widened)
    if nested_ids:
        summary = f'cluster normalization skipped for nested diagram ({n_matched} clusters skipped)'
    else:
        summary = f'{len(widened)} of {n_matched} groups widened'
        if skipped:
            summary += f' ({skipped} left alone, side by side)'

    print(f'normalize-boxes: {len(nodes)} nodes -> width {target_w:g}, '
          f'{len(moves)} repositioned, {summary}'
          + (f' -> x {cl_x:.2f} width {cl_w:.2f}' if widened else ''))
    changed = svg != original_svg
    if args.dry_run:
        print('normalize-boxes: --dry-run, file not written')
        if args.strict and not changed:
            print('normalize-boxes: --strict, exiting 2 because the SVG was unchanged')
            return 2
        return 0

    open(args.svg, 'w', encoding='utf-8').write(svg)
    if args.strict and not changed:
        print('normalize-boxes: --strict, exiting 2 because the SVG was unchanged')
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
