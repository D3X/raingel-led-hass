# Raingel LED for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Release](https://img.shields.io/github/v/release/Seventh-Void/raingel-led-hass)](https://github.com/Seventh-Void/raingel-led-hass/releases)

Local Bluetooth control for LED lights that normally use the
[**Raingel** app](https://play.google.com/store/apps/details?id=com.raingel.app),
such as the **TONOR** microphone boom arm. These use DoHome `VC-BLELIGHT`
controllers. No cloud and no phone app needed. Works with **HomeKit Bridge**,
so the light shows up in Apple Home and Siri.

## Features

- On / off
- RGB colour
- Brightness
- All 18 built-in effects: Fade, Jump, Breathe, Flash, Meteor, Stack, Float,
  Follow spot, Wave, Water, Rainbow, Blink, Bounce, Shuttle, Twinkle, On/off,
  Curtain, Alternate
- Four music modes using the lamp's built-in microphone (Classic, Roll,
  Energy, Spectrum), fixed at sensitivity 80
- Automatic Bluetooth discovery
- Works with a local Bluetooth adapter (including on Home Assistant OS) or an
  ESPHome Bluetooth proxy

## Supported devices

Any light controlled by the Raingel app should work. Its advertisement includes:

| Field | Value |
| --- | --- |
| Service UUID | `0000af30-0000-1000-8000-00805f9b34fb` |
| Manufacturer ID | `22872` (`0x5958`) |
| Name | Varies by brand: `VC-BLELIGHT`, `TONOR`, … |

Tested with:

- TONOR boom arm (RGB strip, manufacturer data `10 02`)

To check your device, install **nRF Connect** on your phone and scan for it,
or look under **Settings → Devices & services → Bluetooth** in Home Assistant.
If it works with something else, please open an issue so it can be added to
the list.

## Installation

### HACS (recommended)

1. In Home Assistant open **HACS → ⋮ (top right) → Custom repositories**.
2. Add `https://github.com/Seventh-Void/raingel-led-hass` with type **Integration**.
3. Search for **Raingel LED**, install it, then restart Home Assistant.

### Manual

Copy `custom_components/raingel_led` into your Home Assistant
`config/custom_components/` folder and restart.

## Setup

1. Close the Raingel app on your phone. The light only accepts one connection
   at a time.
2. Home Assistant should discover the light. Go to **Settings → Devices &
   services** and click **Configure** on the discovered card.
   If it doesn't appear, click **Add integration** and search for **Raingel LED**.

Your Home Assistant server needs a Bluetooth adapter within range of the light,
or an [ESPHome Bluetooth proxy](https://esphome.io/projects/) nearby.

## Apple Home / HomeKit

1. **Settings → Devices & services → Add integration → HomeKit Bridge**.
2. Include the **Light** domain, or only this light.
3. Scan the pairing QR code from Home Assistant's notifications with the Home
   app (**+ → Add Accessory**).

HomeKit shows on/off, colour and brightness. It doesn't support effects. To
use effects from Apple Home, create Home Assistant scenes with them and
include scenes in the bridge.

## Limitations

- **Assumed state.** The controller doesn't report its state, so if you change it
  with the remote or phone app, Home Assistant won't know.
- **One connection at a time.** Home Assistant keeps the connection open for 10
  seconds after the last command. The phone app can't connect during that
  time.
- **Colour accuracy.** Only saturated colours (red, green, blue, yellow, cyan,
  magenta, white) reproduce reliably on this hardware. In-between colours may
  look off.
- Effects use a rainbow palette at medium speed.

## Troubleshooting

**`br-connection-profile-unavailable` / "No more profiles to connect to"**

These controllers wrongly advertise support for Classic Bluetooth, so BlueZ
tries a Classic connection and fails. The integration works around this by
setting BlueZ's `PreferredBearer` to `le` before connecting. This needs BlueZ
running with `--experimental`, which is the default on Home Assistant OS. If
you see a *"Could not set PreferredBearer"* warning in the logs:

- update Home Assistant OS so you get a newer BlueZ, or
- on Docker/Core installs, set `ControllerMode = le` in `/etc/bluetooth/main.conf`, or
- use an ESPHome Bluetooth proxy, which only uses BLE.

**Debug logging**

```yaml
logger:
  logs:
    custom_components.raingel_led: debug
```

The log shows every command sent to the light as hex.

## Protocol

| Command | Bytes |
| --- | --- |
| Power | `01 <0/1>` |
| Brightness | `02 <0-255>` |
| Colour | `03 r g b 00 00 00` |
| Effect | `07 <mode> <speed 0-100> <brightness 0-100> <palette…>` |
| Music (mic) | `04 <mode 0-3> <sensitivity 0-100>` |

Commands are written without response to characteristic `AE01` (service
`AE30`). All of this was worked out by
[agustinprod/vclights](https://github.com/agustinprod/vclights), which
decompiled the Raingel app. See its
[protocol notes](https://github.com/agustinprod/vclights/blob/main/docs/protocol.md)
for the full details.

## Credits & license

Protocol from [vclights](https://github.com/agustinprod/vclights) by agustinprod (MIT).
This integration is released under the [MIT License](LICENSE). It isn't
affiliated with Raingel, DoHome or TONOR.
