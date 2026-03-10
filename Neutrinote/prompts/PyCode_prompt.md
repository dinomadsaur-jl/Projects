You are an expert Python developer specializing in clean, modern CLI applications. Build a minimal viable console-based Google Docs clone (local-only MVP text editor) using pure Python — no web frameworks, no JavaScript, no GUI libraries (no Tkinter, PyQt, curses unless absolutely necessary).

Core features and acceptance criteria:
- Editable document title (default: "Untitled document")
- Multi-line rich text editing with support for:
  - Bold, italic, underline (shown via ANSI styles in terminal)
  - Bullet lists (- or •) and numbered lists (1., 2., etc.)
  - Headings (e.g. # H1, ## H2, ### H3 — rendered with bigger/bolder ANSI style)
- Basic formatting commands via keyboard shortcuts (e.g. Ctrl+B for bold, Ctrl+I for italic, etc.)
- Auto-save document (title + content with formatting markers) to a local JSON file on exit or every few changes
- Auto-load from the JSON file when starting the program (if exists)
- Clean terminal UI: show current title at top, editor area below, status/help bar at bottom
- Single-user, local only — no network, no real-time anything

Required tech stack (use exactly this — minimal dependencies):
- Python 3.9+
- rich >= 13.0 (for beautiful terminal formatting, panels, live display, ANSI styles)
- prompt_toolkit >= 3.0 (for advanced key bindings, multiline input, styled text editing)
  - Install: pip install rich prompt_toolkit
- json (standard library) for save/load
- No other external packages (no textual, no typer, no click unless needed for CLI args)

Desired project architecture and folder structure (follow exactly):
docs-editor/
├── main.py                 # Entry point: sets up the application, key bindings, main loop
├── editor/
│   ├── __init__.py
│   ├── document.py         # Document class: holds title + content lines with formatting
│   ├── renderer.py         # Functions to render styled text to terminal using rich
│   └── storage.py          # Save/load logic (JSON file handling)
├── data/
│   └── document.json       # Auto-generated save file (gitignored)
└── requirements.txt        # rich prompt_toolkit

Architecture guidelines:
- Document class holds content as list of dicts: {"text": str, "bold": bool, "italic": bool, "underline": bool, "type": "paragraph"|"bullet"|"numbered"|"heading1"|"heading2"|"heading3"}
- Use prompt_toolkit's Application with key bindings for formatting toggles and navigation
- Live rendering with rich.Live to update the screen in real time
- Storage: simple JSON serialization (store formatting as flags)
- Minimal state machine: title edit mode vs content edit mode (toggle with e.g. Ctrl+T)
- Graceful exit on Ctrl+C / Ctrl+Q with auto-save

Resources and references (follow closely):
- prompt_toolkit documentation: https://python-prompt-toolkit.readthedocs.io/en/master/
  - Especially: key bindings, Application, FormattedText, ANSI color/style support
- rich documentation: https://rich.readthedocs.io/en/stable/
  - Panels, Live display, bold/italic/underline styles, colors
- Example pattern: prompt_toolkit + rich for styled multiline editors (search for "prompt_toolkit rich live editor")

Strict constraints — Do NOT:
- Do NOT use any web technologies (FastAPI, Flask, HTML, Quill, TipTap, JavaScript)
- Do NOT use GUI libraries (Tkinter, PyQt, pygame, curses)
- Do NOT use heavy TUI frameworks (textual, urwid) — stick to prompt_toolkit + rich
- Do NOT add real-time collaboration, networking, authentication
- Do NOT use external databases — only local JSON file
- Do NOT start with lorem ipsum — start with empty document
- Do NOT add advanced features (tables, images, comments, export to PDF/docx)

Output format & steps:
1. Show the full folder structure (matching the one above)
2. Provide complete code for each file:
   - main.py
   - editor/document.py
   - editor/renderer.py
   - editor/storage.py
   - requirements.txt
3. Include exact terminal commands to set up & run:
   mkdir docs-editor
   cd docs-editor
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install rich prompt_toolkit
   # Create folders/files as above
   python main.py
4. After code: Add verification steps:
   "Run python main.py → see empty editor with title 'Untitled document' → type text → press Ctrl+B to toggle bold → add bullet list with - → edit title → exit with Ctrl+Q → restart → title and formatted content should reload. Check no crashes."

Think step-by-step before coding:
- Design Document data model (how to store formatting per line/span)
- Plan key bindings (navigation, formatting toggles, mode switch)
- Outline rendering pipeline: convert document model → rich Text → Live display
- Implement save/load with JSON (serialize formatting flags)
- Handle input loop with prompt_toolkit Application
- Ensure graceful shutdown and auto-save

Now implement the full, runnable pure-Python console text editor.