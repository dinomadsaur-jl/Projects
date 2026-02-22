#!/usr/bin/env python3
"""
PyWA - Python to PWA Compiler
Compiles Python UI code into optimized, installable Progressive Web Apps.
Handles mobile/desktop responsiveness and cross-browser compatibility.

Usage:
    python pywa.py build myapp.py
    python pywa.py build myapp.py --name "My App" --color "#6200ea"
    python pywa.py serve
    python pywa.py watch myapp.py
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
from pathlib import Path
from datetime import datetime


# ══════════════════════════════════════════════════════════════════
#  BUILT-IN THEMES
#  Each theme sets: theme_color, accent, bg_color, surface, border,
#  text, text_muted, radius, font, shadow_style
#  "custom" means: use whatever is in pywa.json or CLI flags.
# ══════════════════════════════════════════════════════════════════
THEMES = {

    # ── Light ─────────────────────────────────────────────────────
    # Clean white background, deep navy primary, coral accent.
    # Best for: general apps, productivity, professional tools.
    "light": {
        "theme_color":  "#1a1a2e",   # navbar / primary UI colour
        "accent":       "#e94560",   # buttons, highlights, active states
        "bg_color":     "#ffffff",   # page background
        "surface":      "#f5f5f5",   # cards, inputs, secondary surfaces
        "border":       "#e0e0e0",   # dividers, input borders
        "text":         "#1a1a1a",   # body text
        "text_muted":   "#666666",   # secondary / helper text
        "radius":       "12px",      # card border-radius
        "font":         "'Segoe UI', system-ui, sans-serif",
        "shadow":       "0 2px 12px rgba(0,0,0,.08)",
    },

    # ── Dark ──────────────────────────────────────────────────────
    # True dark background, electric violet primary, neon cyan accent.
    # Best for: developer tools, media apps, night-friendly UIs.
    "dark": {
        "theme_color":  "#7c3aed",   # rich violet primary
        "accent":       "#06b6d4",   # cyan highlight
        "bg_color":     "#0d0d0d",   # near-black background
        "surface":      "#1a1a1a",   # card / input background
        "border":       "#2a2a2a",   # subtle dividers
        "text":         "#f0f0f0",   # primary text (off-white, easier on eyes)
        "text_muted":   "#888888",   # muted / secondary text
        "radius":       "10px",
        "font":         "'Cascadia Code', 'Fira Code', monospace",
        "shadow":       "0 4px 20px rgba(0,0,0,.4)",
    },

    # ── Glass ─────────────────────────────────────────────────────
    # Frosted-glass cards over a vivid gradient background.
    # Best for: portfolios, landing pages, lifestyle apps.
    "glass": {
        "theme_color":  "#6d28d9",   # deep purple navbar
        "accent":       "#f59e0b",   # amber glow accent
        "bg_color":     "#0f172a",   # dark navy behind the glass
        "surface":      "rgba(255,255,255,0.08)",  # translucent card fill
        "border":       "rgba(255,255,255,0.15)",  # glass edge highlight
        "text":         "#f1f5f9",   # light text on dark bg
        "text_muted":   "#94a3b8",
        "radius":       "20px",      # rounder for soft glass look
        "font":         "'Segoe UI', system-ui, sans-serif",
        "shadow":       "0 8px 32px rgba(0,0,0,.3), inset 0 1px 0 rgba(255,255,255,.1)",
    },

    # ── Nature ────────────────────────────────────────────────────
    # Forest greens, warm earth tones, organic feel.
    # Best for: health, fitness, outdoor, eco apps.
    "nature": {
        "theme_color":  "#2d6a4f",   # deep forest green
        "accent":       "#95d5b2",   # soft mint highlight
        "bg_color":     "#f8fffe",   # near-white with a hint of green
        "surface":      "#edf6f0",   # very light sage
        "border":       "#b7e4c7",   # light green dividers
        "text":         "#1b4332",   # dark green text
        "text_muted":   "#52796f",   # muted teal
        "radius":       "16px",      # organic roundness
        "font":         "'Georgia', 'Times New Roman', serif",
        "shadow":       "0 2px 16px rgba(45,106,79,.1)",
    },

    # ── Sunset ────────────────────────────────────────────────────
    # Warm gradients, coral + orange palette, energetic feel.
    # Best for: social apps, food, entertainment, creative tools.
    "sunset": {
        "theme_color":  "#c0392b",   # deep red / coral navbar
        "accent":       "#f39c12",   # warm amber/gold accent
        "bg_color":     "#fffbf7",   # warm off-white
        "surface":      "#fff0e6",   # warm cream surface
        "border":       "#f5c6a0",   # soft peach border
        "text":         "#2c1810",   # dark warm brown text
        "text_muted":   "#8b5a3c",
        "radius":       "14px",
        "font":         "'Segoe UI', system-ui, sans-serif",
        "shadow":       "0 2px 16px rgba(192,57,43,.12)",
    },

    # ── Ocean ─────────────────────────────────────────────────────
    # Deep blues and teals, cool and calm.
    # Best for: finance, analytics, data dashboards, utility apps.
    "ocean": {
        "theme_color":  "#0369a1",   # strong ocean blue
        "accent":       "#0891b2",   # teal accent
        "bg_color":     "#f0f9ff",   # very light sky blue
        "surface":      "#e0f2fe",   # light blue surface
        "border":       "#bae6fd",   # pale blue border
        "text":         "#0c1a2e",   # deep navy text
        "text_muted":   "#0369a1",
        "radius":       "8px",       # crisper / more utilitarian
        "font":         "'Segoe UI', system-ui, sans-serif",
        "shadow":       "0 2px 12px rgba(3,105,161,.1)",
    },

    # ── Custom ────────────────────────────────────────────────────
    # Uses your own values from pywa.json or CLI --color / --accent.
    # Set "theme": "custom" in pywa.json and supply all colour fields.
    "custom": None,  # signals: do not apply a preset, use raw config values
}

# ── Defaults applied when theme = "light" or nothing specified ────
DEFAULTS = {
    "name":        None,          # None = derive from filename at build time
    "short_name":  None,          # None = derive from name
    "theme":       "light",       # which THEMES entry to use
    "output_dir":  "pwa_output",  # folder where compiled files are written
    "version":     "1.0.0",       # shown in manifest.json and SW cache key
    # ── only used when theme = "custom" ──────────────────────────
    "theme_color": "#1a1a2e",
    "accent":      "#e94560",
    "bg_color":    "#ffffff",
}


def resolve_theme(config: dict) -> dict:
    """
    Merge a named theme into config.
    Custom values in config always win over the theme preset.

    Priority (highest → lowest):
      1. Explicit keys in config (from JSON / CLI)
      2. Theme preset values
      3. DEFAULTS fallback
    """
    theme_name = config.get("theme", "light").lower()

    if theme_name == "custom" or theme_name not in THEMES:
        # No preset — use config values as-is
        return config

    preset = THEMES[theme_name]

    # Build merged dict: preset first, then config overrides
    merged = {**preset}
    for k, v in config.items():
        if v is not None:
            merged[k] = v

    # Keep theme key so we can reference it later
    merged["theme"] = theme_name
    return merged


# ══════════════════════════════════════════════════════════════════
#  REGISTRY  (tracks all PyWAApp subclasses & instances globally)
# ══════════════════════════════════════════════════════════════════
_PYWA_REGISTRY = {"classes": [], "instances": []}


# ══════════════════════════════════════════════════════════════════
#  PYTHON UI DSL  (the "language" your user writes)
# ══════════════════════════════════════════════════════════════════
class PyWAApp:
    """Base class users extend to define their PWA."""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        _PYWA_REGISTRY["classes"].append(cls)

    def __init__(self):
        _PYWA_REGISTRY["instances"].append(self)
        self.title        = "PyWA App"
        self.theme_color  = "#1a1a2e"
        self.accent_color = "#e94560"
        self.bg_color     = "#ffffff"
        self.dark_mode    = False
        self._pages       = {}
        self._nav_items   = []
        self._styles      = []
        self._scripts     = []
        self._current_page= "home"

    # ── Page registration ──────────────────────────────────────
    def page(self, name, title=None):
        """Decorator: @app.page('home')"""
        def decorator(fn):
            self._pages[name] = {"fn": fn, "title": title or name.title()}
            return fn
        return decorator

    def nav(self, label, page, icon="●"):
        self._nav_items.append({"label": label, "page": page, "icon": icon})

    # ── UI Components ──────────────────────────────────────────
    def heading(self, text, level=1, cls=""):
        return f'<h{level} class="pywa-heading {cls}">{text}</h{level}>'

    def text(self, content, cls=""):
        return f'<p class="pywa-text {cls}">{content}</p>'

    def button(self, label, onclick="", cls="", variant="primary"):
        return (f'<button class="pywa-btn pywa-btn-{variant} {cls}" '
                f'onclick="{onclick}">{label}</button>')

    def input(self, placeholder="", id="", type="text", cls=""):
        return (f'<input class="pywa-input {cls}" type="{type}" '
                f'id="{id}" placeholder="{placeholder}" />')

    def card(self, *children, cls=""):
        inner = "\n".join(children)
        return f'<div class="pywa-card {cls}">{inner}</div>'

    def row(self, *children, cls=""):
        inner = "\n".join(children)
        return f'<div class="pywa-row {cls}">{inner}</div>'

    def col(self, *children, cls=""):
        inner = "\n".join(children)
        return f'<div class="pywa-col {cls}">{inner}</div>'

    def image(self, src, alt="", cls=""):
        return f'<img class="pywa-img {cls}" src="{src}" alt="{alt}" loading="lazy" />'

    def badge(self, text, color="accent"):
        return f'<span class="pywa-badge pywa-badge-{color}">{text}</span>'

    def divider(self):
        return '<hr class="pywa-divider" />'

    def spacer(self, size="md"):
        return f'<div class="pywa-spacer-{size}"></div>'

    def grid(self, *children, cols=2, cls=""):
        inner = "\n".join(children)
        return f'<div class="pywa-grid pywa-grid-{cols} {cls}">{inner}</div>'

    def list_items(self, items, ordered=False):
        tag  = "ol" if ordered else "ul"
        rows = "\n".join(f"<li>{i}</li>" for i in items)
        return f'<{tag} class="pywa-list">{rows}</{tag}>'

    def hero(self, heading, subtext, *children):
        inner = "\n".join(children)
        return f'''<section class="pywa-hero">
  <h1 class="pywa-hero-title">{heading}</h1>
  <p class="pywa-hero-sub">{subtext}</p>
  <div class="pywa-hero-actions">{inner}</div>
</section>'''

    def navbar(self, title, *children):
        inner = "\n".join(children)
        return f'''<nav class="pywa-navbar">
  <span class="pywa-navbar-title">{title}</span>
  <div class="pywa-navbar-links">{inner}</div>
</nav>'''

    def footer(self, text):
        return f'<footer class="pywa-footer"><p>{text}</p></footer>'

    def custom_html(self, raw):
        return raw

    def custom_css(self, css):
        self._styles.append(css)

    def custom_js(self, js):
        self._scripts.append(js)

    # ── Render ─────────────────────────────────────────────────
    def render_page(self, name):
        if name in self._pages:
            return self._pages[name]["fn"](self) or ""
        return "<p>Page not found</p>"


# ══════════════════════════════════════════════════════════════════
#  COMPATIBILITY CHECKER
# ══════════════════════════════════════════════════════════════════
class CompatibilityChecker:

    CHECKS = [
        # (pattern, issue, fix_fn)
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
  /* ── Theme colours (injected by compiler from THEMES preset or custom values) */
  --color-bg:         {bg_color};      /* page background                    */
  --color-primary:    {theme_color};   /* navbar, primary buttons, links      */
  --color-accent:     {accent};        /* highlights, badges, active states   */
  --color-text:       {text};          /* main body text                      */
  --color-text-muted: {text_muted};    /* secondary / helper text             */
  --color-surface:    {surface};       /* cards, inputs, secondary panels     */
  --color-border:     {border};        /* dividers, input outlines            */

  /* ── Shape & spacing */
  --radius-sm:      6px;
  --radius-md:      {radius};          /* cards (theme-specific roundness)    */
  --radius-lg:      20px;
  --shadow-sm:      {shadow};          /* card resting shadow                 */
  --shadow-md:      0 4px 16px rgba(0,0,0,.15);
  --shadow-lg:      0 8px 32px rgba(0,0,0,.2);

  /* ── Typography */
  --font-sans:      {font};            /* primary font stack                  */
  --font-mono:      'Cascadia Code', 'Fira Code', monospace;

  /* ── Spacing scale */
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

/* ── Fluid Typography ────────────────────────────────────── */
h1 { font-size: clamp(1.8rem, 5vw, 3rem);   font-weight: 800; line-height: 1.1; }
h2 { font-size: clamp(1.4rem, 3.5vw, 2rem); font-weight: 700; }
h3 { font-size: clamp(1.1rem, 2.5vw, 1.5rem); font-weight: 600; }
p  { font-size: clamp(0.95rem, 2vw, 1.05rem); color: var(--color-text-muted); }

/* ── Navbar ──────────────────────────────────────────────── */
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
.pywa-navbar-title { font-weight: 800; font-size: 1.2rem; letter-spacing: -.02em; }
.pywa-navbar-links { display: flex; gap: var(--space-md); }
.pywa-navbar-links a { color: rgba(255,255,255,.8); text-decoration: none; font-size: .9rem; transition: color var(--transition); }
.pywa-navbar-links a:hover { color: #fff; }

/* Mobile navbar */
@media (max-width: 640px) {
  .pywa-navbar { padding: var(--space-sm) var(--space-md); }
  .pywa-navbar-links { gap: var(--space-sm); }
  .pywa-navbar-links a { font-size: .8rem; }
}

/* ── Bottom Tab Nav (mobile) ─────────────────────────────── */
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
  transition: color var(--transition);
  gap: 2px;
}
.pywa-tab-btn .tab-icon { font-size: 1.3rem; }
.pywa-tab-btn.active, .pywa-tab-btn:hover { color: var(--color-primary); }

@media (max-width: 768px) {
  .pywa-tab-nav { display: block; }
  body { padding-bottom: calc(70px + env(safe-area-inset-bottom)); }
  .pywa-navbar-links { display: none; }
}

/* ── Page System ─────────────────────────────────────────── */
.pywa-page { display: none; animation: pywa-fadein .25s ease; }
.pywa-page.active { display: block; }

@keyframes pywa-fadein {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ── Hero ────────────────────────────────────────────────── */
.pywa-hero {
  background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
  color: #fff;
  padding: var(--space-xl) var(--space-lg);
  text-align: center;
}
.pywa-hero-title { color: #fff; margin-bottom: var(--space-sm); }
.pywa-hero-sub   { color: rgba(255,255,255,.85); font-size: 1.1rem; margin-bottom: var(--space-lg); }
.pywa-hero-actions { display: flex; gap: var(--space-md); justify-content: center; flex-wrap: wrap; }

@media (max-width: 640px) {
  .pywa-hero { padding: var(--space-lg) var(--space-md); }
}

/* ── Cards ───────────────────────────────────────────────── */
.pywa-card {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-lg);
  box-shadow: var(--shadow-sm);
  transition: box-shadow var(--transition), transform var(--transition);
}
.pywa-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }

/* ── Buttons ─────────────────────────────────────────────── */
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
  text-decoration: none;
  white-space: nowrap;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
  min-height: 44px; /* WCAG touch target */
}
.pywa-btn-primary {
  background: var(--color-primary);
  color: #fff;
}
.pywa-btn-primary:hover { filter: brightness(1.15); transform: translateY(-1px); }
.pywa-btn-primary:active { transform: translateY(0); }
.pywa-btn-accent  { background: var(--color-accent); color: #fff; }
.pywa-btn-outline {
  background: transparent;
  color: var(--color-primary);
  border: 2px solid var(--color-primary);
}
.pywa-btn-outline:hover { background: var(--color-primary); color: #fff; }
.pywa-btn-ghost { background: transparent; color: var(--color-text); }
.pywa-btn-ghost:hover { background: var(--color-surface); }

@media (max-width: 480px) {
  .pywa-btn { width: 100%; justify-content: center; }
}

/* ── Inputs ──────────────────────────────────────────────── */
.pywa-input {
  width: 100%;
  padding: .65em 1em;
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 1rem;
  font-family: var(--font-sans);
  background: var(--color-bg);
  color: var(--color-text);
  transition: border-color var(--transition), box-shadow var(--transition);
  min-height: 44px;
}
.pywa-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-primary) 20%, transparent);
}

/* ── Grid ────────────────────────────────────────────────── */
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

/* ── Row / Col ───────────────────────────────────────────── */
.pywa-row { display: flex; gap: var(--space-md); flex-wrap: wrap; align-items: flex-start; }
.pywa-col { display: flex; flex-direction: column; gap: var(--space-sm); flex: 1; min-width: 200px; }

/* ── Badges ──────────────────────────────────────────────── */
.pywa-badge {
  display: inline-block;
  padding: .2em .7em;
  border-radius: 999px;
  font-size: .75rem;
  font-weight: 700;
  letter-spacing: .03em;
  text-transform: uppercase;
}
.pywa-badge-accent  { background: var(--color-accent);  color: #fff; }
.pywa-badge-primary { background: var(--color-primary); color: #fff; }
.pywa-badge-neutral { background: var(--color-surface); color: var(--color-text-muted); }

/* ── Misc ────────────────────────────────────────────────── */
.pywa-divider    { border: none; border-top: 1px solid var(--color-border); margin: var(--space-md) 0; }
.pywa-spacer-xs  { height: var(--space-xs); }
.pywa-spacer-sm  { height: var(--space-sm); }
.pywa-spacer-md  { height: var(--space-md); }
.pywa-spacer-lg  { height: var(--space-lg); }
.pywa-spacer-xl  { height: var(--space-xl); }
.pywa-img        { max-width: 100%; height: auto; border-radius: var(--radius-sm); }
.pywa-list       { padding-left: 1.5em; color: var(--color-text-muted); }
.pywa-list li    { margin-bottom: var(--space-xs); }
.pywa-heading    { color: var(--color-text); margin-bottom: var(--space-sm); }
.pywa-text       { margin-bottom: var(--space-md); }

/* ── Main Content ────────────────────────────────────────── */
.pywa-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-lg);
}
@media (max-width: 640px) {
  .pywa-main { padding: var(--space-md); }
}

/* ── Footer ──────────────────────────────────────────────── */
.pywa-footer {
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
  padding: var(--space-lg);
  text-align: center;
  color: var(--color-text-muted);
  font-size: .9rem;
}

/* ── Deprecated marquee fallback ─────────────────────────── */
.pywa-marquee {
  overflow: hidden; white-space: nowrap;
  animation: pywa-scroll 10s linear infinite;
}
@keyframes pywa-scroll {
  from { transform: translateX(100%); }
  to   { transform: translateX(-100%); }
}

/* ── Auto dark mode (only applied when theme = light/nature/ocean/sunset) */
/* For dark/glass themes this block is not needed but is harmless.         */
@media (prefers-color-scheme: dark) {
  :root.pywa-auto-dark {
    --color-bg:         #0d0d0d;
    --color-text:       #f0f0f0;
    --color-text-muted: #999;
    --color-surface:    #1a1a1a;
    --color-border:     #2a2a2a;
  }
}

/* ── Glass theme extras ───────────────────────────────────── */
body.pywa-theme-glass {
  background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
  min-height: 100vh;
}
body.pywa-theme-glass .pywa-card {
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  background: var(--color-surface) !important;
  border: 1px solid var(--color-border);
}
body.pywa-theme-glass .pywa-navbar {
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  background: rgba(109,40,217,0.7) !important;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}

/* ── PWA Install Banner ──────────────────────────────────── */
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
  cursor: pointer; font-weight: 700;
}
#pywa-install-banner button:hover { background: rgba(255,255,255,.35); }
"""

    def optimize(self, html, config):
        """Inject responsive meta tags and base CSS."""

        viewport = '<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />'
        mobile_capable = '<meta name="mobile-web-app-capable" content="yes" />'
        apple_capable  = '<meta name="apple-mobile-web-app-capable" content="yes" />'
        apple_title    = f'<meta name="apple-mobile-web-app-title" content="{config["name"]}" />'
        apple_status   = f'<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />'
        description    = f'<meta name="description" content="{config["name"]} — built with PyWA" />'
        og_title       = f'<meta property="og:title" content="{config["name"]}" />'
        og_type        = '<meta property="og:type" content="website" />'
        charset        = '<meta charset="UTF-8" />'

        # Pull theme-aware values (with fallbacks for custom theme)
        _t = config
        base_css = self.BASE_CSS.replace("{", "{{").replace("}", "}}") \
                                .replace("{{bg_color}}",    "{bg_color}") \
                                .replace("{{theme_color}}", "{theme_color}") \
                                .replace("{{accent}}",      "{accent}") \
                                .replace("{{surface}}",     "{surface}") \
                                .replace("{{border}}",      "{border}") \
                                .replace("{{text}}",        "{text}") \
                                .replace("{{text_muted}}",  "{text_muted}") \
                                .replace("{{radius}}",      "{radius}") \
                                .replace("{{font}}",        "{font}") \
                                .replace("{{shadow}}",      "{shadow}") \
                                .format(
            theme_color = _t.get("theme_color", "#1a1a2e"),
            accent      = _t.get("accent",      "#e94560"),
            bg_color    = _t.get("bg_color",    "#ffffff"),
            surface     = _t.get("surface",     "#f5f5f5"),
            border      = _t.get("border",      "#e0e0e0"),
            text        = _t.get("text",        "#1a1a1a"),
            text_muted  = _t.get("text_muted",  "#666666"),
            radius      = _t.get("radius",      "12px"),
            font        = _t.get("font",        "'Segoe UI', system-ui, sans-serif"),
            shadow      = _t.get("shadow",      "0 2px 12px rgba(0,0,0,.08)"),
        )

        # Theme name for body class (e.g. pywa-theme-glass)
        theme_name = config.get("theme", "light")
        # Auto-dark class only for light-based themes
        auto_dark_class = "pywa-auto-dark" if theme_name in ("light","nature","ocean","sunset") else ""

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

        # Inject theme class onto <body> (or add body tag)
        body_class = f"pywa-theme-{theme_name} {auto_dark_class}".strip()
        if "<body>" in html:
            html = html.replace("<body>", f'<body class="{body_class}">', 1)
        elif "<body " in html:
            html = re.sub(r'<body ([^>]*)>', lambda m: f'<body class="{body_class}" {m.group(1)}>', html, count=1)

        return html


# ══════════════════════════════════════════════════════════════════
#  HTML GENERATOR  (turns PyWAApp pages into a full document)
# ══════════════════════════════════════════════════════════════════
class HTMLGenerator:

    def generate(self, app_instance, config):
        pages_html   = ""
        tab_btns     = ""
        desktop_links= ""

        nav_items = app_instance._nav_items
        pages     = app_instance._pages

        # If no nav registered, auto-build from pages
        if not nav_items:
            icons = ["⌂", "★", "✉", "☰", "♥", "⚙"]
            for i, (name, meta) in enumerate(pages.items()):
                nav_items.append({
                    "label": meta["title"],
                    "page":  name,
                    "icon":  icons[i % len(icons)],
                })

        first_page = list(pages.keys())[0] if pages else "home"

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
            content = meta["fn"](app_instance)
            pages_html += f'''
    <div class="pywa-page {active}" id="page-{name}">
      <main class="pywa-main">
        {content or ""}
      </main>
    </div>'''

        extra_css = "\n".join(app_instance._styles)
        extra_js  = "\n".join(app_instance._scripts)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <title>{config['name']}</title>
  <link rel="manifest" href="manifest.json" />
  <meta name="theme-color" content="{config['theme_color']}" />
  <link rel="apple-touch-icon" href="icon-192.png" />
  {"<style>" + extra_css + "</style>" if extra_css else ""}
</head>
<body>

  <!-- Navbar (desktop) -->
  <nav class="pywa-navbar">
    <span class="pywa-navbar-title">{config['name']}</span>
    <div class="pywa-navbar-links">{desktop_links}</div>
  </nav>

  <!-- Pages -->
  {pages_html}

  <!-- Bottom Tab Nav (mobile) -->
  <div class="pywa-tab-nav">
    <div class="pywa-tab-nav-inner">
      {tab_btns}
    </div>
  </div>

  <!-- PWA Install Banner -->
  <div id="pywa-install-banner">
    📱 Install this app
    <button onclick="pywaInstall()">Install</button>
    <button onclick="document.getElementById('pywa-install-banner').classList.remove('show')">✕</button>
  </div>

  <script>
    // ── Navigation ────────────────────────────────────────
    function pywaNavigate(page) {{
      document.querySelectorAll('.pywa-page').forEach(p => p.classList.remove('active'));
      document.querySelectorAll('.pywa-tab-btn').forEach(b => b.classList.remove('active'));
      const pg = document.getElementById('page-' + page);
      const tb = document.getElementById('tab-' + page);
      if (pg) pg.classList.add('active');
      if (tb) tb.classList.add('active');
      window.history.pushState({{page}}, '', '#' + page);
    }}

    // ── Back/Forward ──────────────────────────────────────
    window.addEventListener('popstate', e => {{
      if (e.state && e.state.page) pywaNavigate(e.state.page);
    }});

    // ── PWA Install ───────────────────────────────────────
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

    // ── Service Worker ────────────────────────────────────
    if ('serviceWorker' in navigator) {{
      navigator.serviceWorker.register('sw.js')
        .then(() => console.log('[PyWA] Service worker ready'))
        .catch(e => console.warn('[PyWA] SW error', e));
    }}

    // ── Hash-based routing on load ────────────────────────
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
        "name":             config["name"],
        "short_name":       config["short_name"],
        "start_url":        "index.html",
        "display":          "standalone",
        "background_color": config["bg_color"],
        "theme_color":      config["theme_color"],
        "orientation":      "any",
        "scope":            "./",
        "icons": [
            {"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ]
    }, indent=2)


def make_sw(file_list, version):
    files = json.dumps(file_list, indent=4)
    return f"""/* PyWA Service Worker v{version} — auto-generated */
const CACHE = 'pywa-{version}-{hashlib.md5(version.encode()).hexdigest()[:6]}';
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
#  COMPILER  (main entry point)
# ══════════════════════════════════════════════════════════════════
class PyWACompiler:

    def __init__(self, config=None):
        self.config    = {**DEFAULTS, **(config or {})}
        self.checker   = CompatibilityChecker()
        self.optimizer = ResponsiveOptimizer()
        self.generator = HTMLGenerator()

    def _banner(self):
        print("""
╔═══════════════════════════════════════╗
║   PyWA — Python → PWA Compiler        ║
║   Responsive • Installable • Offline  ║
╚═══════════════════════════════════════╝""")

    def compile(self, source_file):
        self._banner()
        src = Path(source_file)
        print(f"\n  📄 Source : {src}")
        print(f"  📦 Output : {self.config['output_dir']}/\n")

        # ── 1. Load & execute Python source ──────────────────
        print("  [1/6] Loading Python source...")

        # Clear registry before loading
        _PYWA_REGISTRY["classes"].clear()
        _PYWA_REGISTRY["instances"].clear()

        # Build namespace with PyWAApp available
        import types
        mod = types.ModuleType("pywa_user_app")
        mod.__file__ = str(src)
        mod.PyWAApp  = PyWAApp
        namespace    = vars(mod)

        try:
            code = compile(src.read_text(encoding="utf-8"), str(src), "exec")
            exec(code, namespace)
        except SyntaxError as e:
            print(f"\n  🚨 Syntax error in {src.name} line {e.lineno}: {e.msg}")
            sys.exit(1)
        except Exception as e:
            import traceback
            print(f"\n  🚨 Runtime error: {e}")
            traceback.print_exc()
            sys.exit(1)

        # Find app — prefer live instance, fall back to class
        app = None
        if _PYWA_REGISTRY["instances"]:
            app = _PYWA_REGISTRY["instances"][-1]
        elif _PYWA_REGISTRY["classes"]:
            app = _PYWA_REGISTRY["classes"][-1]()

        if not app:
            print("  🚨 No PyWAApp subclass or instance found in source file.")
            print("     Define: class MyApp(PyWAApp): ...")
            sys.exit(1)

        # ── Derive app name from filename if not set in JSON/CLI/app ──────
        # Priority: CLI/JSON "name" > app.title attr > filename stem
        if not self.config.get("name"):
            stem = Path(source_file).stem  # e.g. "my_task_app"
            # Convert snake_case / kebab-case to Title Case
            self.config["name"] = stem.replace("_", " ").replace("-", " ").title()

        # Pull colour/title overrides from the app class itself
        for key in ("title", "theme_color", "accent_color", "bg_color"):
            val = getattr(app, key, None)
            if val:
                mapped = {"title": "name", "accent_color": "accent"}.get(key, key)
                # App attribute only wins if config key not already set by JSON/CLI
                if not self.config.get(mapped):
                    self.config[mapped] = val

        # Auto-generate short_name from name if not set
        if not self.config.get("short_name"):
            words = self.config["name"].split()
            self.config["short_name"] = (
                "".join(w[0].upper() for w in words[:3])
                if len(words) > 1 else words[0][:6]
            )

        # ── Apply theme preset ────────────────────────────────────────────
        self.config = resolve_theme(self.config)

        theme_display = self.config.get("theme", "light")
        print(f"     ✅ App: '{self.config['name']}' | theme: {theme_display} | {len(app._pages)} page(s)")

        # ── 2. Generate HTML ──────────────────────────────────
        print("  [2/6] Generating HTML...")
        html = self.generator.generate(app, self.config)
        print(f"     ✅ {len(html):,} bytes generated")

        # ── 3. Optimize for responsive / mobile ──────────────
        print("  [3/6] Optimising for mobile + desktop...")
        html = self.optimizer.optimize(html, self.config)
        print("     ✅ Viewport, touch targets, fluid typography injected")

        # ── 4. Compatibility check & auto-fix ─────────────────
        print("  [4/6] Running compatibility checks...")
        html, issues, fixes = self.checker.check(html)
        if issues:
            for issue in issues:
                print(f"     {issue}")
            for fix in fixes:
                print(fix)
        else:
            print("     ✅ No compatibility issues found")

        # ── 5. Write output files ─────────────────────────────
        print("  [5/6] Writing output files...")
        out = Path(self.config["output_dir"])
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)

        (out / "index.html").write_text(html, encoding="utf-8")
        print("     ✅ index.html")

        (out / "manifest.json").write_text(make_manifest(self.config))
        print("     ✅ manifest.json")

        files_to_cache = ["index.html", "manifest.json", "icon-192.png", "icon-512.png"]
        (out / "sw.js").write_text(make_sw(files_to_cache, self.config["version"]))
        print("     ✅ sw.js")

        for size in [192, 512]:
            (out / f"icon-{size}.png").write_bytes(make_png(size, self.config["theme_color"]))
        print("     ✅ icon-192.png / icon-512.png")

        # ── 6. Summary ────────────────────────────────────────
        total = sum(f.stat().st_size for f in out.iterdir())
        print(f"\n  [6/6] Compiled! {total:,} bytes → ./{self.config['output_dir']}/")

        return out


# ══════════════════════════════════════════════════════════════════
#  AUTO SERVER  (background thread, no manual termux step)
# ══════════════════════════════════════════════════════════════════
import threading
import http.server
import socketserver
import socket
import subprocess
import webbrowser


class _SilentHandler(http.server.SimpleHTTPRequestHandler):
    """Serves files silently — no access log spam."""
    def log_message(self, fmt, *args):
        pass
    def log_error(self, fmt, *args):
        pass


def find_free_port(start=8080):
    """Find a free port starting from `start`."""
    for port in range(start, start + 20):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", port))
                return port
        except OSError:
            continue
    return start


def start_server(directory, port):
    """Start HTTP server in a daemon background thread."""
    abs_dir = str(Path(directory).resolve())

    class Handler(_SilentHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=abs_dir, **kw)

    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("", port), Handler)

    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


def open_browser(url):
    """
    Open browser on Android (Termux), Linux desktop, or any platform.
    Tries multiple strategies so it always works.
    """
    # Android / Termux — use am (Activity Manager)
    for cmd in [
        ["am", "start", "--user", "0", "-a", "android.intent.action.VIEW", "-d", url],
        ["termux-open-url", url],
        ["xdg-open", url],
        ["open", url],                   # macOS
    ]:
        try:
            result = subprocess.run(
                cmd, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, timeout=4
            )
            if result.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    # Last resort — Python webbrowser module
    try:
        webbrowser.open(url)
        return True
    except Exception:
        pass

    return False


# ══════════════════════════════════════════════════════════════════
#  WATCH MODE  (auto-recompile on save, live-reload in browser)
# ══════════════════════════════════════════════════════════════════
def watch_and_serve(source_file, config, port, open=True):
    """
    Watches source file for changes, recompiles, and injects a
    live-reload script so the browser refreshes automatically.
    """
    compiler   = PyWACompiler(config)
    out_dir    = config.get("output_dir", "pwa_output")
    last_mtime = 0
    version    = [0]   # mutable counter for reload polling

    RELOAD_SCRIPT = """
<script>
/* PyWA Live Reload */
(function(){
  let v = null;
  setInterval(async () => {
    try {
      const r = await fetch('/__pywa_version__');
      const t = await r.text();
      if (v === null) { v = t; return; }
      if (t !== v) location.reload();
    } catch(e) {}
  }, 800);
})();
</script>"""

    # Patch compiler to inject live-reload script
    original_compile = compiler.compile

    def patched_compile(src):
        out = original_compile(src)
        # Inject reload script into index.html
        idx = out / "index.html"
        html = idx.read_text(encoding="utf-8")
        if RELOAD_SCRIPT not in html:
            html = html.replace("</body>", RELOAD_SCRIPT + "\n</body>")
        idx.write_text(html, encoding="utf-8")

        # Write version file so browser knows to reload
        version[0] += 1
        (out / "__pywa_version__").write_text(str(version[0]))
        return out

    compiler.compile = patched_compile

    # Initial compile
    print(f"\n  [watch] Compiling {source_file}...")
    try:
        compiler.compile(source_file)
        last_mtime = os.path.getmtime(source_file)
    except Exception as e:
        print(f"  ⚠️  Initial compile error: {e}")

    # Start server
    httpd = start_server(out_dir, port)
    url   = f"http://localhost:{port}"
    print(f"  [watch] Serving at {url}")
    print(f"  [watch] Watching {source_file} — browser auto-reloads on save")
    print(f"  [watch] Press Ctrl+C to stop\n")
    if open:
        open_browser(url)

    try:
        while True:
            time.sleep(0.8)
            try:
                mtime = os.path.getmtime(source_file)
            except FileNotFoundError:
                continue
            if mtime != last_mtime:
                last_mtime = mtime
                ts = datetime.now().strftime("%H:%M:%S")
                print(f"  [{ts}] Change detected — recompiling...", end=" ", flush=True)
                try:
                    compiler.compile(source_file)
                    print("✅")
                except Exception as e:
                    print(f"⚠️  {e}")
    except KeyboardInterrupt:
        print("\n  [watch] Stopped.")
        httpd.shutdown()


# ══════════════════════════════════════════════════════════════════
#  JSON CONFIG  (pywa.json  — lives next to your .py file)
# ══════════════════════════════════════════════════════════════════
"""
pywa.json — all fields optional, merged under CLI flags.

{
  "name":        "My App",
  "short_name":  "App",
  "theme_color": "#6200ea",
  "accent":      "#03dac6",
  "bg_color":    "#ffffff",
  "version":     "1.0.0",
  "output_dir":  "pwa_output",
  "port":        8080,
  "no_open":     false,
  "no_serve":    false
}
"""

def load_json_config(py_file: Path) -> dict:
    """
    Looks for pywa.json in this order:
      1. Same folder as the .py file  → myapp/pywa.json
      2. Current working directory    → ./pywa.json
    Returns merged dict (empty if none found).
    """
    candidates = [
        py_file.parent / "pywa.json",
        Path.cwd() / "pywa.json",
    ]
    for path in candidates:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                print(f"  📄 Config loaded: {path}")
                return data
            except json.JSONDecodeError as e:
                print(f"  ⚠️  pywa.json parse error: {e}")
    return {}


def init_config(py_file: Path):
    """
    Write a fully-annotated starter pywa.json next to the .py file.
    Name is derived from the filename — just edit what you need.
    """
    dest = py_file.parent / "pywa.json"
    if dest.exists():
        print(f"  ⚠️  {dest} already exists — not overwriting.")
        return

    name = py_file.stem.replace("_", " ").replace("-", " ").title()

    # Build JSON with inline comments as separate _comment keys
    # (JSON doesn't support real comments — these explain each field)
    starter = {
        "_info": "PyWA config — all fields optional. Delete any you don't need.",

        # ── Identity ──────────────────────────────────────────────────────
        # name: Full app name shown in browser tab and install prompt.
        #       Leave as null to auto-derive from the Python filename.
        "name": name,

        # short_name: Used on home screen icon label (keep under 12 chars).
        #             null = auto-generated from name initials.
        "short_name": None,

        # version: Shown in manifest. Bump this to force SW cache refresh.
        "version": "1.0.0",

        # ── Theme ─────────────────────────────────────────────────────────
        # theme: Built-in theme preset. Options:
        #   "light"   — White bg, deep navy + coral  (general apps)
        #   "dark"    — Black bg, violet + cyan       (dev tools, media)
        #   "glass"   — Frosted glass over dark bg    (portfolios, landing)
        #   "nature"  — Forest greens, serif font     (health, eco apps)
        #   "sunset"  — Warm coral + amber            (social, food apps)
        #   "ocean"   — Deep blues, crisp borders     (finance, analytics)
        #   "custom"  — Use the colour fields below   (full control)
        "theme": "light",

        # ── Custom colours (only used when theme = "custom") ──────────────
        # theme_color: Navbar background and primary button colour.
        "theme_color": None,

        # accent: Highlights, badges, active tab indicator.
        "accent": None,

        # bg_color: Main page background.
        "bg_color": None,

        # ── Build output ──────────────────────────────────────────────────
        # output_dir: Folder where compiled HTML/JS/icons are written.
        "output_dir": "pwa_output",

        # ── Server ────────────────────────────────────────────────────────
        # port: Local server port. 0 = auto-find a free port.
        "port": 0,

        # no_open: Set true to suppress auto-opening the browser.
        "no_open": False,

        # no_serve: Set true to compile only (no local server started).
        "no_serve": False
    }

    # Write clean JSON (strip None values to keep file tidy)
    clean = {k: v for k, v in starter.items() if v is not None or k in ("short_name","theme_color","accent","bg_color")}
    dest.write_text(json.dumps(clean, indent=2))
    print(f"\n  ✅ Created {dest}")
    print("  Open in Acode and edit the \"theme\" field to change the look.")
    print("  Available themes: light, dark, glass, nature, sunset, ocean, custom")
    print(f"  Then run:  python pywa.py build {py_file.name}\n")


# ══════════════════════════════════════════════════════════════════
#  FILE PICKER  (no GUI needed — pure terminal)
# ══════════════════════════════════════════════════════════════════

def _pick_from_list(files: list) -> Path | None:
    """
    Arrow-key terminal menu using only stdlib (sys/tty/termios).
    Falls back to numbered list if terminal is not a TTY
    (e.g. piped input, basic Termux session).
    """
    import sys, os

    # ── Non-interactive fallback (numbered list) ───────────────
    if not sys.stdin.isatty():
        print("\n  Available .py files:")
        for i, f in enumerate(files, 1):
            print(f"    [{i}] {f.name}")
        print()
        try:
            choice = input("  Enter number: ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(files):
                return files[idx]
        except (ValueError, EOFError):
            pass
        return None

    # ── Arrow-key menu (full TTY) ──────────────────────────────
    try:
        import tty, termios
    except ImportError:
        # Windows — just use numbered list
        return _pick_numbered(files)

    CYAN   = "\033[96m"
    WHITE  = "\033[97m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"
    CLEAR  = "\033[2K\r"
    UP     = "\033[{}A"
    ARROW_UP   = b'\x1b[A'
    ARROW_DOWN = b'\x1b[B'
    ENTER      = (b'\r', b'\n', b'')

    selected = 0

    def draw(sel):
        lines = []
        for i, f in enumerate(files):
            if i == sel:
                lines.append(f"  {CYAN}▶  {f.name}{RESET}  {DIM}({f.parent}){RESET}")
            else:
                lines.append(f"  {DIM}   {f.name}{RESET}")
        return "\n".join(lines)

    # Save terminal state
    fd   = sys.stdin.fileno()
    old  = termios.tcgetattr(fd)

    print(f"\n  {WHITE}Select your Python app file{RESET}  {DIM}(↑↓ arrows, Enter){RESET}\n")
    rendered = draw(selected)
    print(rendered, end="", flush=True)
    num_lines = len(files)

    try:
        tty.setraw(fd)
        while True:
            ch = os.read(fd, 3)
            if ch in ENTER:
                break
            elif ch == ARROW_UP and selected > 0:
                selected -= 1
            elif ch == ARROW_DOWN and selected < len(files) - 1:
                selected += 1
            elif ch == b'q':
                selected = -1
                break
            # Redraw
            sys.stdout.write(UP.format(num_lines - 1) + "\r")
            sys.stdout.write(draw(selected))
            sys.stdout.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

    print("\n")
    if selected == -1:
        return None
    return files[selected]


def _pick_numbered(files: list) -> Path | None:
    print("\n  Available .py files:")
    for i, f in enumerate(files, 1):
        print(f"    [{i}] {f.name}  ({f.parent})")
    print()
    try:
        choice = input("  Enter number (or q to quit): ").strip()
        if choice.lower() == 'q':
            return None
        idx = int(choice) - 1
        if 0 <= idx < len(files):
            return files[idx]
    except (ValueError, EOFError):
        pass
    return None


def pick_py_file(search_dir: Path = None) -> Path | None:
    """
    Find all .py files (excluding pywa.py itself and __pycache__).
    Strategy:
      - 1 file found  → use it automatically (no prompt)
      - 2-9 files     → show arrow-key/numbered menu
      - 0 files       → error with hint
      - 10+ files     → ask user to type name (with suggestions)
    """
    base = search_dir or Path.cwd()

    # Collect candidates — skip pywa.py, venv, __pycache__, hidden dirs
    skip_names = {"pywa.py", "setup.py", "conftest.py"}
    skip_dirs  = {"__pycache__", ".git", "venv", ".venv", "env", "node_modules"}

    found = []
    for f in sorted(base.rglob("*.py")):
        if f.name in skip_names:
            continue
        if any(part in skip_dirs for part in f.parts):
            continue
        found.append(f)

    if not found:
        print(f"\n  ❌ No .py app files found in {base}")
        print("  Make sure your app file is in the current directory.\n")
        return None

    # ── Auto-select if only one file ──────────────────────────
    if len(found) == 1:
        print(f"\n  Auto-selected: {found[0].name}\n")
        return found[0]

    # ── Arrow/numbered menu for 2–9 files ─────────────────────
    if len(found) <= 9:
        return _pick_from_list(found)

    # ── Type-to-filter for 10+ files ──────────────────────────
    print(f"\n  Found {len(found)} .py files. Start typing a name (Tab shows matches):\n")
    for f in found[:5]:
        print(f"    {f.name}")
    if len(found) > 5:
        print(f"    ... and {len(found)-5} more\n")

    try:
        # Enable readline tab-complete if available
        try:
            import readline
            names = [f.name for f in found]
            def completer(text, state):
                matches = [n for n in names if n.startswith(text)]
                return matches[state] if state < len(matches) else None
            readline.set_completer(completer)
            readline.parse_and_bind("tab: complete")
        except ImportError:
            pass

        name = input("  Filename: ").strip()
        # Try exact match first, then partial
        for f in found:
            if f.name == name or f.stem == name:
                return f
        # Partial match
        matches = [f for f in found if name.lower() in f.name.lower()]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            return _pick_from_list(matches)
    except EOFError:
        pass

    return None


# ══════════════════════════════════════════════════════════════════
#  CONFIG MERGER  (JSON → CLI flags → DEFAULTS, in priority order)
# ══════════════════════════════════════════════════════════════════
def merge_config(args_dict: dict, json_cfg: dict) -> dict:
    """
    Priority (highest to lowest):
      1. CLI flags (--name, --color, etc.)
      2. pywa.json values
      3. Built-in DEFAULTS
    """
    # Map CLI arg names → config keys
    arg_to_key = {
        "name":       "name",
        "short_name": "short_name",
        "theme":      "theme",      # e.g. --theme dark
        "color":      "theme_color",
        "accent":     "accent",
        "bg":         "bg_color",
        "out":        "output_dir",
        "version":    "version",
    }
    # Start from DEFAULTS but don't lock in name (stays None until filename known)
    merged = {k: v for k, v in DEFAULTS.items()}

    # Layer 1: JSON config
    for k, v in json_cfg.items():
        if v is not None:
            merged[k] = v

    # Layer 2: CLI flags (only if explicitly set by user)
    for arg_key, cfg_key in arg_to_key.items():
        val = args_dict.get(arg_key)
        if val:
            merged[cfg_key] = val

    return merged


# ══════════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        prog="pywa",
        description="PyWA — Python to PWA Compiler"
    )
    sub = parser.add_subparsers(dest="command")

    # ── build ──────────────────────────────────────────────────
    build_p = sub.add_parser(
        "build",
        help="Compile, serve and open — all in one command"
    )
    build_p.add_argument("file",         nargs="?",   help="Python source file (optional — shows picker if omitted)")
    build_p.add_argument("--name",                    help="App name (overrides pywa.json and filename)")
    build_p.add_argument("--short-name",              help="Short home-screen label (max 12 chars)")
    build_p.add_argument("--theme",                   help="Theme preset: light|dark|glass|nature|sunset|ocean|custom")
    build_p.add_argument("--color",                   help="Primary/navbar colour hex — only used with --theme custom")
    build_p.add_argument("--accent",                  help="Accent/highlight colour hex — only used with --theme custom")
    build_p.add_argument("--bg",                      help="Page background colour hex — only used with --theme custom")
    build_p.add_argument("--out",                     help="Output directory", default=None)
    build_p.add_argument("--version",                 help="App version", default=None)
    build_p.add_argument("--port",                    help="Port for local server", type=int, default=0)
    build_p.add_argument("--no-open",                 help="Don't auto-open browser", action="store_true")
    build_p.add_argument("--no-serve",                help="Only compile, don't serve", action="store_true")
    build_p.add_argument("--config",                  help="Path to a specific .json config file", default=None)

    # ── watch ──────────────────────────────────────────────────
    watch_p = sub.add_parser(
        "watch",
        help="Watch, auto-recompile and live-reload browser on save"
    )
    watch_p.add_argument("file",         nargs="?",   help="Python source file (optional — shows picker if omitted)")
    watch_p.add_argument("--name",                    help="App name")
    watch_p.add_argument("--theme",                   help="Theme preset: light|dark|glass|nature|sunset|ocean|custom")
    watch_p.add_argument("--color",                   help="Primary colour hex (custom theme only)")
    watch_p.add_argument("--accent",                  help="Accent colour hex (custom theme only)")
    watch_p.add_argument("--out",                     help="Output directory", default=None)
    watch_p.add_argument("--port",                    help="Port", type=int, default=0)
    watch_p.add_argument("--no-open",                 help="Don't auto-open browser", action="store_true")
    watch_p.add_argument("--config",                  help="Path to a specific .json config file", default=None)

    # ── init ───────────────────────────────────────────────────
    init_p = sub.add_parser(
        "init",
        help="Create a starter pywa.json config next to your .py file"
    )
    init_p.add_argument("file", nargs="?", help="Python source file (shows picker if omitted)")

    args = parser.parse_args()

    # ── shared: resolve file (picker if not given) ─────────────
    def resolve_file(file_arg):
        if file_arg:
            p = Path(file_arg)
            if not p.exists():
                print(f"\n  ❌ File not found: {file_arg}\n")
                sys.exit(1)
            return p
        # No file given — launch picker
        picked = pick_py_file()
        if not picked:
            print("  No file selected. Exiting.")
            sys.exit(0)
        return picked

    # ── shared: load + merge config ────────────────────────────
    def get_config(file_path, args_ns):
        # Custom config path?
        if hasattr(args_ns, "config") and args_ns.config:
            cfg_path = Path(args_ns.config)
            if not cfg_path.exists():
                print(f"  ❌ Config file not found: {cfg_path}")
                sys.exit(1)
            json_cfg = json.loads(cfg_path.read_text())
            print(f"  📄 Config loaded: {cfg_path}")
        else:
            json_cfg = load_json_config(file_path)

        return merge_config(vars(args_ns), json_cfg)

    # ── handle: init ───────────────────────────────────────────
    if args.command == "init":
        py_file = resolve_file(getattr(args, "file", None))
        init_config(py_file)
        return

    # ── handle: build ──────────────────────────────────────────
    if args.command == "build":
        py_file = resolve_file(args.file)
        config  = get_config(py_file, args)

        # Port: CLI > JSON config > default
        port = args.port or config.get("port", 0) or find_free_port(8080)
        no_open  = args.no_open  or config.get("no_open",  False)
        no_serve = args.no_serve or config.get("no_serve", False)

        # Compile
        out_dir = PyWACompiler(config).compile(str(py_file))

        if no_serve:
            return

        url = f"http://localhost:{port}"
        print(f"  🌐 Starting local server on port {port}...")
        httpd = start_server(str(out_dir), port)
        time.sleep(0.3)

        if not no_open:
            print(f"  📱 Opening {url} ...")
            opened = open_browser(url)
            if not opened:
                print(f"  ℹ️  Couldn't auto-open. Visit manually: {url}")

        print(f"\n  ✅ Running at {url}")
        print(f"  Tap ⋮ → 'Add to Home Screen' to install as PWA")
        print(f"  Press Ctrl+C to stop\n")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n  Server stopped.")
            httpd.shutdown()

    # ── handle: watch ──────────────────────────────────────────
    elif args.command == "watch":
        py_file = resolve_file(args.file)
        config  = get_config(py_file, args)

        port    = args.port or config.get("port", 0) or find_free_port(8080)
        no_open = args.no_open or config.get("no_open", False)

        watch_and_serve(str(py_file), config, port, open=(not no_open))

    # ── no command: show help + launch picker ──────────────────
    else:
        print("""
╔═══════════════════════════════════════╗
║   PyWA — Python → PWA Compiler        ║
╚═══════════════════════════════════════╝

Commands:
  build [file]   Compile + serve + open browser
  watch [file]   Live-reload dev mode
  init  [file]   Create a starter pywa.json config

File argument is optional — if omitted, a file picker appears.

Examples:
  python pywa.py build                    ← picker appears
  python pywa.py build myapp.py           ← direct
  python pywa.py build myapp.py --color "#6200ea"
  python pywa.py init myapp.py            ← create pywa.json
  python pywa.py watch                    ← picker + live reload

pywa.json keys (all optional):
  name, short_name, theme_color, accent,
  bg_color, version, output_dir, port,
  no_open, no_serve
""")
        # Offer to launch picker right now
        try:
            ans = input("  Launch file picker now? [Y/n]: ").strip().lower()
        except EOFError:
            ans = "n"
        if ans in ("", "y", "yes"):
            py_file = pick_py_file()
            if py_file:
                json_cfg = load_json_config(py_file)
                config   = merge_config({}, json_cfg)
                port     = config.get("port", 0) or find_free_port(8080)
                out_dir  = PyWACompiler(config).compile(str(py_file))
                url      = f"http://localhost:{port}"
                httpd    = start_server(str(out_dir), port)
                time.sleep(0.3)
                open_browser(url)
                print(f"\n  ✅ Running at {url}")
                print(f"  Press Ctrl+C to stop\n")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\n  Server stopped.")
                    httpd.shutdown()


if __name__ == "__main__":
    main()
