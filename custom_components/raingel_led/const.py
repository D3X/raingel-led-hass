"""Constants for the Raingel LED integration.

Protocol details come from https://github.com/agustinprod/vclights, which
extracted them from the decompiled Raingel app.
"""

DOMAIN = "raingel_led"

MANUFACTURER_ID = 22872
SERVICE_ADVERTISED = "0000af30-0000-1000-8000-00805f9b34fb"
CHAR_WRITE = "0000ae01-0000-1000-8000-00805f9b34fb"

# Drop the BLE connection after this many idle seconds so the phone app
# can still connect when Home Assistant isn't actively using the light.
DISCONNECT_DELAY = 120

OP_POWER = 0x01
OP_BRIGHTNESS = 0x02
OP_COLOR = 0x03
OP_MODE = 0x07
OP_MIC = 0x04

# Firmware effect ids (opcode 0x07).
EFFECTS = {
    "Fade": 1,
    "Jump": 2,
    "Breathe": 3,
    "Flash": 4,
    "Meteor": 5,
    "Stack": 6,
    "Float": 7,
    "Follow spot": 8,
    "Wave": 9,
    "Water": 10,
    "Rainbow": 11,
    "Blink": 12,
    "Bounce": 13,
    "Shuttle": 14,
    "Twinkle": 15,
    "On/off": 16,
    "Curtain": 17,
    "Alternate": 18,
}

# Palette indices: 0 red, 1 green, 2 blue, 3 yellow, 4 cyan, 5 violet,
# 6 orange, 7 white. This is the app's "spectrum" preset.
EFFECT_PALETTE = (0, 6, 3, 1, 4, 2, 5)
EFFECT_SPEED = 50

# Music modes driven by the lamp's built-in microphone (opcode 0x04).
MUSIC_EFFECTS = {
    "Music: Classic": 0,
    "Music: Roll": 1,
    "Music: Energy": 2,
    "Music: Spectrum": 3,
}
MUSIC_SENSITIVITY = 30  # 0-100
