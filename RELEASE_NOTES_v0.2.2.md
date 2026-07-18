# ScreenLine HomeComfort v0.2.2

## Opgelost

- Batterijsensoren zijn opnieuw toegevoegd.
- Batterijstatus wordt weer gelezen uit `blind.status.batteryReceived`.
- Bedekkingsstatus wordt gelezen uit de geneste WISE Hub-status.
- Lamellenhoek wordt gelezen uit `currentInclination` en `inclinationReceived`.
- Correcte omzetting van -75° tot +75° naar Home Assistant 0–100% tilt.
- Exacte tiltpositie instellen is opnieuw beschikbaar.
- Na een bedieningsopdracht worden meerdere vertraagde statusupdates uitgevoerd.
- Fysiek ontvangen waarden worden gebruikt zolang de hub de doelpositie nog niet heeft bevestigd.
