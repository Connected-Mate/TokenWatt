"""Tiny HTML view for TokenWatt Sources & About.

A single, compact page — one card, readable, no dashboard, no charts.
Written to /tmp/ and opened with `open`.
"""

from __future__ import annotations

from pathlib import Path


TMP_PATH = Path("/tmp/tokenwatt_sources.html")


_CSS = """
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Inter", system-ui, sans-serif;
    background: #f4f4f5;
    color: #18181b;
    line-height: 1.6;
    padding: 3rem 1.5rem;
    -webkit-font-smoothing: antialiased;
  }
  @media (prefers-color-scheme: dark) {
    body { background: #0a0a0b; color: #f4f4f5; }
    .card { background: #17171a !important; border-color: #27272a !important; }
    .muted { color: #9ca3af !important; }
    a { color: #93c5fd !important; }
    code { background: #27272a !important; }
  }
  .card {
    max-width: 520px;
    margin: 0 auto;
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 1.75rem 1.75rem 1.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 10px 40px rgba(0,0,0,0.06);
  }
  header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.25rem; }
  .logo {
    width: 36px; height: 36px; border-radius: 9px;
    background: linear-gradient(135deg, #60a5fa, #a78bfa);
    display: grid; place-items: center; font-size: 1.1rem;
  }
  h1 { font-size: 1.1rem; font-weight: 600; letter-spacing: -0.01em; }
  .muted { color: #6b7280; font-size: 0.88rem; }
  h2 {
    font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em;
    color: #6b7280; font-weight: 600; margin: 1.5rem 0 0.6rem;
  }
  p { font-size: 0.92rem; margin-bottom: 0.5rem; }
  ul { list-style: none; padding: 0; }
  li { font-size: 0.9rem; padding: 0.25rem 0; }
  li::before { content: "·"; color: #9ca3af; margin-right: 0.5rem; }
  a { color: #2563eb; text-decoration: none; }
  a:hover { text-decoration: underline; }
  code {
    background: #f4f4f5; padding: 0.1rem 0.4rem; border-radius: 4px;
    font-family: "SF Mono", Menlo, monospace; font-size: 0.82em;
  }
  table { width: 100%; font-size: 0.88rem; border-collapse: collapse; margin-top: 0.4rem; }
  td { padding: 0.3rem 0; }
  td.num { text-align: right; font-variant-numeric: tabular-nums; color: #6b7280; }
  footer { margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #e5e7eb; font-size: 0.8rem; color: #6b7280; text-align: center; }
  @media (prefers-color-scheme: dark) { footer { border-color: #27272a; } }
"""


def _build_html(
    wh_output: float,
    wh_input: float,
    wh_cache_create: float,
    wh_cache_read: float,
    l_per_kwh: float,
) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>TokenWatt — Sources</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{_CSS}</style>
</head>
<body>
<div class="card">
  <header>
    <div class="logo">⚡</div>
    <div>
      <h1>TokenWatt</h1>
      <div class="muted">Sources & methodology</div>
    </div>
  </header>

  <p>Claude Code tokens, shown as electricity and water. Every constant
  below is peer-reviewed or from an official source.</p>

  <h2>⚡ Electricity per token</h2>
  <table>
    <tr><td>Output</td><td class="num"><code>{wh_output} Wh</code></td></tr>
    <tr><td>Input</td><td class="num"><code>{wh_input} Wh</code></td></tr>
    <tr><td>Cache creation</td><td class="num"><code>{wh_cache_create} Wh</code></td></tr>
    <tr><td>Cache read</td><td class="num"><code>{wh_cache_read} Wh</code></td></tr>
  </table>
  <p class="muted" style="margin-top: 0.6rem;">
    Calibrated so a Claude 3 Opus 400-token round-trip ≈ 4 Wh.
  </p>
  <ul style="margin-top: 0.4rem;">
    <li><a href="https://arxiv.org/abs/2505.09598">arXiv:2505.09598 — How Hungry is AI?</a></li>
    <li><a href="https://arxiv.org/abs/2204.05149">arXiv:2204.05149 — Patterson et al., Carbon footprint of ML</a></li>
    <li><a href="https://www.iea.org/reports/energy-and-ai">IEA 2025 — Energy and AI</a></li>
  </ul>

  <h2>💧 Water per kWh</h2>
  <p><code>{l_per_kwh} L / kWh</code> — datacenter WUE
  (cooling + upstream power generation).</p>
  <ul>
    <li><a href="https://arxiv.org/abs/2304.03271">arXiv:2304.03271 — Ren et al., Making AI Less Thirsty</a></li>
  </ul>

  <h2>🏠 Everyday units</h2>
  <ul>
    <li>🍞 Toast 40 Wh · 🍟 Airfryer 500 Wh · 🧺 Washing cycle 800 Wh · 🔥 Induction meal 1500 Wh</li>
    <li>🍶 Bottle 0.5 L · 🍳 Pot 2 L · 🚿 Shower 80 L · 🛁 Bathtub 150 L</li>
  </ul>
  <ul style="margin-top: 0.4rem;">
    <li><a href="https://agirpourlatransition.ademe.fr/particuliers/maison/electromenager">ADEME — household appliances</a></li>
    <li><a href="https://energy.ec.europa.eu/topics/energy-efficiency/energy-label-and-ecodesign_en">EU Commission — energy label</a></li>
    <li><a href="https://www.energystar.gov/products">US DOE Energy Star</a></li>
  </ul>

  <footer>
    <a href="https://github.com/Connected-Mate/TokenWatt">github.com/Connected-Mate/TokenWatt</a> · MIT
  </footer>
</div>
</body>
</html>
"""


def write_sources_html() -> Path:
    from equivalences import (
        L_WATER_PER_KWH,
        WH_CACHE_CREATE,
        WH_CACHE_READ,
        WH_INPUT,
        WH_OUTPUT,
    )
    TMP_PATH.write_text(
        _build_html(
            WH_OUTPUT,
            WH_INPUT,
            WH_CACHE_CREATE,
            WH_CACHE_READ,
            L_WATER_PER_KWH,
        ),
        encoding="utf-8",
    )
    return TMP_PATH
