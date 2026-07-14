'''
v1.1

- Sublime Text Markdown ToC Plugin

# Purpose
This plugin for Sublime Text is an interactive table of contents for markdown files. When activated the 
plugin reads the current markdown file and generates a table of contents from the headings. The table 
of contents is interactive. By clicking a heading in the table of contents it will take the cursor to that
spot in the document. 

# Deployment Linux
- Save markdown_toc_interactive.py file in the folder '.config/sublime-text/Packages/User/'
- Create keyboard shortcut to open the plugin
    - Go to Preferences > Key Bindings and add this line:
        { "keys": ["ctrl+1"], "command": "open_markdown_toc" }
    - Change out 'ctrl+1' with your prefered keyboard shortcut

# Functionality
- Use keyboard shortcut to open and close plugin
- Click a heading in the plugin to go to that heading in the document
- Click [Refresh] to refresh the ToC, also saving the file and switching tabs and back will refresh

# Changelog
- 26-02-10 v1.1 : Converted [Close] to [Refresh], use the keyboard shortcut to close the plugin 
- 26-02-06 v1.0 : Initial creation; reads the .md file headings and generates a ToC. 
    Switch between .md tabs and the ToC automatically updates to active tab.
    Refreshes on saving .md file.
'''

import sublime
import sublime_plugin
import re
import os

class MarkdownTocUpdateCommand(sublime_plugin.TextCommand):
    def run(self, edit, source_view_id):
        source_view = sublime.View(source_view_id)
        if not source_view.is_valid():
            return

        file_path = source_view.file_name()
        display_name = os.path.basename(file_path) if file_path else "Untitled"

        content = source_view.substr(sublime.Region(0, source_view.size()))
        matches = self._extract_headings(content)

        # UI layout: build the fixed header block as a list of lines so the row
        # of the [Refresh] button and the start row of the headings are derived
        # from the layout instead of hardcoded. The listener reads these back.
        refresh_label = "[Refresh]"
        header_lines = [
            "MARKDOWN NAVIGATION",
            f"Active: {display_name}",
            refresh_label,
            "=" * 30,
            "",  # blank separator before the headings
        ]
        refresh_row = header_lines.index(refresh_label)
        header_start_row = len(header_lines)

        toc_text = "\n".join(header_lines) + "\n"

        regions = []
        for level, title, pos in matches:
            indent = "  " * (len(level) - 1)
            toc_text += f"{indent}• {title}\n"
            regions.append(pos)

        self.view.set_read_only(False)
        self.view.replace(edit, sublime.Region(0, self.view.size()), toc_text)
        self.view.set_read_only(True)

        self.view.settings().set("toc_source_id", source_view_id)
        self.view.settings().set("header_positions", regions)
        self.view.settings().set("toc_refresh_row", refresh_row)
        self.view.settings().set("toc_header_start_row", header_start_row)

    @staticmethod
    def _extract_headings(content):
        """Return (level, title, char_offset) for each ATX heading, skipping
        anything inside fenced code blocks so code comments aren't treated as
        headings."""
        heading_re = re.compile(r'^(#+)\s+(.*)')
        fence_re = re.compile(r'^\s*(```|~~~)')
        matches = []
        offset = 0
        in_fence = False
        for line in content.splitlines(keepends=True):
            if fence_re.match(line):
                in_fence = not in_fence
            elif not in_fence:
                m = heading_re.match(line)
                if m:
                    matches.append((m.group(1), m.group(2).rstrip(), offset))
            offset += len(line)
        return matches

class MarkdownTocListener(sublime_plugin.ViewEventListener):
    def on_activated_async(self):
        if self.view.score_selector(0, "text.html.markdown"):
            self.update_toc_panel()

    def on_post_save_async(self):
        if self.view.score_selector(0, "text.html.markdown"):
            self.update_toc_panel()

    def update_toc_panel(self):
        window = self.view.window()
        if not window: return
        toc_view = next((v for v in window.views() if v.name() == "Navigation"), None)
        if toc_view:
            toc_view.run_command("markdown_toc_update", {"source_view_id": self.view.id()})

    def on_selection_modified(self):
        if self.view.name() != "Navigation":
            return

        # Only react to genuine user interaction with the panel. When the TOC is
        # rebuilt programmatically the cursor moves too, but the panel is not the
        # active view; acting on that would steal focus and can create a
        # focus/refresh feedback loop.
        window = self.view.window()
        if not window or window.active_view() != self.view:
            return

        sel = self.view.sel()
        if len(sel) == 0:
            return
        line_row, _ = self.view.rowcol(sel[0].begin())

        settings = self.view.settings()
        refresh_row = settings.get("toc_refresh_row")
        header_start_row = settings.get("toc_header_start_row")
        if refresh_row is None or header_start_row is None:
            return

        # 1. Handle "Refresh" click.
        if line_row == refresh_row:
            source_view_id = settings.get("toc_source_id")
            if source_view_id:
                self.view.run_command("markdown_toc_update", {"source_view_id": source_view_id})
            return

        # 2. Handle header jumps.
        header_index = line_row - header_start_row
        positions = settings.get("header_positions", [])

        if 0 <= header_index < len(positions):
            source_view = sublime.View(settings.get("toc_source_id"))
            source_window = source_view.window() if source_view.is_valid() else None
            if source_window:
                target_pos = positions[header_index]
                source_window.focus_view(source_view)
                source_view.sel().clear()
                source_view.sel().add(sublime.Region(target_pos, target_pos))
                source_view.show_at_center(target_pos)

class CloseMarkdownTocCommand(sublime_plugin.WindowCommand):
    def run(self):
        toc_view = next((v for v in self.window.views() if v.name() == "Navigation"), None)
        if toc_view:
            self.window.focus_view(toc_view)
            self.window.run_command("close_file")
            
        self.window.set_layout({
            "cols": [0.0, 1.0], "rows": [0.0, 1.0], "cells": [[0, 0, 1, 1]]
        })

class OpenMarkdownTocCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        window = self.view.window()
        if not window:
            return
        toc_view = next((v for v in window.views() if v.name() == "Navigation"), None)
        
        if toc_view:
            window.run_command("close_markdown_toc")
            return
        
        if window.num_groups() < 2:
            window.set_layout({
                "cols": [0.0, 0.8, 1.0], "rows": [0.0, 1.0], "cells": [[0, 0, 1, 1], [1, 0, 2, 1]]
            })
            
        toc_view = window.new_file()
        toc_view.set_name("Navigation")
        toc_view.set_scratch(True)
        toc_view.settings().set("word_wrap", False)
        # Ensure the navigation panel itself doesn't trigger its own listener
        toc_view.settings().set("is_toc_panel", True) 
        window.set_view_index(toc_view, 1, 0)
        
        toc_view.run_command("markdown_toc_update", {"source_view_id": self.view.id()})
        window.focus_view(self.view)