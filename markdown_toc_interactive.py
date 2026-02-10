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
        matches = [(m.group(1), m.group(2), m.start()) for m in re.finditer(r'^(#+)\s+(.*)', content, re.MULTILINE)]
        
        # Updated UI Layout
        toc_text = "MARKDOWN NAVIGATION\n"
        toc_text += f"Active: {display_name}\n"  # Line index 1
        toc_text += "[Refresh]\n"     # Line index 2 (The "Button")
        toc_text += ("=" * 30) + "\n\n"
        
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
        
        sel = self.view.sel()[0]
        line_row, _ = self.view.rowcol(sel.begin())
        
        # 1. Handle "Refresh" Click (Line index 2 / Row 3)
        if line_row == 2:
            source_view_id = self.view.settings().get("toc_source_id")
            if source_view_id:
                self.view.run_command("markdown_toc_update", {"source_view_id": source_view_id})
            return

        # 2. Handle Header Jumps (Headers now start at line index 5 / Row 6)
        header_index = line_row - 5
        positions = self.view.settings().get("header_positions", [])
        
        if 0 <= header_index < len(positions):
            source_view = sublime.View(self.view.settings().get("toc_source_id"))
            if source_view.is_valid():
                target_pos = positions[header_index]
                source_view.window().focus_view(source_view)
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