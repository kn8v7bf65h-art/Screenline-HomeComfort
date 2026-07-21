# ScreenLine HomeComfort v0.2.4

This release adds the same one-step slat control available from the official
HomeComfort app and physical remote.

For every blind, Home Assistant now creates:

- **Tilt slats one step forward**
- **Tilt slats one step backward**

The buttons call the native local WISE Hub endpoint:

```http
POST /api/rooms/{room_id}/tilt
```

with either `INCREMENT` or `DECREMENT`. The hub applies its native step size
(typically 15 degrees). Only one status refresh is scheduled three seconds
after a press to minimise battery and radio usage.
