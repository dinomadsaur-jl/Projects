#!/usr/bin/env python3
"""
PyWA - Python to PWA Compiler
Compiles ANY Python file to an installable Progressive Web App.
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
import subprocess
import tempfile
import threading
import http.server
import socketserver
import socket
import webbrowser
from pathlib import Path
from datetime import datetime

# ══════════════════════════════════════════════════════════════════
#  BUILT-IN THEMES
# ══════════════════════════════════════════════════════════════════
THEMES = {
    "light": {
        "theme_color": "#1a1a2e",
        "accent": "#e94560",
        "bg_color": "#ffffff",
        "surface": "#f5f5f5",
        "border": "#e0e0e0",
        "text": "#1a1a1a",
        "text_muted": "#666666",
        "radius": "12px",
        "font": "'Segoe UI', system-ui, sans-serif",
        "shadow": "0 2px 12px rgba(0,0,0,.08)",
    },
    "dark": {
        "theme_color": "#7c3aed",
        "accent": "#06b6d4",
        "bg_color": "#0d0d0d",
        "surface": "#1a1a1a",
        "border": "#2a2a2a",
        "text": "#f0f0f0",
        "text_muted": "#888888",
        "radius": "10px",
        "font": "'Cascadia Code', 'Fira Code', monospace",
        "shadow": "0 4px 20px rgba(0,0,0,.4)",
    },
    "glass": {
        "theme_color": "#6d28d9",
        "accent": "#f59e0b",
        "bg_color": "#0f172a",
        "surface": "rgba(255,255,255,0.08)",
        "border": "rgba(255,255,255,0.15)",
        "text": "#f1f5f9",
        "text_muted": "#94a3b8",
        "radius": "20px",
        "font": "'Segoe UI', system-ui, sans-serif",
        "shadow": "0 8px 32px rgba(0,0,0,.3), inset 0 1px 0 rgba(255,255,255,.1)",
    },
    "nature": {
        "theme_color": "#2d6a4f",
        "accent": "#95d5b2",
        "bg_color": "#f8fffe",
        "surface": "#edf6f0",
        "border": "#b7e4c7",
        "text": "#1b4332",
        "text_muted": "#52796f",
        "radius": "16px",
        "font": "'Georgia', 'Times New Roman', serif",
        "shadow": "0 2px 16px rgba(45,106,79,.1)",
    },
    "sunset": {
        "theme_color": "#c0392b",
        "accent": "#f39c12",
        "bg_color": "#fffbf7",
        "surface": "#fff0e6",
        "border": "#f5c6a0",
        "text": "#2c1810",
        "text_muted": "#8b5a3c",
        "radius": "14px",
        "font": "'Segoe UI', system-ui, sans-serif",
        "shadow": "0 2px 16px rgba(192,57,43,.12)",
    },
    "ocean": {
        "theme_color": "#0369a1",
        "accent": "#0891b2",
        "bg_color": "#f0f9ff",
        "surface": "#e0f2fe",
        "border": "#bae6fd",
        "text": "#0c1a2e",
        "text_muted": "#0369a1",
        "radius": "8px",
        "font": "'Segoe UI', system-ui, sans-serif",
        "shadow": "0 2px 12px rgba(3,105,161,.1)",
    },
    "custom": None,
}

DEFAULTS = {
    "name": None,
    "short_name": None,
    "theme": "light",
    "output_dir": "pwa_output",
    "version": "1.0.0",
    "theme_color": "#1a1a2e",
    "accent": "#e94560",
    "bg_color": "#ffffff",
    "surface": "#f5f5f5",
    "border": "#e0e0e0",
    "text": "#1a1a1a",
    "text_muted": "#666666",
    "radius": "12px",
    "font": "'Segoe UI', system-ui, sans-serif",
    "shadow": "0 2px 12px rgba(0,0,0,.08)",
}

def resolve_theme(config):
    """Merge a named theme into config."""
    theme_name = config.get("theme", "light").lower()
    
    if theme_name == "custom" or theme_name not in THEMES:
        return config
    
    preset = THEMES[theme_name]
    merged = {**preset}
    for k, v in config.items():
        if v is not None:
            merged[k] = v
    
    merged["theme"] = theme_name
    return merged


# ══════════════════════════════════════════════════════════════════
#  COMPATIBILITY CHECKER
# ══════════════════════════════════════════════════════════════════
class CompatibilityChecker:
    CHECKS = [
        (r'<marquee', "❌ <marquee> is deprecated", 
         lambda h: h.replace('<marquee', '<div class="pywa-marquee"')),
        (r'<blink', "❌ <blink> is deprecated",
         lambda h: re.sub(r'<blink[^>]*>(.*?)</blink>', r'<span>\1</span>', h, flags=re.S)),
        (r'target=["\']_blank["\'](?!.*rel=)', "⚠️ _blank without rel=noopener",
         lambda h: re.sub(r'(target=["\']_blank["\'])(?!.*?rel=)', r'\1 rel="noopener noreferrer"', h)),
        (r'<img(?!.*?alt=)', "⚠️ <img> missing alt attribute",
         lambda h: re.sub(r'(<img)(?![^>]*alt=)', r'\1 alt=""', h)),
        (r'user-scalable=no', "❌ user-scalable=no breaks accessibility",
         lambda h: h.replace('user-scalable=no', 'user-scalable=yes')),
    ]
    
    def check(self, html):
        """Check HTML for compatibility issues and fix them."""
        issues = []
        fixes = []
        content = html
        
        for pattern, message, fix_fn in self.CHECKS:
            if re.search(pattern, content, re.IGNORECASE):
                issues.append(message)
                if fix_fn:
                    try:
                        content = fix_fn(content)
                        fixes.append(f"  ✅ Auto-fixed: {message}")
                    except Exception:
                        fixes.append(f"  ⚠️  Could not auto-fix: {message}")
        
        return content, issues, fixes


# ══════════════════════════════════════════════════════════════════
#  RESPONSIVE OPTIMIZER - FIXED VERSION
# ══════════════════════════════════════════════════════════════════
class ResponsiveOptimizer:
    """Adds responsive meta tags and PWA CSS to HTML."""
    
    BASE_CSS = """
/* ── PyWA Reset & Base ──────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --color-bg: {bg_color};
  --color-primary: {theme_color};
  --color-accent: {accent};
  --color-text: {text};
  --color-text-muted: {text_muted};
  --color-surface: {surface};
  --color-border: {border};
  --radius-sm: 6px;
  --radius-md: {radius};
  --radius-lg: 20px;
  --shadow-sm: {shadow};
  --shadow-md: 0 4px 16px rgba(0,0,0,.15);
  --font-sans: {font};
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 32px;
  --space-xl: 64px;
  --transition: 0.2s ease;
}

html { font-size: 16px; scroll-behavior: smooth; }
body {
  font-family: var(--font-sans);
  background: var(--color-bg);
  color: var(--color-text);
  line-height: 1.6;
  min-height: 100vh;
}

h1 { font-size: clamp(1.8rem, 5vw, 3rem); font-weight: 800; }
h2 { font-size: clamp(1.4rem, 3.5vw, 2rem); font-weight: 700; }
p { color: var(--color-text-muted); }

/* Navbar */
.pywa-navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-md) var(--space-lg);
  background: var(--color-primary);
  color: #fff;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: var(--shadow-md);
}
.pywa-navbar-title { font-weight: 800; font-size: 1.2rem; }
.pywa-navbar-links { display: flex; gap: var(--space-md); }
.pywa-navbar-links a { color: rgba(255,255,255,.8); text-decoration: none; }

/* Mobile tab nav */
.pywa-tab-nav {
  display: none;
  position: fixed;
  bottom: 0; left: 0; right: 0;
  background: var(--color-bg);
  border-top: 1px solid var(--color-border);
  z-index: 200;
  padding-bottom: env(safe-area-inset-bottom);
}
.pywa-tab-nav-inner {
  display: flex;
  justify-content: space-around;
  align-items: center;
}
.pywa-tab-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-sm);
  background: none;
  border: none;
  color: var(--color-text-muted);
  font-size: .65rem;
  cursor: pointer;
  gap: 2px;
}
.pywa-tab-btn .tab-icon { font-size: 1.3rem; }
.pywa-tab-btn.active, .pywa-tab-btn:hover { color: var(--color-primary); }

@media (max-width: 768px) {
  .pywa-tab-nav { display: block; }
  body { padding-bottom: calc(70px + env(safe-area-inset-bottom)); }
  .pywa-navbar-links { display: none; }
}

/* Pages */
.pywa-page { display: none; animation: fadein .25s ease; }
.pywa-page.active { display: block; }
@keyframes fadein {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Main content */
.pywa-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-lg);
}

/* Cards */
.pywa-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  margin-bottom: var(--space-md);
  box-shadow: var(--shadow-sm);
}

/* Buttons */
.pywa-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-sm);
  padding: .65em 1.4em;
  border-radius: var(--radius-sm);
  border: none;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  min-height: 44px;
}
.pywa-btn-primary {
  background: var(--color-primary);
  color: #fff;
}
.pywa-btn-accent {
  background: var(--color-accent);
  color: #fff;
}

/* Inputs */
.pywa-input {
  width: 100%;
  padding: .65em 1em;
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 1rem;
  background: var(--color-bg);
  color: var(--color-text);
  min-height: 44px;
}

/* Install banner */
#pywa-install-banner {
  display: none;
  position: fixed;
  bottom: 80px; left: 50%;
  transform: translateX(-50%);
  background: var(--color-primary);
  color: #fff;
  padding: var(--space-sm) var(--space-lg);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  z-index: 999;
  gap: var(--space-md);
  align-items: center;
  font-size: .9rem;
  animation: fadein .3s ease;
}
#pywa-install-banner.show { display: flex; }
#pywa-install-banner button {
  background: rgba(255,255,255,.2);
  border: none; color: #fff;
  padding: .4em 1em; border-radius: var(--radius-sm);
  cursor: pointer;
}

/* Terminal output */
.terminal-output {
  background: #1e1e1e;
  color: #f0f0f0;
  padding: 20px;
  border-radius: 8px;
  font-family: monospace;
  white-space: pre-wrap;
  overflow-x: auto;
}
"""
    
    def optimize(self, html, config):
        """Add responsive meta tags and PWA CSS to HTML."""
        
        # Meta tags
        viewport = '<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">'
        mobile_capable = '<meta name="mobile-web-app-capable" content="yes">'
        apple_capable = '<meta name="apple-mobile-web-app-capable" content="yes">'
        apple_title = f'<meta name="apple-mobile-web-app-title" content="{config["name"]}">'
        apple_status = '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">'
        description = f'<meta name="description" content="{config["name"]} — built with PyWA">'
        charset = '<meta charset="UTF-8">'
        
        # Replace placeholders in CSS
        css = self.BASE_CSS
        css = css.replace('{bg_color}', config.get("bg_color", "#ffffff"))
        css = css.replace('{theme_color}', config.get("theme_color", "#1a1a2e"))
        css = css.replace('{accent}', config.get("accent", "#e94560"))
        css = css.replace('{surface}', config.get("surface", "#f5f5f5"))
        css = css.replace('{border}', config.get("border", "#e0e0e0"))
        css = css.replace('{text}', config.get("text", "#1a1a1a"))
        css = css.replace('{text_muted}', config.get("text_muted", "#666666"))
        css = css.replace('{radius}', config.get("radius", "12px"))
        css = css.replace('{font}', config.get("font", "'Segoe UI', system-ui, sans-serif"))
        css = css.replace('{shadow}', config.get("shadow", "0 2px 12px rgba(0,0,0,.08)"))
        
        # Build head injection
        head_inject = f"""
  {charset}
  {viewport}
  {mobile_capable}
  {apple_capable}
  {apple_title}
  {apple_status}
  {description}
  <style id="pywa-base">{css}</style>"""
        
        # Insert into HTML
        if "<head>" in html:
            html = html.replace("<head>", f"<head>{head_inject}", 1)
        elif "<html" in html:
            html = html.replace("<html", "<html>\n<head>" + head_inject + "</head>", 1)
        else:
            html = f"<!DOCTYPE html>\n<html>\n<head>{head_inject}</head>\n<body>{html}</body>\n</html>"
        
        # Add theme class to body
        theme_name = config.get("theme", "light")
        body_class = f' class="pywa-theme-{theme_name}"'
        
        if "<body>" in html:
            html = html.replace("<body>", f"<body{body_class}>", 1)
        elif "<body " in html:
            html = re.sub(r'<body\s+', f'<body{body_class} ', html, 1)
        
        return html


# ══════════════════════════════════════════════════════════════════
#  HTML GENERATOR
# ══════════════════════════════════════════════════════════════════
class HTMLGenerator:
    """Generates the final HTML for the PWA."""
    
    def generate(self, content, config, content_is_html=False):
        """Generate complete HTML with navigation."""
        
        # Prepare content
        if content_is_html:
            main_content = content
        else:
            main_content = f'<pre class="terminal-output">{content}</pre>'
        
        # Simple navigation
        nav_links = '<a href="#" onclick="pywaNavigate(\'content\');return false;">App</a>'
        tab_btns = '''
      <button class="pywa-tab-btn active" onclick="pywaNavigate('content')" id="tab-content">
        <span class="tab-icon">📱</span>
        <span>App</span>
      </button>'''
        
        # Build HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <title>{config['name']}</title>
  <link rel="manifest" href="manifest.json">
  <meta name="theme-color" content="{config['theme_color']}">
  <link rel="apple-touch-icon" href="icon-192.png">
</head>
<body>
  <!-- Navbar -->
  <nav class="pywa-navbar">
    <span class="pywa-navbar-title">{config['name']}</span>
    <div class="pywa-navbar-links">
      {nav_links}
    </div>
  </nav>

  <!-- Content -->
  <div class="pywa-page active" id="page-content">
    <main class="pywa-main">
      {main_content}
    </main>
  </div>

  <!-- Mobile Navigation -->
  <div class="pywa-tab-nav">
    <div class="pywa-tab-nav-inner">
      {tab_btns}
    </div>
  </div>

  <!-- Install Banner -->
  <div id="pywa-install-banner">
    📱 Install this app
    <button onclick="pywaInstall()">Install</button>
    <button onclick="document.getElementById('pywa-install-banner').classList.remove('show')">✕</button>
  </div>

  <script>
    // Navigation
    function pywaNavigate(page) {{
      document.querySelectorAll('.pywa-page').forEach(p => p.classList.remove('active'));
      document.querySelectorAll('.pywa-tab-btn').forEach(b => b.classList.remove('active'));
      const pg = document.getElementById('page-' + page);
      const tb = document.getElementById('tab-' + page);
      if (pg) pg.classList.add('active');
      if (tb) tb.classList.add('active');
    }}

    // PWA Install
    let pywaInstallEvent = null;
    window.addEventListener('beforeinstallprompt', e => {{
      e.preventDefault();
      pywaInstallEvent = e;
      document.getElementById('pywa-install-banner').classList.add('show');
    }});

    function pywaInstall() {{
      if (!pywaInstallEvent) return;
      pywaInstallEvent.prompt();
      pywaInstallEvent.userChoice.then(() => {{
        pywaInstallEvent = null;
        document.getElementById('pywa-install-banner').classList.remove('show');
      }});
    }}

    // Service Worker
    if ('serviceWorker' in navigator) {{
      navigator.serviceWorker.register('sw.js')
        .then(() => console.log('[PyWA] Service worker ready'))
        .catch(e => console.warn('[PyWA] SW error', e));
    }}
  </script>
</body>
</html>"""
        
        return html


# ══════════════════════════════════════════════════════════════════
#  ASSET GENERATORS
# ══════════════════════════════════════════════════════════════════
def make_png(size, hex_color):
    """Generate a simple PNG icon."""
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    raw = b""
    for _ in range(size):
        row = b"\x00"
        for _ in range(size):
            row += bytes([r, g, b, 255])
        raw += row
    
    def chunk(name, data):
        crc = zlib.crc32(name + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", crc)
    
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


def make_manifest(config):
    """Generate web app manifest."""
    return json.dumps({
        "name": config.get("name", "PyWA App"),
        "short_name": config.get("short_name", config.get("name", "PyWA")[:12]),
        "start_url": "index.html",
        "display": "standalone",
        "background_color": config.get("bg_color", "#ffffff"),
        "theme_color": config.get("theme_color", "#1a1a2e"),
        "orientation": "any",
        "scope": "./",
        "icons": [
            {"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ]
    }, indent=2)


def make_sw(file_list, version):
    """Generate service worker for offline support."""
    files = json.dumps(file_list, indent=4)
    return f"""const CACHE = 'pywa-{version}-{hashlib.md5(version.encode()).hexdigest()[:6]}';
const FILES = {files};

self.addEventListener('install', e => {{
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)));
  self.skipWaiting();
}});

self.addEventListener('activate', e => {{
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
}});

self.addEventListener('fetch', e => {{
  if (e.request.method !== 'GET') return;
  e.respondWith(
    caches.match(e.request).then(cached => {{
      if (cached) return cached;
      return fetch(e.request).then(res => {{
        if (res && res.status === 200) {{
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }}
        return res;
      }});
    }})
  );
}});
"""


# ══════════════════════════════════════════════════════════════════
#  PYTHON RUNNER - Runs Python and captures output
# ══════════════════════════════════════════════════════════════════
class PythonRunner:
    """Runs Python file and captures its output."""
    
    @staticmethod
    def run_and_capture(file_path):
        """Run Python file and capture stdout/stderr."""
        try:
            result = subprocess.run(
                [sys.executable, str(file_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout
            if result.stderr:
                output += "\n" + result.stderr if output else result.stderr
            
            # Check if output is HTML
            is_html = PythonRunner._is_html(output)
            
            return output, is_html, result.returncode
            
        except subprocess.TimeoutExpired:
            return "Error: Execution timed out (30 seconds)", False, 1
        except Exception as e:
            return f"Error: {str(e)}", False, 1
    
    @staticmethod
    def _is_html(text):
        """Check if text contains HTML."""
        html_patterns = [
            r'<html',
            r'<!DOCTYPE',
            r'<body',
            r'<head',
            r'<div',
            r'<script',
            r'Plotly\.newPlot',
            r'<svg',
        ]
        text_lower = text.lower()
        for pattern in html_patterns:
            if re.search(pattern, text_lower):
                return True
        return False


# ══════════════════════════════════════════════════════════════════
#  FILE PICKER
# ══════════════════════════════════════════════════════════════════
def pick_py_file():
    """Simple file picker."""
    base = Path.cwd()
    print(f"\n  🔍 Searching for Python files in: {base}")
    
    found = []
    for f in base.glob("*.py"):
        if f.name not in ["pywa.py", "pywa_v0p2.py", "pywa_v0p3.py"]:
            found.append(f)
    
    if not found:
        print(f"\n  ❌ No Python files found in current directory")
        return None
    
    if len(found) == 1:
        print(f"  ✅ Found: {found[0].name}")
        return found[0]
    
    print("\n  📁 Found multiple Python files:\n")
    for i, f in enumerate(found, 1):
        print(f"    [{i}] {f.name}")
    print("\n    [0] Cancel")
    
    while True:
        try:
            choice = input("\n  Select file number: ").strip()
            if choice == "0":
                return None
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(found):
                    return found[idx]
                else:
                    print(f"  Please enter a number between 1 and {len(found)}")
            except ValueError:
                print("  Please enter a valid number")
        except (EOFError, KeyboardInterrupt):
            return None


# ══════════════════════════════════════════════════════════════════
#  SERVER FUNCTIONS
# ══════════════════════════════════════════════════════════════════
def find_free_port(start=8080):
    """Find a free port starting from start."""
    for port in range(start, start + 20):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", port))
                return port
        except OSError:
            continue
    return start


def start_server(directory, port):
    """Start HTTP server in current thread."""
    os.chdir(directory)
    
    handler = http.server.SimpleHTTPRequestHandler
    httpd = socketserver.TCPServer(("", port), handler)
    
    print(f"\n  🌐 Server running at http://localhost:{port}")
    print("  Press Ctrl+C to stop\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
        httpd.shutdown()


def open_browser(url):
    """Open URL in browser."""
    try:
        if sys.platform == 'win32':
            os.startfile(url)
        else:
            import subprocess
            subprocess.run(['xdg-open', url], check=False)
        return True
    except:
        try:
            webbrowser.open(url)
            return True
        except:
            return False


# ══════════════════════════════════════════════════════════════════
#  PYWA COMPILER
# ══════════════════════════════════════════════════════════════════
class PyWACompiler:
    """Main compiler class."""
    
    def __init__(self, config=None):
        self.config = {**DEFAULTS, **(config or {})}
        self.checker = CompatibilityChecker()
        self.optimizer = ResponsiveOptimizer()
        self.generator = HTMLGenerator()
    
    def _banner(self):
        print("""
╔═══════════════════════════════════════╗
║   PyWA — Python to PWA Compiler       ║
║   Your Python → Installable Web App   ║
╚═══════════════════════════════════════╝""")
    
    def compile(self, source_file):
        """Compile Python file to PWA."""
        self._banner()
        src = Path(source_file)
        print(f"\n  📄 Source : {src}")
        print(f"  📦 Output : {self.config['output_dir']}/\n")
        
        # Step 1: Run Python file and capture output
        print("  [1/4] Running Python file...")
        output, is_html, returncode = PythonRunner.run_and_capture(src)
        
        if returncode != 0:
            print(f"  ⚠️  Script exited with code {returncode}")
        
        output_type = "HTML" if is_html else "text"
        print(f"     ✅ Captured {len(output)} bytes ({output_type})")
        
        # Step 2: Set app name if not provided
        if not self.config.get('name'):
            self.config['name'] = src.stem.replace('_', ' ').replace('-', ' ').title()
        
        if not self.config.get('short_name'):
            words = self.config['name'].split()
            self.config['short_name'] = ''.join(w[0] for w in words[:3])[:8]
        
        # Apply theme
        self.config = resolve_theme(self.config)
        
        # Step 3: Generate HTML
        print("  [2/4] Generating HTML...")
        html = self.generator.generate(output, self.config, is_html)
        
        # Step 4: Optimize for web
        print("  [3/4] Optimizing for PWA...")
        html = self.optimizer.optimize(html, self.config)
        
        # Step 5: Write files
        print("  [4/4] Writing PWA files...")
        out_dir = Path(self.config["output_dir"])
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True)
        
        # Write HTML
        (out_dir / "index.html").write_text(html, encoding="utf-8")
        print("     ✅ index.html")
        
        # Write manifest
        (out_dir / "manifest.json").write_text(make_manifest(self.config))
        print("     ✅ manifest.json")
        
        # Write service worker
        files_to_cache = ["index.html", "manifest.json", "icon-192.png", "icon-512.png"]
        (out_dir / "sw.js").write_text(make_sw(files_to_cache, self.config["version"]))
        print("     ✅ sw.js")
        
        # Generate icons
        for size in [192, 512]:
            (out_dir / f"icon-{size}.png").write_bytes(make_png(size, self.config["theme_color"]))
        print("     ✅ icons")
        
        # Copy source for reference
        (out_dir / "source.py").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        
        # Calculate total size
        total_size = sum(f.stat().st_size for f in out_dir.glob("**/*") if f.is_file())
        print(f"\n  ✅ Compiled! {total_size:,} bytes → ./{self.config['output_dir']}/")
        
        return out_dir


# ══════════════════════════════════════════════════════════════════
#  MAIN CLI
# ══════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        prog="pywa",
        description="PyWA — Compile Python to PWA"
    )
    
    parser.add_argument("file", nargs="?", help="Python file to compile")
    parser.add_argument("--name", help="App name")
    parser.add_argument("--theme", help="Theme: light|dark|glass|nature|sunset|ocean|custom", default="light")
    parser.add_argument("--color", help="Primary color (hex)")
    parser.add_argument("--accent", help="Accent color (hex)")
    parser.add_argument("--out", help="Output directory", default="pwa_output")
    parser.add_argument("--serve", action="store_true", help="Start web server after compile")
    parser.add_argument("--port", type=int, default=8080, help="Port for web server")
    parser.add_argument("--open", action="store_true", help="Open in browser after compile")
    
    args = parser.parse_args()
    
    # If no file, show picker
    if not args.file:
        print("\n  No file specified. Launching file picker...")
        file_path = pick_py_file()
        if not file_path:
            print("\n  ❌ No file selected. Exiting.")
            return
        args.file = str(file_path)
    
    # Build config
    config = {
        "name": args.name,
        "theme": args.theme,
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
        port = args.port or find_free_port(8080)
        url = f"http://localhost:{port}"
        
        if args.open:
            open_browser(url)
        
        start_server(out_dir, port)


if __name__ == "__main__":
    main()