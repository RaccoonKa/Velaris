import json
import os
import base64

def get_user_data_dir():
    appdata = os.getenv('APPDATA')
    if appdata:
        data_dir = os.path.join(appdata, "Velaris")
    else:
        data_dir = os.path.join(os.path.expanduser("~"), ".velaris")
    return data_dir

CONFIG_DIR = get_user_data_dir()
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")
PROGRESS_FILE = os.path.join(CONFIG_DIR, "progress.json")

DEFAULT_SETTINGS = {
    "volume": 0.4,
    "muting_music": False,
    "sfx_volume": 0.2,
    "muting_sfx": False,
    "brightness": 1.0,
    "current_theme": "red",
    "current_bg_index": 1,
    "companion": "red",
    "language": "en",
    "vsync": False,
    "skip_splash": False,
    "nickname": "Player",
    "emoji_pack": "Standard"
}

DEFAULT_PROGRESS = {
    "money": 10000,
    "titles_unlocked": ["Новичок"],
    "current_title": "Новичок",
    "blackjack_count": 0,
    "win_count": 0,
    "redeemed_codes": [],
    "last_spin_date": "",
    "free_spins": 0
}

def load_settings():
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_SETTINGS.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)

def load_progress():
    if not os.path.exists(PROGRESS_FILE):
        return DEFAULT_PROGRESS.copy()
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            encoded_data = f.read()
            decoded_data = base64.b64decode(encoded_data).decode('utf-8')
            return json.loads(decoded_data)
    except Exception:
        return DEFAULT_PROGRESS.copy()

def save_progress(progress):
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)

    try:
        json_str = json.dumps(progress)
        encoded_data = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            f.write(encoded_data)
    except Exception:
        pass