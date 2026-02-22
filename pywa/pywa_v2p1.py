#!/usr/bin/env python3
"""
PyWA - Python to PWA Compiler
Packages Python WITH the PWA - runs in browser using Pyodide.
Simplified version with better error handling.
"""

import os
import sys
import json
import shutil
import struct
import zlib
import time
import re
import hashlib
import argparse
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
        "font": "'Segoe UI', system-ui, sans-serif",
    },
    "dark": {
        "theme_color": "#7c3aed",
        "accent": "#06b6d4",
        "bg_color": "#0d0d0d",
        "surface": "#1a1a1a",
        "border": "#2a2a2a",
        "text": "#f0f0f0",
        "text_muted": "#888888",
        "font": "'Cascadia Code', monospace",
    },
}

DEFAULTS = {
    "name": None,
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
    "font": "'Segoe UI', system-ui, sans-serif",
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
#  PWA GENERATOR - Simplified version
# ══════════════════════════════════════════════════════════════════
class PyodidePWA:
    """Generates PWA that runs Python in browser with Pyodide."""
    
    CSS = """
* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

:root {{
    --primary: {theme_color};
    --bg: {bg_color};
    --text: {text};
    --surface: {surface};
    --font: {font};
}}

body {{
    background: var(--bg);
    color: var(--text);
    font-family: var(--font);
    line-height: 1.6;
    min-height: 100vh;
}}

.app-header {{
    background: var(--primary);
    color: white;
    padding: 12px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: sticky;
    top: 0;
    z-index: 1000;
}}

@media all and (display-mode: standalone) {{
    .app-header {{ display: none; }}
}}

.refresh-btn {{
    background: rgba(255,255,255,0.2);
    border: none;
    color: white;
    padding: 6px 16px;
    border-radius: 20px;
    cursor: pointer;
    font-size: 14px;
}}

.refresh-btn:disabled {{
    opacity: 0.5;
    cursor: not-allowed;
}}

.install-hint {{
    background: var(--surface);
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 8px 12px;
    margin: 8px;
    font-size: 14px;
    display: none;
}}

.install-hint.show {{ display: block; }}

.loading {{
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.95);
    color: white;
    z-index: 2000;
    justify-content: center;
    align-items: center;
    flex-direction: column;
}}

.loading.show {{ display: flex; }}

.spinner {{
    border: 4px solid rgba(255,255,255,0.3);
    border-radius: 50%;
    border-top: 4px solid white;
    width: 50px;
    height: 50px;
    animation: spin 1s linear infinite;
    margin-bottom: 20px;
}}

@keyframes spin {{
    0% {{ transform: rotate(0deg); }}
    100% {{ transform: rotate(360deg); }}
}}

#output {{
    width: 100%;
    min-height: calc(100vh - 120px);
    padding: 0;
}}

.error {{
    color: #ff4444;
    padding: 20px;
    background: #ffeeee;
    border-radius: 8px;
    margin: 20px;
    white-space: pre-wrap;
    font-family: monospace;
}}

pre {{
    background: #1e1e1e;
    color: #f0f0f0;
    padding: 20px;
    margin: 20px;
    border-radius: 8px;
    overflow: auto;
    font-family: monospace;
}}
"""
    
    HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <title>{title}</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-title" content="{title}">
    <meta name="theme-color" content="{theme_color}">
    <link rel="manifest" href="manifest.json">
    <link rel="apple-touch-icon" href="icon-192.png">
    <link rel="icon" href="icon-192.png">
    <script src="https://cdn.jsdelivr.net/pyodide/v0.24.1/full/pyodide.js"></script>
    <style>
{css}
    </style>
</head>
<body>
    <div class="app-header">
        <span>{title}</span>
        <button class="refresh-btn" onclick="runPython()">↻ Refresh Data</button>
    </div>
    
    <div class="install-hint" id="installHint">
        📱 Tap menu → Add to Home screen
    </div>
    
    <div class="loading" id="loading">
        <div class="spinner"></div>
        <div id="loadingStatus">Initializing...</div>
    </div>
    
    <div id="output"></div>

    <script>
        if (/Android|iPhone/i.test(navigator.userAgent)) {{
            if (!window.matchMedia('(display-mode: standalone)').matches) {{
                document.getElementById('installHint').classList.add('show');
            }}
        }}
        
        let pyodide = null;
        let isReady = false;
        const PYTHON_CODE = {python_code};
        const PACKAGES = {packages};
        
        async function init() {{
            const loading = document.getElementById('loading');
            const status = document.getElementById('loadingStatus');
            
            loading.classList.add('show');
            
            try {{
                status.textContent = 'Loading Pyodide...';
                pyodide = await loadPyodide({{
                    indexURL: "https://cdn.jsdelivr.net/pyodide/v0.24.1/full/",
                }});
                
                if (PACKAGES.length > 0) {{
                    status.textContent = 'Loading packages...';
                    await pyodide.loadPackage('micropip');
                    const micropip = pyodide.pyimport('micropip');
                    
                    for (const pkg of PACKAGES) {{
                        status.textContent = `Installing ${{pkg}}...`;
                        try {{
                            await micropip.install(pkg);
                        }} catch (e) {{
                            console.warn(`Failed to install ${{pkg}}:`, e);
                        }}
                    }}
                }}
                
                isReady = true;
                status.textContent = 'Ready!';
                setTimeout(() => loading.classList.remove('show'), 500);
                
                // Auto-run on first load
                runPython();
                
            }} catch (error) {{
                document.getElementById('output').innerHTML = 
                    '<div class="error">Init failed: ' + error + '</div>';
                loading.classList.remove('show');
            }}
        }}
        
        async function runPython() {{
            if (!isReady) {{
                await init();
                return;
            }}
            
            const output = document.getElementById('output');
            const loading = document.getElementById('loading');
            const status = document.getElementById('loadingStatus');
            const btn = document.querySelector('.refresh-btn');
            
            loading.classList.add('show');
            btn.disabled = true;
            status.textContent = 'Running...';
            
            try {{
                output.innerHTML = '';
                
                // Run Python code
                await pyodide.runPythonAsync(PYTHON_CODE);
                
                // Get output
                const stdout = pyodide.runPython(`
import sys
sys.stdout.getvalue() if hasattr(sys.stdout, 'getvalue') else ''
                `);
                
                if (stdout) {{
                    if (stdout.includes('<div') || stdout.includes('<html')) {{
                        output.innerHTML = stdout;
                    }} else {{
                        output.innerHTML = '<pre>' + stdout.replace(/</g, '&lt;') + '</pre>';
                    }}
                }}
                
            }} catch (error) {{
                output.innerHTML = '<div class="error">' + error + '</div>';
            }}
            
            loading.classList.remove('show');
            btn.disabled = false;
        }}
        
        // Initialize on page load
        init();
        
        // Auto-refresh when installed
        if (window.matchMedia('(display-mode: standalone)').matches) {{
            setInterval(runPython, 5 * 60 * 1000);
        }}
    </script>
</body>
</html>"""
    
    @classmethod
    def generate(cls, python_file, config):
        """Generate PWA with embedded Python code."""
        
        # Read original Python code
        with open(python_file, 'r', encoding='utf-8') as f:
            python_code = f.read()
        
        # Add CORS proxy and ensure HTML output
        wrapped_code = '''
# PyWA - Browser environment setup
import sys
from io import StringIO
sys.stdout = StringIO()

# CORS proxy for Yahoo Finance
import requests
def fetch_with_proxy(url):
    try:
        proxy_url = f"https://api.allorigins.win/raw?url={url}"
        return requests.get(proxy_url, timeout=30)
    except:
        return requests.get(url, timeout=30)

original_get = requests.get
def patched_get(url, **kwargs):
    if 'yahoo.com' in url:
        return fetch_with_proxy(url)
    return original_get(url, **kwargs)
requests.get = patched_get

# User code
''' + python_code + '''

# Ensure output is captured
import sys
print(sys.stdout.getvalue())
'''
        
        # Detect packages
        packages = []
        if 'numpy' in python_code:
            packages.append('numpy')
        if 'pandas' in python_code:
            packages.append('pandas')
        if 'plotly' in python_code:
            packages.append('plotly')
        if 'scipy' in python_code:
            packages.append('scipy')
        if 'requests' in python_code:
            packages.append('requests')
        
        # Format CSS
        css = cls.CSS.format(
            theme_color=config.get("theme_color", "#1a1a2e"),
            bg_color=config.get("bg_color", "#ffffff"),
            text=config.get("text", "#1a1a1a"),
            surface=config.get("surface", "#f5f5f5"),
            font=config.get("font", "'Segoe UI', system-ui, sans-serif")
        )
        
        # Generate HTML
        html = cls.HTML_TEMPLATE.format(
            title=config.get('name', 'PyWA App'),
            theme_color=config.get("theme_color", "#1a1a2e"),
            css=css,
            python_code=json.dumps(wrapped_code),
            packages=json.dumps(packages)
        )
        
        return html


# ══════════════════════════════════════════════════════════════════
#  ASSET GENERATORS
# ══════════════════════════════════════════════════════════════════
def make_png(size, hex_color):
    """Generate PNG icon."""
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    raw = bytearray([r, g, b, 255]) * size * size
    
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
        "background_color": "#ffffff",
        "theme_color": config.get("theme_color", "#1a1a2e"),
        "icons": [
            {"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"},
        ]
    }, indent=2)


def make_sw(version):
    """Generate service worker."""
    return f"""const CACHE = 'pywa-{version}';
const FILES = ['index.html', 'manifest.json', 'icon-192.png', 'icon-512.png'];

self.addEventListener('install', e => {{
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)));
  self.skipWaiting();
}});

self.addEventListener('activate', e => {{
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ));
  self.clients.claim();
}});

self.addEventListener('fetch', e => {{
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  );
}});
"""


# ══════════════════════════════════════════════════════════════════
#  FILE PICKER
# ══════════════════════════════════════════════════════════════════
def pick_py_file():
    """Simple file picker."""
    base = Path.cwd()
    files = [f for f in base.glob("*.py") if not f.name.startswith("pywa")]
    
    if not files:
        print("No Python files found")
        return None
    
    if len(files) == 1:
        return files[0]
    
    print("\nSelect Python file:")
    for i, f in enumerate(files, 1):
        print(f"  {i}. {f.name}")
    
    try:
        choice = input("\nNumber: ").strip()
        return files[int(choice)-1]
    except:
        return None


# ══════════════════════════════════════════════════════════════════
#  SERVER
# ══════════════════════════════════════════════════════════════════
def find_free_port():
    for port in range(8080, 8100):
        try:
            with socket.socket() as s:
                s.bind(("", port))
                return port
        except:
            continue
    return 8080


def serve_directory(directory, port):
    """Simple HTTP server for initial install."""
    os.chdir(directory)
    
    try:
        import http.server
        import socketserver
        
        handler = http.server.SimpleHTTPRequestHandler
        httpd = socketserver.TCPServer(("0.0.0.0", port), handler)
        
        print(f"\n{'='*50}")
        print(f"🌐 PWA Ready!")
        print(f"{'='*50}")
        print(f"\n📱 Open in Chrome: http://localhost:{port}")
        print(f"\n👉 Then tap menu → Add to Home screen")
        print(f"\nPress Ctrl+C to stop\n")
        
        try:
            webbrowser.open(f"http://localhost:{port}")
        except:
            pass
        
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs="?", help="Python file")
    parser.add_argument("--name", help="App name")
    parser.add_argument("--theme", default="light", help="Theme")
    parser.add_argument("--color", default="#1a1a2e", help="Primary color")
    parser.add_argument("--out", default="pwa_output", help="Output dir")
    parser.add_argument("--no-serve", action="store_true", help="Compile only")
    
    args = parser.parse_args()
    
    if not args.file:
        file_path = pick_py_file()
        if not file_path:
            return
        args.file = str(file_path)
    
    config = {
        "name": args.name or Path(args.file).stem.replace('_', ' ').title(),
        "theme": args.theme,
        "theme_color": args.color,
        "output_dir": args.out,
        "version": datetime.now().strftime("%Y%m%d")
    }
    config = resolve_theme(config)
    
    print("\n" + "="*50)
    print(f"🚀 PyWA - {Path(args.file).name}")
    print("="*50)
    
    # Generate PWA
    html = PyodidePWA.generate(args.file, config)
    
    out_dir = Path(config["output_dir"])
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir()
    
    (out_dir / "index.html").write_text(html, encoding='utf-8')
    (out_dir / "manifest.json").write_text(make_manifest(config))
    (out_dir / "sw.js").write_text(make_sw(config["version"]))
    
    for size in [192, 512]:
        (out_dir / f"icon-{size}.png").write_bytes(make_png(size, config["theme_color"]))
    
    print(f"\n✅ PWA created in: {out_dir}/")
    
    if not args.no_serve:
        serve_directory(out_dir, find_free_port())
    else:
        print(f"\n📁 Files saved to: {out_dir}/")
        print("Run without --no-serve to start install server")


if __name__ == "__main__":
    main()