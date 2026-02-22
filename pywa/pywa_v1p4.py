#!/usr/bin/env python3
"""
PyWA - Python to PWA Compiler
Specifically optimized for SectorIndexv12.py that generates sector_flow.html
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
#  HTML CAPTURER - Specifically for sector_flow.html
# ══════════════════════════════════════════════════════════════════
class HTMLCapturer:
    """Specifically designed to capture sector_flow.html from SectorIndexv12.py"""
    
    @staticmethod
    def capture(file_path, timeout_seconds=120):
        """Run Python and capture sector_flow.html"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return "Error: File not found", False, 1
            
            print(f"  🏃 Running: {file_path.name}")
            
            # Check if sector_flow.html exists before running
            html_file = Path(file_path.parent) / "sector_flow.html"
            if html_file.exists():
                print(f"     📁 Found existing sector_flow.html")
                # Save its modification time
                before_mtime = html_file.stat().st_mtime
            else:
                before_mtime = 0
                print(f"     📁 No existing sector_flow.html")
            
            # Run the Python script
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
            
            # Wait a moment for file writes to complete
            time.sleep(2)
            
            # Check if sector_flow.html was created or updated
            if html_file.exists():
                after_mtime = html_file.stat().st_mtime
                
                # If file is new or updated, read it
                if after_mtime > before_mtime:
                    try:
                        html_content = html_file.read_text(encoding='utf-8')
                        file_size = len(html_content)
                        print(f"     ✅ Captured sector_flow.html ({file_size} bytes)")
                        
                        # Verify it's actual HTML content
                        if '<html' in html_content.lower() or '<!DOCTYPE' in html_content.upper():
                            return html_content, True, result.returncode
                        else:
                            print(f"     ⚠️  File exists but doesn't look like HTML")
                            return html_content, True, result.returncode
                    except Exception as e:
                        print(f"     ⚠️  Error reading file: {e}")
            
            # If we see "saved to sector_flow.html" in output, try one more time
            if 'sector_flow.html' in result.stdout and 'saved' in result.stdout.lower():
                time.sleep(1)  # Give it one more second
                if html_file.exists():
                    html_content = html_file.read_text(encoding='utf-8')
                    print(f"     ✅ Captured sector_flow.html from output reference")
                    return html_content, True, result.returncode
            
            # Check stdout for HTML
            if HTMLCapturer._is_html(result.stdout):
                print(f"     ✅ Captured HTML from stdout")
                return result.stdout, True, result.returncode
            
            # Return stdout as fallback (this is what you're seeing)
            output = result.stdout
            if result.stderr:
                output += f"\n\n--- STDERR ---\n{result.stderr}"
            
            print(f"     ⚠️  No HTML file found, using text output")
            return output, False, result.returncode
            
        except Exception as e:
            return f"Unexpected error: {str(e)}", False, 1
    
    @staticmethod
    def _is_html(text):
        """Quick check if text is HTML."""
        if not text or len(text) < 100:
            return False
        # Look for common HTML patterns
        patterns = ['<html', '<!DOCTYPE', '<head', '<body', '<div', '<script']
        text_lower = text.lower()
        for pattern in patterns:
            if pattern in text_lower:
                return True
        return False


# ══════════════════════════════════════════════════════════════════
#  PWA WRAPPER - FIXED with proper CSS escaping
# ══════════════════════════════════════════════════════════════════
class PWAWrapper:
    """Creates PWA that displays the captured HTML."""
    
    # CSS with ALL curly braces escaped (doubled)
    BASE_CSS = """
/* PyWA - Minimal wrapper */
* {{ 
    margin: 0; 
    padding: 0; 
    box-sizing: border-box; 
}}

:root {{ 
    --primary: {theme_color}; 
}}

/* Small header - shows when not installed */
.app-header {{
    background: var(--primary);
    color: white;
    padding: 8px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-family: sans-serif;
    position: sticky;
    top: 0;
    z-index: 1000;
}}

/* Hide header when installed as PWA */
@media all and (display-mode: standalone) {{
    .app-header {{ display: none; }}
}}

.refresh-btn {{
    background: rgba(255,255,255,0.2);
    border: none;
    color: white;
    padding: 4px 12px;
    border-radius: 16px;
    cursor: pointer;
    font-size: 14px;
}}

.refresh-btn:disabled {{ 
    opacity: 0.5; 
    cursor: not-allowed;
}}

/* Install hint */
.install-hint {{
    background: #f0f0f0;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 8px 12px;
    margin: 8px;
    font-size: 14px;
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
    z-index: 2000;
    font-family: sans-serif;
}}
.loading.show {{ display: block; }}

/* Content area */
#content {{
    width: 100%;
    min-height: calc(100vh - 60px);
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
    <div class="app-header">
        <span>{title}</span>
        <button class="refresh-btn" onclick="refreshData()">↻ Refresh Data</button>
    </div>
    
    <div class="install-hint" id="installHint">
        📱 Tap Chrome menu → "Add to Home screen" to install
    </div>
    
    <div class="loading" id="loading">Updating data...</div>
    
    <div id="content">
        {content}
    </div>

    <script>
        // Show install hint on mobile
        if (/Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) {{
            if (!window.matchMedia('(display-mode: standalone)').matches) {{
                document.getElementById('installHint').classList.add('show');
            }}
        }}
        
        // Refresh function - re-runs Python
        function refreshData() {{
            const loading = document.getElementById('loading');
            const content = document.getElementById('content');
            const btn = document.querySelector('.refresh-btn');
            
            loading.classList.add('show');
            btn.disabled = true;
            
            fetch('/_refresh')
                .then(response => {{
                    if (!response.ok) {{
                        throw new Error('Network error');
                    }}
                    return response.text();
                }})
                .then(html => {{
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
                    content.innerHTML = '<pre style="color:#ff4444; padding:20px;">Error refreshing: ' + error.message + '</pre>';
                    loading.classList.remove('show');
                    btn.disabled = false;
                }});
        }}
        
        // Auto-refresh every 5 minutes when installed
        if (window.matchMedia('(display-mode: standalone)').matches) {{
            setInterval(refreshData, 5 * 60 * 1000);
        }}
        
        // Handle Plotly resize
        window.addEventListener('resize', function() {{
            if (typeof Plotly !== 'undefined') {{
                try {{ Plotly.Plots.resize(); }} catch(e) {{}}
            }}
        }});
        
        console.log('PWA loaded - content length:', document.getElementById('content').innerHTML.length);
    </script>
</body>
</html>"""
    
    @classmethod
    def wrap(cls, content, config, is_html=False):
        """Wrap content in PWA."""
        
        # Format CSS with theme color
        css = cls.BASE_CSS.format(
            theme_color=config.get("theme_color", "#1a1a2e")
        )
        
        # Prepare content
        if is_html and content:
            # If it's a full HTML document, extract body content
            if '<body' in content.lower():
                body_match = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL | re.IGNORECASE)
                if body_match:
                    main_content = body_match.group(1)
                else:
                    main_content = content
            else:
                main_content = content
        else:
            # Escape text output
            escaped = html_module.escape(content or "No output")
            main_content = f'<pre style="background:#1e1e1e;color:#f0f0f0;padding:20px;font-family:monospace;">{escaped}</pre>'
        
        # Generate final HTML
        return cls.HTML_TEMPLATE.format(
            title=config.get('name', 'PyWA App'),
            theme_color=config.get("theme_color", "#1a1a2e"),
            css=css,
            content=main_content
        )


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
  if (e.request.url.includes('/_refresh')) {{
    e.respondWith(fetch(e.request));
    return;
  }}
  e.respondWith(caches.match(e.request).then(cached => cached || fetch(e.request)));
}});
"""


# ══════════════════════════════════════════════════════════════════
#  REFRESH SERVER - Specifically for sector_flow.html
# ══════════════════════════════════════════════════════════════════
class RefreshHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    source_file = None
    
    def do_GET(self):
        if self.path == '/_refresh':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            
            try:
                print(f"\n     🔄 Re-running: {self.source_file}")
                
                # Check sector_flow.html before running
                html_file = Path.cwd() / "sector_flow.html"
                before_mtime = html_file.stat().st_mtime if html_file.exists() else 0
                
                # Run the Python script
                result = subprocess.run(
                    [sys.executable, self.source_file],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=Path(self.source_file).parent
                )
                
                # Wait for file write
                time.sleep(2)
                
                # Check for updated sector_flow.html
                if html_file.exists():
                    after_mtime = html_file.stat().st_mtime
                    if after_mtime > before_mtime:
                        content = html_file.read_text(encoding='utf-8')
                        print(f"     ✅ Updated sector_flow.html")
                        
                        # Extract body if needed
                        if '<body' in content.lower():
                            body_match = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL | re.IGNORECASE)
                            if body_match:
                                content = body_match.group(1)
                    else:
                        # File exists but wasn't updated, use it anyway
                        content = html_file.read_text(encoding='utf-8')
                else:
                    # No HTML file, use stdout
                    content = result.stdout
                    if result.stderr:
                        content += f"\n\n{result.stderr}"
                
                self.wfile.write(content.encode('utf-8'))
                
            except Exception as e:
                self.wfile.write(f"Error: {e}".encode('utf-8'))
        else:
            super().do_GET()
    
    def log_message(self, *args): pass


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
#  SERVER FUNCTIONS
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


def serve_with_refresh(directory, port, source_file):
    os.chdir(directory)
    RefreshHTTPRequestHandler.source_file = source_file
    
    try:
        httpd = socketserver.TCPServer(("0.0.0.0", port), RefreshHTTPRequestHandler)
    except Exception as e:
        print(f"\nFailed to start server: {e}")
        return
    
    # Get local IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "192.168.x.x"
    
    print(f"\n{'='*50}")
    print(f"🌐 PWA Ready!")
    print(f"{'='*50}")
    print(f"\n📱 Local:  http://localhost:{port}")
    print(f"📱 Android: http://{local_ip}:{port}")
    print(f"\n📁 Source: {source_file}")
    print(f"\n👉 Open in Chrome, then menu → 'Add to Home screen'")
    print(f"\nPress Ctrl+C to stop\n")
    
    try:
        webbrowser.open(f"http://localhost:{port}")
    except:
        pass
    
    try:
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
    
    # Build config
    config = {
        "name": args.name or Path(args.file).stem.replace('_', ' ').title(),
        "theme": args.theme,
        "theme_color": args.color,
        "output_dir": args.out,
        "version": datetime.now().strftime("%Y%m%d")
    }
    config = resolve_theme(config)
    
    print("\n" + "="*50)
    print(f"🚀 PyWA - Building {Path(args.file).name}")
    print("="*50)
    
    # Capture HTML output
    content, is_html, _ = HTMLCapturer.capture(Path(args.file))
    print(f"\n📊 Type: {'✅ HTML' if is_html else '⚠️ Text'}")
    
    # Generate PWA
    html = PWAWrapper.wrap(content, config, is_html)
    
    # Write files
    out_dir = Path(config["output_dir"])
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir()
    
    (out_dir / "index.html").write_text(html, encoding='utf-8')
    (out_dir / "manifest.json").write_text(make_manifest(config))
    (out_dir / "sw.js").write_text(make_sw(config["version"]))
    
    for size in [192, 512]:
        (out_dir / f"icon-{size}.png").write_bytes(make_png(size, config["theme_color"]))
    
    print(f"\n✅ PWA saved to: {out_dir}/")
    
    if not args.no_serve:
        serve_with_refresh(out_dir, find_free_port(), args.file)


if __name__ == "__main__":
    main()