#!/usr/bin/env python3
"""Rebrand Chromium -> Saturn in the UI string resources, keeping translations.

Chromium keys each translation (.xtb) by a fingerprint of the English source
text. Editing the English text in a .grd changes that fingerprint, so the
translations would silently fall back to English. This script edits the .grd
text, recomputes every message id with grit itself, and moves the matching
translations to the new ids (with "Chromium" -> "Saturn" in their text too).

Mentions of the Chromium *project* ("The Chromium Authors", "Chromium open
source project", ...) are left alone. Safe to run twice (second run is a no-op).

Usage: python3 rebrand_strings.py <chromium src dir>
"""

import glob
import os
import re
import sys

BRAND = 'Saturn'

# (grd file, translation glob) pairs, relative to src. The grd's <part> files
# are found and edited automatically.
TARGETS = [
    ('chrome/app/chromium_strings.grd', 'chrome/app/resources/chromium_strings_*.xtb'),
    ('components/components_chromium_strings.grd',
     'components/strings/components_chromium_strings_*.xtb'),
]

# "Chromium" not followed by a project-ish word.
SOURCE_RE = re.compile(r'\bChromium\b(?! ?(?:Authors|open[ -]source|project|OS\b|Projects?))')
TEXT_SEGMENT_RE = re.compile(r'>([^<]*)<')
PART_RE = re.compile(r'<part\s+file="([^"]+)"')
TRANSLATION_RE = re.compile(r'(<translation id=")(\d+)("[^>]*>)(.*?)(</translation>)', re.S)


def load_grit(src):
  sys.path.insert(0, os.path.join(src, 'tools', 'grit'))
  from grit import grd_reader  # pylint: disable=import-outside-toplevel
  from grit.node import message  # pylint: disable=import-outside-toplevel
  return grd_reader, message


def message_ids(grd_reader, message_mod, grd_path):
  root = grd_reader.Parse(grd_path, skip_validation_checks=True)
  ids = []
  for node in root.Preorder():
    if isinstance(node, message_mod.MessageNode):
      ids.append((node.attrs['name'], node.GetCliques()[0].GetId()))
  return ids


def rebrand_markup(text):
  # Only touch text between tags, never attributes (names, desc, meaning).
  return TEXT_SEGMENT_RE.sub(lambda m: '>' + SOURCE_RE.sub(BRAND, m.group(1)) + '<', text)


def grd_files(grd_path):
  files = [grd_path]
  with open(grd_path, encoding='utf-8') as f:
    for part in PART_RE.findall(f.read()):
      files.append(os.path.join(os.path.dirname(grd_path), part))
  return files


def process(src, grd_rel, xtb_glob, grd_reader, message_mod):
  grd_path = os.path.join(src, grd_rel)
  before = message_ids(grd_reader, message_mod, grd_path)

  changed_files = 0
  for path in grd_files(grd_path):
    with open(path, encoding='utf-8', newline='') as f:
      old = f.read()
    new = rebrand_markup(old)
    if new != old:
      with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(new)
      changed_files += 1

  after = message_ids(grd_reader, message_mod, grd_path)
  if [n for n, _ in before] != [n for n, _ in after]:
    sys.exit(f'{grd_rel}: message order changed while rebranding; aborting')
  id_map = {old: new for (_, old), (_, new) in zip(before, after) if old != new}

  moved = 0
  for xtb in sorted(glob.glob(os.path.join(src, xtb_glob))):
    with open(xtb, encoding='utf-8', newline='') as f:
      old = f.read()

    def fix(m):
      nonlocal moved
      if m.group(2) not in id_map:
        return m.group(0)
      moved += 1
      body = re.sub(r'\bChromium\b', BRAND, m.group(4))
      return m.group(1) + id_map[m.group(2)] + m.group(3) + body + m.group(5)

    new = TRANSLATION_RE.sub(fix, old)
    if new != old:
      with open(xtb, 'w', encoding='utf-8', newline='') as f:
        f.write(new)
  print(f'{grd_rel}: {changed_files} grd/grdp files edited, '
        f'{len(id_map)} messages renamed, {moved} translations moved')


def main():
  if len(sys.argv) != 2:
    sys.exit(__doc__)
  src = os.path.abspath(sys.argv[1])
  grd_reader, message_mod = load_grit(src)
  for grd_rel, xtb_glob in TARGETS:
    process(src, grd_rel, xtb_glob, grd_reader, message_mod)


if __name__ == '__main__':
  main()
