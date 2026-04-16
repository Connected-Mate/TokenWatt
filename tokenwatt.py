#!/usr/bin/env python3
"""TokenWatt - Claude Code tokens shown as everyday electricity
and water equivalents, in your macOS menu bar.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import rumps

from equivalences import (
    compact_title,
    electricity_lines,
    fmt_litres,
    fmt_wh,
    totals_to_wh,
    water_lines,
    wh_to_litres,
)


CLAUDE_DIR = Path.home() / ".claude" / "projects"
PROJECT_DIR = Path(__file__).resolve().parent
SOURCES_PATH = PROJECT_DIR / "SOURCES.md"
GITHUB_URL = "https://github.com/Connected-Mate/TokenWatt"
REFRESH_SECONDS = 30


def _iter_jsonl_files() -> list[Path]:
    if not CLAUDE_DIR.exists():
        return []
    return list(CLAUDE_DIR.rglob("*.jsonl"))


def _parse_usage(line_str: str):
    try:
        d = json.loads(line_str)
    except json.JSONDecodeError:
        return None
    msg = d.get("message")
    usage = msg.get("usage") if isinstance(msg, dict) else None
    if not usage:
        return None
    return (
        int(usage.get("input_tokens") or 0),
        int(usage.get("output_tokens") or 0),
        int(usage.get("cache_creation_input_tokens") or 0),
        int(usage.get("cache_read_input_tokens") or 0),
        d.get("timestamp"),
    )


def collect_stats() -> dict:
    today = datetime.now(timezone.utc).date()
    totals = {"input": 0, "output": 0, "cache_create": 0, "cache_read": 0}
    today_totals = {"input": 0, "output": 0, "cache_create": 0, "cache_read": 0}

    for path in _iter_jsonl_files():
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as fh:
                for raw in fh:
                    parsed = _parse_usage(raw)
                    if parsed is None:
                        continue
                    inp, out, cc, cr, ts = parsed
                    totals["input"] += inp
                    totals["output"] += out
                    totals["cache_create"] += cc
                    totals["cache_read"] += cr
                    if ts:
                        try:
                            day = datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
                        except ValueError:
                            continue
                        if day == today:
                            today_totals["input"] += inp
                            today_totals["output"] += out
                            today_totals["cache_create"] += cc
                            today_totals["cache_read"] += cr
        except OSError:
            continue

    return {
        "today_wh": totals_to_wh(today_totals),
        "total_wh": totals_to_wh(totals),
    }


def _item(text: str) -> rumps.MenuItem:
    return rumps.MenuItem(text, callback=None)


class TokenWattApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("TokenWatt", title="TW …", quit_button=None)
        self._refresh()

    @rumps.timer(REFRESH_SECONDS)
    def _tick(self, _sender) -> None:
        self._refresh()

    def _on_refresh(self, _sender) -> None:
        self._refresh()

    def _on_open_sources(self, _sender) -> None:
        if SOURCES_PATH.exists():
            subprocess.Popen(["open", str(SOURCES_PATH)])
        else:
            subprocess.Popen(["open", f"{GITHUB_URL}/blob/main/SOURCES.md"])

    def _on_open_github(self, _sender) -> None:
        subprocess.Popen(["open", GITHUB_URL])

    def _on_about(self, _sender) -> None:
        try:
            choice = rumps.alert(
                title="TokenWatt",
                message=(
                    "Your Claude Code tokens, shown as everyday electricity "
                    "and water.\n\n"
                    "Reads ~/.claude/projects/*.jsonl locally.\n"
                    "No telemetry. No network calls.\n\n"
                    "Every constant is peer-reviewed or from an official "
                    "source — see Sources & methodology.\n\n"
                    f"{GITHUB_URL}"
                ),
                ok="Open sources",
                cancel="Close",
            )
            if choice == 1:
                self._on_open_sources(_sender)
        except Exception as exc:  # noqa: BLE001
            print(f"About dialog failed: {exc}")
            self._on_open_sources(_sender)

    def _refresh(self) -> None:
        try:
            stats = collect_stats()
        except Exception as exc:  # noqa: BLE001
            self.title = "TW ERR"
            print(f"TokenWatt error: {exc}")
            return

        self.title = compact_title(stats["today_wh"]) if stats["today_wh"] > 0 else "🍟0  🚿0"
        self._rebuild_menu(stats)

    def _block(self, label: str, wh: float) -> list:
        litres = wh_to_litres(wh)
        rows = [
            _item(label),
            None,
            _item(f"   ⚡  {fmt_wh(wh)}"),
        ]
        for txt in electricity_lines(wh):
            rows.append(_item(f"      {txt}"))
        rows.append(None)
        rows.append(_item(f"   💧  {fmt_litres(litres)}"))
        for txt in water_lines(litres):
            rows.append(_item(f"      {txt}"))
        return rows

    def _rebuild_menu(self, stats: dict) -> None:
        self.menu.clear()
        items: list = self._block("📅  Today", stats["today_wh"])
        items.append(None)
        items += self._block("📈  All time", stats["total_wh"])
        items += [
            None,
            rumps.MenuItem("📖  Sources & methodology", callback=self._on_open_sources),
            rumps.MenuItem("🐙  GitHub", callback=self._on_open_github),
            None,
            rumps.MenuItem("↻  Refresh", callback=self._on_refresh),
            rumps.MenuItem("ⓘ  About", callback=self._on_about),
            rumps.MenuItem("✕  Quit", callback=rumps.quit_application),
        ]
        self.menu = items


if __name__ == "__main__":
    TokenWattApp().run()
