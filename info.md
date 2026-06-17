# MyIqua Water Softener

Home Assistant integration for **iQua / EcoWater / Viessmann Aquahome** softeners
on the modern **`api.myiquaapp.com`** backend (the newer EU "iQua" app) — the one
the older public integrations (`apioem.ecowater.com`) can't reach.

- Sensors: water usage (today / avg / total / available), live flow, salt level,
  regeneration info, hardness, WiFi.
- Binary sensors: leak / continuous-flow, low salt, excessive use, error, online…
- **Start regeneration** button.
- **On-demand live WebSocket** ("Live view") for real-time flow — auto-closes after 5 min.

Config is UI-only: e-mail + password (device auto-discovered).

Based on the proof-of-concept by **@jakubkotlorz** (`myiqua-api-poc`).
