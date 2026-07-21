# Changelog

## 0.2.1

- Added HomeComfort-style integration icon.
- Added rectangular HomeComfort logo.
- Added light and dark mode brand assets.
- Added 2x resolution assets for HiDPI displays.
- Added repository-level HACS branding.
- Added a branding preview to the README.

## 0.2.0

- Added verified HomeComfort cloud login.
- Added registered WISE Hub selection.
- Added automatic token renewal and reauthentication.

## 0.2.2

- Herstelt batterij-, bedekkings- en lamellenhoekstatus.
- Leest de status opnieuw correct uit het geneste `blind.status`-object.
- Voegt het sensorplatform en exacte tiltbediening opnieuw toe.

## 0.2.3

- Fixed incorrect closed state when `currentCoverage` differs from `coverageReceived`.
- Home Assistant position now uses `currentCoverage` first; `coverageReceived` is fallback only.
- Corrected Venetian tilt semantics: 0° is open, ±75° is closed.
- `current_tilt_position` now represents slat openness rather than tilt direction.
- Added `screenline_tilt_direction` attribute to preserve upward/downward direction.
- Reduced normal polling from 15 seconds to 5 minutes.
- Reduced command follow-up refreshes to 3 and 10 seconds.
- Fixed negative inclination values being incorrectly clamped to 0 by the API client.

## 0.2.4

- Added two incremental slat-control buttons per blind.
- Uses the native WISE Hub `/tilt` endpoint with `INCREMENT` and `DECREMENT`.
- A single delayed refresh after three seconds limits unnecessary radio traffic.
