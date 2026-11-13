import json
import os
import secrets
import socket
import sys

APP_DIR = os.path.join(os.path.expanduser("~"), ".satlink_remote_pro")
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
LOG_FILE = os.path.join(APP_DIR, "access_log.jsonl")
APP_VERSION = "PRO 2.3.0 Neon"


def _ensure_dir():
    os.makedirs(APP_DIR, exist_ok=True)


def _new_device_id():
    return "SL-PC-" + secrets.token_hex(4).upper()


def _new_pin():
    return str(secrets.randbelow(900000) + 100000)


def _new_master_pin():
    # Default is intentionally simple so the user can enter settings first time.
    # The UI asks the user to change it after setup.
    return "1234"


def default_name():
    try:
        return socket.gethostname()
    except Exception:
        return "حاسبتي"


def _merge_defaults(cfg):
    changed = False
    defaults = {
        "device_id": _new_device_id(),
        "device_name": default_name(),
        "pin": _new_pin(),
        "approved": True,
        "require_pin": True,
        "port": 47655,
        "master_pin": _new_master_pin(),
        "auto_start_windows": False,
        "run_server_on_app_start": True,
        "minimize_to_tray_on_close": True,
        "notify_on_connection": True,
        "lock_exit_with_master": True,
        "relay_server_url": "http://127.0.0.1:7777",
        "owner_token": "SLR-CHANGE-ME-PRO-2026",
        "relay_auto_start": True,
        "start_relay_server_with_agent": True,
    }
    for key, value in defaults.items():
        if key not in cfg:
            cfg[key] = value
            changed = True
    if changed:
        save_config(cfg)
    return cfg


def load_config():
    _ensure_dir()
    if not os.path.exists(CONFIG_FILE):
        cfg = {}
        return _merge_defaults(cfg)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if not isinstance(cfg, dict):
            cfg = {}
    except Exception:
        cfg = {}
    return _merge_defaults(cfg)


def save_config(cfg):
    _ensure_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def rename_device(name):
    cfg = load_config()
    clean = (name or "").strip()
    if clean:
        cfg["device_name"] = clean[:60]
        save_config(cfg)
    return cfg


def rotate_pin():
    cfg = load_config()
    cfg["pin"] = _new_pin()
    save_config(cfg)
    return cfg


def change_master_pin(new_pin):
    cfg = load_config()
    clean = "".join(ch for ch in str(new_pin or "") if ch.isdigit())
    if len(clean) < 4:
        raise ValueError("Master PIN يجب أن يكون 4 أرقام أو أكثر")
    cfg["master_pin"] = clean[:12]
    save_config(cfg)
    return cfg


def set_bool_option(key, value):
    cfg = load_config()
    cfg[key] = bool(value)
    save_config(cfg)
    return cfg


def normalize_digits(value) -> str:
    text = str(value or "")
    out = []
    for ch in text:
        code = ord(ch)
        if "0" <= ch <= "9":
            out.append(ch)
        elif 0x0660 <= code <= 0x0669:
            out.append(str(code - 0x0660))
        elif 0x06F0 <= code <= 0x06F9:
            out.append(str(code - 0x06F0))
    return "".join(out).strip()


def check_master_pin(pin) -> bool:
    cfg = load_config()
    return normalize_digits(pin) == normalize_digits(cfg.get("master_pin", "1234"))


def pythonw_executable():
    exe = sys.executable
    folder = os.path.dirname(exe)
    base = os.path.basename(exe).lower()
    if base == "python.exe":
        pyw = os.path.join(folder, "pythonw.exe")
        if os.path.exists(pyw):
            return pyw
    return exe
