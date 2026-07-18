# ScreenLine HomeComfort v0.2.3

This release fixes position translation and reduces radio/status traffic.

## Position fix

ScreenLine reports `currentCoverage` as percentage covered. Home Assistant expects percentage open. A value of 78 is now exposed as position 22 and is no longer marked closed.

`coverageReceived` is retained as a diagnostic attribute but is only used when `currentCoverage` is absent. Confirmation flags no longer cause a valid current value to be discarded.

## Tilt fix

ScreenLine uses -75° through +75°, where 0° is horizontal/open and both extremes are closed. Home Assistant uses 0% closed and 100% open. The integration now converts based on slat openness:

- ±75° → 0% tilt/opening
- 0° → 100% tilt/opening
- ±37.5° → approximately 50%

The original direction remains visible in `screenline_inclination_degrees` and `screenline_tilt_direction`.

## Battery-conscious refresh

- Regular polling: every 5 minutes
- After a command: refresh after 3 and 10 seconds
- Removed immediate plus 2/5/10/20/40-second refresh burst

## Installation

Replace the integration files, restart Home Assistant, and reload the integration if necessary.
