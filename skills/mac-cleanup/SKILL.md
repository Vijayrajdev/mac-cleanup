---
name: mac-cleanup
description: Safe, approval-first Mac cleanup. Scans caches, build folders, unused apps, leftovers from uninstalled apps and VS Code extensions, rates each item Safe / Caution / Risky, shows a themed HTML report, and moves only approved items to the Trash. Use when the user says "clean my mac", "free up space", "monthly cleanup" or runs /mac-cleanup.
---

# Mac cleanup

<!-- Author: Vijay Raj C K · https://vijayraj.vercel.app/ · https://github.com/Vijayrajdev/mac-cleanup · MIT -->

Find what is safe to remove on this Mac, explain every item in plain language, show a visual report, and remove **only** what the user approves.

## Ground rules

1. **Scan first, change nothing.** Every scan command is read-only.
2. **Explain everything.** For each item: what it is, its size, why it isn't needed, what happens if it's removed, and how to undo it.
3. **Rate every item** with one of three risk levels (below). Never guess "Safe" — when unsure, use "Caution".
4. **Ask before removing.** Wait for the user to choose groups. Use AskUserQuestion with `multiSelect` for optional items.
5. **Move to Trash, never `rm`.** Use `mv` into `~/.Trash/<descriptive-name>` so everything can be restored. The user empties the Trash.
6. **Never touch:** `~/Documents`, `~/Desktop`, `~/Pictures`, `~/Music`, `~/Movies`, Downloads contents (only *suggest* big or old downloads), project source code, `~/.ssh`, Keychains, `~/.claude`, password-manager or browser profile data, anything under `/System`.
7. **No sudo.** For root-owned paths (`/Library/...`, some apps in `/Applications`), give the user one ready-to-paste `sudo bash -c '...'` command that moves things to `~/.Trash`. Never type or ask for their password.
8. **Privacy-protected folders.** macOS blocks some `~/Library/Containers` and `~/Library/Group Containers` paths ("Operation not permitted"). Tell the user to drag those to the Trash in Finder (Cmd+Shift+G), and to check for Office autosaves first.
9. **zsh gotchas.** An unquoted `$LIST` does not word-split in zsh and unmatched globs abort the whole command. Run loops inside `bash -c '...'` or use `setopt nullglob`.

## Risk levels

| Level | Badge | Meaning | Examples |
|---|---|---|---|
| Safe | 🟢 | Regenerated automatically, no effect on the user | npm/Homebrew/pip caches, VS Code caches, `.next`, `dist`, `__pycache__`, old duplicate extension versions, leftovers of apps that are no longer installed |
| Caution | 🟡 | Removable, but there is a one-time cost (re-download, rebuild, re-login, setting reset) | `node_modules` / `.venv` in idle projects, apps unused for 60+ days, themes, extensions for unused languages |
| Risky | 🔴 | Could lose data or break something the user relies on | anything that might hold user files (Office group containers, app data of an *installed* app), language runtimes other projects use, big files in Downloads |

🔴 items are never bundled into a group answer. List them individually and ask about each one by name.

## 1. Overview

```bash
df -h /System/Volumes/Data
du -sh ~/* ~/.[!.]* 2>/dev/null | sort -rh | head -30
du -sh ~/.Trash 2>/dev/null
```

If the Trash is large, remind the user to empty it — space is only freed then.

## 2. Caches (usually 🟢)

- `~/.npm/_cacache`, `~/.npm/_npx`
- `~/Library/Caches/Homebrew` (or preview `brew cleanup -n`)
- `~/Library/Caches/pip`, `~/.cache/uv`, `~/.cache/pip`
- `~/Library/Application Support/Code/{Cache,CachedData,CachedExtensionVSIXs}`
- `du -sh ~/Library/Caches/* | sort -rh | head` for anything else large

## 3. Project folders

Find the user's code folders (look for `~/Development`, `~/Projects`, `~/code`, `~/dev`, `~/src`, `~/GitHub`).

```bash
find <dir> -maxdepth 4 -type d \( -name node_modules -o -name .next -o -name dist -o -name build -o -name .venv -o -name venv -o -name __pycache__ -o -name target \) -prune -exec du -sh {} + 2>/dev/null | sort -rh
```

For each project, find when its source last changed (ignore the folders above). Then:
- `.next`, `dist`, `build`, `__pycache__`: 🟢 anywhere.
- `node_modules`, `.venv`, `venv`, `target`: 🟡, and only for projects untouched for ~3 months. Say how to recreate them (`npm install`, `python3 -m venv .venv && pip install -r requirements.txt`, `cargo build`).
- Before suggesting a virtualenv, read its `pyvenv.cfg` — if `home` points at a Python install that's otherwise unused, mention it.

## 4. Apps

```bash
for a in /Applications/*.app ~/Applications/*.app; do
  s=$(du -sh "$a" | cut -f1)
  lu=$(mdls -raw -name kMDItemLastUsedDate "$a" | cut -c1-10)
  [ -d "$a/Contents/_MASReceipt" ] && st=AppStore || st=""
  echo "$s | used:$lu | $st | $a"
done
```

Suggest apps not opened in 60+ days as 🟡. App Store apps can be re-downloaded for free; say so. Never suggest Claude, the user's code editor, terminal, or the app they used to install this skill.

## 5. Leftovers from uninstalled apps

- Compare `~/Library/Application Support/*`, `~/Library/Preferences/*.plist`, `~/Library/Containers`, `~/Library/Group Containers` against installed apps.
- Orphaned background jobs (their program no longer exists):
  ```bash
  for p in ~/Library/LaunchAgents/*.plist /Library/LaunchAgents/*.plist /Library/LaunchDaemons/*.plist; do
    prog=$(plutil -extract Program raw "$p" 2>/dev/null || plutil -extract ProgramArguments.0 raw "$p" 2>/dev/null)
    [ -e "$prog" ] || echo "ORPHAN: $p -> $prog"
  done
  launchctl list | grep -v com.apple   # exit codes other than 0/- mean a job keeps failing
  ```
  Stop a user agent before moving it: `launchctl bootout gui/$(id -u) <plist>`.
- Before calling something a leftover, check that no installed tool still uses it (e.g. a CLI that an editor extension downloads).

## 6. VS Code extensions (if VS Code is installed)

`code` CLI: `"/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"`.

1. List extensions with sizes from `~/.vscode/extensions`, and read `~/Library/Application Support/Code/User/settings.json` for the active `workbench.colorTheme`, `workbench.iconTheme` and `editor.defaultFormatter` entries.
2. Count file types in the user's project folders (ts, tsx, js, py, sql, tf, java, cpp, c, go, rs, ipynb, vue, sol…).
3. Group suggestions:
   - 🟢 old duplicate versions (two folders for one extension — VS Code only uses the newest)
   - 🟡 themes / icon sets that aren't active
   - 🟡 language tools with no matching files in any project
   - 🟡 deprecated or duplicate extensions (e.g. IntelliCode, Remote-WSL on a Mac, several snippet packs for the same thing)
   - "Your call" for anything that depends on habits (AI assistants, Jira, Live Share…)
4. Uninstall with `code --uninstall-extension <id>` inside a `bash -c` loop, **two passes** (extension packs block their members on the first pass). If one still refuses, its error names the extension that depends on it — tell the user.
5. Remind the user to quit VS Code (Cmd+Q) and reopen it — only then are the folders deleted.

## 7. Visual report

After scanning, write the findings as JSON and render the themed report that ships with this skill:

```bash
python3 "<this skill's folder>/scripts/render_report.py" /path/to/findings.json --open
```

Put `findings.json` in a temporary folder (e.g. `$TMPDIR/mac-cleanup/`). The renderer writes `report.html` next to it and opens it in the browser. Schema:

```json
{
  "machine": "Alex's MacBook Air",
  "disk": { "total_gb": 228, "free_gb": 119 },
  "groups": [
    {
      "id": "A",
      "title": "Caches",
      "summary": "Temporary downloads that apps rebuild automatically.",
      "items": [
        {
          "name": "npm download cache",
          "path": "~/.npm/_cacache",
          "size_mb": 2450,
          "risk": "safe",
          "why": "Copies of packages npm already downloaded.",
          "effect": "Next npm install re-downloads what it needs.",
          "undo": "Restore from Trash, or just run npm install."
        }
      ]
    }
  ],
  "keep": [ { "name": "Python 3.12", "why": "Default python3; used by 2 projects." } ],
  "manual": [ "Drag ~/Library/Group Containers/UBF8T346G9.* to the Trash in Finder." ]
}
```

`risk` is `safe`, `caution` or `risky`. Every field except `path`, `effect` and `undo` is required.

The report is read-only — it never deletes anything. Removal happens only in this conversation.

## 8. Present and confirm

In the chat, give a short summary (disk free, reclaimable total by risk level) and a numbered table per group with the risk badge on each row. Then ask which groups to remove.

Right before removing, print a confirmation block:

```
⚠️  About to move to Trash
🟢 A. Caches ................................ 2.9 GB
🟡 D. node_modules in 2 idle projects ....... 900 MB
🔴 Office group container (may hold autosaved documents) — confirmed individually
Everything goes to ~/.Trash and can be restored until you empty it.
```

## 9. Remove and verify

- Move only approved items to `~/.Trash/<descriptive-name>` and print `trashed: <path>` per item, or `FAILED: <path>` with the reason.
- Re-run the relevant listing to confirm.
- Finish with: what was moved, how much space it frees once the Trash is emptied, anything the user must do by hand (the sudo command, Finder drags, restarting VS Code), and a reminder to empty the Trash when happy.
