# Saturn

Saturn is a personal, open-source Chromium browser built on
[ungoogled-chromium](https://github.com/ungoogled-software/ungoogled-chromium-windows)
(Windows). This folder holds the tooling plus Saturn's own patches. Chromium's
source lives in the ungoogled checkout.

## Layout

| Path | What |
|---|---|
| `ungoogled-chromium-windows\` | ungoogled checkout (tag `157.0.8103.38-1.1`). Not part of this repo. |
| `ungoogled-chromium-windows\build\src\` | Chromium source, **a git repo** (see below) |
| `…\src\out\Default\` | official release build (ungoogled `build.py`) |
| `…\src\out\Dev\` | fast dev build (`dev-build.cmd`) |
| `saturn\patches\` | Saturn's patches (`git format-patch` files) + `series` |
| `saturn\scripts\rebrand_strings.py` | Chromium → Saturn in UI strings, keeps translations |
| `saturn\scripts\build_saturn.py` | wraps ungoogled's `build.py` with Saturn's steps |
| `saturn\dev.gn` | GN args for `out\Dev` |
| `dev-build.cmd` | incremental dev build → `build-dev.log` |
| `build-saturn.cmd` | full release build from a fresh ungoogled tag → `build-release.log` |
| `watch-build.ps1` | progress meter: `watch-build.ps1 -Log build-dev.log` |

## Daily work (dev build)

```
dev-build.cmd                      # gn gen + ninja chrome, logs to build-dev.log
powershell -ExecutionPolicy Bypass -File watch-build.ps1 -Log build-dev.log
ungoogled-chromium-windows\build\src\out\Dev\chrome.exe --user-data-dir=C:\Users\ignit\saturn_dev\test-profile
```

`out\Dev` is `is_official_build=false`, component build, `symbol_level=1`, no
PGO/LTO, plus ungoogled's privacy flags. Edit `saturn\dev.gn`, not
`out\Dev\args.gn` (the script regenerates it). The first build takes a while;
after that only changed files rebuild. A dev build is slower at runtime than a
release build, so judge speed with the release build.

## How Saturn's changes are tracked

**Choice: a git repo inside `build\src` + exported patch files.**

- `build\src` is a git repo. Its first commit (tag `base-<ungoogled tag>`) is the
  pristine tree right after ungoogled's patches. `out\` is not tracked.
  Some third-party folders that are git repos of their own are recorded as
  gitlinks, not content; don't patch inside those.
- Saturn's work happens on branch `saturn`, **one commit per patch**, in
  `git commit` messages starting with `Saturn:`.
- The last commit, `Generated: rebrand_strings.py`, is script output and is not
  exported (it gets regenerated on every update).
- The commits are exported to `saturn\patches\` with `git format-patch`; that
  folder (plus scripts) is what this repo keeps and what release builds apply.

Why git and not quilt: git does diffs, rebases and 3-way merges for us, and
`git am --3way` copes with small upstream drift during monthly updates.

### Changing a patch / adding one

```
cd ungoogled-chromium-windows\build\src
git checkout saturn
# new patch: edit files, then
git commit -am "Saturn: <what>"
# fix an existing patch: commit with --fixup <sha>, then
git rebase -i --autosquash base-157.0.8103.38-1.1
```

Then re-export (keep the generated commit out; it is always last):

```
git rebase -i base-157.0.8103.38-1.1    # move/drop the Generated commit to the end if needed
del ..\..\..\saturn\patches\*.patch
git format-patch --zero-commit --no-signature -o ..\..\..\saturn\patches base-157.0.8103.38-1.1..HEAD~1
cd ..\..\..\saturn\patches && dir /b *.patch > series
```

Commit `saturn_dev` afterwards.

### Current patches

1. **0001 product branding** – `BRANDING` (product/company name → exe version
   info, installer), `chromium_install_modes.h` (user data in
   `%LOCALAPPDATA%\Saturn\User Data`, app id/ProgIDs). UI strings (window
   title, About, menus, default profile name "Your Saturn") come from
   `rebrand_strings.py`, which edits `chromium_strings.grd` /
   `components_chromium_strings.grd` and moves the ~46k translations to the
   new message ids so other languages keep working. Mentions of the Chromium
   *project* ("The Chromium Authors", "Chromium open source project") stay.
   The exe is still named `chrome.exe`.
2. **0002 saturn:// scheme** – `saturn://` is the visible name of `chrome://`.
   Internally pages are still `chrome://` so WebUI, permissions and policies
   are untouched. Typed input (`url_fixer.cc`) and browser navigations
   (`BrowserURLHandler`) map `saturn://` → `chrome://`; `url_formatter::FormatUrl`
   shows `chrome://` as `saturn://` everywhere URLs are displayed; the omnibox
   treats `saturn:` as a URL and suggests `saturn://` pages. 6 files, ~60 lines.
3. **0003 component build fix** – drops one export (`CordRepBtree::AddEdge<1>`)
   from abseil's x64 `.def` files; ungoogled's clang inlines it, so the
   `out\Dev` component build failed to link. Release builds don't use `.def`
   files. Drop this patch once upstream's `.def` matches again.
4. **0004 sidebar layout (phase 1)** – Arc-style sidebar built on Chromium's
   native vertical tabs (on by default, 258px). The toolbar (back/forward/
   reload, sidebar toggle, sliders = app menu, URL pill) moves into the
   sidebar; a 25px "Saturn" title bar; the page is a card with 10px margins and
   5px corners; dark-mode colors from the Figma design (sidebar #454545, title
   bar #161616, 38px tab rows, "New tab" row at 40%). Collapsing the sidebar
   (toggle or Ctrl+Shift+L) or fullscreen falls back to the stock layout.
   Sizes/colors live in `chrome/browser/ui/views/frame/saturn_sidebar_constants.h`.
5. **0005 sidebar phase 2** – while expanded, Chromium's pinned tabs become a
   3-column favorites grid (46px tiles, white 5%, no outline); a divider with
   **Clear** (closes today's unpinned tabs, opening a fresh tab first if
   nothing is pinned) and the New tab row sit between the grid and today's
   tabs. The header lives in `TabStripView` (`SetSaturnTodayHeader`) and is
   built in `vertical_tab_strip_region_view.cc`; collapsed, the stock rail and
   + button are unchanged. "Clear" is a hard-coded English string for now.
6. **0006 sidebar phase 3 (spaces, Pinned list)** – a space is a Chromium
   profile, so each space has its own cookies, favorites (pinned tabs) and
   Pinned list. The sidebar shows the space name ("Primary" for the initial
   profile) above the favorites; the Pinned list is the bookmark folder
   `Other bookmarks/Pinned` of that profile (click opens or switches to the
   page, right-click → Remove; tabs get "Add to Pinned list" in their context
   menu; helpers in `chrome/browser/ui/tabs/saturn_pinned_folder.h`). The
   bottom bar has Downloads, one dot per space (click switches: the target
   space's window takes this window's place and this one minimizes) and +
   (new space via the profile picker). Rename a space in its profile
   settings. Strings are hard-coded English for now.
7. **0007 sidebar matches Figma** (node 4126:990) – icons exported from Figma
   (`saturn\figma-icons\*.svg`, converted with `saturn\scripts\svg_to_icon.py`
   into `chrome/app/vector_icons/saturn_*.icon`); square buttons on white-5%
   tiles. The window gets a DWM **acrylic** backdrop (blurs what's behind it;
   needs Windows 11 with transparency effects on) and the sidebar is #161616
   at 80% over it; the title bar stays opaque. **Inter** and **JetBrains Mono**
   (`saturn\fonts`, OFL) ship in `saturn_fonts\` next to the binaries, are
   sideloaded into DirectWrite at startup, and Inter becomes the default UI
   font. The app menu opens from the bottom-left settings button; the
   sliders button opens site settings (page info); the URL pill drops the
   location icon and gets a copy-link button; Figma window controls.

## Monthly update (release build)

When ungoogled-chromium-windows publishes a new tag:

```
build-saturn.cmd 158.0.xxxx.yy-1.1
powershell -ExecutionPolicy Bypass -File watch-build.ps1 -Log build-release.log
```

It clones the tag into `release\<tag>\` (download cache shared with the main
checkout), runs ungoogled's `build.py --tarball`, and in between:

1. makes `build\src` a git repo (base commit) and applies `saturn\patches\series`
   with `git am --3way`, then runs `rebrand_strings.py`;
2. copies `gn.exe` to `buildtools\win\` (V8 metagen needs it; otherwise ninja
   fails around 33%) and builds with `DEPOT_TOOLS_WIN_TOOLCHAIN=0`.

Output: `release\<tag>\build\src\out\Default\chrome.exe` and `mini_installer.exe`.
Each tree is large; delete old `release\` folders.

**If a patch no longer applies**, the log shows the `git am` failure. Fix it in
that tree: `cd release\<tag>\build\src`, resolve the files, `git add`,
`git am --continue`, then re-export the patches as above (base tag there is the
first commit) and rerun with a fresh folder. Then move dev work to the new tree.

## Build gotchas

- Raw ninja needs `VsDevCmd.bat -arch=x64` and `DEPOT_TOOLS_WIN_TOOLCHAIN=0`
  (both scripts do this).
- V8 metagen needs `gn.exe` in `build\src\buildtools\win\`.
- ungoogled prunes the checked-in `.tlb` files; `midl.py` then leaves 0-byte
  `.tlb` placeholders in `third_party\win_build_output` and asserts on them in
  any later build. Both scripts delete 0-byte `.tlb` files before ninja.
- Clang 23 can't build Chromium's precompiled headers, so `dev.gn` sets
  `enable_precompiled_headers=false` (official builds don't use PCH anyway).
- Python 3.12 at `%LOCALAPPDATA%\Programs\Python\Python312` with the `clang`
  pip package (for V8 metagen's libclang bindings).
