#!/usr/bin/env python3
"""TokenWatt - Claude Code token usage in menu bar, compared to toasters.

Reads ~/.claude/projects/**/*.jsonl, aggregates token usage, converts to
energy and shows household-appliance equivalents in the macOS menu bar.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import rumps

from equivalences import format_equivalents, totals_to_wh


CLAUDE_DIR = Path.home() / ".claude" / "projects"
REFRESH_SECONDS = 30


def _iter_jsonl_files() -> list[Path]:
    if not CLAUDE_DIR.exists():
        return []
    return list(CLAUDE_DIR.rglob("*.jsonl"))


def _parse_usage(line: str) -> tuple[int, int, int, int, str | None] | None:
    try:
        d = json.loads(line)
    except json.JSONDecodeError:
        return None
    usage = d.get("message", {}).get("usage") if isinstance(d.get("message"), dict) else None
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


def _fmt(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)


class TokenWattApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("TokenWatt", title="TW --", quit_button=None)
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
                "Mesure ta consommation de tokens Claude Code et compare-la a "
                "des appareils du quotidien (grille-pain, airfryer, machine a "
                "laver, bouilloire, LED).\n\n"
                "Open source - MIT License.\n"
                "Patrick Code - powered by TGV Europe."
            ),
        )

    def _refresh(self) -> None:
        try:
            stats = collect_stats()
        except Exception as exc:  # noqa: BLE001
            self.title = "TW ERR"
            print(f"TokenWatt error: {exc}")
            return

        today_tokens = stats["today_tokens"]
        today_wh = stats["today_wh"]
        self.title = f"TW {_fmt(today_tokens)} ({today_wh:.1f}Wh)"
        self._rebuild_menu(stats)

    def _rebuild_menu(self, stats: dict) -> None:
        self.menu.clear()

        def token_line(totals: dict) -> str:
            cache = totals["cache_create"] + totals["cache_read"]
            return (
                f"  tokens: {_fmt(sum(totals.values()))}   "
                f"(in {_fmt(totals['input'])} / "
                f"out {_fmt(totals['output'])} / "
                f"cache {_fmt(cache)})"
            )

        items: list = [
            rumps.MenuItem("Aujourd'hui", callback=None),
            rumps.MenuItem(token_line(stats["today_totals"]), callback=None),
            rumps.MenuItem(f"  energie: {stats['today_wh']:.2f} Wh", callback=None),
            None,
        ]
        for line in format_equivalents(stats["today_wh"]):
            items.append(rumps.MenuItem(f"  {line}", callback=None))

        items += [
            None,
            rumps.MenuItem("Total (historique)", callback=None),
            rumps.MenuItem(token_line(stats["totals"]), callback=None),
            rumps.MenuItem(
                f"  energie: {stats['total_wh']:.2f} Wh "
                f"({stats['total_wh']/1000:.3f} kWh)",
                callback=None,
            ),
            None,
        ]
        for line in format_equivalents(stats["total_wh"], prefix="historique"):
            items.append(rumps.MenuItem(f"  {line}", callback=None))

        items += [
            None,
            rumps.MenuItem("Refresh", callback=self._on_refresh),
            rumps.MenuItem("Open ~/.claude/projects", callback=self._on_open_dir),
            None,
            rumps.MenuItem("About", callback=self._on_about),
            rumps.MenuItem("Quit", callback=rumps.quit_application),
        ]
        self.menu = items


if __name__ == "__main__":
    TokenWattApp().run()
