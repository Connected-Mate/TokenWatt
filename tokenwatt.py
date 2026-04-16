#!/usr/bin/env python3
"""TokenWatt - Claude Code token usage in the macOS menu bar,
expressed in household-appliance units, euros, and grams of CO2.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import rumps

from equivalences import (
    fmt_co2,
    fmt_eur,
    headline_bar,
    headline_compact,
    headline_lines,
    headline_pick,
    other_lines,
    sparkline,
    totals_to_wh,
)


CLAUDE_DIR = Path.home() / ".claude" / "projects"
REFRESH_SECONDS = 30
SPARKLINE_DAYS = 7


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


def _project_name(path: Path) -> str:
    """~/.claude/projects/-Users-bob-Desktop-MYAPP/.../x.jsonl -> MYAPP"""
    try:
        rel = path.relative_to(CLAUDE_DIR)
    except ValueError:
        return "unknown"
    top = rel.parts[0] if rel.parts else "unknown"
    if top.startswith("-"):
        top = top.lstrip("-").split("-")[-1]
    return top or "unknown"


def _empty_bucket() -> dict:
    return {"input": 0, "output": 0, "cache_create": 0, "cache_read": 0}


def _add(a: dict, inp: int, out: int, cc: int, cr: int) -> None:
    a["input"] += inp
    a["output"] += out
    a["cache_create"] += cc
    a["cache_read"] += cr


def collect_stats() -> dict:
    today = datetime.now(timezone.utc).date()
    totals = _empty_bucket()
    today_totals = _empty_bucket()
    by_day: dict = defaultdict(_empty_bucket)
    by_project_today: dict = defaultdict(_empty_bucket)

    for path in _iter_jsonl_files():
        project = _project_name(path)
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    parsed = _parse_usage(line)
                    if parsed is None:
                        continue
                    inp, out, cc, cr, ts = parsed
                    _add(totals, inp, out, cc, cr)
                    if ts:
                        try:
                            day = datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
                        except ValueError:
                            continue
                        _add(by_day[day], inp, out, cc, cr)
                        if day == today:
                            _add(today_totals, inp, out, cc, cr)
                            _add(by_project_today[project], inp, out, cc, cr)
        except OSError:
            continue

    last_days = [today - timedelta(days=i) for i in reversed(range(SPARKLINE_DAYS))]
    week_wh = [totals_to_wh(by_day.get(d, _empty_bucket())) for d in last_days]

    top_projects = sorted(
        by_project_today.items(),
        key=lambda kv: totals_to_wh(kv[1]),
        reverse=True,
    )[:3]

    return {
        "totals": totals,
        "today_totals": today_totals,
        "total_tokens": sum(totals.values()),
        "today_tokens": sum(today_totals.values()),
        "total_wh": totals_to_wh(totals),
        "today_wh": totals_to_wh(today_totals),
        "week_wh": week_wh,
        "week_labels": [d.strftime("%a") for d in last_days],
        "top_projects": [(name, totals_to_wh(b)) for name, b in top_projects],
    }


def _fmt_tokens(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.2f}B"
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
                "watt-hours (per-type weights), and compared to toasts,\n"
                "airfryer runs, washing cycles, phone charges, plus € cost\n"
                "and g CO₂ equivalent on the French grid.\n\n"
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
        self.title = headline_compact(today_wh) if today_wh > 0 else "🍞 0"
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
            _header("📅  Today"),
            _header(f"   {today_hero}"),
            _header(f"   {headline_bar(today_wh)}") if today_wh > 0 else _header("   —"),
            None,
            _header(f"   🪙 {_fmt_tokens(today_tokens)} tokens"),
            _header(f"   ⚡ {_fmt_wh(today_wh)}"),
            _header(f"   💶 {fmt_eur(today_wh)}"),
            _header(f"   🌱 {fmt_co2(today_wh)}"),
            None,
        ]
        for line in headline_lines(today_wh):
            items.append(_header(f"   {line}"))

        more_today = rumps.MenuItem("   More equivalents ▸")
        for line in other_lines(today_wh):
            more_today.add(rumps.MenuItem(line, callback=None))
        items.append(more_today)

        if stats["top_projects"]:
            items += [None, _header("   🏆 Top projects today")]
            for name, wh in stats["top_projects"]:
                items.append(_header(f"      · {name} — {_fmt_wh(wh)} · {fmt_eur(wh)}"))

        week = stats["week_wh"]
        if any(v > 0 for v in week):
            items += [
                None,
                _header("   📊 Last 7 days"),
                _header(f"      {sparkline(week)}  (peak {_fmt_wh(max(week))})"),
                _header(f"      {' '.join(stats['week_labels'])}"),
            ]

        items += [
            None,
            _header("📈  All time"),
            _header(f"   {total_hero}"),
            None,
            _header(f"   🪙 {_fmt_tokens(total_tokens)} tokens"),
            _header(f"   ⚡ {_fmt_wh(total_wh)}"),
            _header(f"   💶 {fmt_eur(total_wh)}"),
            _header(f"   🌱 {fmt_co2(total_wh)}"),
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
