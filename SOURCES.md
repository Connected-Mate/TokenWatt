# TokenWatt — Sources & Methodology

Every constant used in the conversion pipeline is documented below, with a
reference. If you think any of them is wrong, open an issue or PR — they
live in `equivalences.py` and are overridable via environment variables.

## 1. Tokens → electricity (Wh)

Four constants, one per token type. Default values (overridable):

| Token type       | Wh/token (default) | Env var                        |
|------------------|--------------------|--------------------------------|
| Output           | 0.005              | `TOKENWATT_WH_OUTPUT`          |
| Input            | 0.0003             | `TOKENWATT_WH_INPUT`           |
| Cache creation   | 0.0003             | `TOKENWATT_WH_CACHE_CREATE`    |
| Cache read       | 0.00003            | `TOKENWATT_WH_CACHE_READ`      |

### Why four values?
- **Output tokens** are generated one at a time (autoregressive decoding)
  and are the dominant energy cost.
- **Input tokens** go through a single prefill pass, heavily batched — much
  cheaper per token.
- **Cache-creation tokens** have the same cost profile as input (prefill).
- **Cache-read tokens** are served from a KV cache — roughly one order of
  magnitude cheaper again.

### Calibration
Tuned so that a representative Claude 3 Opus round-trip (≈100 input +
300 output tokens) lands near the ≈4 Wh figure reported by:

- Anthropic Claude energy analysis —
  <https://www.energycosts.co.uk/articles/anthropic-claude-ai-energy/>
- "How Hungry is AI?" benchmark, Ren et al., arXiv:2505.09598 —
  <https://arxiv.org/html/2505.09598v1>
- "From Prompts to Power", arXiv:2511.05597 —
  <https://arxiv.org/html/2511.05597>

Keep in mind that per-model variation is huge (GPT-4.1 nano ≈ 0.45 Wh per
long prompt vs o3 ≈ 39 Wh — a 70× range).

## 2. Electricity → water (L)

Single ratio: **1.8 L of water per kWh** of datacenter energy.

- Default: `L_WATER_PER_KWH = 1.8`
- Env var: `TOKENWATT_L_WATER_PER_KWH`

### Source
Shaolei Ren et al., *"Making AI Less 'Thirsty': Uncovering and Addressing
the Secret Water Footprint of AI Models"*, 2023.
arXiv:2304.03271 — <https://arxiv.org/abs/2304.03271>

The paper derives an on-site water usage effectiveness (WUE) of ≈1.8 L/kWh
across US hyperscale datacenters, covering both:
1. On-site cooling-tower evaporation.
2. Off-site water consumed by the power generation mix.

Efficient datacenters can go below 0.5 L/kWh; less-efficient / warmer
locations go well above 3 L/kWh. 1.8 is a defensible middle.

## 3. Electricity comparisons (Wh per use)

All values from French energy-supplier guides and EU class-A datasheets,
rounded for readability.

| Appliance              | Wh   | Source |
|------------------------|------|--------|
| LED hour (10 W)        | 10   | 10 W × 1 h (nameplate) |
| Phone charge           | 15   | iPhone-class battery capacity |
| MacBook hour           | 30   | Charging load, Apple specs |
| Toast (1 slice)        | 40   | 1200 W × 2 min |
| Kettle cup (250 mL)    | 100  | 90 °C rise, ideal efficiency |
| Microwave (5 min)      | 150  | 1800 W × 5 min |
| Airfryer run (20 min)  | 500  | 1500 W × 20 min |
| Washing cycle          | 800  | 40 °C, EU class A |
| Fridge day             | 800  | Class-A fridge-freezer, 24 h |
| Pizza oven bake        | 900  | 200 °C, 15 min |
| Induction meal         | 1500 | 3 kW burner × 30 min |
| Home AC hour           | 2000 | Split unit, moderate load |
| EV km                  | 180  | Industry average Wh/km |

References:
- Alpiq consumption guide — <https://particuliers.alpiq.fr/guide-energie/economie-energie/consommation-electrique-petit-electromenager>
- Hellowatt airfryer — <https://www.hellowatt.fr/suivi-consommation-energie/consommation-electrique/consommation-air-fryer>
- Moulinex airfryer — <https://www.moulinex.fr/appareils-de-cuisson/friteuses-sans-huile/consommation-air-fryer>
- Otovo appliance table — <https://www.otovo.fr/blog/energie/tableau-consommation-electromenagers/>
- mon-club-elec toaster — <https://www.mon-club-elec.fr/quelle-est-la-consommation-electrique-dun-grille-pain/>

## 4. Water comparisons (L per use)

Typical household usage figures, French/EU context.

| Item              | Litres | Source |
|-------------------|--------|--------|
| Glass of water    | 0.25   | 250 mL standard glass |
| Water bottle      | 0.5    | 500 mL standard PET |
| Kettle fill       | 1.7    | Capacity of a full kettle |
| Hand wash         | 2      | 20 s at ~6 L/min tap |
| Shampoo / rinse   | 5      | ADEME household profile |
| Toilet flush      | 6      | Dual-flush average |
| Cooking batch     | 10     | Pasta + rinse |
| Shower (5 min)    | 80     | 16 L/min mixer |
| Bathtub           | 150    | Typical fill |
| Tree (daily need) | 40     | Mature urban tree |
| Pool refill 1 m³  | 1000   | By definition |

References:
- ADEME household water guide —
  <https://agirpourlatransition.ademe.fr/particuliers/maison/consommer-mieux-gaspiller-moins/bien-utiliser-leau>
- Centre d'Information sur l'Eau —
  <https://www.cieau.com/>

## 5. Pick logic

`pick_best(value, units)` walks candidate units from biggest to smallest
and returns the first whose count ≥ 0.2. This avoids the "47 water
bottles" problem — if you have 21 L of water, we report "a quarter of a
shower", not 42 bottles.

Counts under 1 are rendered as **pie circles**: ◔ ¼, ◑ ½, ◕ ¾, ● ≈1.
Counts between 1 and 10 are rendered as up to 10 filled circles with a
final wedge. Counts over 10 collapse to `●●●●●●●●●●  × N`.
