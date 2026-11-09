"""Converts simple stroked/filled SVGs (as exported from Figma) to Chromium
.icon files. Supports <path d> with M L H V C Z (absolute or relative) and
<circle>. Usage:
  svg_to_icon.py in.svg out.icon --canvas 20 [--dx 0 --dy 0]
"""
import argparse
import re
import xml.etree.ElementTree as ET

HEADER = """// Copyright 2026 The Saturn Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Generated from the Figma design by saturn/scripts/svg_to_icon.py.
"""


def fmt(v):
    s = ('%.4f' % v).rstrip('0').rstrip('.')
    if s in ('-0', ''):
        s = '0'
    return s + ('f' if '.' in s else '')


def tokens(d):
    return re.findall(r'[MmLlHhVvCcZz]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?', d)


def convert_path(d, dx, dy):
    out = []
    t = tokens(d)
    i = 0
    cmd = None
    cx = cy = sx = sy = 0.0

    def num():
        nonlocal i
        v = float(t[i])
        i += 1
        return v

    while i < len(t):
        if re.match(r'[A-Za-z]', t[i]):
            cmd = t[i]
            i += 1
            if cmd in 'Zz':
                out.append('CLOSE,')
                cx, cy = sx, sy
                continue
        rel = cmd.islower()
        c = cmd.upper()
        if c == 'M':
            x, y = num(), num()
            if rel:
                x, y = cx + x, cy + y
            cx, cy, sx, sy = x, y, x, y
            out.append('MOVE_TO, %s, %s,' % (fmt(x + dx), fmt(y + dy)))
            cmd = 'l' if rel else 'L'
        elif c == 'L':
            x, y = num(), num()
            if rel:
                x, y = cx + x, cy + y
            cx, cy = x, y
            out.append('LINE_TO, %s, %s,' % (fmt(x + dx), fmt(y + dy)))
        elif c == 'H':
            x = num()
            if rel:
                x += cx
            cx = x
            out.append('H_LINE_TO, %s,' % fmt(x + dx))
        elif c == 'V':
            y = num()
            if rel:
                y += cy
            cy = y
            out.append('V_LINE_TO, %s,' % fmt(y + dy))
        elif c == 'C':
            p = [num() for _ in range(6)]
            if rel:
                p = [p[k] + (cx if k % 2 == 0 else cy) for k in range(6)]
            cx, cy = p[4], p[5]
            out.append('CUBIC_TO, ' + ', '.join(
                fmt(p[k] + (dx if k % 2 == 0 else dy)) for k in range(6)) + ',')
        else:
            raise ValueError('unsupported command ' + cmd)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--canvas', type=float, required=True)
    ap.add_argument('--dx', type=float, default=0)
    ap.add_argument('--dy', type=float, default=0)
    ap.add_argument('--stroke', type=float, default=None,
                    help='override stroke width')
    a = ap.parse_args()

    root = ET.parse(a.src).getroot()
    lines = ['CANVAS_DIMENSIONS, %s,' % fmt(a.canvas).rstrip('f')]
    first = True
    for el in root.iter():
        tag = el.tag.split('}')[-1]
        if tag not in ('path', 'circle'):
            continue
        if not first:
            lines.append('NEW_PATH,')
        first = False
        stroke = el.get('stroke')
        opacity = el.get('fill-opacity') or el.get('stroke-opacity')
        if opacity:
            lines.append('PATH_COLOR_ALPHA, 0x%02X,' % round(float(opacity) * 255))
        if tag == 'circle':
            lines.append('CIRCLE, %s, %s, %s,' % (
                fmt(float(el.get('cx')) + a.dx), fmt(float(el.get('cy')) + a.dy),
                fmt(float(el.get('r')))))
            continue
        if stroke and stroke != 'none':
            w = a.stroke or float(el.get('stroke-width', '1'))
            lines.append('STROKE, %s,' % fmt(w))
        lines += convert_path(el.get('d'), a.dx, a.dy)
    open(a.dst, 'w', newline='\n').write(HEADER + '\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
