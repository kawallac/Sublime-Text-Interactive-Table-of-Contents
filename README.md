# Sublime-Text-Interactive-Table-of-Contents
This plugin for Sublime Text is an interactive table of contents for markdown files. When activated the  plugin reads the current markdown file and generates a table of contents from the headings. The table  of contents is interactive. By clicking a heading in the table of contents it will take the cursor to that spot in the document. 

# Deployment
- Save markdown_toc_interactive.py file in the folder '~./sublime-text/Packages/User/'
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
