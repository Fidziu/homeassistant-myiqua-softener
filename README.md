# MyIqua Water Softener — Home Assistant integration

> **🏠 Works with the latest Home Assistant (tested on 2026.6+).**
> **🍴 Extended fork of [jakubkotlorz/myiqua-api-poc](https://github.com/jakubkotlorz/myiqua-api-poc)** —
> this version adds the modern `api.myiquaapp.com` backend support, the full sensor
> set, alert binary-sensors, a *Start regeneration* button, and an **on-demand live
> WebSocket** for real-time flow. Full credit to the original author for the auth +
> base client.

Custom Home Assistant integration for **iQua / EcoWater / Viessmann Aquahome**
smart water softeners that use the **modern `api.myiquaapp.com` cloud backend**
(the EU/"iQua" app backend), with live data over WebSocket.

> **Why this exists.** The public integrations
> ([`arturzx/homeassistant-iqua-softener`](https://github.com/arturzx/homeassistant-iqua-softener)
> and forks) talk to the *old* `apioem.ecowater.com` API. EU / Viessmann-Aquahome
> accounts (the newer **iQua** app) live on a **different backend** —
> `api.myiquaapp.com` — where those integrations just return *"Invalid user or
> password"*. This integration targets that new backend, so it works for accounts
> the old ones can't reach.

Built on top of the proof-of-concept by
[**@jakubkotlorz** (`myiqua-api-poc`)](https://github.com/jakubkotlorz/myiqua-api-poc)
— credit to the original author for reverse-engineering the auth + base client.
This is an extended version (full sensor set, alerts, regeneration button, and an
on-demand live WebSocket).

---

## What you get

**Sensors** (cloud-polled every 5 min)
- Water used today (L), Average daily use (L), Treated water available (L), Total water used (L)
- Current water flow (L/min)
- Salt level (%), Out-of-salt in (days) + Out-of-salt date, Days since last regeneration + Last regeneration date, Total regenerations
- Water hardness (gpg), Days in operation, WiFi signal (dBm)

**Binary sensors (alerts)** — flags reported by the device
- Leak / continuous-flow alert (device's own continuous-flow monitor)
- Low salt, Excessive water use, Shutoff valve, Resin, Error, Online

**Button**
- Start regeneration (`PUT /command {function:"regenerate", action:"regenerate"}`)

**Switch — "Live view"** (on-demand)
- Opens the device's WebSocket so flow/usage update **in real time** (HA becomes the
  "active client" — no need to keep the phone app open). **Auto-closes after 5 min**
  so there is never a 24/7 connection.

The "Total water used" sensor is `device_class: water` + `state_class:
total_increasing` in litres, so it can be used directly as a **water source in the
HA Energy dashboard**.

---

## How it works (architecture)

| Concern | Detail |
| --- | --- |
| Base URL | `https://api.myiquaapp.com/v1` |
| Auth | `POST /auth/login {email,password}` → `access_token` (JWT, ~24 h) + `refresh_token`. Sent as `Authorization: Bearer …`. On a 401 we re-login. |
| Poll data | `GET /devices/{id}/detail-or-summary` → `device.properties` (each property has `value` and, for volumes/flow, a `converted_value` already in litres / L·min⁻¹). |
| Discovery | `GET /devices` at config time → first softener is auto-selected (config flow only asks for e-mail + password). |
| Live | `GET /devices/{id}/live` → `{websocket_uri}` → connect `wss://api.myiquaapp.com{uri}` (token in `?p=`). Server pushes JSON frames `{"name":<prop>,"type":"property","value":N,"converted_property":{…}}`. Opening the socket sets `app_active=true`, which makes the device stream. |
| Commands | `PUT /devices/{id}/command {function, action}` (regenerate / schedule / cancel). |
| Rate limit | The legacy EcoWater API blocked accounts above ~1000 req/day. At 5-min polling this is ~288/day. The live WebSocket is one short-lived connection, opened only on demand. |
| Discovery note | The cloud only refreshes `current_water_flow_gpm` while a client is "active" (app open **or** our live WebSocket). Polling alone shows a frozen value between active sessions — this is a cloud limitation, not a bug. Leak detection does **not** depend on it (the device computes `flow_monitor_alert` itself). |
| Salt level | **Read-only.** The softener does not measure salt; `salt_level_tenths` is the level last entered on the device and counted down per regeneration. The cloud API has **no write** for it (checked 2026-10-23: not among the 18 items of `GET /devices/{id}/settings`, not in the OpenAPI spec, not in the iQua web app). After refilling, set the level on the softener's control panel. |
| Diagnostics | *Settings → Devices & services → MyIqua → ⋮ → Download diagnostics* returns the device properties, the cloud's settings list and enriched data (e-mail/password redacted). |

OpenAPI spec (handy reference): `https://api.myiquaapp.com/v1/openapi.json`.

---

## Install

1. Copy the `myiqua_softener` folder into `…/config/custom_components/`.
2. Restart Home Assistant.
3. *Settings → Devices & Services → Add Integration → "MyIqua Water Softener"* →
   enter your iQua app e-mail + password. The device is discovered automatically.

The bundled `iqua_softener` PyPI dependency is **not** required (this integration
talks to the API directly with `aiohttp`).

---

## Files

```
myiqua_softener/
├── __init__.py        # setup/unload, forwards sensor+binary_sensor+button+switch
├── api.py             # IquaApiAsync: login, GET helpers, command, live ws url
├── coordinator.py     # DataUpdateCoordinator (5 min), config_entry-aware
├── config_flow.py     # email+password, auto-discovers the device
├── entity.py          # base entity: DeviceInfo + property reader
├── sensor.py          # 14 sensors (+2 derived date sensors)
├── binary_sensor.py   # 7 alert/connectivity binary sensors
├── button.py          # Start regeneration
├── switch.py          # On-demand live WebSocket ("Live view")
├── const.py
├── manifest.json
├── strings.json
└── translations/{en,pl}.json
```

See **[CHANGELOG.md](CHANGELOG.md)** for what changed and when.
