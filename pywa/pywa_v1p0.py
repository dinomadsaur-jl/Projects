#!/usr/bin/env python3
"""
PyWA - Python to PWA Compiler
Captures ANY Python-generated HTML and creates a live-updating PWA.
Perfect for dashboards, plots, and visualizations on Android!
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
#  HTML CAPTURER - Runs ANY Python file and captures its HTML output
# ══════════════════════════════════════════════════════════════════
class HTMLCapturer:
    """Runs ANY Python file and captures its HTML output."""
    
    @staticmethod
    def capture(file_path):
        """Run Python and capture any HTML it generates."""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return f"<pre>Error: File not found: {file_path}</pre>", True, 1
            
            # Look for HTML files before running
            html_files_before = set(Path.cwd().glob("*.html"))
            
            # Run the Python script
            print(f"  🏃 Running: {file_path.name}")
            result = subprocess.run(
                [sys.executable, str(file_path)],
                capture_output=True,
                text=True,
                timeout=120,  # Longer timeout for data fetching
                cwd=Path.cwd()
            )
            
            # Check for new HTML files
            html_files_after = set(Path.cwd().glob("*.html"))
            new_html = html_files_after - html_files_before
            
            if new_html:
                # Get the most recent HTML file
                latest_html = max(new_html, key=lambda p: p.stat().st_mtime)
                html_content = latest_html.read_text(encoding='utf-8')
                print(f"     ✅ Captured from: {latest_html.name}")
                return html_content, True, result.returncode
            
            # Check stdout for HTML
            if HTMLCapturer._is_html(result.stdout):
                print(f"     ✅ Captured HTML from stdout")
                return result.stdout, True, result.returncode
            
            # Return stdout as fallback
            output = result.stdout
            if result.stderr:
                output += f"\n\n--- STDERR ---\n{result.stderr}"
            
            if result.returncode != 0:
                print(f"     ⚠️  Script exited with code {result.returncode}")
            
            return output, False, result.returncode
            
        except subprocess.TimeoutExpired:
            return "<pre>Error: Execution timed out (120 seconds)</pre>", True, 1
        except Exception as e:
            return f"<pre>Error: {str(e)}</pre>", True, 1
    
    @staticmethod
    def _is_html(text):
        """Check if text contains HTML."""
        if not text:
            return False
        html_patterns = [
            '<html', '<!DOCTYPE', '<body', '<head', '<div',
            '<script', '<svg', '<canvas', '<style', '<table',
            'Plotly', 'chart', 'dashboard'
        ]
        text_lower = text.lower()
        for pattern in html_patterns:
            if pattern.lower() in text_lower:
                return True
        return False


# ══════════════════════════════════════════════════════════════════
#  PWA WRAPPER - Generic wrapper with live refresh
# ══════════════════════════════════════════════════════════════════
class PWAWrapper:
    """Generic PWA wrapper with live refresh on install."""
    
    CSS_TEMPLATE = """
* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

:root {{
    --bg: {bg_color};
    --primary: {theme_color};
    --accent: {accent};
    --text: {text};
    --surface: {surface};
    --border: {border};
    --font: {font};
}}

body {{
    background: var(--bg);
    color: var(--text);
    font-family: var(--font);
    line-height: 1.6;
    min-height: 100vh;
    padding-bottom: env(safe-area-inset-bottom);
}}

/* Simple header */
.app-header {{
    background: var(--primary);
    color: white;
    padding: 12px 16px;
    font-size: 1.2rem;
    font-weight: 600;
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    display: flex;
    justify-content: space-between;
    align-items: center;
}}

.refresh-btn {{
    background: rgba(255,255,255,0.2);
    border: none;
    color: white;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 0.9rem;
    cursor: pointer;
    transition: background 0.2s;
}}

.refresh-btn:hover {{
    background: rgba(255,255,255,0.3);
}}

.refresh-btn:disabled {{
    opacity: 0.5;
    cursor: not-allowed;
}}

/* Main content */
.content {{
    max-width: 100%;
    margin: 0 auto;
    padding: 0;
    overflow-x: auto;
}}

/* Install hint */
.install-hint {{
    background: var(--surface);
    border: 1px solid var(--border);
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
    text-align: center;
    padding: 20px;
    color: var(--primary);
}}
.loading.show {{ display: block; }}

/* Preserve original HTML styling */
{content_css}
"""
    
    HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <title>{title}</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-title" content="{title}">
    <meta name="theme-color" content="{theme_color}">
    <link rel="manifest" href="manifest.json">
    <link rel="apple-touch-icon" href="icon-192.png">
    <style>{css}</style>
</head>
<body>
    <div class="app-header">
        <span>{title}</span>
        <button class="refresh-btn" onclick="refreshData()">↻ Refresh</button>
    </div>
    
    <div class="install-hint" id="installHint">
        📱 Tap menu → "Add to Home screen" to install
    </div>
    
    <div class="loading" id="loading">Loading new data...</div>
    
    <div class="content" id="content">
        {content}
    </div>

    <script>
        // Show install hint on mobile
        if (/Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) {{
            if (!window.matchMedia('(display-mode: standalone)').matches) {{
                document.getElementById('installHint').classList.add('show');
            }}
        }}
        
        // Live refresh function - re-runs Python and updates content
        function refreshData() {{
            const loading = document.getElementById('loading');
            const content = document.getElementById('content');
            const btn = document.querySelector('.refresh-btn');
            
            loading.classList.add('show');
            btn.disabled = true;
            btn.textContent = '↻ Refreshing...';
            
            fetch('/_refresh')
                .then(response => {{
                    if (!response.ok) {{
                        throw new Error('Network response was not ok');
                    }}
                    return response.text();
                }})
                .then(html => {{
                    content.innerHTML = html;
                    loading.classList.remove('show');
                    btn.disabled = false;
                    btn.textContent = '↻ Refresh';
                    
                    // Re-run any scripts in the new content
                    Array.from(content.getElementsByTagName('script')).forEach(oldScript => {{
                        const newScript = document.createElement('script');
                        Array.from(oldScript.attributes).forEach(attr => {{
                            newScript.setAttribute(attr.name, attr.value);
                        }});
                        newScript.appendChild(document.createTextNode(oldScript.innerHTML));
                        oldScript.parentNode.replaceChild(newScript, oldScript);
                    }});
                }})
                .catch(error => {{
                    console.error('Refresh failed:', error);
                    loading.classList.remove('show');
                    btn.disabled = false;
                    btn.textContent = '↻ Refresh';
                    alert('Failed to refresh data. Check Python script.');
                }});
        }}
        
        // Auto-refresh every 5 minutes if installed as PWA
        if (window.matchMedia('(display-mode: standalone)').matches) {{
            setInterval(refreshData, 5 * 60 * 1000);
        }}
        
        // Handle Plotly resize if present
        window.addEventListener('resize', function() {{
            if (typeof Plotly !== 'undefined') {{
                try {{
                    Plotly.Plots.resize();
                }} catch(e) {{
                    console.log('Plotly resize error:', e);
                }}
            }}
        }});
    </script>
</body>
</html>"""
    
    @classmethod
    def wrap(cls, content, config, is_html=False):
        """Wrap content in PWA with live refresh."""
        
        # Extract any CSS from the original HTML to preserve styling
        content_css = ""
        if is_html and content:
            # Try to extract styles to preserve them
            style_matches = re.findall(r'<style[^>]*>(.*?)</style>', content, re.DOTALL | re.IGNORECASE)
            if style_matches:
                content_css = '\n'.join(style_matches)
        
        # Format CSS with theme colors (using double braces for CSS curly braces)
        css = cls.CSS_TEMPLATE.format(
            bg_color=config.get("bg_color", "#ffffff"),
            theme_color=config.get("theme_color", "#1a1a2e"),
            accent=config.get("accent", "#e94560"),
            text=config.get("text", "#1a1a1a"),
            surface=config.get("surface", "#f5f5f5"),
            border=config.get("border", "#e0e0e0"),
            font=config.get("font", "'Segoe UI', system-ui, sans-serif"),
            content_css=content_css
        )
        
        # Prepare content
        if is_html and content:
            main_content = content
        else:
            main_content = f'<pre style="background:#1e1e1e;color:#f0f0f0;padding:16px;border-radius:8px;overflow:auto;">{content or "No output"}</pre>'
        
        # Generate HTML
        html = cls.HTML_TEMPLATE.format(
            title=config.get('name', 'PyWA App'),
            theme_color=config.get("theme_color", "#1a1a2e"),
            css=css,
            content=main_content
        )
        
        return html


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
    
    # Create a simple pattern
    raw = bytearray()
    for y in range(size):
        for x in range(size):
            # Simple gradient effect
            factor = 1.0 - (abs(x - size/2) / (size/2)) * 0.3
            raw.extend([
                int(min(255, r * factor)),
                int(min(255, g * factor)),
                int(min(255, b * factor)),
                255
            ])
    
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
            {"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"},
        ]
    }, indent=2)


def make_sw(version):
    """Generate service worker with refresh endpoint."""
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
  // Special endpoint for refresh - bypass cache
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
#  REFRESH SERVER - Handles live updates
# ══════════════════════════════════════════════════════════════════
class RefreshHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler with refresh endpoint."""
    
    source_file = None
    
    def do_GET(self):
        if self.path == '/_refresh':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            try:
                # Re-run the Python script
                result = subprocess.run(
                    [sys.executable, self.source_file],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=Path(self.source_file).parent
                )
                
                # Check for new HTML files
                html_files = list(Path.cwd().glob("*.html"))
                if html_files:
                    latest_html = max(html_files, key=lambda p: p.stat().st_mtime)
                    content = latest_html.read_text(encoding='utf-8')
                else:
                    content = result.stdout
                    if result.stderr:
                        content += f"\n\n<hr><pre style='color:#ff4444;'>{result.stderr}</pre>"
                
                self.wfile.write(content.encode('utf-8'))
            except subprocess.TimeoutExpired:
                self.wfile.write(b"<pre>Refresh timeout (120 seconds)</pre>")
            except Exception as e:
                self.wfile.write(f"<pre>Refresh error: {str(e)}</pre>".encode('utf-8'))
        else:
            super().do_GET()
    
    def log_message(self, format, *args):
        """Silence log messages."""
        pass


# ══════════════════════════════════════════════════════════════════
#  FILE PICKER
# ══════════════════════════════════════════════════════════════════
def pick_py_file():
    """Simple file picker."""
    base = Path.cwd()
    print(f"\n  🔍 Searching for Python files in: {base}")
    
    found = []
    for f in base.glob("*.py"):
        if f.name not in ["pywa.py", "pywa_v0p2.py", "pywa_v0p3.py", "pywa_v1p0.py"]:
            found.append(f)
    
    if not found:
        print(f"\n  ❌ No Python files found")
        return None
    
    if len(found) == 1:
        print(f"  ✅ Found: {found[0].name}")
        return found[0]
    
    print("\n  📁 Multiple files found:\n")
    for i, f in enumerate(found, 1):
        print(f"    [{i}] {f.name}")
    print("\n    [0] Cancel")
    
    while True:
        try:
            choice = input("\n  Select file number: ").strip()
            if choice == "0":
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(found):
                return found[idx]
            print(f"  Enter 1-{len(found)}")
        except (ValueError, KeyboardInterrupt):
            print("  Invalid input")
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
        except OSError:
            continue
    return 8080


def get_local_ip():
    """Get local IP address."""
    try:
        # Create a temporary socket to get local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "192.168.x.x"


def serve_with_refresh(directory, port, source_file):
    """Start server with refresh endpoint."""
    os.chdir(directory)
    
    RefreshHTTPRequestHandler.source_file = source_file
    handler = RefreshHTTPRequestHandler
    
    try:
        httpd = socketserver.TCPServer(("0.0.0.0", port), handler)
    except OSError as e:
        print(f"\n  ❌ Failed to start server on port {port}: {e}")
        return
    
    local_ip = get_local_ip()
    
    print(f"\n  {'='*50}")
    print(f"  🌐 Server running!")
    print(f"  {'='*50}")
    print(f"\n  📱 On this device:  http://localhost:{port}")
    print(f"  📱 On Android:      http://{local_ip}:{port}")
    print(f"\n  💡 Features:")
    print(f"     • Click 'Refresh' to update data")
    print(f"     • Auto-refresh every 5 minutes when installed")
    print(f"     • Tap menu → 'Add to Home screen' to install")
    print(f"\n  Press Ctrl+C to stop\n")
    
    # Try to open browser on this device
    try:
        webbrowser.open(f"http://localhost:{port}")
    except:
        pass
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
        httpd.shutdown()


# ══════════════════════════════════════════════════════════════════
#  MAIN COMPILER
# ══════════════════════════════════════════════════════════════════
class PyWACompiler:
    """Main compiler class."""
    
    def __init__(self, config=None):
        self.config = {**DEFAULTS, **(config or {})}
    
    def compile(self, source_file):
        """Compile Python file to PWA."""
        print("\n" + "="*50)
        print("🚀 PyWA - Python to PWA Compiler")
        print("="*50)
        
        src = Path(source_file)
        print(f"\n  📄 Source: {src.name}")
        print(f"  📦 Output: {self.config['output_dir']}/\n")
        
        # Step 1: Run Python and capture output
        print("  [1/4] Running Python...")
        content, is_html, returncode = HTMLCapturer.capture(src)
        
        # Step 2: Set app name if not provided
        if not self.config.get('name'):
            self.config['name'] = src.stem.replace('_', ' ').replace('-', ' ').title()
        
        if not self.config.get('short_name'):
            words = self.config['name'].split()
            self.config['short_name'] = ''.join(w[0] for w in words[:3])[:12]
        
        # Apply theme
        self.config = resolve_theme(self.config)
        
        # Step 3: Generate PWA HTML
        print("  [2/4] Generating PWA...")
        html = PWAWrapper.wrap(content, self.config, is_html)
        
        # Step 4: Write files
        print("  [3/4] Writing files...")
        out_dir = Path(self.config["output_dir"])
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True)
        
        # Write HTML
        (out_dir / "index.html").write_text(html, encoding='utf-8')
        print("     ✅ index.html")
        
        # Write manifest
        (out_dir / "manifest.json").write_text(make_manifest(self.config))
        print("     ✅ manifest.json")
        
        # Write service worker
        (out_dir / "sw.js").write_text(make_sw(self.config["version"]))
        print("     ✅ sw.js")
        
        # Generate icons
        for size in [192, 512]:
            (out_dir / f"icon-{size}.png").write_bytes(make_png(size, self.config["theme_color"]))
        print("     ✅ icons")
        
        # Calculate total size
        total_size = sum(f.stat().st_size for f in out_dir.glob("**/*") if f.is_file())
        print(f"\n  [4/4] ✅ Complete! {total_size:,} bytes")
        
        return out_dir


# ══════════════════════════════════════════════════════════════════
#  MAIN CLI
# ══════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        description="PyWA - Convert ANY Python script to a live-updating PWA"
    )
    parser.add_argument("file", nargs="?", help="Python file to convert")
    parser.add_argument("--name", help="App name")
    parser.add_argument("--theme", default="light", help="Theme: light/dark")
    parser.add_argument("--color", help="Primary color (hex)")
    parser.add_argument("--out", default="pwa_output", help="Output directory")
    parser.add_argument("--port", type=int, help="Port (default: auto)")
    parser.add_argument("--no-serve", action="store_true", help="Compile only")
    parser.add_argument("--no-open", action="store_true", help="Don't open browser")
    
    args = parser.parse_args()
    
    # Pick file if not specified
    if not args.file:
        file_path = pick_py_file()
        if not file_path:
            return
        args.file = str(file_path)
    
    # Build config
    config = {
        "name": args.name,
        "theme": args.theme,
        "theme_color": args.color,
        "output_dir": args.out,
        "version": datetime.now().strftime("%Y%m%d.%H%M")
    }
    config = {k: v for k, v in config.items() if v is not None}
    
    # Compile
    compiler = PyWACompiler(config)
    out_dir = compiler.compile(args.file)
    
    # Serve if not disabled
    if not args.no_serve:
        port = args.port or find_free_port()
        serve_with_refresh(out_dir, port, args.file)
    else:
        print(f"\n  📁 Files saved to: {out_dir}/")
        print("  Run with --serve to start server")


if __name__ == "__main__":
    main()