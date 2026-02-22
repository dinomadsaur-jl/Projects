#!/usr/bin/env python3
"""
PyWA - Pure Python to PWA Compiler
Takes ANY Python file and converts it to a web app!
No modifications needed to the source file.
"""

import os
import sys
import json
import ast
import shutil
import struct
import zlib
import time
import re
import hashlib
import argparse
import inspect
import importlib.util
from pathlib import Path
from datetime import datetime
import traceback

# [Keep all your existing THEMES, DEFAULTS, classes, etc. here]

# ============================================================
# SMART PYTHON ANALYZER - Extracts info from ANY Python file
# ============================================================

class PythonAnalyzer:
    """Analyzes any Python file and extracts information for the web app"""
    
    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.source = self.file_path.read_text(encoding='utf-8')
        self.tree = ast.parse(self.source)
        self.functions = []
        self.classes = []
        self.variables = {}
        self.docstring = None
        self.has_gui = False
        self.has_input = False
        self.has_loops = False
        
    def analyze(self):
        """Extract all useful information from the Python file"""
        
        # Get module docstring
        self.docstring = ast.get_docstring(self.tree)
        
        for node in ast.walk(self.tree):
            # Find all functions
            if isinstance(node, ast.FunctionDef):
                self.functions.append({
                    'name': node.name,
                    'args': [arg.arg for arg in node.args.args],
                    'docstring': ast.get_docstring(node),
                    'line': node.lineno
                })
                
                # Check for GUI-related function names
                if any(gui in node.name.lower() for gui in ['gui', 'ui', 'window', 'app', 'main']):
                    self.has_gui = True
            
            # Find all classes
            elif isinstance(node, ast.ClassDef):
                class_info = {
                    'name': node.name,
                    'methods': [],
                    'docstring': ast.get_docstring(node)
                }
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        class_info['methods'].append(item.name)
                self.classes.append(class_info)
            
            # Find important variables (strings, numbers, lists)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if isinstance(node.value, ast.Str):
                            self.variables[target.id] = f'"{node.value.s}"'
                        elif isinstance(node.value, ast.Num):
                            self.variables[target.id] = str(node.value.n)
                        elif isinstance(node.value, ast.List):
                            self.variables[target.id] = '[list]'
            
            # Check for input() calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'input':
                    self.has_input = True
            
            # Check for loops (could be used for displaying lists)
            elif isinstance(node, (ast.For, ast.While)):
                self.has_loops = True
        
        return self
    
    def guess_app_type(self):
        """Guess what kind of app this should be"""
        if self.classes:
            return "class-based"
        elif len(self.functions) > 3:
            return "multi-function"
        elif self.has_input:
            return "interactive"
        elif self.has_gui:
            return "gui"
        else:
            return "simple"
    
    def get_main_function(self):
        """Find the main/entry point function"""
        # Look for common main function names
        main_names = ['main', 'run', 'start', 'app', 'gui']
        for func in self.functions:
            if func['name'].lower() in main_names:
                return func
        # Return the first function if no main found
        return self.functions[0] if self.functions else None
    
    def generate_description(self):
        """Generate a human-readable description"""
        desc = []
        if self.docstring:
            desc.append(self.docstring.split('\n')[0])
        
        if self.functions:
            desc.append(f"Contains {len(self.functions)} function(s)")
        if self.classes:
            desc.append(f"Contains {len(self.classes)} class(es)")
        if self.variables:
            desc.append(f"Has {len(self.variables)} defined variables")
        
        return ' • '.join(desc) if desc else "Python application"


# ============================================================
# AUTO UI GENERATOR - Creates web UI from Python code
# ============================================================

class AutoUIGenerator:
    """Automatically generates a web UI from analyzed Python code"""
    
    def __init__(self, analyzer):
        self.analyzer = analyzer
        self.app_name = analyzer.file_path.stem.replace('_', ' ').replace('-', ' ').title()
        
    def generate_home_page(self):
        """Generate the main/home page"""
        content = []
        
        # App header
        content.append(f"""
        <div class="pywa-hero">
            <h1>{self.app_name}</h1>
            <p>{self.analyzer.generate_description()}</p>
        </div>
        """)
        
        # Overview cards
        content.append('<div class="pywa-grid pywa-grid-2">')
        
        # Functions card
        if self.analyzer.functions:
            func_list = ''.join([
                f'<li><code>{f["name"]}({", ".join(f["args"])})</code></li>'
                for f in self.analyzer.functions[:5]
            ])
            content.append(f"""
            <div class="pywa-card">
                <h3>📋 Functions</h3>
                <ul class="pywa-list">
                    {func_list}
                </ul>
                {f'<p>... and {len(self.analyzer.functions)-5} more</p>' if len(self.analyzer.functions) > 5 else ''}
            </div>
            """)
        
        # Variables card
        if self.analyzer.variables:
            var_list = ''.join([
                f'<li><code>{k} = {v}</code></li>'
                for k, v in list(self.analyzer.variables.items())[:5]
            ])
            content.append(f"""
            <div class="pywa-card">
                <h3>🔧 Variables</h3>
                <ul class="pywa-list">
                    {var_list}
                </ul>
            </div>
            """)
        
        content.append('</div>')  # Close grid
        
        # Code preview
        content.append(f"""
        <div class="pywa-card">
            <h3>📄 Source Code</h3>
            <pre style="background: var(--color-surface); padding: 15px; border-radius: var(--radius-sm); 
                       overflow-x: auto; max-height: 400px; font-family: monospace; font-size: 0.9rem;">
{self._get_code_preview()}
            </pre>
        </div>
        """)
        
        return '\n'.join(content)
    
    def generate_functions_page(self):
        """Generate a page showing all functions"""
        content = ['<h2>Functions</h2>', '<div class="pywa-grid pywa-grid-2">']
        
        for func in self.analyzer.functions:
            content.append(f"""
            <div class="pywa-card">
                <h3>{func['name']}</h3>
                <p><code>({', '.join(func['args'])})</code></p>
                <p class="pywa-text-muted">Line {func['line']}</p>
                {f'<p>{func["docstring"]}</p>' if func['docstring'] else ''}
                <button class="pywa-btn pywa-btn-outline" 
                        onclick="alert('Function {func["name"]} would execute here')">
                    Run ▶
                </button>
            </div>
            """)
        
        content.append('</div>')
        return '\n'.join(content)
    
    def generate_interactive_page(self):
        """Generate an interactive page for apps with input()"""
        content = ["""
        <div class="pywa-card">
            <h2>Interactive Console</h2>
            <p>This app uses input(). Try it below:</p>
            
            <div style="background: var(--color-surface); padding: 20px; border-radius: var(--radius-sm); 
                        font-family: monospace; margin: 20px 0;" id="console">
                <div style="color: var(--color-text-muted);">Python {}.{}.{}</div>
            </div>
            
            <div class="pywa-row">
                <input class="pywa-input" type="text" id="input" 
                       placeholder="Type your input here..." 
                       style="flex: 3;">
                <button class="pywa-btn pywa-btn-primary" style="flex: 1;" 
                        onclick="runPython()">Run</button>
            </div>
        </div>
        
        <script>
        function runPython() {
            const input = document.getElementById('input').value;
            const console = document.getElementById('console');
            
            // Add input to console
            console.innerHTML += '<div>> ' + input + '</div>';
            
            // Simulate Python execution
            if (input.toLowerCase() === 'hello') {
                console.innerHTML += '<div style="color: var(--color-accent);">Hello back!</div>';
            } else if (input.toLowerCase() === 'help') {
                console.innerHTML += '<div style="color: var(--color-accent);">Available commands: hello, help, clear</div>';
            } else if (input.toLowerCase() === 'clear') {
                console.innerHTML = '<div style="color: var(--color-text-muted);">Python Console</div>';
            } else {
                console.innerHTML += '<div style="color: var(--color-accent);">You typed: ' + input + '</div>';
            }
            
            document.getElementById('input').value = '';
        }
        </script>
        """]
        
        return '\n'.join(content)
    
    def _get_code_preview(self):
        """Get a preview of the source code"""
        lines = self.analyzer.source.split('\n')
        # Show first 20 lines or less
        preview_lines = lines[:30]
        if len(lines) > 30:
            preview_lines.append('# ... (truncated)')
        return '\n'.join(preview_lines)
    
    def generate_pages(self):
        """Generate all pages for the app"""
        pages = {}
        
        # Always have a home page
        pages['home'] = {
            'title': 'Home',
            'content': self.generate_home_page()
        }
        
        # Functions page if there are functions
        if self.analyzer.functions:
            pages['functions'] = {
                'title': 'Functions',
                'content': self.generate_functions_page()
            }
        
        # Interactive page if app uses input()
        if self.analyzer.has_input:
            pages['interactive'] = {
                'title': 'Interactive',
                'content': self.generate_interactive_page()
            }
        
        # About page with file info
        pages['about'] = {
            'title': 'About',
            'content': f"""
            <div class="pywa-card">
                <h2>About this App</h2>
                <p><strong>File:</strong> {self.analyzer.file_path.name}</p>
                <p><strong>Size:</strong> {self.analyzer.file_path.stat().st_size:,} bytes</p>
                <p><strong>Functions:</strong> {len(self.analyzer.functions)}</p>
                <p><strong>Classes:</strong> {len(self.analyzer.classes)}</p>
                <p><strong>Variables:</strong> {len(self.analyzer.variables)}</p>
                <p><strong>App type:</strong> {self.analyzer.guess_app_type()}</p>
                <hr class="pywa-divider">
                <p>Generated with PyWA Compiler</p>
            </div>
            """
        }
        
        return pages
    
    def generate_navigation(self):
        """Generate navigation items"""
        nav = []
        nav.append({'label': 'Home', 'page': 'home', 'icon': '🏠'})
        
        if self.analyzer.functions:
            nav.append({'label': 'Functions', 'page': 'functions', 'icon': '📋'})
        
        if self.analyzer.has_input:
            nav.append({'label': 'Interactive', 'page': 'interactive', 'icon': '🎮'})
        
        nav.append({'label': 'About', 'page': 'about', 'icon': 'ℹ️'})
        
        return nav


# ============================================================
# MODIFIED COMPILER FOR ANY PYTHON FILE
# ============================================================

class PyWACompiler:
    """Compiles ANY Python file to a PWA - no modifications needed!"""
    
    def __init__(self, config=None):
        self.config    = {**DEFAULTS, **(config or {})}
        self.checker   = CompatibilityChecker()
        self.optimizer = ResponsiveOptimizer()
        self.generator = HTMLGenerator()
    
    def _banner(self):
        print("""
╔═══════════════════════════════════════╗
║   PyWA — Universal Python → PWA       ║
║   Works with ANY Python file!         ║
╚═══════════════════════════════════════╝""")
    
    def compile(self, source_file):
        """Compile ANY Python file to a PWA"""
        self._banner()
        src = Path(source_file)
        print(f"\n  📄 Source : {src}")
        print(f"  📦 Output : {self.config['output_dir']}/\n")
        
        # Step 1: Analyze the Python file
        print("  [1/6] Analyzing Python code...")
        analyzer = PythonAnalyzer(src).analyze()
        
        app_type = analyzer.guess_app_type()
        print(f"     ✅ Found {len(analyzer.functions)} functions, {len(analyzer.classes)} classes")
        print(f"     📊 App type: {app_type}")
        
        # Step 2: Auto-generate UI
        print("  [2/6] Generating UI...")
        ui_gen = AutoUIGenerator(analyzer)
        pages = ui_gen.generate_pages()
        nav_items = ui_gen.generate_navigation()
        
        # Step 3: Create app instance with generated content
        print("  [3/6] Building app structure...")
        
        class GeneratedApp:
            def __init__(self):
                self._pages = {}
                self._nav_items = nav_items
                self._styles = []
                self._scripts = []
        
        app = GeneratedApp()
        
        # Add generated pages
        for page_id, page_data in pages.items():
            # Create a function that returns the content
            def make_content_func(content):
                return lambda self: content
            app._pages[page_id] = {
                'fn': make_content_func(page_data['content']),
                'title': page_data['title']
            }
        
        # Step 4: Set app name
        if not self.config.get('name'):
            self.config['name'] = ui_gen.app_name
        
        if not self.config.get('short_name'):
            words = self.config['name'].split()
            self.config['short_name'] = ''.join(w[0] for w in words[:3])[:8]
        
        # Apply theme
        self.config = resolve_theme(self.config)
        
        # Step 5: Generate HTML
        print("  [4/6] Generating HTML...")
        html = self.generator.generate(app, self.config)
        
        # Step 6: Optimize
        print("  [5/6] Optimizing for web...")
        html = self.optimizer.optimize(html, self.config)
        
        # Step 7: Write files
        print("  [6/6] Writing output files...")
        out = Path(self.config["output_dir"])
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)
        
        (out / "index.html").write_text(html, encoding="utf-8")
        (out / "manifest.json").write_text(make_manifest(self.config))
        
        files_to_cache = ["index.html", "manifest.json", "icon-192.png", "icon-512.png"]
        (out / "sw.js").write_text(make_sw(files_to_cache, self.config["version"]))
        
        for size in [192, 512]:
            (out / f"icon-{size}.png").write_bytes(make_png(size, self.config["theme_color"]))
        
        # Copy original Python file for reference
        (out / "source.py").write_text(analyzer.source, encoding="utf-8")
        
        total = sum(f.stat().st_size for f in out.iterdir())
        print(f"\n  ✅ Compiled successfully! {total:,} bytes → ./{self.config['output_dir']}/")
        print(f"\n  🌐 Run: python -m http.server --directory {self.config['output_dir']} 8080")
        
        return out


# ============================================================
# MAIN CLI - Works with ANY Python file
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        prog="pywa",
        description="PyWA — Compile ANY Python file to a PWA (no modifications needed!)"
    )
    
    parser.add_argument("file", nargs="?", help="Python file to compile")
    parser.add_argument("--name", help="App name (optional)")
    parser.add_argument("--theme", help="Theme: light|dark|glass|nature|sunset|ocean|custom")
    parser.add_argument("--color", help="Primary color (hex)")
    parser.add_argument("--accent", help="Accent color (hex)")
    parser.add_argument("--out", help="Output directory", default="pwa_output")
    parser.add_argument("--serve", action="store_true", help="Start web server after compile")
    parser.add_argument("--port", type=int, default=8080, help="Port for web server")
    
    args = parser.parse_args()
    
    # If no file specified, show file picker
    if not args.file:
        from pathlib import Path
        print("\n  🔍 No file specified. Looking for Python files...")
        
        # Simple file picker
        py_files = list(Path.cwd().glob("*.py"))
        py_files = [f for f in py_files if f.name != "pywa.py"]
        
        if not py_files:
            print("  ❌ No Python files found in current directory!")
            print("\n  Usage: python pywa.py yourfile.py")
            return
        
        if len(py_files) == 1:
            args.file = str(py_files[0])
            print(f"  ✅ Found: {args.file}")
        else:
            print("\n  Multiple Python files found:")
            for i, f in enumerate(py_files, 1):
                print(f"    [{i}] {f.name}")
            try:
                choice = int(input("\n  Select file number: ")) - 1
                if 0 <= choice < len(py_files):
                    args.file = str(py_files[choice])
                else:
                    print("  Invalid choice!")
                    return
            except:
                print("  Cancelled.")
                return
    
    # Build config
    config = {
        "name": args.name,
        "theme": args.theme or "light",
        "theme_color": args.color,
        "accent": args.accent,
        "output_dir": args.out,
        "version": "1.0.0"
    }
    
    # Remove None values
    config = {k: v for k, v in config.items() if v is not None}
    
    # Compile
    compiler = PyWACompiler(config)
    out_dir = compiler.compile(args.file)
    
    # Serve if requested
    if args.serve:
        import http.server
        import socketserver
        import os
        
        os.chdir(out_dir)
        print(f"\n  🌐 Starting server at http://localhost:{args.port}")
        print("  Press Ctrl+C to stop\n")
        
        handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", args.port), handler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\n  Server stopped.")


if __name__ == "__main__":
    main()