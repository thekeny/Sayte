NAME = "Sayte"
W, H = 400, 700
HOTKEY = "ctrl+alt+r"

DB_PATH = "data/sayte.sqlite"
ICON_PATH = "images/sayte-icon.png"

MAIN_UI_PATH = "ui/main_window.ui"
NOTE_UI_PATH = "ui/note_window.ui"
NOTE_CARD_UI_PATH = "ui/note_card.ui"
TAG_CHIP_UI_PATH = "ui/tag_chip.ui"
RECORDING_UI_PATH = "ui/recording_window.ui"
SETTINGS_UI_PATH = "ui/settings_window.ui"
HOTKEY_UI_PATH = "ui/hotkey_dialog.ui"

LOGO_PATH = "images/sayte-logo.png"
SETTINGS_ICON_PATH = "images/settings.svg"
MICROPHONE_ICON_PATH = "images/microphone.svg"
TRASH_ICON_PATH = "images/trash.svg"

SAMPLE_RATE = 16000
WHISPER_MODEL = "base"
MODEL_CACHE_PATH = "data/models"

TITLE_LENGTH = 60
PREVIEW_LENGTH = 120
NOTE_HEIGHT = 88
TAGGED_NOTE_HEIGHT = 108
SAVE_MESSAGE_MS = 1000

WAVE_INTERVAL_MS = 80
WAVE_LEVEL_COUNT = 32
WAVE_COLOR = "#6c63ff"
WAVE_SCALE = 8
WAVE_MIN_HEIGHT = 4
WAVE_BAR_GAP = 3
WAVE_RADIUS = 2

WINDOW_MARGIN = 15
HIDE_MESSAGE_MS = 3000

HOTKEY_MESSAGE = 0x0312
HOTKEY_ID = 0x5341
HOTKEY_NO_REPEAT = 0x4000
HOTKEY_MODIFIERS = {
    "alt": 0x0001,
    "ctrl": 0x0002,
    "shift": 0x0004,
    "win": 0x0008
}
