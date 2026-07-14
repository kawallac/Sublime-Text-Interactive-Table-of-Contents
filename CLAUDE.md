# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-file **Sublime Text plugin** (`markdown_toc_interactive.py`, Python 3.8 plugin host) that renders an interactive table of contents for the active Markdown file into a side panel. Clicking a heading in the panel jumps the source view to that heading; clicking `[Refresh]` rebuilds the TOC. There is no build system, no dependencies, and no test framework — the "runtime" is Sublime Text itself.

## Development workflow

There is no `build`/`lint`/`test` command. The two things you can do outside Sublime:

- **Syntax check:** `python3 -m py_compile markdown_toc_interactive.py` (then `rm -rf __pycache__` — bytecode is gitignored).
- **Deploy to test:** the plugin runs from `~/.config/sublime-text/Packages/User/markdown_toc_interactive.py`, which is a **plain copy**, not a symlink. Edits in this repo do nothing until copied there:
  ```
  cp markdown_toc_interactive.py ~/.config/sublime-text/Packages/User/
  ```
  Sublime auto-reloads plugins in `Packages/` on file change. **But if the plugin host has crashed (SIGABRT), auto-reload won't recover it — restart Sublime Text.**

Manual verification is the only real test: open the panel (keybinding bound to `open_markdown_toc`, e.g. `ctrl+1`), click headings, and repeatedly click `[Refresh]` (historically the crash trigger).

## Architecture

Three command/listener classes coordinate through a hidden scratch view named `"Navigation"` and its view-level settings:

- **`OpenMarkdownTocCommand`** (`open_markdown_toc`, the keybinding entry point) — toggles the panel: creates a 2-group layout + the `"Navigation"` scratch view, or closes it if already open.
- **`MarkdownTocUpdateCommand`** (`markdown_toc_update`) — a `TextCommand` run *on the Navigation view* that rebuilds its contents from a source view's headings.
- **`MarkdownTocListener`** (`ViewEventListener`, one instance per view) — rebuilds the TOC when a Markdown view is activated/saved, and handles clicks inside the Navigation panel via `on_selection_modified`.

State is passed entirely through `Navigation.settings()`:
- `toc_source_id` — the source view's `.id()` (rehydrated with `sublime.View(id)`; always `.is_valid()`-check it, the source may be closed).
- `header_positions` — list of **character offsets** (not row numbers) into the source buffer, one per heading, used for the jump target.
- `toc_refresh_row` / `toc_header_start_row` — the panel row of `[Refresh]` and the first heading, **derived from the layout** in `MarkdownTocUpdateCommand` and read back by the listener. Do not hardcode these row numbers in the listener; keep them layout-derived so the two classes stay in sync.

Headings are parsed by `MarkdownTocUpdateCommand._extract_headings`, which tracks fenced-code-block state (```` ``` ````/`~~~`) so `#` comments inside code blocks are not treated as headings. Offsets accumulate via `len(line)` over `splitlines(keepends=True)` so they match Sublime's character-based `Region` positions exactly.

## Critical constraint: never mutate views synchronously inside event callbacks

`on_selection_modified` fires **synchronously** on every selection change, including the ones your own code causes. The plugin's history is a series of crashes from violating this:

- Calling a view-mutating `run_command` (TOC rebuild, or moving another view's selection) directly inside `on_selection_modified` fires *more* selection events nested on the same call stack. On the `[Refresh]` row this re-triggered itself and recursed until the plugin host aborted with `Py_FatalError` / **SIGABRT** ("Cannot recover from stack overflow").

The established fix pattern, which any change here must preserve:
1. **Defer** the work off the event with `sublime.set_timeout(handler, 0)` so mutations run on a fresh call stack, never nested in event dispatch.
2. Guard with a **`toc_handling` reentrancy flag** (set before scheduling, cleared in a `finally`) so mutation-induced selection events are ignored until handling completes.
3. Only act when the panel is the **active view** (`window.active_view() == self.view`) — this skips events caused by programmatic rebuilds — and re-validate window/focus inside the deferred handler.

Also defensive-check `sel()` is non-empty before indexing `sel()[0]`, and null-check `view.window()` before use (a valid view can still return `None`).

## Working principles

- **Do it right; no shortcuts or workarounds.** Prefer correct, properly-installed tooling over dropping binaries into ad-hoc locations. If a task can't be done properly in this environment, say so rather than hacking around it.
- Deployment target path is Linux-specific (`~/.config/sublime-text/...`); the README also documents this. Keep README and this file consistent when changing deployment steps.
