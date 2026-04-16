#!/usr/bin/env python3
"""TokenWatt - Claude Code token usage in the macOS menu bar,
expressed in household-appliance units.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import rumps

from equivalences import (
    headline_lines,
    headline_pick,
    other_lines,
    totals_to_wh,
)


CLAUDE_DIR = Path.home() / ".claude" / "projects"
REFRESH_SECONDS = 30


def _iter_jsonl_files() -> list[Path]:
    if not CLAUDE_DIR.exists():
        return []
    return list(CLAUDE_DIR.rglob("*.jsonl"))


def _parse_usage(line: str):
    try:
        d = json.loads(line)
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
                for line in fh:
                    parsed = _parse_usage(line)
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
        "totals": totals,
        "today_totals": today_totals,
        "total_tokens": sum(totals.values()),
        "today_tokens": sum(today_totals.values()),
        "total_wh": totals_to_wh(totals),
        "today_wh": totals_to_wh(today_totals),
    }


def _fmt_tokens(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)


def _fmt_wh(wh: float) -> str:
    if wh >= 1000:
        return f"{wh/1000:.2f} kWh"
    return f"{wh:.1f} Wh"


def _header(text: str) -> rumps.MenuItem:
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

    def _on_open_dir(self, _sender) -> None:
        os.system(f'open "{CLAUDE_DIR}"')

    def _on_about(self, _sender) -> None:
        rumps.alert(
            title="TokenWatt",
            message=(
                "Your Claude Code token usage, in kitchen-appliance units.\n\n"
                "Tokens are read from ~/.claude/projects/*.jsonl, converted to\n"
                "watt-hours using per-type weights, and compared to toasts,\n"
                "airfryer runs, washing cycles, phone charges, and more.\n\n"
                "Open source — MIT License.\n"
                "github.com/Connected-Mate/TokenWatt"
            ),
        )

    def _refresh(self) -> None:
        try:
            stats = collect_stats()
        except Exception as exc:  # noqa: BLE001
            self.title = "TW ERR"
            print(f"TokenWatt error: {exc}")
            return

        today_wh = stats["today_wh"]
        _, headline, _ = headline_pick(today_wh)
        self.title = headline if today_wh > 0 else "TW idle"
        self._rebuild_menu(stats)

    def _rebuild_menu(self, stats: dict) -> None:
        self.menu.clear()

        today_tokens = stats["today_tokens"]
        today_wh = stats["today_wh"]
        total_tokens = stats["total_tokens"]
        total_wh = stats["total_wh"]

        _, today_hero, _ = headline_pick(today_wh)
        _, total_hero, _ = headline_pick(total_wh)

        items: list = [
            _header(f"📅  Today  —  {_fmt_tokens(today_tokens)} tokens · {_fmt_wh(today_wh)}"),
            _header(f"   {today_hero}"),
            None,
        ]
        for line in headline_lines(today_wh):
            items.append(_header(f"   {line}"))

        more_today = rumps.MenuItem("   More equivalents ▸")
        for line in other_lines(today_wh):
            more_today.add(rumps.MenuItem(line, callback=None))
        items.append(more_today)

        items += [
            None,
            _header(f"📈  All time  —  {_fmt_tokens(total_tokens)} tokens · {_fmt_wh(total_wh)}"),
            _header(f"   {total_hero}"),
            None,
        ]
        for line in headline_lines(total_wh):
            items.append(_header(f"   {line}"))

        more_total = rumps.MenuItem("   More equivalents ▸")
        for line in other_lines(total_wh):
            more_total.add(rumps.MenuItem(line, callback=None))
        items.append(more_total)

        items += [
            None,
            rumps.MenuItem("↻  Refresh", callback=self._on_refresh),
            rumps.MenuItem("📂  Open Claude logs folder", callback=self._on_open_dir),
            None,
            rumps.MenuItem("ⓘ  About TokenWatt", callback=self._on_about),
            rumps.MenuItem("✕  Quit", callback=rumps.quit_application),
        ]
        self.menu = items


if __name__ == "__main__":
    TokenWattApp().run()
