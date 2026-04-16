# TokenWatt

> How many toasters is your Claude Code session worth?

TokenWatt is a tiny **macOS menu-bar app** that reads your local Claude Code
session logs, sums up the tokens you've burned, converts the total to
watt-hours, and tells you **how many toasts, airfryer runs, washing-machine
cycles, MacBook-hours or LED-hours** that represents.

It runs 100% locally. No telemetry, no API calls, no account needed.

```
TW 312.4k (3.12 Wh)          <-- in your menu bar
  ----------------------------------
  Aujourd'hui
    tokens: 312.4k (in 42k / out 28k / cache 242k)
    energie: 3.12 Wh
    [toast]  0.08 x toast grille-pain
    [tea]    0.03 x tasses bouilloire
    [fry]    0.01 x cycles airfryer 20 min
    [wash]   0.00 x cycles machine a laver
  ...
```

## Install

Requires macOS + Python 3.10+.

```bash
cd ~/Documents/TokenWatt
./run.sh
```

The first run creates a `.venv`, installs [`rumps`](https://github.com/jaredks/rumps),
and launches the menu-bar icon (`TW ...`). Click it to see the breakdown.

To launch at login, add `run.sh` as a Login Item in **System Settings >
General > Login Items**.

### Install via Claude Code (one-shot prompt)

Open Claude Code in any directory and paste this:

> Clone https://github.com/Connected-Mate/TokenWatt into `~/Documents/TokenWatt`
> (or `git pull` if it already exists), then run `./run.sh` in the
> background so the TokenWatt icon appears in my macOS menu bar.
> Python 3.10+ must be available. The script creates its own `.venv` and
> installs `rumps` on first run. Confirm the menu-bar icon is visible and
> report the token/Wh summary it shows.

Claude Code will handle the clone, venv bootstrap, and launch without any
further input.

## What it reads

TokenWatt walks `~/.claude/projects/**/*.jsonl` — the transcript files that
Claude Code writes for every session — and sums the `message.usage` blocks:

- `input_tokens`
- `output_tokens`
- `cache_creation_input_tokens`
- `cache_read_input_tokens`

Nothing is uploaded. Nothing is written back. The app is read-only.

## How the energy numbers work

Energy per token is a moving target, but **not all tokens cost the same**.
TokenWatt weighs four token types separately:

| Token type       | Default Wh/token | Why |
|------------------|------------------|-----|
| output           | 0.005            | Autoregressive generation — the expensive part |
| input            | 0.0003           | Single prefill pass, batched |
| cache creation   | 0.0003           | Same cost profile as input |
| cache read       | 0.00003          | Served from KV cache — roughly 10x cheaper |

Calibrated so that a ~400-token Claude 3 Opus round-trip (~100 in, 300 out)
lands near the published **~4 Wh** figure
([EnergyCosts.co.uk](https://www.energycosts.co.uk/articles/anthropic-claude-ai-energy/),
[arxiv:2505.09598](https://arxiv.org/html/2505.09598v1)).
For reference, GPT-4.1 nano is ~70x cheaper than o3 per prompt — model
choice dominates everything else.

Override any of the four via env vars:

```bash
TOKENWATT_WH_OUTPUT=0.003 \
TOKENWATT_WH_INPUT=0.0002 \
TOKENWATT_WH_CACHE_CREATE=0.0002 \
TOKENWATT_WH_CACHE_READ=0.00002 \
./run.sh
```

### Appliance reference values (Wh per use)

| Appliance              | Wh  | Basis |
|------------------------|-----|-------|
| Toast (1 slice)        | 40  | 1200 W x 2 min |
| Kettle (1 cup 250 mL)  | 100 | 90 degC heat |
| Microwave (5 min)      | 150 | 1800 W x 5 min |
| Airfryer (20 min)      | 500 | 1500 W x 20 min |
| Washing machine (cycle)| 800 | 40 degC, EU class A |
| LED bulb (1 h)         | 10  | 10 W x 1 h |
| MacBook (1 h)          | 30  | average charging load |
| Smartphone (1 charge)  | 15  | iPhone-class battery |

Sources: [Alpiq](https://particuliers.alpiq.fr/guide-energie/economie-energie/consommation-electrique-petit-electromenager),
[Hellowatt](https://www.hellowatt.fr/suivi-consommation-energie/consommation-electrique/consommation-air-fryer),
[Moulinex](https://www.moulinex.fr/appareils-de-cuisson/friteuses-sans-huile/consommation-air-fryer),
[Otovo](https://www.otovo.fr/blog/energie/tableau-consommation-electromenagers/),
[mon-club-elec](https://www.mon-club-elec.fr/quelle-est-la-consommation-electrique-dun-grille-pain/).

Edit `equivalences.py` to tune any of them — they're all in one dict.

## Architecture

```
tokenwatt.py       # rumps App, menu-bar UI, 30 s refresh timer
equivalences.py    # tokens -> Wh -> appliance-uses
requirements.txt   # rumps
run.sh             # bootstrap venv + launch
```

No database, no config file. State = whatever is in `~/.claude/projects/`.

## Why

Because "I spent 1.2 M tokens today" is a meaningless number, and "I spent
the energy of 30 toasts" is not. Making the cost visible — in kitchen units
— is the point.

## Prior art (go check these out too)

- [`ryoppippi/ccusage`](https://github.com/ryoppippi/ccusage) — CLI, the
  reference for parsing Claude Code JSONL.
- [`tddworks/ClaudeBar`](https://github.com/tddworks/ClaudeBar) — Swift
  menu-bar app for quota tracking.
- [`hamed-elfayome/Claude-Usage-Tracker`](https://github.com/hamed-elfayome/Claude-Usage-Tracker) —
  SwiftUI, native, focused on usage limits.
- [TokenCap](https://www.tokencap.app/), [Claudoscope](https://claudoscope.com/),
  [ClaudeUsageBar](https://www.claudeusagebar.com/) — richer UIs if you want
  session windows, notarized binaries, etc.

TokenWatt's differentiator: **the kitchen-appliance unit system**.

## License

MIT. See `LICENSE`.

---

Built with Patrick Code — powered by TGV Europe.
