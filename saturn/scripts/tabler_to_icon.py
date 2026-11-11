"""Converts Tabler outline icons (24x24, 2px round strokes) to Chromium .icon
files with Saturn's thinner menu stroke. Supports <path> (all commands but T),
<circle>, <rect>, <line>, <polyline>.

  tabler_to_icon.py in.svg out.icon [--stroke 1.8]
"""
import argparse
import re
import xml.etree.ElementTree as ET

HEADER = """// Copyright 2026 The Saturn Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Generated from a Tabler icon (MIT) by saturn/scripts/tabler_to_icon.py.
"""

ARGS = {'M': 2, 'L': 2, 'H': 1, 'V': 1, 'C': 6, 'S': 4, 'Q': 4, 'A': 7, 'Z': 0}
NAMES = {'M': 'MOVE_TO', 'L': 'LINE_TO', 'H': 'H_LINE_TO', 'V': 'V_LINE_TO',
         'C': 'CUBIC_TO', 'S': 'CUBIC_TO_SHORTHAND', 'Q': 'QUADRATIC_TO',
         'A': 'ARC_TO'}


def fmt(v):
    s = ('%.4f' % v).rstrip('0').rstrip('.')
    if s in ('-0', ''):
        s = '0'
    return s + ('f' if '.' in s else '')


def path_cmds(d):
    toks = re.findall(r'[A-Za-z]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?', d)
    out = []
    i = 0
    cmd = None
    while i < len(toks):
        if re.match(r'[A-Za-z]', toks[i]):
            cmd = toks[i]
            i += 1
        c = cmd.upper()
        if c not in ARGS:
            raise ValueError('unsupported command ' + cmd)
        if c == 'Z':
            out.append('CLOSE,')
            continue
        n = ARGS[c]
        vals = [float(v) for v in toks[i:i + n]]
        i += n
        name = NAMES[c]
        if cmd.islower():
            name = 'R_' + name
        out.append(name + ', ' + ', '.join(fmt(v) for v in vals) + ',')
        if c == 'M':
            cmd = 'l' if cmd.islower() else 'L'
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--stroke', type=float, default=1.8)
    a = ap.parse_args()
    root = ET.parse(a.src).getroot()
    lines = ['CANVAS_DIMENSIONS, 24,']
    first = True
    for el in root.iter():
        tag = el.tag.split('}')[-1]
        if tag not in ('path', 'circle', 'rect', 'line', 'polyline'):
            continue
        if el.get('stroke') == 'none':
            continue
        body = []
        g = lambda k: float(el.get(k, '0'))
        if tag == 'path':
            body = path_cmds(el.get('d'))
        elif tag == 'circle':
            body = ['CIRCLE, %s, %s, %s,' % (fmt(g('cx')), fmt(g('cy')),
                                            fmt(g('r')))]
        elif tag == 'rect':
            body = ['ROUND_RECT, %s, %s, %s, %s, %s,' % (
                fmt(g('x')), fmt(g('y')), fmt(g('width')), fmt(g('height')),
                fmt(g('rx')))]
        elif tag == 'line':
            body = ['MOVE_TO, %s, %s,' % (fmt(g('x1')), fmt(g('y1'))),
                    'LINE_TO, %s, %s,' % (fmt(g('x2')), fmt(g('y2')))]
        elif tag == 'polyline':
            pts = [float(v) for v in re.findall(r'-?[\d.]+', el.get('points'))]
            body = ['MOVE_TO, %s, %s,' % (fmt(pts[0]), fmt(pts[1]))]
            body += ['LINE_TO, %s, %s,' % (fmt(pts[k]), fmt(pts[k + 1]))
                     for k in range(2, len(pts), 2)]
        if el.get('fill') not in (None, 'none') and el.get('fill') != 'currentColor':
            pass
        if not first:
            lines.append('NEW_PATH,')
        first = False
        filled = el.get('fill') == 'currentColor'
        if not filled:
            lines.append('STROKE, %s,' % fmt(a.stroke))
        lines += body
    open(a.dst, 'w', newline='\n').write(HEADER + '\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
