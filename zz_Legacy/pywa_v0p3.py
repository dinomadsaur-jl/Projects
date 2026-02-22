#!/usr/bin/env python3
"""
PyWA - Python to PWA Compiler
Compiles ANY Python file to an optimized, installable Progressive Web App.
No modifications needed to your Python code!
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
import textwrap
import inspect
import importlib.util
import traceback
import threading
import http.server
import socketserver
import socket
import subprocess
import webbrowser
from pathlib import Path
from datetime import datetime

# ══════════════════════════════════════════════════════════════════
#  BUILT-IN THEMES
# ══════════════════════════════════════════════════════════════════
THEMES = {
    "light": {
        "theme_color":  "#1a1a2e",
        "accent":       "#e94560",
        "bg_color":     "#ffffff",
        "surface":      "#f5f5f5",
        "border":       "#e0e0e0",
        "text":         "#1a1a1a",
        "text_muted":   "#666666",
        "radius":       "12px",
        "font":         "'Segoe UI', system-ui, sans-serif",
        "shadow":       "0 2px 12px rgba(0,0,0,.08)",
    },
    "dark": {
        "theme_color":  "#7c3aed",
        "accent":       "#06b6d4",
        "bg_color":     "#0d0d0d",
        "surface":      "#1a1a1a",
        "border":       "#2a2a2a",
        "text":         "#f0f0f0",
        "text_muted":   "#888888",
        "radius":       "10px",
        "font":         "'Cascadia Code', 'Fira Code', monospace",
        "shadow":       "0 4px 20px rgba(0,0,0,.4)",
    },
    "glass": {
        "theme_color":  "#6d28d9",
        "accent":       "#f59e0b",
        "bg_color":     "#0f172a",
        "surface":      "rgba(255,255,255,0.08)",
        "border":       "rgba(255,255,255,0.15)",
        "text":         "#f1f5f9",
        "text_muted":   "#94a3b8",
        "radius":       "20px",
        "font":         "'Segoe UI', system-ui, sans-serif",
        "shadow":       "0 8px 32px rgba(0,0,0,.3), inset 0 1px 0 rgba(255,255,255,.1)",
    },
    "nature": {
        "theme_color":  "#2d6a4f",
        "accent":       "#95d5b2",
        "bg_color":     "#f8fffe",
        "surface":      "#edf6f0",
        "border":       "#b7e4c7",
        "text":         "#1b4332",
        "text_muted":   "#52796f",
        "radius":       "16px",
        "font":         "'Georgia', 'Times New Roman', serif",
        "shadow":       "0 2px 16px rgba(45,106,79,.1)",
    },
    "sunset": {
        "theme_color":  "#c0392b",
        "accent":       "#f39c12",
        "bg_color":     "#fffbf7",
        "surface":      "#fff0e6",
        "border":       "#f5c6a0",
        "text":         "#2c1810",
        "text_muted":   "#8b5a3c",
        "radius":       "14px",
        "font":         "'Segoe UI', system-ui, sans-serif",
        "shadow":       "0 2px 16px rgba(192,57,43,.12)",
    },
    "ocean": {
        "theme_color":  "#0369a1",
        "accent":       "#0891b2",
        "bg_color":     "#f0f9ff",
        "surface":      "#e0f2fe",
        "border":       "#bae6fd",
        "text":         "#0c1a2e",
        "text_muted":   "#0369a1",
        "radius":       "8px",
        "font":         "'Segoe UI', system-ui, sans-serif",
        "shadow":       "0 2px 12px rgba(3,105,161,.1)",
    },
    "custom": None,
}

# ══════════════════════════════════════════════════════════════════
#  DEFAULTS
# ══════════════════════════════════════════════════════════════════
DEFAULTS = {
    "name":        None,
    "short_name":  None,
    "theme":       "light",
    "output_dir":  "pwa_output",
    "version":     "1.0.0",
    "theme_color": "#1a1a2e",
    "accent":      "#e94560",
    "bg_color":    "#ffffff",
    "surface":     "#f5f5f5",
    "border":      "#e0e0e0",
    "text":        "#1a1a1a",
    "text_muted":  "#666666",
    "radius":      "12px",
    "font":        "'Segoe UI', system-ui, sans-serif",
    "shadow":      "0 2px 12px rgba(0,0,0,.08)",
}

# ══════════════════════════════════════════════════════════════════
#  THEME RESOLVER
# ══════════════════════════════════════════════════════════════════
def resolve_theme(config: dict) -> dict:
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
        (r'<marquee',       "❌ <marquee> is deprecated",        lambda h: h.replace('<marquee', '<div class="pywa-marquee"')),
        (r'<blink',         "❌ <blink> is deprecated",          lambda h: re.sub(r'<blink[^>]*>(.*?)</blink>', r'<span>\1</span>', h, flags=re.S)),
        (r'<font ',         "❌ <font> tag is deprecated",       lambda h: re.sub(r'<font[^>]*>(.*?)</font>', r'<span>\1</span>', h, flags=re.S)),
        (r'<center>',       "❌ <center> is deprecated",         lambda h: h.replace('<center>', '<div style="text-align:center">').replace('</center>', '</div>')),
        (r'target=["\']_blank["\'](?!.*rel=)', "⚠️ _blank without rel=noopener",
            lambda h: re.sub(r'(target=["\']_blank["\'])(?!.*?rel=)', r'\1 rel="noopener noreferrer"', h)),
        (r'<img(?!.*?alt=)', "⚠️ <img> missing alt attribute",  lambda h: re.sub(r'(<img)(?![^>]*alt=)', r'\1 alt=""', h)),
        (r'style="[^"]*color:\s*#[0-9a-fA-F]{3,6}[^"]*"', "ℹ️ Inline color found — prefer CSS variables", None),
        (r'onclick=["\'][^"\']*eval\(', "🚨 eval() in onclick — security risk", None),
        (r'document\.write\(', "❌ document.write() breaks modern parsers", None),
        (r'var\s+', "ℹ️ var used — prefer const/let for modern JS", None),
        (r'<table(?!.*role=)', "⚠️ Layout table — add role='presentation' if not data",
            lambda h: re.sub(r'<table(?![^>]*role=)', '<table role="presentation"', h)),
        (r'autofocus', "⚠️ autofocus can harm accessibility on mobile", None),
        (r'user-scalable=no', "❌ user-scalable=no breaks accessibility",
            lambda h: h.replace('user-scalable=no', 'user-scalable=yes')),
        (r'user-scalable=0',  "❌ user-scalable=0 breaks accessibility",
            lambda h: h.replace('user-scalable=0', 'user-scalable=yes')),
    ]

    def check(self, html):
        issues  = []
        fixes   = []
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
#  RESPONSIVE OPTIMIZER
# ══════════════════════════════════════════════════════════════════
class ResponsiveOptimizer:
    BASE_CSS = """
/* ── PyWA Reset & Base ──────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --color-bg:         {bg_color};
  --color-primary:    {theme_color};
  --color-accent:     {accent};
  --color-text:       {text};
  --color-text-muted: {text_muted};
  --color-surface:    {surface};
  --color-border:     {border};

  --radius-sm:      6px;
  --radius-md:      {radius};
  --radius-lg:      20px;
  --shadow-sm:      {shadow};
  --shadow-md:      0 4px 16px rgba(0,0,0,.15);
  --shadow-lg:      0 8px 32px rgba(0,0,0,.2);

  --font-sans:      {font};
  --font-mono:      'Cascadia Code', 'Fira Code', monospace;

  --space-xs:       4px;
  --space-sm:       8px;
  --space-md:       16px;
  --space-lg:       32px;
  --space-xl:       64px;
  --transition:     0.2s ease;
}

html { font-size: 16px; scroll-behavior: smooth; }

body {
  font-family: var(--font-sans);
  background: var(--color-bg);
  color: var(--color-text);
  line-height: 1.6;
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}

h1 { font-size: clamp(1.8rem, 5vw, 3rem); font-weight: 800; }
h2 { font-size: clamp(1.4rem, 3.5vw, 2rem); font-weight: 700; }
h3 { font-size: clamp(1.1rem, 2.5vw, 1.5rem); font-weight: 600; }
p { font-size: clamp(0.95rem, 2vw, 1.05rem); color: var(--color-text-muted); }

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

@media (max-width: 640px) {
  .pywa-navbar { padding: var(--space-sm) var(--space-md); }
  .pywa-navbar-links { gap: var(--space-sm); }
}

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

.pywa-page { display: none; animation: pywa-fadein .25s ease; }
.pywa-page.active { display: block; }

@keyframes pywa-fadein {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

.pywa-hero {
  background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
  color: #fff;
  padding: var(--space-xl) var(--space-lg);
  text-align: center;
}
.pywa-hero-title { color: #fff; margin-bottom: var(--space-sm); }
.pywa-hero-sub { color: rgba(255,255,255,.85); }

.pywa-card {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  box-shadow: var(--shadow-sm);
  transition: box-shadow var(--transition), transform var(--transition);
}
.pywa-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }

.pywa-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  padding: .65em 1.4em;
  border-radius: var(--radius-sm);
  border: none;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition);
  min-height: 44px;
}
.pywa-btn-primary {
  background: var(--color-primary);
  color: #fff;
}
.pywa-btn-primary:hover { filter: brightness(1.15); }
.pywa-btn-accent { background: var(--color-accent); color: #fff; }
.pywa-btn-outline {
  background: transparent;
  color: var(--color-primary);
  border: 2px solid var(--color-primary);
}
.pywa-btn-ghost { background: transparent; color: var(--color-text); }

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
.pywa-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-primary) 20%, transparent);
}

.pywa-grid { display: grid; gap: var(--space-md); }
.pywa-grid-1 { grid-template-columns: 1fr; }
.pywa-grid-2 { grid-template-columns: repeat(2, 1fr); }
.pywa-grid-3 { grid-template-columns: repeat(3, 1fr); }
.pywa-grid-4 { grid-template-columns: repeat(4, 1fr); }

@media (max-width: 768px) {
  .pywa-grid-3, .pywa-grid-4 { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 480px) {
  .pywa-grid-2, .pywa-grid-3, .pywa-grid-4 { grid-template-columns: 1fr; }
}

.pywa-row { display: flex; gap: var(--space-md); flex-wrap: wrap; }
.pywa-col { display: flex; flex-direction: column; gap: var(--space-sm); flex: 1; }

.pywa-badge {
  display: inline-block;
  padding: .2em .7em;
  border-radius: 999px;
  font-size: .75rem;
  font-weight: 700;
  text-transform: uppercase;
}
.pywa-badge-accent { background: var(--color-accent); color: #fff; }
.pywa-badge-primary { background: var(--color-primary); color: #fff; }

.pywa-divider { border: none; border-top: 1px solid var(--color-border); margin: var(--space-md) 0; }
.pywa-spacer-md { height: var(--space-md); }
.pywa-img { max-width: 100%; height: auto; border-radius: var(--radius-sm); }
.pywa-list { padding-left: 1.5em; color: var(--color-text-muted); }

.pywa-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-lg);
}

.pywa-footer {
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
  padding: var(--space-lg);
  text-align: center;
  color: var(--color-text-muted);
}

.pywa-marquee {
  overflow: hidden; white-space: nowrap;
  animation: pywa-scroll 10s linear infinite;
}
@keyframes pywa-scroll {
  from { transform: translateX(100%); }
  to   { transform: translateX(-100%); }
}

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
  animation: pywa-fadein .3s ease;
  max-width: calc(100vw - 2 * var(--space-lg));
  flex-wrap: wrap;
  justify-content: center;
}
#pywa-install-banner.show { display: flex; }
#pywa-install-banner button {
  background: rgba(255,255,255,.2);
  border: none; color: #fff;
  padding: .4em 1em; border-radius: var(--radius-sm);
  cursor: pointer;
}
"""

def optimize(self, html, config):
    """Inject responsive meta tags and base CSS."""
    
    viewport = '<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />'
    mobile_capable = '<meta name="mobile-web-app-capable" content="yes" />'
    apple_capable  = '<meta name="apple-mobile-web-app-capable" content="yes" />'
    apple_title    = f'<meta name="apple-mobile-web-app-title" content="{config["name"]}" />'
    apple_status   = '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />'
    description    = f'<meta name="description" content="{config["name"]} — built with PyWA" />'
    og_title       = f'<meta property="og:title" content="{config["name"]}" />'
    og_type        = '<meta property="og:type" content="website" />'
    charset        = '<meta charset="UTF-8" />'

    # Get theme values
    _t = config
    
    # FIX: Use simple string replacement instead of .format()
    # Copy the BASE_CSS and replace placeholders one by one
    base_css = self.BASE_CSS
    
    # Replace all placeholders with actual values
    base_css = base_css.replace('{bg_color}', _t.get("bg_color", "#ffffff"))
    base_css = base_css.replace('{theme_color}', _t.get("theme_color", "#1a1a2e"))
    base_css = base_css.replace('{accent}', _t.get("accent", "#e94560"))
    base_css = base_css.replace('{surface}', _t.get("surface", "#f5f5f5"))
    base_css = base_css.replace('{border}', _t.get("border", "#e0e0e0"))
    base_css = base_css.replace('{text}', _t.get("text", "#1a1a1a"))
    base_css = base_css.replace('{text_muted}', _t.get("text_muted", "#666666"))
    base_css = base_css.replace('{radius}', _t.get("radius", "12px"))
    base_css = base_css.replace('{font}', _t.get("font", "'Segoe UI', system-ui, sans-serif"))
    base_css = base_css.replace('{shadow}', _t.get("shadow", "0 2px 12px rgba(0,0,0,.08)"))

    head_inject = f"""
  {charset}
  {viewport}
  {mobile_capable}
  {apple_capable}
  {apple_title}
  {apple_status}
  {description}
  {og_title}
  {og_type}
  <style id="pywa-base">{base_css}</style>"""

    if "<head>" in html:
        html = html.replace("<head>", f"<head>{head_inject}", 1)
    else:
        html = f"<head>{head_inject}</head>" + html

    # Inject theme class onto <body>
    theme_name = config.get("theme", "light")
    auto_dark_class = "pywa-auto-dark" if theme_name in ("light","nature","ocean","sunset") else ""
    body_class = f"pywa-theme-{theme_name} {auto_dark_class}".strip()
    
    if "<body>" in html:
        html = html.replace("<body>", f'<body class="{body_class}">', 1)
    elif "<body " in html:
        html = re.sub(r'<body ([^>]*)>', lambda m: f'<body class="{body_class}" {m.group(1)}>', html, count=1)

    return html

# ══════════════════════════════════════════════════════════════════
#  HTML GENERATOR
# ══════════════════════════════════════════════════════════════════
class HTMLGenerator:
    def generate(self, app_instance, config):
        pages_html = ""
        tab_btns = ""
        desktop_links = ""

        nav_items = getattr(app_instance, '_nav_items', [])
        pages = getattr(app_instance, '_pages', {})

        if not pages:
            pages = {'home': {'fn': lambda self: '<p>No content</p>', 'title': 'Home'}}

        first_page = list(pages.keys())[0]

        # Auto-generate navigation if none provided
        if not nav_items:
            icons = ["⌂", "★", "✉", "☰", "♥", "⚙"]
            for i, (name, meta) in enumerate(pages.items()):
                nav_items.append({
                    "label": meta.get('title', name.title()),
                    "page": name,
                    "icon": icons[i % len(icons)],
                })

        for item in nav_items:
            active = 'active' if item["page"] == first_page else ''
            tab_btns += f'''
      <button class="pywa-tab-btn {active}" onclick="pywaNavigate('{item["page"]}')" id="tab-{item["page"]}">
        <span class="tab-icon">{item["icon"]}</span>
        <span>{item["label"]}</span>
      </button>'''
            desktop_links += f'<a href="#" onclick="pywaNavigate(\'{item["page"]}\');return false;">{item["label"]}</a>'

        for name, meta in pages.items():
            active = 'active' if name == first_page else ''
            content_fn = meta.get('fn', lambda self: '')
            content = content_fn(app_instance) or ''
            pages_html += f'''
    <div class="pywa-page {active}" id="page-{name}">
      <main class="pywa-main">
        {content}
      </main>
    </div>'''

        extra_css = "\n".join(getattr(app_instance, '_styles', []))
        extra_js = "\n".join(getattr(app_instance, '_scripts', []))

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <title>{config.get('name', 'PyWA App')}</title>
  <link rel="manifest" href="manifest.json" />
  <meta name="theme-color" content="{config.get('theme_color', '#1a1a2e')}" />
  <link rel="apple-touch-icon" href="icon-192.png" />
  {f'<style>{extra_css}</style>' if extra_css else ''}
</head>
<body>

  <nav class="pywa-navbar">
    <span class="pywa-navbar-title">{config.get('name', 'PyWA App')}</span>
    <div class="pywa-navbar-links">{desktop_links}</div>
  </nav>

  {pages_html}

  <div class="pywa-tab-nav">
    <div class="pywa-tab-nav-inner">
      {tab_btns}
    </div>
  </div>

  <div id="pywa-install-banner">
    📱 Install this app
    <button onclick="pywaInstall()">Install</button>
    <button onclick="document.getElementById('pywa-install-banner').classList.remove('show')">✕</button>
  </div>

  <script>
    function pywaNavigate(page) {{
      document.querySelectorAll('.pywa-page').forEach(p => p.classList.remove('active'));
      document.querySelectorAll('.pywa-tab-btn').forEach(b => b.classList.remove('active'));
      const pg = document.getElementById('page-' + page);
      const tb = document.getElementById('tab-' + page);
      if (pg) pg.classList.add('active');
      if (tb) tb.classList.add('active');
      window.history.pushState({{page}}, '', '#' + page);
    }}

    window.addEventListener('popstate', e => {{
      if (e.state && e.state.page) pywaNavigate(e.state.page);
    }});

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

    if ('serviceWorker' in navigator) {{
      navigator.serviceWorker.register('sw.js')
        .then(() => console.log('[PyWA] Service worker ready'))
        .catch(e => console.warn('[PyWA] SW error', e));
    }}

    window.addEventListener('load', () => {{
      const hash = window.location.hash.replace('#', '');
      if (hash) pywaNavigate(hash);
    }});

    {extra_js}
  </script>
</body>
</html>"""
        return html


# ══════════════════════════════════════════════════════════════════
#  ASSET GENERATORS
# ══════════════════════════════════════════════════════════════════
def make_png(size, hex_color):
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
#  PYTHON ANALYZER - Extracts info from ANY Python file
# ══════════════════════════════════════════════════════════════════
class PythonAnalyzer:
    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.source = self.file_path.read_text(encoding='utf-8')
        self.tree = ast.parse(self.source)
        self.functions = []
        self.classes = []
        self.variables = {}
        self.docstring = None
        self.has_input = False
        self.has_loops = False
        
    def analyze(self):
        self.docstring = ast.get_docstring(self.tree)
        
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                self.functions.append({
                    'name': node.name,
                    'args': [arg.arg for arg in node.args.args],
                    'docstring': ast.get_docstring(node),
                    'line': node.lineno
                })
            
            elif isinstance(node, ast.ClassDef):
                methods = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        methods.append(item.name)
                self.classes.append({
                    'name': node.name,
                    'methods': methods,
                    'docstring': ast.get_docstring(node)
                })
            
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if isinstance(node.value, ast.Str):
                            self.variables[target.id] = f'"{node.value.s}"'
                        elif isinstance(node.value, ast.Num):
                            self.variables[target.id] = str(node.value.n)
                        elif isinstance(node.value, ast.List):
                            self.variables[target.id] = f'[{len(node.value.elts)} items]'
            
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'input':
                    self.has_input = True
            
            elif isinstance(node, (ast.For, ast.While)):
                self.has_loops = True
        
        return self
    
    def guess_app_type(self):
        if self.classes:
            return "Object-oriented"
        elif len(self.functions) > 5:
            return "Multi-function"
        elif self.has_input:
            return "Interactive"
        else:
            return "Simple"
    
    def get_main_function(self):
        main_names = ['main', 'run', 'start', 'app']
        for func in self.functions:
            if func['name'].lower() in main_names:
                return func
        return self.functions[0] if self.functions else None
    
    def generate_description(self):
        parts = []
        if self.docstring:
            parts.append(self.docstring.split('\n')[0])
        if self.functions:
            parts.append(f"{len(self.functions)} functions")
        if self.classes:
            parts.append(f"{len(self.classes)} classes")
        if self.variables:
            parts.append(f"{len(self.variables)} variables")
        return " • ".join(parts) if parts else "Python application"


# ══════════════════════════════════════════════════════════════════
#  AUTO UI GENERATOR
# ══════════════════════════════════════════════════════════════════
class AutoUIGenerator:
    def __init__(self, analyzer):
        self.analyzer = analyzer
        self.app_name = analyzer.file_path.stem.replace('_', ' ').replace('-', ' ').title()
        
    def generate_home_page(self):
        content = []
        
        content.append(f"""
        <div class="pywa-hero">
            <h1>{self.app_name}</h1>
            <p>{self.analyzer.generate_description()}</p>
        </div>
        """)
        
        content.append('<div class="pywa-grid pywa-grid-2">')
        
        if self.analyzer.functions:
            func_list = ''.join([
                f'<li><code>{f["name"]}({", ".join(f["args"])})</code></li>'
                for f in self.analyzer.functions[:8]
            ])
            content.append(f"""
            <div class="pywa-card">
                <h3>📋 Functions</h3>
                <ul class="pywa-list">
                    {func_list}
                </ul>
                {f'<p>... and {len(self.analyzer.functions)-8} more</p>' if len(self.analyzer.functions) > 8 else ''}
                <button class="pywa-btn pywa-btn-outline" style="margin-top:10px;" 
                        onclick="pywaNavigate('functions')">View All →</button>
            </div>
            """)
        
        if self.analyzer.classes:
            class_list = ''.join([
                f'<li><code>{c["name"]}</code> ({len(c["methods"])} methods)</li>'
                for c in self.analyzer.classes[:5]
            ])
            content.append(f"""
            <div class="pywa-card">
                <h3>📚 Classes</h3>
                <ul class="pywa-list">
                    {class_list}
                </ul>
            </div>
            """)
        
        if self.analyzer.variables:
            var_list = ''.join([
                f'<li><code>{k} = {v}</code></li>'
                for k, v in list(self.analyzer.variables.items())[:8]
            ])
            content.append(f"""
            <div class="pywa-card">
                <h3>🔧 Variables</h3>
                <ul class="pywa-list">
                    {var_list}
                </ul>
            </div>
            """)
        
        content.append('</div>')
        
        content.append(f"""
        <div class="pywa-card">
            <h3>📄 Source Code Preview</h3>
            <pre style="background: var(--color-surface); padding: 15px; border-radius: var(--radius-sm); 
                       overflow-x: auto; max-height: 400px; font-family: monospace; font-size: 0.85rem;">
{self._get_code_preview()}
            </pre>
        </div>
        """)
        
        return '\n'.join(content)
    
    def generate_functions_page(self):
        if not self.analyzer.functions:
            return "<p>No functions found</p>"
        
        content = ['<h2>All Functions</h2>', '<div class="pywa-grid pywa-grid-2">']
        
        for func in self.analyzer.functions:
            args_html = ', '.join(func['args']) if func['args'] else 'none'
            content.append(f"""
            <div class="pywa-card">
                <h3>{func['name']}</h3>
                <p><strong>Parameters:</strong> <code>{args_html}</code></p>
                <p><strong>Line:</strong> {func['line']}</p>
                {f'<p><em>{func["docstring"]}</em></p>' if func['docstring'] else ''}
                <button class="pywa-btn pywa-btn-outline" 
                        onclick="alert('Function {func["name"]} would execute here')">
                    Run ▶
                </button>
            </div>
            """)
        
        content.append('</div>')
        return '\n'.join(content)
    
    def generate_interactive_page(self):
        if not self.analyzer.has_input:
            return None
        
        return """
        <div class="pywa-card">
            <h2>Interactive Console</h2>
            <p>This app uses input(). Try it below:</p>
            
            <div style="background: var(--color-surface); padding: 20px; border-radius: var(--radius-sm); 
                        font-family: monospace; margin: 20px 0; height: 200px; overflow-y: auto;" 
                 id="console">
                <div style="color: var(--color-text-muted);">Python Interactive Console</div>
                <div style="color: var(--color-accent);">>>> </div>
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
            
            if (input.toLowerCase() === 'clear') {
                console.innerHTML = '<div style="color: var(--color-text-muted);">Python Interactive Console</div><div style="color: var(--color-accent);">>>> </div>';
                document.getElementById('input').value = '';
                return;
            }
            
            // Remove the last prompt
            let html = console.innerHTML;
            html = html.replace('<div style="color: var(--color-accent);">>>> </div>', '');
            
            // Add input
            html += '<div>> ' + input + '</div>';
            
            // Add simulated output
            if (input.startsWith('print(')) {
                const match = input.match(/\\(['"](.*)['"]\\)/);
                if (match) {
                    html += '<div style="color: var(--color-accent);">' + match[1] + '</div>';
                }
            } else if (input.match(/^[0-9+\\-*/()]+$/)) {
                try {
                    const result = eval(input);
                    html += '<div style="color: var(--color-accent);">' + result + '</div>';
                } catch(e) {
                    html += '<div style="color: #ff4444;">Error: Invalid expression</div>';
                }
            } else if (input === 'help') {
                html += '<div style="color: var(--color-accent);">Available: print(), math, clear</div>';
            } else {
                html += '<div style="color: var(--color-accent);">You typed: ' + input + '</div>';
            }
            
            // Add new prompt
            html += '<div style="color: var(--color-accent);">>>> </div>';
            
            console.innerHTML = html;
            document.getElementById('input').value = '';
            console.scrollTop = console.scrollHeight;
        }
        
        document.getElementById('input').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                runPython();
            }
        });
        </script>
        """
    
    def generate_source_page(self):
        return f"""
        <div class="pywa-card">
            <h2>Source Code</h2>
            <p>File: {self.analyzer.file_path.name}</p>
            <pre style="background: var(--color-surface); padding: 15px; border-radius: var(--radius-sm); 
                       overflow-x: auto; max-height: 600px; font-family: monospace; font-size: 0.85rem;">
{self.analyzer.source}
            </pre>
        </div>
        """
    
    def generate_about_page(self):
        return f"""
        <div class="pywa-card">
            <h2>About</h2>
            <p><strong>File:</strong> {self.analyzer.file_path.name}</p>
            <p><strong>Size:</strong> {self.analyzer.file_path.stat().st_size:,} bytes</p>
            <p><strong>Lines:</strong> {len(self.analyzer.source.split('\\n'))}</p>
            <p><strong>Functions:</strong> {len(self.analyzer.functions)}</p>
            <p><strong>Classes:</strong> {len(self.analyzer.classes)}</p>
            <p><strong>Variables:</strong> {len(self.analyzer.variables)}</p>
            <p><strong>App type:</strong> {self.analyzer.guess_app_type()}</p>
            <hr class="pywa-divider">
            <p>Generated with PyWA Compiler</p>
        </div>
        """
    
    def _get_code_preview(self):
        lines = self.analyzer.source.split('\n')
        preview_lines = lines[:30]
        if len(lines) > 30:
            preview_lines.append('# ... (truncated)')
        return '\n'.join(preview_lines)
    
    def generate_pages(self):
        pages = {}
        
        pages['home'] = {
            'title': 'Home',
            'content': self.generate_home_page()
        }
        
        if self.analyzer.functions:
            pages['functions'] = {
                'title': 'Functions',
                'content': self.generate_functions_page()
            }
        
        interactive = self.generate_interactive_page()
        if interactive:
            pages['interactive'] = {
                'title': 'Console',
                'content': interactive
            }
        
        pages['source'] = {
            'title': 'Source',
            'content': self.generate_source_page()
        }
        
        pages['about'] = {
            'title': 'About',
            'content': self.generate_about_page()
        }
        
        return pages
    
    def generate_navigation(self):
        nav = [{'label': 'Home', 'page': 'home', 'icon': '🏠'}]
        
        if self.analyzer.functions:
            nav.append({'label': 'Functions', 'page': 'functions', 'icon': '📋'})
        
        if self.analyzer.has_input:
            nav.append({'label': 'Console', 'page': 'interactive', 'icon': '🎮'})
        
        nav.append({'label': 'Source', 'page': 'source', 'icon': '📄'})
        nav.append({'label': 'About', 'page': 'about', 'icon': 'ℹ️'})
        
        return nav


# ══════════════════════════════════════════════════════════════════
#  FILE PICKER
# ══════════════════════════════════════════════════════════════════
def _pick_from_list(files):
    if not files:
        return None
    
    print("\n  📁 Found Python files:\n")
    
    for i, f in enumerate(files, 1):
        try:
            display = f.relative_to(Path.cwd())
        except ValueError:
            display = f
        print(f"    [{i}] {display}")
    
    print("\n    [0] Cancel")
    
    while True:
        try:
            choice = input("\n  Select file number: ").strip()
            
            if choice == "0":
                return None
            
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(files):
                    return files[idx]
                else:
                    print(f"  Please enter a number between 1 and {len(files)}")
            except ValueError:
                print("  Please enter a valid number")
                
        except (EOFError, KeyboardInterrupt):
            print("\n")
            return None


def pick_py_file():
    base = Path.cwd()
    
    print(f"\n  🔍 Searching for Python files in: {base}")
    
    skip_dirs = {"__pycache__", ".git", ".venv", "venv", "env", "node_modules"}
    
    found = []
    for f in base.glob("*.py"):
        if f.name != "pywa.py" and f.name != "pywa_v0p2.py":
            found.append(f)
    
    if not found:
        print(f"\n  ❌ No Python files found in current directory")
        return None
    
    return _pick_from_list(found)


# ══════════════════════════════════════════════════════════════════
#  PYWA COMPILER
# ══════════════════════════════════════════════════════════════════
class PyWACompiler:
    def __init__(self, config=None):
        self.config = {**DEFAULTS, **(config or {})}
        self.checker = CompatibilityChecker()
        self.optimizer = ResponsiveOptimizer()
        self.generator = HTMLGenerator()
    
    def _banner(self):
        print("""
╔═══════════════════════════════════════╗
║   PyWA — Universal Python → PWA       ║
║   Works with ANY Python file!         ║
╚═══════════════════════════════════════╝""")
    
    def compile(self, source_file):
        self._banner()
        src = Path(source_file)
        print(f"\n  📄 Source : {src}")
        print(f"  📦 Output : {self.config['output_dir']}/\n")
        
        print("  [1/5] Analyzing Python code...")
        analyzer = PythonAnalyzer(src).analyze()
        print(f"     ✅ Found {len(analyzer.functions)} functions, {len(analyzer.classes)} classes")
        
        print("  [2/5] Generating UI...")
        ui_gen = AutoUIGenerator(analyzer)
        pages = ui_gen.generate_pages()
        nav_items = ui_gen.generate_navigation()
        
        print("  [3/5] Building app...")
        
        class GeneratedApp:
            def __init__(self):
                self._pages = {}
                self._nav_items = nav_items
                self._styles = []
                self._scripts = []
        
        app = GeneratedApp()
        
        for page_id, page_data in pages.items():
            def make_content_func(content):
                return lambda self: content
            app._pages[page_id] = {
                'fn': make_content_func(page_data['content']),
                'title': page_data['title']
            }
        
        if not self.config.get('name'):
            self.config['name'] = ui_gen.app_name
        
        if not self.config.get('short_name'):
            words = self.config['name'].split()
            self.config['short_name'] = ''.join(w[0] for w in words[:3])[:8]
        
        self.config = resolve_theme(self.config)
        
        print("  [4/5] Generating HTML...")
        html = self.generator.generate(app, self.config)
        html = self.optimizer.optimize(html, self.config)
        
        print("  [5/5] Writing files...")
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
        
        (out / "source.py").write_text(analyzer.source, encoding="utf-8")
        
        total = sum(f.stat().st_size for f in out.iterdir())
        print(f"\n  ✅ Compiled! {total:,} bytes → ./{self.config['output_dir']}/")
        
        return out


# ══════════════════════════════════════════════════════════════════
#  SERVER FUNCTIONS
# ══════════════════════════════════════════════════════════════════
def find_free_port(start=8080):
    for port in range(start, start + 20):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", port))
                return port
        except OSError:
            continue
    return start


def start_server(directory, port):
    abs_dir = str(Path(directory).resolve())
    os.chdir(abs_dir)
    
    handler = http.server.SimpleHTTPRequestHandler
    httpd = socketserver.TCPServer(("", port), handler)
    
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def open_browser(url):
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
#  MAIN CLI
# ══════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        prog="pywa",
        description="PyWA — Compile ANY Python file to a PWA"
    )
    
    parser.add_argument("file", nargs="?", help="Python file to compile")
    parser.add_argument("--name", help="App name")
    parser.add_argument("--theme", help="Theme: light|dark|glass|nature|sunset|ocean|custom", default="light")
    parser.add_argument("--color", help="Primary color (hex)")
    parser.add_argument("--accent", help="Accent color (hex)")
    parser.add_argument("--out", help="Output directory", default="pwa_output")
    parser.add_argument("--serve", action="store_true", help="Start web server")
    parser.add_argument("--port", type=int, default=0, help="Port for web server")
    
    args = parser.parse_args()
    
    # Show help if no args
    if not args.file and len(sys.argv) == 1:
        parser.print_help()
        print("\n" + "="*50)
        print("No file specified. Launching file picker...")
        print("="*50)
        
        file_path = pick_py_file()
        if not file_path:
            print("\n  ❌ No file selected. Exiting.")
            return
        args.file = str(file_path)
    
    # If still no file, exit
    if not args.file:
        print("\n  ❌ No file specified. Use: python pywa.py yourfile.py")
        return
    
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
        
        print(f"\n  🌐 Starting server at {url}")
        httpd = start_server(out_dir, port)
        
        open_browser(url)
        
        print("  Press Ctrl+C to stop\n")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n  Server stopped.")
            httpd.shutdown()


if __name__ == "__main__":
    main()