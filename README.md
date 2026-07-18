# ScreenLine WISE for Home Assistant

Unofficial local Home Assistant integration for Pellini ScreenLine WISE / HomeComfort hubs.

## Features

- Local HTTPS communication with the WISE hub
- Automatic discovery of rooms and Venetian blinds after configuration
- Open, close and stop
- Set exact blind position
- Set exact slat tilt
- Battery sensors
- Config flow and token reauthentication
- Configurable polling interval (10–300 seconds)

## Installation

### HACS custom repository

1. Put this project in a GitHub repository.
2. In HACS, open **Integrations** → menu → **Custom repositories**.
3. Add the repository URL as category **Integration**.
4. Install **ScreenLine WISE** and restart Home Assistant.

### Manual

Copy `custom_components/screenline_wise` to Home Assistant's `config/custom_components/` folder and restart Home Assistant.

## Configuration

Add the integration through **Settings → Devices & services → Add integration → ScreenLine WISE**.

Enter:

- Hub IP address, for example `192.168.68.71`
- Bearer token without the word `Bearer`
- Leave SSL verification disabled because the WISE hub uses a self-signed ScreenLine certificate

The token is sensitive. Do not post it publicly or commit it to Git.

## Position mapping

ScreenLine reports `coverage` as `0` for fully raised and `100` for fully lowered. Home Assistant uses the reverse convention, so this integration converts the values automatically.

ScreenLine inclination is mapped from `-75..75` degrees to Home Assistant's `0..100` tilt scale. Commands are rounded to 15-degree steps for SL20/22W Venetian blinds.

## Tested hardware

- WISE hub local API on HTTPS port 8080
- Venetian SL20/22W blinds
- API routes used:
  - `GET /api/plant/rooms?includeBlinds=true&includeGlasses=true`
  - `POST /api/rooms/{room_id}/position`
  - `POST /api/rooms/{room_id}/move`

## Notes

This is an unofficial integration and is not affiliated with Pellini or ScreenLine. The local API is undocumented and may change after hub firmware updates.


## Changelog

### 0.1.1

- Use the physically reported coverage and inclination while a movement is pending.
- Refresh more frequently after movement commands.
- Use the dedicated WISE tilt endpoint for the tilt up/down controls.
