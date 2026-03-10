You are an expert Python developer specializing in desktop GUI applications and rich text editing. This project is a standalone, desktop-based rich text document editor inspired by tools like Notion or Google Keep, built with Tkinter and the Python standard library. It features a clean, minimalist interface with a document title, a formatting toolbar, and a persistent text area.

Core features and acceptance criteria:

· Rich Text Editing: Users can create and edit documents with standard formatting options (bold, italic, underline, strikethrough, headings, bullet lists, numbered lists, blockquotes) using a word-processor style interface.
· Persistent Document Storage: The document title and body content are automatically saved to a local JSON file upon every change or at a debounced interval, ensuring data persistence across application sessions without a database.
· Auto-Save Indicator: A visual indicator (e.g., "Saved" or "Saving...") in the status bar or title area provides feedback on the persistence state.
· Editable Title: The document title at the top of the window is an editable text field that is also saved to the local file.
· Formatting Toolbar: A toolbar with clearly labeled or icon-based buttons for text formatting. The active formatting state (e.g., bold button highlighted) reflects the current text selection.
· Clean, Minimal UI: The interface is uncluttered, focusing on the content with a traditional desktop application layout.

Required tech stack (use exactly these — no substitutes unless impossible):

· Language: Python 3.10+ (with type hints)
· GUI Framework: Tkinter (built-in, no external GUI frameworks)
· Rich Text Widget: Tkinter Text widget with custom tags for formatting
· Configuration/Persistence: JSON file storage (using Python's json module)
· Additional Libraries: Only Python standard library modules (no external PyPI packages except for development tools if needed)

Desired project architecture and folder structure (follow exactly):

```
project-root/
├── src/
│   ├── __init__.py
│   ├── main.py                 # Application entry point
│   ├── app.py                  # Main application window and setup
│   ├── components/
│   │   ├── __init__.py
│   │   ├── title_bar.py        # Editable title widget (Entry)
│   │   ├── toolbar.py          # Formatting buttons and controls (Frame with buttons)
│   │   ├── editor.py           # Rich text editor widget (Text with formatting tags)
│   │   └── status_bar.py       # Status indicator (Label for save status)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── document.py         # Document data model (dataclass)
│   │   └── persistence.py      # JSON file save/load functions
│   ├── utils/
│   │   ├── __init__.py
│   │   └── debouncer.py        # Simple debouncing mechanism for auto-save
│   └── types/
│       └── __init__.py         # Type definitions and protocols
├── data/
│   └── document.json           # Auto-generated persistent storage file
├── tests/
│   ├── __init__.py
│   ├── test_persistence.py
│   └── test_editor.py
├── .gitignore
├── README.md
├── requirements.txt            # For development tools (optional, e.g., pytest, mypy)
└── pyproject.toml              # Project configuration
```

Architecture rules:

· Separation of Concerns: The application follows a simple MVC-inspired pattern. app.py is the controller, components/ are the views, and core/document.py is the model. core/persistence.py handles data storage.
· Component Communication: The main App class instantiates all components and manages communication between them using Tkinter variables (StringVar, BooleanVar) and event callbacks.
· Persistence Strategy: On every keystroke or title change, a debounced function saves the current document state to data/document.json. The debouncer should wait for a short period of inactivity (e.g., 500ms) before writing to disk to improve performance. The status bar reflects the save state (saving/saved).
· Text Formatting: The editor uses Tkinter's Text widget with custom tags for formatting. Bold, italic, underline, and strikethrough are implemented using tag configurations. Headings use different font sizes. Lists are implemented using numbered/bullet prefixes with proper indentation.
· Type Hints: All function signatures must include type hints. Use dataclasses for data models.
· Error Handling: Implement graceful error handling for file I/O operations (permission errors, corrupt JSON). On startup, if no document exists, create a new one with default content.
· Testing: Unit tests should cover persistence logic and editor formatting functions.

Resources and references (follow these exactly):

· Python Tkinter Documentation
· Tkinter Text Widget Reference
· Python Dataclasses Documentation
· Python JSON Module
· Real Python: Python GUI With Tkinter

Strict constraints — Do NOT:

· Do NOT use any external GUI frameworks or libraries beyond the Python standard library.
· Do NOT use a database; persistence must rely solely on JSON file storage.
· Do NOT implement cloud synchronization, user accounts, or multi-document features.
· Do NOT use threading for complex background tasks (keep it simple with debouncing).
· Do NOT add any web components or browser integration.
· Do NOT use deprecated Python features or syntax.

Output requirements:

1. Ensure the folder structure above is created exactly.
2. Provide the full, working code for all Python files listed in the structure.
3. Include exact terminal setup & run commands: python src/main.py (after navigating to project root).
4. Add setup instructions: python -m venv venv (optional) and activation steps.
5. After code, add verification/test steps:
   · Run the application with python src/main.py
   · Verify the window opens with a title bar, toolbar, and text area
   · Type text in the editor and apply formatting (bold, italic, etc.) using the toolbar; confirm the changes are visible
   · Change the document title
   · Check that the status bar shows "Saved" after a brief pause
   · Close the application and reopen it; verify the title and editor content persist
   · Inspect data/document.json to verify the saved data structure

Think step-by-step before writing any code:

· Design the document data structure as a dataclass with fields for title and content (stored as plain text with format markers or HTML-like tags)
· Plan the persistence mechanism: JSON serialization of the document dataclass
· Design the debouncer: a simple class that uses after() to delay save operations
· Map out the editor formatting: create tag configurations for each format type, implement toggle functions that apply tags to selected text
· Design the toolbar: create a Frame with buttons that call editor formatting functions and reflect current state using tag checks
· Plan the layout using Tkinter grid/pack: title bar at top, toolbar below, text widget expanding in middle, status bar at bottom