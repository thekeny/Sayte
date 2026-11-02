from pathlib import Path


NAME = "Sayte"
W, H = 400, 700
HOTKEY = "ctrl+alt+r"
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "sayte.sqlite"
ICON_PATH = BASE_DIR / "images" / "sayte-icon.png"
SAMPLE_RATE = 16000
WHISPER_MODEL = "base"
