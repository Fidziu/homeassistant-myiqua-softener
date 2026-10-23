# Changelog

All notable changes to the MyIqua Water Softener integration.
Format loosely follows [Keep a Changelog]. Dates are ISO (YYYY-MM-DD).

## [0.2.1] — 2026-10-23

### Fixed
- **A single rejected login no longer takes the softener offline for days.**
  On 2026-10-21 the iQua cloud answered `POST /v1/auth/login` once with 401
  although the password was correct. The coordinator turned that straight into
  `ConfigEntryAuthFailed`, HA stopped polling and — because the config flow had
  no reauth step — every entity (incl. the leak sensor) stayed `unavailable`
  for two days until the entry was reloaded by hand.
  - Now a rejected login only fails that update (`UpdateFailed`) and is retried
    on the next 5-minute cycle. HA is asked to re-authenticate only after
    **≥ 3 rejections in a row spanning ≥ 30 minutes**; a successful update
    resets the streak. The streak survives setup retries/reloads.

### Added
- **Re-authentication** (`reauth` / `reauth_confirm`): when HA does ask, the
  flow first retries the stored credentials and, if the cloud accepts them
  again, reloads the entry silently. Only otherwise it shows "Re-authenticate"
  with the e-mail pre-filled. The account must still contain the same softener.
- **Reconfigure** (entry menu → *Reconfigure*): change e-mail / password without
  removing the integration.
- EN/PL strings for both; tests (`pytest-homeassistant-custom-component`).

### Changed
- `hacs.json` minimum Home Assistant 2024.11.0 (reauth/reconfigure helpers).

## [0.2.0] — 2026-06-17

First working deployment for the **Aquahome Duo Smart** (EU / Viessmann-EcoWater,
iQua app). Everything below was built and deployed on the same day, in this order.

### Discovery / investigation
- Confirmed the iQua app for EU accounts uses **`api.myiquaapp.com`**, not the
  `apioem.ecowater.com` backend the public integrations target (proved by an
  identical *"Invalid user or password"* for our account vs. a garbage account on
  apioem). Endpoint discovered by proxying the iQua app's traffic (mitmproxy).
- Pulled the full **OpenAPI spec** (`/v1/openapi.json`) and the device's live
  `properties`, `detail-or-summary`, `enriched-data`, `datapoints/.../graph`.

### Added — core
- Custom component **`myiqua_softener`** based on @jakubkotlorz's `myiqua-api-poc`,
  rewritten/extended:
  - `config_flow` now asks only **e-mail + password** and **auto-discovers** the
    device via `GET /devices` (no manual serial/DSN needed).
  - Coordinator made **`config_entry`-aware** (HA 2026.x requirement).
  - Fixed for **HA 2026.6**: replaced the removed `async_forward_entry_setup`
    pattern with `async_forward_entry_setups`.
- **14 sensors** + 2 derived date sensors, with correct litre / L·min⁻¹ units via
  the API's `converted_value`. Salt level from `salt_level_tenths/10`.
- **7 binary sensors** (leak/continuous-flow, low salt, excessive use, shutoff
  valve, resin, error, online).
- English + Polish translations; `manifest.json` set to `iot_class:
  cloud_polling`.

### Added — control & live
- **Start regeneration** button — `PUT /command {function:"regenerate",
  action:"regenerate"}` (exact command lifted from the iQua web app bundle).
- **"Live view" switch** — opens `wss://api.myiquaapp.com/ws/?p=…` on demand; live
  frames patch the coordinator data so sensors update in real time. **Auto-closes
  after 300 s.**

### Changed
- Polling interval **15 min → 5 min** (~288 req/day; safely under the legacy
  ~1000/day cap).

### Notes / known limitations
- `current_water_flow` is only fresh while a client is "active" (phone app open or
  the Live view switch). Between active sessions the cloud freezes the value — a
  cloud limitation. Leak detection is unaffected (device-side `flow_monitor_alert`).
- The cloud's historical `datapoints/.../graph` returned sparse/garbled values for
  this unit, so HA history is built going forward (Energy dashboard + recorder)
  rather than back-filled.

### Home Assistant side (not part of the component, same day)
- Dashboard **"Zmiękczacz"** (`woda-zmiekczacz`), 3-column sections layout.
- Automations (push to mobile): leak / low-salt (level-based, threshold helper) /
  offline / high-daily-usage (threshold helper).
- `Total water used` added to the **Energy** dashboard as the house water meter.

[0.2.1]: https://github.com/Fidziu/homeassistant-myiqua-softener/releases/tag/v0.2.1
[0.2.0]: https://github.com/jakubkotlorz/myiqua-api-poc
[Keep a Changelog]: https://keepachangelog.com/
