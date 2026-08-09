#!/usr/bin/env python3
"""Build HTML preview comparing glow variants for the Nopaste logo."""

import base64
import io
from PIL import Image

# Load original logo
img = Image.open("/tmp/orig_logo.png")
buf = io.BytesIO()
img.save(buf, "PNG")
b64 = base64.b64encode(buf.getvalue()).decode()

html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nopaste — Logo Glow Preview</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

:root {{
    --bg-app: #0e1012;
    --bg-surface: #1a1c1e;
    --bg-surface-alt: #212427;
    --text-main: #e2e2e6;
    --text-muted: #9ba3af;
    --accent: #8ab4f8;
    --border: #33373b;
    --border-hover: #44494e;
    --font-sans: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    --radius-sm: 4px;
    --radius-md: 8px;
    --radius-lg: 12px;
    --space-2: 8px;
    --space-3: 12px;
    --space-4: 16px;
    --space-6: 24px;
    --space-8: 32px;
    --shadow-sm: 0 1px 2px 0 rgba(0,0,0,.30), 0 1px 3px 1px rgba(0,0,0,.15);
}}

* {{ box-sizing: border-box; }}
body {{
    margin: 0;
    background: var(--bg-app);
    color: var(--text-main);
    font-family: var(--font-sans);
    font-size: 14px;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
}}

/* Header */
.site-header {{
    height: 68px;
    background: var(--bg-surface);
    border-bottom: 1px solid var(--border);
    position: sticky; top: 0; z-index: 100;
}}
.header-container {{
    max-width: 1400px;
    height: 100%;
    margin: 0 auto;
    padding: 0 var(--space-4);
    display: flex;
    align-items: center;
    justify-content: space-between;
}}
.header-brand {{ display: flex; align-items: center; gap: var(--space-3); }}
.brand-lockup {{ display: flex; align-items: center; gap: var(--space-3); text-decoration: none; }}
.brand-mark {{
    position: relative;
    width: 58px; height: 58px;
    display: inline-flex;
    align-items: center; justify-content: center;
    flex-shrink: 0;
}}
.brand-logo {{
    width: auto; height: 54px; max-width: 54px;
    object-fit: contain;
    border-radius: var(--radius-sm);
    display: block;
    position: relative; z-index: 1;
}}
.brand-wordmark {{
    font-size: 1.25rem; font-weight: 600;
    letter-spacing: -0.02em;
    color: var(--text-main);
}}
.header-actions {{ display: flex; align-items: center; gap: var(--space-2); }}
.btn {{
    display: inline-flex; align-items: center; gap: var(--space-2);
    padding: var(--space-2) var(--space-4);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--bg-surface-alt);
    color: var(--text-main);
    font-family: inherit; font-size: 13px; font-weight: 500;
    cursor: pointer; text-decoration: none;
}}
.btn:hover {{ border-color: var(--border-hover); background: #2d3135; }}
.btn-icon-image {{ width: 20px; height: 20px; }}

/* Editor */
.container {{ max-width: 960px; margin: 0 auto; padding: var(--space-6) var(--space-4); flex: 1; }}
.editor-card {{
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    overflow: hidden;
}}
.editor-card-header {{ padding: var(--space-6); border-bottom: 1px solid var(--border); }}
.editor-card-header h2 {{ margin: 0 0 4px; font-size: 1.125rem; font-weight: 600; }}
.editor-card-header p {{ margin: 0; color: var(--text-muted); font-size: 13px; }}
.form-container {{ padding: var(--space-4); }}
textarea {{
    width: 100%; height: 280px;
    background: #000;
    color: #fff;
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: var(--space-4);
    font-family: "JetBrains Mono", monospace;
    font-size: 13px;
    resize: vertical;
}}
textarea:focus {{ outline: none; border-color: var(--accent); }}
.form-actions {{
    display: flex; justify-content: space-between; align-items: center;
    margin-top: var(--space-3);
}}
.form-hint {{ color: var(--text-muted); font-size: 12px; }}
.btn-primary {{
    background: var(--accent); color: #000; border-color: var(--accent);
    font-weight: 600;
}}
.btn-primary:hover {{ background: #aecbfa; border-color: #aecbfa; }}
.icon-badge {{ display: inline-flex; align-items: center; }}
.btn-icon-image-save {{ width: 18px; height: 18px; }}

/* Footer */
.site-footer {{
    text-align: center; padding: var(--space-4);
    color: var(--text-muted); font-size: 12px;
}}
.site-footer a {{ color: var(--accent); }}

/* ============= GLOW VARIANTS ============= */

/* VARIANT A: CURRENT (white radial-gradient glow) */
.glow-current .brand-mark::before {{
    content: "";
    position: absolute; inset: -6px;
    border-radius: 999px;
    background: radial-gradient(circle,
        rgba(255,255,255,0.58) 0%,
        rgba(255,255,255,0.34) 26%,
        rgba(255,255,255,0.16) 48%,
        rgba(255,255,255,0.07) 66%,
        rgba(255,255,255,0) 86%);
    transform: scale(1.64);
    filter: blur(12px);
    opacity: 1;
    pointer-events: none;
}}
.glow-current .brand-mark::after {{
    content: "";
    position: absolute; inset: 6px;
    border-radius: 999px;
    background: radial-gradient(circle,
        rgba(255,255,255,0.28) 0%,
        rgba(255,255,255,0.12) 42%,
        rgba(255,255,255,0) 74%);
    transform: scale(1.18);
    opacity: 0.95;
    pointer-events: none;
}}
.glow-current .brand-logo {{
    filter: drop-shadow(0 3px 12px rgba(255, 192, 82, 0.16));
}}

/* VARIANT B: Warm amber subtle glow */
.glow-warm .brand-mark::before {{
    content: "";
    position: absolute; inset: -4px;
    border-radius: 999px;
    background: radial-gradient(circle,
        rgba(255, 183, 77, 0.30) 0%,
        rgba(255, 152, 0, 0.14) 40%,
        rgba(255, 111, 0, 0.05) 65%,
        transparent 85%);
    transform: scale(1.3);
    filter: blur(10px);
    opacity: 1;
    pointer-events: none;
}}
.glow-warm .brand-mark::after {{
    content: "";
    position: absolute; inset: 4px;
    border-radius: 999px;
    background: radial-gradient(circle,
        rgba(255, 200, 100, 0.15) 0%,
        rgba(255, 180, 60, 0.06) 50%,
        transparent 80%);
    transform: scale(1.1);
    opacity: 0.8;
    pointer-events: none;
}}
.glow-warm .brand-logo {{
    filter: drop-shadow(0 2px 10px rgba(255, 170, 50, 0.25));
}}

/* VARIANT C: No glow, just elegant drop-shadow */
.glow-none .brand-mark::before,
.glow-none .brand-mark::after {{
    display: none;
}}
.glow-none .brand-logo {{
    filter: drop-shadow(0 2px 8px rgba(255, 192, 82, 0.20))
            drop-shadow(0 0 3px rgba(255, 160, 50, 0.10));
}}

/* VARIANT D: Soft red-gold dual ring */
.glow-dual .brand-mark::before {{
    content: "";
    position: absolute; inset: -3px;
    border-radius: 999px;
    background: radial-gradient(circle,
        rgba(200, 60, 40, 0.18) 0%,
        rgba(200, 60, 40, 0.06) 50%,
        transparent 80%);
    transform: scale(1.4);
    filter: blur(8px);
    pointer-events: none;
}}
.glow-dual .brand-mark::after {{
    content: "";
    position: absolute; inset: 0;
    border-radius: 999px;
    background: radial-gradient(circle,
        rgba(255, 200, 80, 0.22) 0%,
        rgba(255, 170, 40, 0.08) 45%,
        transparent 75%);
    transform: scale(1.15);
    filter: blur(6px);
    pointer-events: none;
}}
.glow-dual .brand-logo {{
    filter: drop-shadow(0 2px 10px rgba(255, 170, 50, 0.22))
            drop-shadow(0 0px 4px rgba(200, 60, 40, 0.10));
}}

/* === Section Layout === */
.demo-section {{
    max-width: 960px; margin: 40px auto; padding: 0 16px;
}}
.demo-section h2 {{
    color: var(--accent); font-size: 16px; margin: 0 0 6px;
    text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600;
}}
.demo-section p.desc {{
    color: var(--text-muted); font-size: 13px; margin: 0 0 16px;
}}
.demo-divider {{
    border: none; border-top: 1px solid var(--border); margin: 48px 0;
}}
.demo-label {{
    display: inline-block;
    background: rgba(138,180,248,0.12);
    color: var(--accent);
    font-size: 11px; font-weight: 600;
    padding: 3px 10px;
    border-radius: 20px;
    margin-bottom: 12px;
    letter-spacing: 0.04em;
}}
</style>
</head>
<body>

<!-- ====== VARIANT A: CURRENT ====== -->
<div class="demo-section">
    <span class="demo-label">ВАРИАНТ A — ТЕКУЩИЙ</span>
    <h2>Текущее свечение (белый radial-gradient)</h2>
    <p class="desc">scale(1.64) + blur(12px) + opacity:1 — создаёт грязное белое пятно на тёмном фоне</p>
</div>

<div class="glow-current">
<header class="site-header">
    <div class="header-container">
        <div class="header-brand">
            <a href="#" class="brand-lockup">
                <span class="brand-mark">
                    <img src="data:image/png;base64,{b64}" alt="Logo" class="brand-logo">
                </span>
                <span class="brand-wordmark">Nopaste</span>
            </a>
        </div>
        <div class="header-actions">
            <button class="btn" style="pointer-events:none">🌙 Theme</button>
            <a href="#" class="btn">📋 My List</a>
        </div>
    </div>
</header>
<main class="container">
    <div class="editor-card">
        <div class="editor-card-header">
            <h2>Create a new paste</h2>
            <p>Your paste will be saved and linked to this browser's history.</p>
        </div>
        <div class="form-container">
            <textarea placeholder="Paste your text, logs, notes, or config here..." readonly>func main() {{
    fmt.Println("Hello, Goldfinch!")
}}</textarea>
            <div class="form-actions">
                <span class="form-hint">Ctrl + Enter to save</span>
                <button class="btn btn-primary">💾 Save Paste</button>
            </div>
        </div>
    </div>
</main>
</div>

<hr class="demo-divider">

<!-- ====== VARIANT B: WARM ====== -->
<div class="demo-section">
    <span class="demo-label">ВАРИАНТ B — ТЁПЛЫЙ ЯНТАРНЫЙ</span>
    <h2>Мягкое тёплое свечение (amber/gold)</h2>
    <p class="desc">Гармонирует с золотыми тонами щегла. Более деликатное, без «белого пятна».</p>
</div>

<div class="glow-warm">
<header class="site-header">
    <div class="header-container">
        <div class="header-brand">
            <a href="#" class="brand-lockup">
                <span class="brand-mark">
                    <img src="data:image/png;base64,{b64}" alt="Logo" class="brand-logo">
                </span>
                <span class="brand-wordmark">Nopaste</span>
            </a>
        </div>
        <div class="header-actions">
            <button class="btn" style="pointer-events:none">🌙 Theme</button>
            <a href="#" class="btn">📋 My List</a>
        </div>
    </div>
</header>
<main class="container">
    <div class="editor-card">
        <div class="editor-card-header">
            <h2>Create a new paste</h2>
            <p>Your paste will be saved and linked to this browser's history.</p>
        </div>
        <div class="form-container">
            <textarea placeholder="Paste your text, logs, notes, or config here..." readonly>func main() {{
    fmt.Println("Hello, Goldfinch!")
}}</textarea>
            <div class="form-actions">
                <span class="form-hint">Ctrl + Enter to save</span>
                <button class="btn btn-primary">💾 Save Paste</button>
            </div>
        </div>
    </div>
</main>
</div>

<hr class="demo-divider">

<!-- ====== VARIANT C: NO GLOW ====== -->
<div class="demo-section">
    <span class="demo-label">ВАРИАНТ C — БЕЗ СВЕЧЕНИЯ</span>
    <h2>Чистый вид — только drop-shadow</h2>
    <p class="desc">Без псевдо-элементов. Аккуратная тень drop-shadow для лёгкого объёма.</p>
</div>

<div class="glow-none">
<header class="site-header">
    <div class="header-container">
        <div class="header-brand">
            <a href="#" class="brand-lockup">
                <span class="brand-mark">
                    <img src="data:image/png;base64,{b64}" alt="Logo" class="brand-logo">
                </span>
                <span class="brand-wordmark">Nopaste</span>
            </a>
        </div>
        <div class="header-actions">
            <button class="btn" style="pointer-events:none">🌙 Theme</button>
            <a href="#" class="btn">📋 My List</a>
        </div>
    </div>
</header>
<main class="container">
    <div class="editor-card">
        <div class="editor-card-header">
            <h2>Create a new paste</h2>
            <p>Your paste will be saved and linked to this browser's history.</p>
        </div>
        <div class="form-container">
            <textarea placeholder="Paste your text, logs, notes, or config here..." readonly>func main() {{
    fmt.Println("Hello, Goldfinch!")
}}</textarea>
            <div class="form-actions">
                <span class="form-hint">Ctrl + Enter to save</span>
                <button class="btn btn-primary">💾 Save Paste</button>
            </div>
        </div>
    </div>
</main>
</div>

<hr class="demo-divider">

<!-- ====== VARIANT D: DUAL RING ====== -->
<div class="demo-section">
    <span class="demo-label">ВАРИАНТ D — ДВОЙНОЕ КОЛЬЦО</span>
    <h2>Красно-золотое двойное свечение</h2>
    <p class="desc">Тонкая красноватая ореоловая подсветка + золотистый внутренний ореол. Перекликается с красной маской и золотыми перьями щегла.</p>
</div>

<div class="glow-dual">
<header class="site-header">
    <div class="header-container">
        <div class="header-brand">
            <a href="#" class="brand-lockup">
                <span class="brand-mark">
                    <img src="data:image/png;base64,{b64}" alt="Logo" class="brand-logo">
                </span>
                <span class="brand-wordmark">Nopaste</span>
            </a>
        </div>
        <div class="header-actions">
            <button class="btn" style="pointer-events:none">🌙 Theme</button>
            <a href="#" class="btn">📋 My List</a>
        </div>
    </div>
</header>
<main class="container">
    <div class="editor-card">
        <div class="editor-card-header">
            <h2>Create a new paste</h2>
            <p>Your paste will be saved and linked to this browser's history.</p>
        </div>
        <div class="form-container">
            <textarea placeholder="Paste your text, logs, notes, or config here..." readonly>func main() {{
    fmt.Println("Hello, Goldfinch!")
}}</textarea>
            <div class="form-actions">
                <span class="form-hint">Ctrl + Enter to save</span>
                <button class="btn btn-primary">💾 Save Paste</button>
            </div>
        </div>
    </div>
</main>
</div>

<footer class="site-footer">
    <p>© 2026 <a href="#">NorD</a> · Nopaste v1.10.1 · <a href="#">Changelog</a></p>
</footer>

</body>
</html>"""

out_path = "/mnt/c/Users/Legion/OneDrive/Projects/nopaste/src/static/images/logo_glow_preview.html"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)
print("Saved preview HTML: {out_path}")
print("Logo base64 length: {len(b64)} chars")
