#!/usr/bin/env python3
"""
PyWA - Python to PWA Compiler
Captures ANY Python-generated HTML and creates a live-updating PWA.
When refresh is clicked, it RE-RUNS the Python script and updates the display
with the NEW HTML output - exactly as if you ran it fresh!
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
import subprocess
import threading
import http.server
import socketserver
import socket
import webbrowser
import signal
import html as html_module
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

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
#  HTML CAPTURER - Runs Python and captures its HTML output EXACTLY as generated
# ══════════════════════════════════════════════════════════════════
class HTMLCapturer:
    """Runs Python file and captures its HTML output exactly as it would appear."""
    
    @staticmethod
    def capture(file_path, timeout_seconds=120):
        """Run Python and capture any HTML it generates."""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return f"Error: File not found: {file_path}", False, 1
            
            # Look for HTML files before running
            html_files_before = set(Path(file_path.parent).glob("*.html"))
            
            # Run the Python script with timeout
            try:
                result = subprocess.run(
                    [sys.executable, str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    cwd=file_path.parent,
                    env=os.environ.copy()
                )
            except subprocess.TimeoutExpired:
                return "Error: Execution timed out", False, 1
            except Exception as e:
                return f"Error running script: {str(e)}", False, 1
            
            # Check for new HTML files
            html_files_after = set(Path(file_path.parent).glob("*.html"))
            new_html = html_files_after - html_files_before
            
            # If new HTML files found, use the most recent one
            if new_html:
                latest_html = max(new_html, key=lambda p: p.stat().st_mtime)
                try:
                    html_content = latest_html.read_text(encoding='utf-8')
                    return html_content, True, result.returncode
                except Exception as e:
                    pass
            
            # Check stdout for HTML
            if HTMLCapturer._is_html(result.stdout):
                return result.stdout, True, result.returncode
            
            # Return stdout as fallback
            output = result.stdout
            if result.stderr:
                output += f"\n\n--- STDERR ---\n{result.stderr}"
            
            return output, False, result.returncode
            
        except Exception as e:
            return f"Unexpected error: {str(e)}", False, 1
    
    @staticmethod
    def _is_html(text):
        """Check if text contains HTML."""
        if not text or len(text) < 50:
            return False
        
        # Check for HTML doctype or html tag
        if '<!DOCTYPE html' in text[:500].upper():
            return True
        if '<html' in text[:500].lower():
            return True
        
        # Count HTML indicators
        html_patterns = ['<div', '<span', '<table', '<script', '<style']
        score = 0
        for pattern in html_patterns:
            if pattern in text.lower():
                score += 1
        
        return score >= 2


# ══════════════════════════════════════════════════════════════════
#  PWA WRAPPER - Creates PWA that looks EXACTLY like the generated HTML
# ══════════════════════════════════════════════════════════════════
class PWAWrapper:
    """Creates PWA that preserves the EXACT look of the generated HTML."""
    
    # Minimal CSS only for the refresh button - everything else comes from original HTML
    BASE_CSS = """
/* PyWA - Minimal wrapper styles */
* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

:root {{
    --primary: {theme_color};
}}

/* Small header for refresh button - only visible when NOT installed */
.app-header {{
    background: var(--primary);
    color: white;
    padding: 8px 16px;
    font-size: 1rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}

/* Hide header when installed as PWA */
@media all and (display-mode: standalone) {{
    .app-header {{
        display: none;
    }}
}}

.refresh-btn {{
    background: rgba(255,255,255,0.2);
    border: none;
    color: white;
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 0.9rem;
    cursor: pointer;
}}

.refresh-btn:disabled {{
    opacity: 0.5;
    cursor: not-allowed;
}}

/* Install hint - only shown on mobile when not installed */
.install-hint {{
    background: #f0f0f0;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 8px 12px;
    margin: 8px;
    font-size: 0.9rem;
    display: none;
}}
.install-hint.show {{ display: block; }}

/* Loading indicator */
.loading {{
    display: none;
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: rgba(0,0,0,0.8);
    color: white;
    padding: 16px 24px;
    border-radius: 8px;
    z-index: 1000;
}}
.loading.show {{ display: block; }}

/* Content area - EXACTLY as the original HTML */
.content {{
    width: 100%;
    min-height: calc(100vh - 50px);
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
    <style>
{css}
    </style>
</head>
<body>
    <!-- Small header for refresh (hidden when installed) -->
    <div class="app-header">
        <span>{title}</span>
        <button class="refresh-btn" onclick="refreshData()">↻ Refresh Data</button>
    </div>
    
    <!-- Install hint for mobile -->
    <div class="install-hint" id="installHint">
        📱 Tap menu → "Add to Home screen" to install (removes this bar)
    </div>
    
    <!-- Loading indicator -->
    <div class="loading" id="loading">Running Python script...</div>
    
    <!-- EXACT content from Python script - preserved 100% -->
    <div class="content" id="content">
        {content}
    </div>

    <script>
        // Show install hint on mobile
        function isMobile() {{
            return /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
        }}
        
        function isInstalled() {{
            return window.matchMedia('(display-mode: standalone)').matches ||
                   window.navigator.standalone === true;
        }}
        
        if (isMobile() && !isInstalled()) {{
            document.getElementById('installHint').classList.add('show');
        }}
        
        // Refresh function - RE-RUNS the Python script
        function refreshData() {{
            const loading = document.getElementById('loading');
            const content = document.getElementById('content');
            const btn = document.querySelector('.refresh-btn');
            
            loading.classList.add('show');
            btn.disabled = true;
            
            fetch('/_refresh')
                .then(response => response.text())
                .then(html => {{
                    // Replace content with fresh HTML from Python
                    content.innerHTML = html;
                    
                    // Re-run any scripts in the new content
                    Array.from(content.getElementsByTagName('script')).forEach(oldScript => {{
                        const newScript = document.createElement('script');
                        Array.from(oldScript.attributes).forEach(attr => {{
                            newScript.setAttribute(attr.name, attr.value);
                        }});
                        newScript.appendChild(document.createTextNode(oldScript.innerHTML));
                        oldScript.parentNode.replaceChild(newScript, oldScript);
                    }});
                    
                    loading.classList.remove('show');
                    btn.disabled = false;
                }})
                .catch(error => {{
                    content.innerHTML = '<pre style="color:#ff4444;">Error refreshing: ' + error.message + '</pre>';
                    loading.classList.remove('show');
                    btn.disabled = false;
                }});
        }}
        
        // Auto-refresh every 5 minutes when installed
        if (isInstalled()) {{
            setInterval(refreshData, 5 * 60 * 1000);
        }}
        
        // Handle Plotly resize
        window.addEventListener('resize', function() {{
            if (typeof Plotly !== 'undefined') {{
                try {{ Plotly.Plots.resize(); }} catch(e) {{}}
            }}
        }});
    </script>
</body>
</html>"""
    
    @classmethod
    def wrap(cls, content, config, is_html=False):
        """Wrap content in PWA while preserving EXACT original look."""
        
        # Minimal CSS for controls
        css = cls.BASE_CSS.format(
            theme_color=config.get("theme_color", "#1a1a2e")
        )
        
        # Prepare content - if it's HTML, use it EXACTLY as is
        if is_html and content:
            # If it's a full HTML document, extract just the body content
            if '<body' in content.lower():
                body_match = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL | re.IGNORECASE)
                if body_match:
                    main_content = body_match.group(1).strip()
                else:
                    main_content = content
            else:
                main_content = content
        else:
            # Escape text output
            escaped_content = html_module.escape(content or "No output")
            main_content = f'<pre style="background:#1e1e1e;color:#f0f0f0;padding:16px;font-family:monospace;">{escaped_content}</pre>'
        
        # Generate final HTML
        final_html = cls.HTML_TEMPLATE.format(
            title=config.get('name', 'PyWA App'),
            theme_color=config.get("theme_color", "#1a1a2e"),
            css=css,
            content=main_content
        )
        
        return final_html


# ══════════════════════════════════════════════════════════════════
#  ASSET GENERATORS
# ══════════════════════════════════════════════════════════════════
def make_png(size, hex_color):
    """Generate a simple PNG icon."""
    if not hex_color or len(hex_color) < 7:
        hex_color = "#1a1a2e"
    
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    
    raw = bytearray()
    for y in range(size):
        for x in range(size):
            raw.extend([r, g, b, 255])
    
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
  if (e.request.url.includes('/_refresh')) {{
    e.respondWith(fetch(e.request));
    return;
  }}
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  );
}});
"""


# ══════════════════════════════════════════════════════════════════
#  REFRESH SERVER - Re-runs Python and returns FRESH HTML
# ══════════════════════════════════════════════════════════════════
class RefreshHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler that re-runs Python and returns fresh HTML."""
    
    source_file = None
    
    def do_GET(self):
        if self.path == '/_refresh':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            
            try:
                # Look for HTML files before running
                html_files_before = set(Path.cwd().glob("*.html"))
                
                # RE-RUN the Python script
                result = subprocess.run(
                    [sys.executable, self.source_file],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=Path(self.source_file).parent
                )
                
                # Check for new HTML files
                html_files_after = set(Path.cwd().glob("*.html"))
                new_html = html_files_after - html_files_before
                
                if new_html:
                    latest_html = max(new_html, key=lambda p: p.stat().st_mtime)
                    content = latest_html.read_text(encoding='utf-8')
                    
                    # Extract body if full HTML
                    if '<body' in content.lower():
                        body_match = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL | re.IGNORECASE)
                        if body_match:
                            content = body_match.group(1)
                elif HTMLCapturer._is_html(result.stdout):
                    content = result.stdout
                else:
                    content = result.stdout
                    if result.stderr:
                        content += f"\n\n{result.stderr}"
                
                self.wfile.write(content.encode('utf-8'))
                
            except Exception as e:
                self.wfile.write(f"Error: {str(e)}".encode('utf-8'))
        else:
            super().do_GET()
    
    def log_message(self, format, *args):
        pass


# ══════════════════════════════════════════════════════════════════
#  FILE PICKER
# ══════════════════════════════════════════════════════════════════
def pick_py_file():
    """Simple file picker."""
    base = Path.cwd()
    print(f"\n  🔍 Searching for Python files...")
    
    found = []
    for f in base.glob("*.py"):
        if f.name not in ["pywa.py", "pywa_v1p2.py"]:
            found.append(f)
    
    if not found:
        print(f"  ❌ No Python files found")
        return None
    
    if len(found) == 1:
        print(f"  ✅ Found: {found[0].name}")
        return found[0]
    
    print("\n  Multiple files found:\n")
    for i, f in enumerate(found, 1):
        print(f"    [{i}] {f.name}")
    
    while True:
        try:
            choice = input("\n  Select number: ").strip()
            if choice == "0":
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(found):
                return found[idx]
        except:
            return None


# ══════════════════════════════════════════════════════════════════
#  SERVER FUNCTIONS
# ══════════════════════════════════════════════════════════════════
def find_free_port():
    """Find free port."""
    for port in range(8080, 8100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", port))
                return port
        except:
            continue
    return 8080


def get_local_ip():
    """Get local IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "192.168.x.x"


def serve_with_refresh(directory, port, source_file):
    """Start server that re-runs Python on refresh."""
    os.chdir(directory)
    
    RefreshHTTPRequestHandler.source_file = source_file
    handler = RefreshHTTPRequestHandler
    
    try:
        httpd = socketserver.TCPServer(("0.0.0.0", port), handler)
    except Exception as e:
        print(f"\n  ❌ Failed to start server: {e}")
        return
    
    local_ip = get_local_ip()
    
    print(f"\n  {'='*50}")
    print(f"  🌐 PWA Server Ready!")
    print(f"  {'='*50}")
    print(f"\n  📱 Local:  http://localhost:{port}")
    print(f"  📱 Android: http://{local_ip}:{port}")
    print(f"\n  Source: {source_file}")
    print(f"\n  Click 'Refresh Data' to re-run Python script")
    print(f"  Install to home screen to remove the top bar")
    print(f"\n  Press Ctrl+C to stop\n")
    
    try:
        webbrowser.open(f"http://localhost:{port}")
    except:
        pass
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        description="PyWA - Python to Live-updating PWA"
    )
    parser.add_argument("file", nargs="?", help="Python file")
    parser.add_argument("--name", help="App name")
    parser.add_argument("--theme", default="light", help="Theme")
    parser.add_argument("--color", help="Primary color")
    parser.add_argument("--out", default="pwa_output", help="Output dir")
    parser.add_argument("--port", type=int, help="Port")
    parser.add_argument("--no-serve", action="store_true", help="Compile only")
    
    args = parser.parse_args()
    
    if not args.file:
        file_path = pick_py_file()
        if not file_path:
            return
        args.file = str(file_path)
    
    config = {
        "name": args.name,
        "theme": args.theme,
        "theme_color": args.color,
        "output_dir": args.out,
        "version": datetime.now().strftime("%Y%m%d")
    }
    config = {k: v for k, v in config.items() if v is not None}
    
    print("\n" + "="*50)
    print("🚀 PyWA - Python to PWA")
    print("="*50)
    
    src = Path(args.file)
    print(f"\n  📄 File: {src.name}")
    
    # Run Python and capture initial output
    content, is_html, _ = HTMLCapturer.capture(src)
    print(f"  📊 Type: {'HTML' if is_html else 'Text'}")
    
    # Set app name
    if not config.get('name'):
        config['name'] = src.stem.replace('_', ' ').title()
    
    config = resolve_theme(config)
    
    # Generate PWA
    print("  🔧 Building PWA...")
    html_output = PWAWrapper.wrap(content, config, is_html)
    
    # Write files
    out_dir = Path(config["output_dir"])
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir()
    
    (out_dir / "index.html").write_text(html_output, encoding='utf-8')
    (out_dir / "manifest.json").write_text(make_manifest(config))
    (out_dir / "sw.js").write_text(make_sw(config["version"]))
    
    for size in [192, 512]:
        (out_dir / f"icon-{size}.png").write_bytes(make_png(size, config["theme_color"]))
    
    print(f"  ✅ PWA saved to: {out_dir}/")
    
    if not args.no_serve:
        port = args.port or find_free_port()
        serve_with_refresh(out_dir, port, args.file)


if __name__ == "__main__":
    main()