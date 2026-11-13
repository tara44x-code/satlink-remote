import base64
import ctypes
import io
import json
import os
import re
import socket
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from typing import Optional

import pyautogui
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from mss import mss
from PIL import Image, ImageGrab
from waitress import serve

from device_identity import load_config, normalize_digits, LOG_FILE

DISCOVERY_PORT = 47656
DISCOVERY_MAGIC = b"SATLINK_REMOTE_PRO_DISCOVER"
APP_VERSION = "PRO 2.3.0 Neon"
MAX_UPLOAD_MB = 300

# Remote control needs instant input: no 0.1s pause after every action, and no
# FailSafe exception when the phone moves the mouse into a screen corner.
pyautogui.PAUSE = 0.01
pyautogui.FAILSAFE = False

IS_WINDOWS = sys.platform.startswith("win")
ALLOWED_KEYS = set(pyautogui.KEYBOARD_KEYS)

app = Flask(__name__)
CORS(app)
server_state = {"running": False, "enabled": False, "last_client": "", "started_at": None}


def safe_files_dir() -> str:
    """A safe exchange folder. The phone can only see/upload/download here."""
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    base = desktop if os.path.isdir(desktop) else os.path.expanduser("~")
    path = os.path.join(base, "SatLinkRemotePRO_Files")
    os.makedirs(path, exist_ok=True)
    return path




def client_ip() -> str:
    return request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()


def log_event(event_type: str, message: str, client: str = ""):
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        row = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": str(event_type)[:40],
            "client": str(client or "")[:80],
            "message": str(message or "")[:400],
        }
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass


def read_recent_logs(limit: int = 40):
    try:
        if not os.path.exists(LOG_FILE):
            return []
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()[-max(1, min(200, limit)):]
        out = []
        for line in lines:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
        return list(reversed(out))
    except Exception:
        return []


@app.before_request
def require_enabled_state():
    # When the user presses "Stop connection", the server stays alive locally
    # but refuses remote operations and stops discovery responses.
    allowed_when_disabled = {"/api/info", "/api/status"}
    if request.path.startswith("/api/") and request.path not in allowed_when_disabled:
        if not server_state.get("enabled", False):
            return jsonify({"ok": False, "error": "الاتصال متوقف من برنامج الحاسبة"}), 503


def safe_name(name: str) -> str:
    name = os.path.basename(name or "file.bin").strip()
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name)
    return name[:180] or "file.bin"


def unique_path(folder: str, filename: str) -> str:
    filename = safe_name(filename)
    root, ext = os.path.splitext(filename)
    target = os.path.join(folder, filename)
    if not os.path.exists(target):
        return target
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(folder, f"{root}_{stamp}{ext}")


def normalize_pin(value) -> str:
    return normalize_digits(value)


def _check_pin() -> bool:
    cfg = load_config()
    if not cfg.get("require_pin", True):
        return True
    pin = request.headers.get("X-SatLink-PIN") or request.args.get("pin") or ""
    if not pin and request.is_json:
        data = request.get_json(force=True, silent=True) or {}
        pin = data.get("pin", "")
    if not pin:
        pin = request.form.get("pin", "")
    pin = normalize_pin(pin)
    saved = normalize_pin(cfg.get("pin", ""))
    return pin == saved


# ---------------- Input helpers (2.3.0) ----------------
if IS_WINDOWS:
    from ctypes import wintypes

    _ULONG_PTR = ctypes.c_size_t

    class _KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", _ULONG_PTR)]

    class _MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", _ULONG_PTR)]

    class _INPUTUNION(ctypes.Union):
        _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT)]

    class _INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]

    _INPUT_MOUSE, _INPUT_KEYBOARD = 0, 1
    _KEYEVENTF_KEYUP, _KEYEVENTF_UNICODE = 0x0002, 0x0004
    _MOUSEEVENTF_WHEEL = 0x0800

    def _send_inputs(items):
        arr = (_INPUT * len(items))(*items)
        ctypes.windll.user32.SendInput(len(items), arr, ctypes.sizeof(_INPUT))

    def type_unicode(text: str):
        """Types any text (Arabic, emoji, symbols) regardless of keyboard layout."""
        data = text.replace("\r\n", "\n").encode("utf-16-le")
        for i in range(0, len(data), 2):
            code = int.from_bytes(data[i:i + 2], "little")
            if code == 10:  # new line -> Enter
                pyautogui.press("enter")
                continue
            down = _INPUT(type=_INPUT_KEYBOARD, u=_INPUTUNION(ki=_KEYBDINPUT(0, code, _KEYEVENTF_UNICODE, 0, 0)))
            up = _INPUT(type=_INPUT_KEYBOARD, u=_INPUTUNION(ki=_KEYBDINPUT(0, code, _KEYEVENTF_UNICODE | _KEYEVENTF_KEYUP, 0, 0)))
            _send_inputs([down, up])
            time.sleep(0.004)

    def wheel(notches: int):
        """Real mouse-wheel notches (pyautogui on Windows sends 1/120 of a notch)."""
        amount = int(notches) * 120
        _send_inputs([_INPUT(type=_INPUT_MOUSE, u=_INPUTUNION(mi=_MOUSEINPUT(0, 0, ctypes.c_uint32(amount).value, _MOUSEEVENTF_WHEEL, 0, 0)))])
else:
    def type_unicode(text: str):
        pyautogui.write(text, interval=0.01)

    def wheel(notches: int):
        pyautogui.scroll(int(notches))


def draw_cursor(img: Image.Image, scale_x: float, scale_y: float, offset=(0, 0)):
    """mss screenshots do not include the mouse pointer; draw a neon arrow so the phone can see it."""
    try:
        from PIL import ImageDraw
        px, py = pyautogui.position()
        x = (px - offset[0]) * scale_x
        y = (py - offset[1]) * scale_y
        if x < 0 or y < 0 or x > img.width or y > img.height:
            return
        s = max(10, int(img.width / 70))
        pts = [(x, y), (x, y + s * 1.45), (x + s * 0.38, y + s * 1.08), (x + s * 0.62, y + s * 1.62),
               (x + s * 0.86, y + s * 1.5), (x + s * 0.62, y + s * 0.98), (x + s * 1.08, y + s * 0.98)]
        d = ImageDraw.Draw(img)
        d.polygon(pts, fill=(255, 255, 255), outline=(0, 0, 0))
        d.line(pts + [pts[0]], fill=(0, 240, 255), width=max(1, s // 9))
    except Exception:
        pass


# ---------------- File Manager v1.3 ----------------
def _user_folder(name: str) -> str:
    home = os.path.expanduser("~")
    # Standard Windows folders first. If missing, fallback to home.
    candidate = os.path.join(home, name)
    return candidate if os.path.isdir(candidate) else home


def file_roots():
    """Allowed safe roots. The phone cannot browse outside these folders."""
    roots = [
        {"key": "exchange", "name": "مجلد التبادل SatLinkRemotePRO_Files", "path": safe_files_dir()},
        {"key": "desktop", "name": "سطح المكتب Desktop", "path": _user_folder("Desktop")},
        {"key": "downloads", "name": "التنزيلات Downloads", "path": _user_folder("Downloads")},
        {"key": "documents", "name": "المستندات Documents", "path": _user_folder("Documents")},
    ]
    # Remove duplicate paths while keeping order.
    out = []
    seen = set()
    for r in roots:
        rp = os.path.abspath(r["path"])
        if rp.lower() in seen:
            continue
        seen.add(rp.lower())
        rr = dict(r)
        rr["path"] = rp
        out.append(rr)
    return out


def _root_base(root_key: str) -> str:
    for r in file_roots():
        if r["key"] == root_key:
            return os.path.abspath(r["path"])
    raise ValueError("مجلد غير مسموح")


def clean_rel_path(rel: str) -> str:
    rel = str(rel or "").replace("\\", "/").strip()
    rel = rel.lstrip("/")
    if rel in ("", "."):
        return ""
    norm = os.path.normpath(rel).replace("\\", "/")
    if norm in ("", "."):
        return ""
    parts = [p for p in norm.split("/") if p not in ("", ".")]
    if any(p == ".." or ":" in p for p in parts):
        raise ValueError("مسار غير مسموح")
    return "/".join(parts)


def resolve_safe(root_key: str, rel: str) -> tuple[str, str, str]:
    base = _root_base(root_key)
    rel_clean = clean_rel_path(rel)
    target = os.path.abspath(os.path.join(base, rel_clean))
    if os.path.commonpath([base, target]) != base:
        raise ValueError("المسار خارج المجلد المسموح")
    return base, target, rel_clean


def rel_join(a: str, b: str) -> str:
    return clean_rel_path("/".join([x for x in [a, b] if x]))


def json_error(message: str, code: int = 400):
    return jsonify({"ok": False, "error": message}), code


@app.get("/api/fm/roots")
def fm_roots():
    if not _check_pin():
        return jsonify({"ok": False, "error": "PIN غير صحيح"}), 401
    public_roots = [{"key": r["key"], "name": r["name"], "path": r["path"]} for r in file_roots()]
    return jsonify({"ok": True, "roots": public_roots})


@app.get("/api/fm/list")
def fm_list():
    if not _check_pin():
        return jsonify({"ok": False, "error": "PIN غير صحيح"}), 401
    root = request.args.get("root", "exchange")
    rel = request.args.get("path", "")
    try:
        base, folder, rel_clean = resolve_safe(root, rel)
        if not os.path.isdir(folder):
            return json_error("المجلد غير موجود", 404)
        folders, files = [], []
        for entry in os.scandir(folder):
            try:
                st = entry.stat()
                item = {
                    "name": entry.name,
                    "path": rel_join(rel_clean, entry.name),
                    "size": 0 if entry.is_dir() else st.st_size,
                    "modified": int(st.st_mtime),
                    "is_dir": entry.is_dir(),
                }
                if entry.is_dir():
                    folders.append(item)
                elif entry.is_file():
                    files.append(item)
            except Exception:
                continue
        folders.sort(key=lambda x: x["name"].lower())
        files.sort(key=lambda x: x["name"].lower())
        parent = ""
        if rel_clean:
            parent = os.path.dirname(rel_clean).replace("\\", "/")
        return jsonify({
            "ok": True,
            "root": root,
            "path": rel_clean,
            "parent": parent,
            "absolute_path": folder,
            "items": folders + files,
            "count": len(folders) + len(files),
        })
    except Exception as e:
        return json_error(str(e), 400)


@app.post("/api/fm/upload")
def fm_upload():
    if not _check_pin():
        return jsonify({"ok": False, "error": "PIN غير صحيح"}), 401
    root = request.args.get("root", "exchange")
    rel = request.args.get("path", "")
    try:
        _, folder, _ = resolve_safe(root, rel)
        if not os.path.isdir(folder):
            return json_error("مجلد الرفع غير موجود", 404)
        if "file" not in request.files:
            return json_error("لم يصل أي ملف", 400)
        f = request.files["file"]
        target = unique_path(folder, f.filename or "uploaded.bin")
        max_bytes = MAX_UPLOAD_MB * 1024 * 1024
        total = 0
        with open(target, "wb") as out:
            while True:
                chunk = f.stream.read(1024 * 256)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    out.close()
                    try:
                        os.remove(target)
                    except Exception:
                        pass
                    return json_error(f"حجم الملف أكبر من {MAX_UPLOAD_MB}MB", 413)
                out.write(chunk)
        rel_target = rel_join(clean_rel_path(rel), os.path.basename(target))
        log_event("upload", f"رفع ملف إلى الحاسبة: {os.path.basename(target)}", client_ip())
        return jsonify({"ok": True, "name": os.path.basename(target), "path": rel_target, "size": total})
    except Exception as e:
        return json_error(str(e), 400)


@app.post("/api/fm/upload_raw")
def fm_upload_raw():
    """رفع خام بدون multipart. هذا مسار احتياطي أقوى لبعض صور المعرض/الأسماء العربية/ملفات HEIC."""
    if not _check_pin():
        return jsonify({"ok": False, "error": "PIN غير صحيح"}), 401
    root = request.args.get("root", "exchange")
    rel = request.args.get("path", "")
    filename = request.args.get("filename", "uploaded.bin") or "uploaded.bin"
    try:
        _, folder, _ = resolve_safe(root, rel)
        if not os.path.isdir(folder):
            return json_error("مجلد الرفع غير موجود", 404)
        # تنظيف اسم الملف حتى لا يخرج من المجلد المسموح
        filename = os.path.basename(filename.replace("\\", "/")).strip() or "uploaded.bin"
        for bad in ["\r", "\n", "\0", ":", "*", "?", "\"", "<", ">", "|"]:
            filename = filename.replace(bad, "_")
        if len(filename) > 180:
            name, ext = os.path.splitext(filename)
            filename = name[:160] + ext[:20]
        target = unique_path(folder, filename)
        max_bytes = MAX_UPLOAD_MB * 1024 * 1024
        total = 0
        with open(target, "wb") as out:
            while True:
                chunk = request.stream.read(1024 * 256)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    out.close()
                    try:
                        os.remove(target)
                    except Exception:
                        pass
                    return json_error(f"حجم الملف أكبر من {MAX_UPLOAD_MB}MB", 413)
                out.write(chunk)
        rel_target = rel_join(clean_rel_path(rel), os.path.basename(target))
        log_event("upload", f"رفع ملف خام إلى الحاسبة: {os.path.basename(target)}", client_ip())
        return jsonify({"ok": True, "raw": True, "name": os.path.basename(target), "path": rel_target, "size": total})
    except Exception as e:
        return json_error(str(e), 400)


@app.get("/api/fm/download")
def fm_download():
    if not _check_pin():
        return jsonify({"ok": False, "error": "PIN غير صحيح"}), 401
    root = request.args.get("root", "exchange")
    rel = request.args.get("path", "")
    try:
        _, target, rel_clean = resolve_safe(root, rel)
        if not rel_clean or not os.path.isfile(target):
            return json_error("الملف غير موجود", 404)
        log_event("download", f"تحميل ملف من الحاسبة: {os.path.basename(target)}", client_ip())
        return send_file(target, as_attachment=True, download_name=os.path.basename(target), max_age=0)
    except Exception as e:
        return json_error(str(e), 400)


@app.post("/api/fm/delete")
def fm_delete():
    if not _check_pin():
        return jsonify({"ok": False, "error": "PIN غير صحيح"}), 401
    data = request.get_json(force=True, silent=True) or {}
    root = data.get("root", "exchange")
    rel = data.get("path", "")
    try:
        _, target, rel_clean = resolve_safe(root, rel)
        if not rel_clean:
            return json_error("لا يمكن حذف المجلد الرئيسي", 400)
        if os.path.isdir(target):
            shutil.rmtree(target)
        elif os.path.isfile(target):
            os.remove(target)
        else:
            return json_error("العنصر غير موجود", 404)
        log_event("delete", f"حذف عنصر: {rel_clean}", client_ip())
        return jsonify({"ok": True})
    except Exception as e:
        return json_error(str(e), 400)


@app.post("/api/fm/mkdir")
def fm_mkdir():
    if not _check_pin():
        return jsonify({"ok": False, "error": "PIN غير صحيح"}), 401
    data = request.get_json(force=True, silent=True) or {}
    root = data.get("root", "exchange")
    rel = data.get("path", "")
    name = safe_name(str(data.get("name", "مجلد جديد")))
    try:
        _, folder, _ = resolve_safe(root, rel)
        if not os.path.isdir(folder):
            return json_error("المجلد الحالي غير موجود", 404)
        target = os.path.join(folder, name)
        if os.path.exists(target):
            return json_error("يوجد ملف أو مجلد بنفس الاسم", 409)
        os.makedirs(target)
        log_event("mkdir", f"إنشاء مجلد: {name}", client_ip())
        return jsonify({"ok": True, "name": name, "path": rel_join(clean_rel_path(rel), name)})
    except Exception as e:
        return json_error(str(e), 400)


@app.post("/api/fm/rename")
def fm_rename():
    if not _check_pin():
        return jsonify({"ok": False, "error": "PIN غير صحيح"}), 401
    data = request.get_json(force=True, silent=True) or {}
    root = data.get("root", "exchange")
    rel = data.get("path", "")
    new_name = safe_name(str(data.get("new_name", "")))
    try:
        _, target, rel_clean = resolve_safe(root, rel)
        if not rel_clean:
            return json_error("لا يمكن إعادة تسمية المجلد الرئيسي", 400)
        if not os.path.exists(target):
            return json_error("العنصر غير موجود", 404)
        parent = os.path.dirname(target)
        new_target = os.path.abspath(os.path.join(parent, new_name))
        base = _root_base(root)
        if os.path.commonpath([base, new_target]) != base:
            return json_error("الاسم غير مسموح", 400)
        if os.path.exists(new_target):
            return json_error("يوجد عنصر بنفس الاسم", 409)
        os.rename(target, new_target)
        log_event("rename", f"إعادة تسمية: {rel_clean} -> {new_name}", client_ip())
        return jsonify({"ok": True, "name": new_name, "path": rel_join(os.path.dirname(rel_clean), new_name)})
    except Exception as e:
        return json_error(str(e), 400)


@app.post("/api/fm/open")
def fm_open():
    if not _check_pin():
        return jsonify({"ok": False, "error": "PIN غير صحيح"}), 401
    data = request.get_json(force=True, silent=True) or {}
    root = data.get("root", "exchange")
    rel = data.get("path", "")
    try:
        _, target, rel_clean = resolve_safe(root, rel)
        if not rel_clean or not os.path.exists(target):
            return json_error("العنصر غير موجود", 404)
        os.startfile(target)
        log_event("open", f"فتح ملف على الحاسبة: {rel_clean}", client_ip())
        return jsonify({"ok": True})
    except Exception as e:
        return json_error(str(e), 400)


@app.get("/api/info")
def info():
    cfg = load_config()
    return jsonify({
        "app": "SatLink Remote PRO",
        "developer": "مهند سات لنك",
        "version": APP_VERSION,
        "device_id": cfg["device_id"],
        "device_name": cfg["device_name"],
        "require_pin": cfg.get("require_pin", True),
        "status": "online",
        "files_dir": safe_files_dir(),
        "enabled": server_state.get("enabled", False),
        "last_client": server_state.get("last_client", "")
    })


@app.post("/api/auth")
def auth():
    if not _check_pin():
        return jsonify({"ok": False, "error": "PIN غير صحيح"}), 401
    server_state["last_client"] = client_ip()
    log_event("auth", "تم تسجيل دخول من التطبيق", server_state["last_client"])
    return jsonify({"ok": True})




@app.get("/api/status")
def status():
    cfg = load_config()
    return jsonify({
        "ok": True,
        "app": "SatLink Remote PRO",
        "developer": "مهند سات لنك",
        "version": APP_VERSION,
        "device_id": cfg.get("device_id", ""),
        "device_name": cfg.get("device_name", ""),
        "running": server_state.get("running", False),
        "enabled": server_state.get("enabled", False),
        "last_client": server_state.get("last_client", ""),
        "started_at": server_state.get("started_at"),
    })


@app.get("/api/logs")
def logs():
    if not _check_pin():
        return jsonify({"ok": False, "error": "PIN غير صحيح"}), 401
    return jsonify({"ok": True, "logs": read_recent_logs(60)})


@app.get("/api/screenshot")
def screenshot():
    """Speed Engine v2.0.0
    The phone controls quality/scale/FPS. This endpoint focuses on fast capture + fast JPEG.
    Safe note: still requires PIN and the desktop agent must be enabled from the PC.
    """
    if not _check_pin():
        return jsonify({"ok": False, "error": "PIN غير صحيح"}), 401
    quality = int(request.args.get("quality", "50"))
    quality = max(25, min(85, quality))
    scale = float(request.args.get("scale", "0.55"))
    scale = max(0.20, min(1.0, scale))
    max_width = int(request.args.get("max_width", "0") or "0")
    fast = str(request.args.get("fast", "1")).lower() in ("1", "true", "yes")
    gray = str(request.args.get("gray", "0")).lower() in ("1", "true", "yes")

    with_cursor = str(request.args.get("cursor", "0")).lower() in ("1", "true", "yes")

    t0 = time.perf_counter()
    try:
        with mss() as sct:
            mon = sct.monitors[1]
            raw = sct.grab(mon)
            img = Image.frombytes("RGB", raw.size, raw.rgb)
    except Exception:
        # Fallback لبعض الأجهزة إذا فشل MSS أو ظهرت شاشة سوداء بسبب التعريفات.
        img = ImageGrab.grab().convert("RGB")
    capture_ms = int((time.perf_counter() - t0) * 1000)
    # mouse position is in logical pixels; screenshot may be in physical pixels (DPI scaling)
    logical_w, logical_h = pyautogui.size()
    cursor_sx = img.width / max(1, logical_w)
    cursor_sy = img.height / max(1, logical_h)

    if gray:
        img = img.convert("L").convert("RGB")

    target_w = max(1, int(img.width * scale))
    target_h = max(1, int(img.height * scale))
    if max_width > 0 and target_w > max_width:
        ratio = max_width / float(target_w)
        target_w = max(1, int(target_w * ratio))
        target_h = max(1, int(target_h * ratio))
    if target_w != img.width or target_h != img.height:
        resample = Image.Resampling.BILINEAR if fast else Image.Resampling.LANCZOS
        ratio_x = target_w / float(img.width)
        ratio_y = target_h / float(img.height)
        img = img.resize((target_w, target_h), resample)
        cursor_sx *= ratio_x
        cursor_sy *= ratio_y
    if with_cursor:
        draw_cursor(img, cursor_sx, cursor_sy)

    t1 = time.perf_counter()
    buf = io.BytesIO()
    # optimize=True gives smaller images but costs CPU. In Speed Engine we default to fast encode.
    img.save(buf, format="JPEG", quality=quality, optimize=not fast, progressive=False, subsampling=2)
    encode_ms = int((time.perf_counter() - t1) * 1000)
    buf.seek(0)
    resp = send_file(buf, mimetype="image/jpeg", max_age=0)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["X-SatLink-Capture-Ms"] = str(capture_ms)
    resp.headers["X-SatLink-Encode-Ms"] = str(encode_ms)
    resp.headers["X-SatLink-Image-Size"] = f"{img.width}x{img.height}"
    return resp


@app.post("/api/input")
def input_event():
    if not _check_pin():
        return jsonify({"ok": False, "error": "PIN غير صحيح"}), 401
    data = request.get_json(force=True, silent=True) or {}
    action = data.get("action")
    sw = int(data.get("screen_width", 1))
    sh = int(data.get("screen_height", 1))
    x = float(data.get("x", 0))
    y = float(data.get("y", 0))
    real_w, real_h = pyautogui.size()
    rx = max(0, min(real_w - 1, int(x / max(1, sw) * real_w)))
    ry = max(0, min(real_h - 1, int(y / max(1, sh) * real_h)))
    try:
        if action == "move":
            pyautogui.moveTo(rx, ry, duration=0)
        elif action == "tap":
            pyautogui.click(rx, ry)
        elif action == "mouse_down":
            pyautogui.moveTo(rx, ry, duration=0)
            pyautogui.mouseDown()
        elif action == "mouse_up":
            pyautogui.moveTo(rx, ry, duration=0)
            pyautogui.mouseUp()
        elif action == "right_click":
            pyautogui.click(rx, ry, button="right")
        elif action == "double_click":
            pyautogui.doubleClick(rx, ry)
        elif action == "scroll":
            amount = int(data.get("amount", 0))
            if amount:
                pyautogui.moveTo(rx, ry, duration=0)
                wheel(max(-20, min(20, amount)))
        # ---- actions at the current cursor position (Touchpad mode / buttons) ----
        elif action == "move_rel":
            dx = float(data.get("dx", 0)) / max(1, sw) * real_w
            dy = float(data.get("dy", 0)) / max(1, sh) * real_h
            cx, cy = pyautogui.position()
            nx = max(0, min(real_w - 1, int(round(cx + dx))))
            ny = max(0, min(real_h - 1, int(round(cy + dy))))
            pyautogui.moveTo(nx, ny, duration=0)
        elif action == "click_here":
            pyautogui.click()
        elif action == "right_here":
            pyautogui.click(button="right")
        elif action == "middle_here":
            pyautogui.click(button="middle")
        elif action == "double_here":
            pyautogui.doubleClick()
        elif action == "down_here":
            pyautogui.mouseDown()
        elif action == "up_here":
            pyautogui.mouseUp()
        elif action == "scroll_here":
            amount = int(data.get("amount", 0))
            if amount:
                wheel(max(-20, min(20, amount)))
        elif action == "key":
            key = str(data.get("key", "")).lower()
            if key not in ALLOWED_KEYS:
                return jsonify({"ok": False, "error": "مفتاح غير معروف"}), 400
            pyautogui.press(key)
        elif action == "hotkey":
            keys = [str(k).lower() for k in (data.get("keys") or [])][:4]
            if not keys or any(k not in ALLOWED_KEYS for k in keys):
                return jsonify({"ok": False, "error": "اختصار غير معروف"}), 400
            pyautogui.hotkey(*keys)
        elif action == "text":
            text = str(data.get("text", ""))[:2000]
            if text:
                type_unicode(text)
        else:
            return jsonify({"ok": False, "error": "أمر غير معروف"}), 400
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/api/power")
def power_action():
    """Lock / sleep / restart / shutdown. Requires PIN; restart & shutdown wait 10 seconds and can be cancelled."""
    if not _check_pin():
        return jsonify({"ok": False, "error": "PIN غير صحيح"}), 401
    if not IS_WINDOWS:
        return jsonify({"ok": False, "error": "متاح على Windows فقط"}), 400
    data = request.get_json(force=True, silent=True) or {}
    action = str(data.get("action", "")).lower()
    no_window = 0x08000000  # CREATE_NO_WINDOW
    try:
        if action == "lock":
            ctypes.windll.user32.LockWorkStation()
        elif action == "sleep":
            # reply first, then sleep a moment later so the phone gets the answer
            threading.Timer(1.5, lambda: ctypes.windll.powrprof.SetSuspendState(0, 1, 0)).start()
        elif action == "restart":
            subprocess.Popen(["shutdown", "/r", "/t", "10", "/c", "SatLink Remote PRO: Restart"], creationflags=no_window)
        elif action == "shutdown":
            subprocess.Popen(["shutdown", "/s", "/t", "10", "/c", "SatLink Remote PRO: Shutdown"], creationflags=no_window)
        elif action == "cancel":
            subprocess.Popen(["shutdown", "/a"], creationflags=no_window)
        else:
            return jsonify({"ok": False, "error": "أمر غير معروف"}), 400
        log_event("power", f"أمر طاقة: {action}", client_ip())
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/api/clipboard")
def clipboard_set():
    if not _check_pin():
        return jsonify({"ok": False, "error": "PIN غير صحيح"}), 401
    data = request.get_json(force=True, silent=True) or {}
    text = str(data.get("text", ""))[:1000]
    if text:
        type_unicode(text)
    return jsonify({"ok": True})


@app.get("/api/files/info")
def files_info():
    if not _check_pin():
        return jsonify({"ok": False, "error": "PIN غير صحيح"}), 401
    return jsonify({"ok": True, "folder": safe_files_dir(), "max_upload_mb": MAX_UPLOAD_MB})


@app.get("/api/files/list")
def files_list():
    if not _check_pin():
        return jsonify({"ok": False, "error": "PIN غير صحيح"}), 401
    folder = safe_files_dir()
    items = []
    for name in sorted(os.listdir(folder), key=lambda n: os.path.getmtime(os.path.join(folder, n)), reverse=True):
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        st = os.stat(path)
        items.append({
            "name": name,
            "size": st.st_size,
            "modified": int(st.st_mtime)
        })
    return jsonify({"ok": True, "folder": folder, "files": items})


@app.post("/api/files/upload")
def files_upload():
    if not _check_pin():
        return jsonify({"ok": False, "error": "PIN غير صحيح"}), 401
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "لم يصل أي ملف"}), 400
    f = request.files["file"]
    folder = safe_files_dir()
    target = unique_path(folder, f.filename or "uploaded.bin")
    max_bytes = MAX_UPLOAD_MB * 1024 * 1024
    total = 0
    with open(target, "wb") as out:
        while True:
            chunk = f.stream.read(1024 * 256)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                out.close()
                try:
                    os.remove(target)
                except Exception:
                    pass
                return jsonify({"ok": False, "error": f"حجم الملف أكبر من {MAX_UPLOAD_MB}MB"}), 413
            out.write(chunk)
    log_event("upload", f"رفع ملف إلى مجلد التبادل: {os.path.basename(target)}", client_ip())
    return jsonify({"ok": True, "name": os.path.basename(target), "size": total, "folder": folder})


@app.get("/api/files/download")
def files_download():
    if not _check_pin():
        return jsonify({"ok": False, "error": "PIN غير صحيح"}), 401
    name = safe_name(request.args.get("name", ""))
    path = os.path.join(safe_files_dir(), name)
    if not os.path.isfile(path):
        return jsonify({"ok": False, "error": "الملف غير موجود"}), 404
    log_event("download", f"تحميل ملف من مجلد التبادل: {name}", client_ip())
    return send_file(path, as_attachment=True, download_name=name, max_age=0)


@app.post("/api/files/delete")
def files_delete():
    if not _check_pin():
        return jsonify({"ok": False, "error": "PIN غير صحيح"}), 401
    data = request.get_json(force=True, silent=True) or {}
    name = safe_name(str(data.get("name", "")))
    path = os.path.join(safe_files_dir(), name)
    if not os.path.isfile(path):
        return jsonify({"ok": False, "error": "الملف غير موجود"}), 404
    os.remove(path)
    log_event("delete", f"حذف ملف من مجلد التبادل: {name}", client_ip())
    return jsonify({"ok": True})


def discovery_loop(stop_event: threading.Event, port: int):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("", DISCOVERY_PORT))
        sock.settimeout(1.0)
        while not stop_event.is_set():
            try:
                data, addr = sock.recvfrom(4096)
            except socket.timeout:
                continue
            if data != DISCOVERY_MAGIC:
                continue
            if not server_state.get("enabled", False):
                continue
            cfg = load_config()
            payload = json.dumps({
                "app": "SatLink Remote PRO",
                "device_id": cfg["device_id"],
                "device_name": cfg["device_name"],
                "port": port,
                "version": APP_VERSION
            }, ensure_ascii=False).encode("utf-8")
            sock.sendto(payload, addr)
    finally:
        sock.close()


def run_http(port: int):
    serve(app, host="0.0.0.0", port=port, threads=8)


class ServerController:
    def __init__(self):
        self.http_thread: Optional[threading.Thread] = None
        self.discovery_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

    def start(self):
        cfg = load_config()
        port = int(cfg.get("port", 47655))
        if self.http_thread and self.http_thread.is_alive():
            return port
        self.stop_event.clear()
        safe_files_dir()
        self.discovery_thread = threading.Thread(target=discovery_loop, args=(self.stop_event, port), daemon=True)
        self.discovery_thread.start()
        self.http_thread = threading.Thread(target=run_http, args=(port,), daemon=True)
        self.http_thread.start()
        server_state["running"] = True
        server_state["enabled"] = True
        server_state["started_at"] = time.time()
        log_event("start", f"تم تشغيل الاتصال على المنفذ {port}", "localhost")
        return port

    def enable(self):
        cfg = load_config()
        port = int(cfg.get("port", 47655))
        if not (self.http_thread and self.http_thread.is_alive()):
            self.start()
        else:
            server_state["enabled"] = True
            log_event("start", "تم تفعيل الاتصال", "localhost")
        return port

    def disable(self):
        server_state["enabled"] = False
        log_event("stop", "تم إيقاف قبول الاتصالات من البرنامج", "localhost")


if __name__ == "__main__":
    c = ServerController()
    p = c.start()
    print(f"SatLink Remote PRO running on port {p}")
    print(f"Files folder: {safe_files_dir()}")
    while True:
        time.sleep(10)
