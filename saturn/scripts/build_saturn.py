#!/usr/bin/env python3
"""Run ungoogled-chromium-windows' build.py with Saturn's additions.

Called by build-saturn.cmd from inside an ungoogled-chromium-windows checkout.
It runs build.py unchanged, but hooks two points of it:

  1. Right after ungoogled's patches + domain substitution: the tree is turned
     into a git repo (base commit = pristine ungoogled tree), Saturn's patches
     are applied with `git am`, and rebrand_strings.py runs (own commit).
  2. Right before ninja: gn.exe is copied to buildtools\\win (V8 metagen needs
     it there).

Usage: python build_saturn.py <build.py args...>   (cwd = ungoogled repo root)
"""

import os
import runpy
import shutil
import subprocess
import sys
from pathlib import Path

SATURN_DIR = Path(__file__).resolve().parent.parent      # saturn_dev\saturn
PATCH_DIR = SATURN_DIR / 'patches'
REPO_ROOT = Path.cwd()                                   # ungoogled-chromium-windows
SRC = REPO_ROOT / 'build' / 'src'


def log(msg):
  print(f'[saturn] {msg}', flush=True)


def git(*args):
  subprocess.run(['git', '-C', str(SRC), *args], check=True)


def apply_saturn_patches():
  if not (SRC / '.git').exists():
    log('creating git base commit of the ungoogled tree (takes a few minutes)')
    git('init', '-q', '-b', 'ungoogled')
    for key, value in [('core.autocrlf', 'false'), ('core.longpaths', 'true'),
                       ('feature.manyFiles', 'true'), ('core.fscache', 'true'),
                       ('gc.auto', '0'), ('user.name', 'Saturn'),
                       ('user.email', 'saturn@localhost')]:
      git('config', key, value)
    git('add', '-A', '-f', '--', '.', ':!out')
    git('commit', '-q', '-m', 'Base: pristine ungoogled-chromium tree')
  git('checkout', '-q', '-B', 'saturn')

  series = [l.strip() for l in (PATCH_DIR / 'series').read_text().splitlines()
            if l.strip() and not l.startswith('#')]
  for name in series:
    log(f'applying {name}')
    git('am', '-q', '--3way', '--keep-cr', str(PATCH_DIR / name))

  log('rebranding UI strings')
  subprocess.run([sys.executable, str(SATURN_DIR / 'scripts' / 'rebrand_strings.py'), str(SRC)],
                 check=True)
  git('add', '-A', '-f', '--', 'chrome/app', 'components')
  git('commit', '-q', '--allow-empty', '-m', 'Generated: rebrand_strings.py')


def main():
  os.environ['DEPOT_TOOLS_WIN_TOOLCHAIN'] = '0'
  sys.path.insert(0, str(REPO_ROOT))
  sys.argv = ['build.py', *sys.argv[1:]]

  import build  # pylint: disable=import-outside-toplevel,import-error

  # Hook 1: after domain substitution (the last step of ungoogled's patching).
  orig_substitute = build.domain_substitution.apply_substitution

  def substitute_then_patch(*args, **kwargs):
    orig_substitute(*args, **kwargs)
    apply_saturn_patches()

  build.domain_substitution.apply_substitution = substitute_then_patch

  # Hook 2: before ninja runs.
  orig_run = build._run_build_process  # pylint: disable=protected-access

  def run(*args, **kwargs):
    if args and str(args[0]).endswith('ninja.exe'):
      gn_src = SRC / 'out' / 'Default' / 'gn.exe'
      gn_dst = SRC / 'buildtools' / 'win' / 'gn.exe'
      log(f'copying {gn_src} -> {gn_dst}')
      shutil.copy2(gn_src, gn_dst)
      # midl.py leaves 0-byte .tlb placeholders (ungoogled prunes the real
      # ones); a rerun would assert on them.
      for tlb in (SRC / 'third_party' / 'win_build_output').rglob('*.tlb'):
        if tlb.stat().st_size == 0:
          tlb.unlink()
    return orig_run(*args, **kwargs)

  build._run_build_process = run  # pylint: disable=protected-access
  build.main()


if __name__ == '__main__':
  main()
