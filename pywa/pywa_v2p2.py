#!/usr/bin/env python3
"""
PyWA - Python to PWA Compiler
Packages Python WITH the PWA - runs in browser using Pyodide.
Fixed package detection and installation.
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
#  PACKAGE DETECTOR - Improved detection
# ══════════════════════════════════════════════════════════════════
def detect_packages(code):
    """Detect required Python packages from code."""
    packages = set()
    
    # Common package mappings
    package_map = {
        'numpy': ['numpy', 'np'],
        'pandas': ['pandas', 'pd'],
        'plotly': ['plotly', 'px', 'go'],
        'scipy': ['scipy'],
        'requests': ['requests'],
        'matplotlib': ['matplotlib', 'plt'],
        'sklearn': ['scikit-learn'],
        'tensorflow': ['tensorflow'],
        'torch': ['torch'],
        'pillow': ['PIL'],
        'beautifulsoup4': ['bs4'],
        'lxml': ['lxml'],
        'flask': ['flask'],
        'django': ['django'],
        'fastapi': ['fastapi'],
    }
    
    # Check imports
    import_lines = re.findall(r'^import (\w+)|^from (\w+) import', code, re.MULTILINE)
    for line in import_lines:
        for match in line:
            if match:
                for pkg, aliases in package_map.items():
                    if match in aliases or match == pkg:
                        packages.add(pkg)
    
    # Check for common aliases in code
    for pkg, aliases in package_map.items():
        for alias in aliases:
            if alias + '.' in code or alias + ' as ' in code:
                packages.add(pkg)
    
    return list(packages)


# ══════════════════════════════════════════════════════════════════
#  PWA GENERATOR - Fixed package installation
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
    flex-wrap: wrap;
}}

@media all and (display-mode: standalone) {{
    .app-header {{ display: none; }}
}}

.header-title {{
    font-weight: bold;
    font-size: 1.1rem;
}}

.header-controls {{
    display: flex;
    gap: 8px;
}}

.refresh-btn {{
    background: rgba(255,255,255,0.2);
    border: none;
    color: white;
    padding: 6px 16px;
    border-radius: 20px;
    cursor: pointer;
    font-size: 14px;
    transition: background 0.2s;
}}

.refresh-btn:hover {{
    background: rgba(255,255,255,0.3);
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
    padding: 20px;
    text-align: center;
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

.error-details {{
    color: #ff8888;
    font-size: 12px;
    margin-top: 10px;
    max-width: 80%;
    word-break: break-word;
}}

#output {{
    width: 100%;
    min-height: calc(100vh - 120px);
    padding: 0;
}}

.console-container {{
    background: #1e1e1e;
    color: #f0f0f0;
    padding: 20px;
    font-family: 'Cascadia Code', monospace;
    font-size: 13px;
    line-height: 1.5;
    white-space: pre-wrap;
    word-wrap: break-word;
    min-height: 100%;
}}

.console-line {{
    margin: 2px 0;
    border-bottom: 1px solid #333;
    padding: 4px 0;
}}

.console-timestamp {{
    color: #888;
    font-size: 11px;
    margin-right: 10px;
}}

.console-output {{
    color: #00ff00;
}}

.console-error {{
    color: #ff6b6b;
    background: rgba(255,107,107,0.1);
    padding: 8px;
    border-radius: 4px;
    margin: 5px 0;
}}

.console-html {{
    background: white;
    color: black;
    padding: 20px;
    border-radius: 8px;
    margin: 10px 0;
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

.network-status {{
    font-size: 12px;
    margin-top: 10px;
    color: #aaa;
}}

.package-list {{
    margin-top: 10px;
    font-size: 12px;
    color: #88ff88;
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
        <span class="header-title">{title}</span>
        <div class="header-controls">
            <button class="refresh-btn" onclick="clearOutput()">🗑️ Clear</button>
            <button class="refresh-btn" onclick="retryLoading()">↻ Retry</button>
        </div>
    </div>
    
    <div class="install-hint" id="installHint">
        📱 Tap menu → Add to Home screen
    </div>
    
    <div class="loading" id="loading">
        <div class="spinner"></div>
        <div id="loadingStatus">Initializing Python environment...</div>
        <div id="packageStatus" class="package-list"></div>
        <div id="loadingDetails" class="error-details"></div>
        <div id="networkStatus" class="network-status">Checking network...</div>
    </div>
    
    <div id="output"></div>

    <script>
        let pyodide = null;
        let isReady = false;
        let outputLines = [];
        let loadingAttempts = 0;
        
        const PYTHON_CODE = {python_code};
        const PACKAGES = {packages};
        
        // Show install hint
        if (/Android|iPhone/i.test(navigator.userAgent)) {{
            if (!window.matchMedia('(display-mode: standalone)').matches) {{
                document.getElementById('installHint').classList.add('show');
            }}
        }}
        
        // Check network connectivity
        function checkNetwork() {{
            const networkStatus = document.getElementById('networkStatus');
            if (navigator.onLine) {{
                networkStatus.textContent = '📶 Network: Online';
                networkStatus.style.color = '#88ff88';
            }} else {{
                networkStatus.textContent = '📶 Network: Offline - Please connect to internet';
                networkStatus.style.color = '#ff8888';
            }}
        }}
        
        setInterval(checkNetwork, 2000);
        
        // Add line to console output
        function addOutputLine(text, type = 'stdout') {{
            const timestamp = new Date().toLocaleTimeString();
            outputLines.push({{
                timestamp,
                text,
                type
            }});
            
            if (outputLines.length > 1000) {{
                outputLines.shift();
            }}
            
            updateOutput();
        }}
        
        // Clear output
        function clearOutput() {{
            outputLines = [];
            updateOutput();
        }}
        
        // Update display
        function updateOutput() {{
            const output = document.getElementById('output');
            let html = '<div class="console-container">';
            
            outputLines.forEach(line => {{
                if (line.type === 'html') {{
                    html += '<div class="console-html">' + line.text + '</div>';
                }} else if (line.type === 'stderr') {{
                    html += '<div class="console-error">[ERROR] ' + line.text.replace(/</g, '&lt;') + '</div>';
                }} else {{
                    html += '<div class="console-line"><span class="console-timestamp">[' + line.timestamp + ']</span> ' + 
                           '<span class="console-output">' + line.text.replace(/</g, '&lt;') + '</span></div>';
                }}
            }});
            
            html += '</div>';
            output.innerHTML = html;
            window.scrollTo(0, document.body.scrollHeight);
        }}
        
        // Retry loading
        function retryLoading() {{
            loadingAttempts++;
            addOutputLine('🔄 Retrying initialization (attempt ' + (loadingAttempts + 1) + ')...');
            init();
        }}
        
        // Initialize Pyodide with package installation
        async function init() {{
            const loading = document.getElementById('loading');
            const status = document.getElementById('loadingStatus');
            const packageStatus = document.getElementById('packageStatus');
            const details = document.getElementById('loadingDetails');
            
            loading.classList.add('show');
            status.textContent = 'Initializing Python environment...';
            packageStatus.innerHTML = '';
            details.textContent = '';
            
            addOutputLine('🚀 PyWA starting up...');
            addOutputLine('📱 Device: ' + navigator.userAgent);
            addOutputLine('🌐 Network: ' + (navigator.onLine ? 'Online' : 'Offline'));
            
            if (PACKAGES.length > 0) {{
                addOutputLine('📦 Required packages: ' + PACKAGES.join(', '));
                packageStatus.innerHTML = '📦 Packages: ' + PACKAGES.join(', ');
            }}
            
            try {{
                status.textContent = 'Loading Pyodide (5-10MB)...';
                addOutputLine('📦 Loading Pyodide (this may take a moment)...');
                
                // Load Pyodide
                pyodide = await loadPyodide({{
                    indexURL: "https://cdn.jsdelivr.net/pyodide/v0.24.1/full/",
                }});
                
                addOutputLine('✅ Pyodide loaded successfully');
                status.textContent = 'Pyodide loaded';
                
                // Install packages if needed
                if (PACKAGES.length > 0) {{
                    status.textContent = 'Loading package manager...';
                    addOutputLine('📚 Loading micropip...');
                    
                    await pyodide.loadPackage('micropip');
                    const micropip = pyodide.pyimport('micropip');
                    
                    status.textContent = 'Installing packages...';
                    
                    for (const pkg of PACKAGES) {{
                        status.textContent = `Installing ${{pkg}}...`;
                        packageStatus.innerHTML = `📦 Installing ${{pkg}}...`;
                        addOutputLine(`📦 Installing ${{pkg}}...`);
                        
                        try {{
                            // Special handling for some packages
                            if (pkg === 'plotly') {{
                                await micropip.install('plotly');
                                addOutputLine(`✅ plotly installed`);
                            }} else if (pkg === 'pandas') {{
                                await micropip.install('pandas');
                                addOutputLine(`✅ pandas installed`);
                            }} else if (pkg === 'numpy') {{
                                await micropip.install('numpy');
                                addOutputLine(`✅ numpy installed`);
                            }} else if (pkg === 'requests') {{
                                await micropip.install('requests');
                                addOutputLine(`✅ requests installed`);
                            }} else {{
                                await micropip.install(pkg);
                                addOutputLine(`✅ ${{pkg}} installed`);
                            }}
                        }} catch (e) {{
                            addOutputLine(`⚠️ Could not install ${{pkg}}: ${{e}}`, 'stderr');
                        }}
                    }}
                    
                    packageStatus.innerHTML = '✅ All packages installed';
                }}
                
                isReady = true;
                status.textContent = 'Ready!';
                addOutputLine('✅ Python environment ready');
                setTimeout(() => loading.classList.remove('show'), 500);
                
                // Auto-run
                runPython();
                
            }} catch (error) {{
                const errorMsg = `Failed to load Pyodide: ${{error}}`;
                addOutputLine(`❌ ${{errorMsg}}`, 'stderr');
                status.textContent = 'Loading failed';
                details.textContent = error.toString();
                
                addOutputLine('', 'stderr');
                addOutputLine('💡 Troubleshooting tips:', 'stderr');
                addOutputLine('   1. Check your internet connection', 'stderr');
                addOutputLine('   2. Try WiFi instead of mobile data', 'stderr');
                addOutputLine('   3. Click Retry button', 'stderr');
                
                setTimeout(() => loading.classList.remove('show'), 1000);
            }}
        }}
        
        // Run Python code
        async function runPython() {{
            if (!isReady) {{
                await init();
                return;
            }}
            
            const loading = document.getElementById('loading');
            const status = document.getElementById('loadingStatus');
            const btn = document.querySelector('.refresh-btn:last-child');
            
            loading.classList.add('show');
            btn.disabled = true;
            status.textContent = 'Running Python...';
            
            addOutputLine('\\n' + '='.repeat(50));
            addOutputLine('🚀 Starting Python execution');
            addOutputLine('='.repeat(50));
            
            try {{
                // Setup Python to capture all output
                await pyodide.runPythonAsync(`
import sys
from io import StringIO

# Custom output capture
class JSCapture:
    def __init__(self):
        self.buffer = []
    
    def write(self, text):
        if text and text.strip():
            self.buffer.append(text)
            try:
                import js
                js.addOutputLine(text.rstrip())
            except:
                pass
    
    def flush(self):
        pass
    
    def getvalue(self):
        return ''.join(self.buffer)

# Replace stdout and stderr
sys.stdout = JSCapture()
sys.stderr = JSCapture()

print("Python environment ready")
                `);
                
                // Run user code
                addOutputLine('📝 Executing user code...');
                await pyodide.runPythonAsync(PYTHON_CODE);
                
                addOutputLine('='.repeat(50));
                addOutputLine('✅ Python execution complete');
                addOutputLine('='.repeat(50));
                
            }} catch (error) {{
                addOutputLine(`❌ Error: ${{error}}`, 'stderr');
            }}
            
            loading.classList.remove('show');
            btn.disabled = false;
        }}
        
        // Start initialization
        setTimeout(() => {{
            checkNetwork();
            init();
        }}, 500);
        
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
        
        # Detect packages
        packages = detect_packages(python_code)
        print(f"📦 Detected packages: {packages if packages else 'none'}")
        
        # Add CORS proxy wrapper
        wrapped_code = f'''
# PyWA - Python code with CORS proxy
import sys
import requests
import json
from js import window

# CORS proxy for Yahoo Finance
original_get = requests.get

def fetch_with_proxy(url):
    try:
        proxy_url = f"https://api.allorigins.win/raw?url={{url}}"
        print(f"📡 Using proxy for: {{url[:50]}}...")
        response = requests.get(proxy_url, timeout=30)
        print(f"📡 Proxy response: {{response.status_code}}")
        return response
    except Exception as e:
        print(f"⚠️ Proxy error: {{e}}")
        return original_get(url, timeout=30)

def patched_get(url, **kwargs):
    if 'yahoo.com' in url or 'finance' in url:
        return fetch_with_proxy(url)
    return original_get(url, **kwargs)

requests.get = patched_get
print("✅ CORS proxy enabled")

# Your code follows:
{python_code}

# Flush output
sys.stdout.flush()
sys.stderr.flush()
'''
        
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
        print(f"\n📦 Packages will be installed automatically in browser")
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