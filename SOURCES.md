# TokenWatt — Sources & Methodology

Every constant TokenWatt uses is listed below, with a peer-reviewed paper,
official agency report, or manufacturer spec as its source. If any figure
looks wrong, open an issue — they are all one-line edits in
`equivalences.py` and all overridable via environment variables.

---

## 1. Tokens → electricity (Wh)

Four constants (Wh per token), one per token type:

| Token type     | Default (Wh/token) | Env var                     |
|----------------|--------------------|-----------------------------|
| Output         | 0.005              | `TOKENWATT_WH_OUTPUT`       |
| Input          | 0.0003             | `TOKENWATT_WH_INPUT`        |
| Cache creation | 0.0003             | `TOKENWATT_WH_CACHE_CREATE` |
| Cache read     | 0.00003            | `TOKENWATT_WH_CACHE_READ`   |

### Why four values?
- **Output tokens** are generated sequentially (autoregressive decoding) —
  the dominant cost.
- **Input** and **cache-creation** tokens go through a single, heavily
  batched prefill pass — roughly one order of magnitude cheaper per token.
- **Cache-read tokens** are served from a KV cache — another order of
  magnitude cheaper again.

### Calibration
Tuned so a representative Claude 3 Opus round-trip (~100 input + 300 output
tokens) lands near the ~4 Wh figure reported by multiple independent
studies.

### Primary sources
- **Ren, Tomlinson, Chien et al. (2023)** — *Making AI Less 'Thirsty':
  Uncovering and Addressing the Secret Water Footprint of AI Models.*
  arXiv:2304.03271. <https://arxiv.org/abs/2304.03271> — also covers the
  energy side with per-query Wh estimates for GPT-3.
- **Jegham, Elango, Kasiviswanathan et al. (2025)** — *How Hungry is AI?
  Benchmarking Energy, Water, and Carbon Footprint of LLM Inference.*
  arXiv:2505.09598. <https://arxiv.org/abs/2505.09598> — per-model Wh/token
  benchmarks across GPT-4, Claude, Gemini, o-series.
- **Patterson, Gonzalez, Le et al. (2022)** — *The Carbon Footprint of
  Machine Learning Training Will Plateau, Then Shrink.* IEEE Computer
  55(7): 18–28. <https://arxiv.org/abs/2204.05149>
- **IEA (2024)** — *Electricity 2024: Analysis and forecast to 2026*,
  chapter on datacentre electricity consumption.
  <https://www.iea.org/reports/electricity-2024>
- **IEA (2025)** — *Energy and AI* special report.
  <https://www.iea.org/reports/energy-and-ai>

---

## 2. Electricity → water (L per kWh)

Single ratio: **1.8 L of water per kWh** of datacenter energy.

| Constant           | Default | Env var                       |
|--------------------|---------|-------------------------------|
| L water per kWh    | 1.8     | `TOKENWATT_L_WATER_PER_KWH`   |

Derived in Ren et al. (2023) as a US-average on-site + off-site WUE
(water usage effectiveness), covering:

1. Cooling-tower evaporation at the datacenter.
2. Water consumed by the upstream power-generation mix.

Efficient sites (cool climates, closed-loop cooling) can hit < 0.5 L/kWh.
Hot-climate sites can exceed 3 L/kWh. 1.8 is a defensible middle.

**Source:** Ren et al. 2023, arXiv:2304.03271 —
<https://arxiv.org/abs/2304.03271>

---

## 3. Featured electricity units (Wh per use)

Each is deliberately concrete and household-scale. Values are rounded for
legibility.

| Unit              | Wh   | Basis                                   |
|-------------------|------|-----------------------------------------|
| 🍞 Toast          | 40   | 1200 W toaster × 2 min                  |
| 🍟 Airfryer run   | 500  | 1500 W × 20 min (500 g frozen fries)    |
| 🧺 Washing cycle  | 800  | 40 °C cotton programme, EU class A      |
| 🔥 Induction meal | 1500 | 3 kW burner × 30 min                    |

### Sources
- **ADEME** — French Agency for Ecological Transition, household appliance
  consumption guide.
  <https://agirpourlatransition.ademe.fr/particuliers/maison/electromenager>
- **EU Commission** — Energy label regulations defining class A references
  for washers and ovens. <https://energy.ec.europa.eu/topics/energy-efficiency/energy-label-and-ecodesign_en>
- **US DOE / Energy Star** — appliance consumption benchmarks.
  <https://www.energystar.gov/products>

---

## 4. Featured water units (L per use)

| Unit              | Litres | Basis                                |
|-------------------|--------|--------------------------------------|
| 🍶 Water bottle   | 0.5    | Standard 500 mL PET bottle           |
| 🍳 Cooking pot    | 2      | Typical pasta / stock pot fill       |
| 🚿 Shower         | 80     | 5 min × 16 L/min mixer               |
| 🛁 Bathtub        | 150    | Typical fill                         |

### Sources
- **ADEME** — household water-use guide.
  <https://agirpourlatransition.ademe.fr/particuliers/maison/consommer-mieux-gaspiller-moins/bien-utiliser-leau>
- **Centre d'Information sur l'Eau** (French water industry).
  <https://www.cieau.com/>
- **OECD (2022)** — *Water, freshwater and marine environment statistics.*
  <https://www.oecd.org/en/topics/sub-issues/water-management-and-protection.html>

---

## 5. Display logic

- Each refresh shows **all four** electricity and **all four** water units,
  so the user always sees the full scale.
- Counts below 1 render with a fraction phrase and a camembert wedge:
  `◔` ¼ · `◑` ½ · `◕` ¾ · `●` almost one full unit.
- Counts between 1 and 100 show one decimal; above 100 they round to an
  integer with thousands separators.
- Menu-bar title uses the airfryer (electricity) and shower (water) units
  as the default references, falling back to smaller units for low values.
