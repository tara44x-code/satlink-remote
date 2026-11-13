import base64
import json
import os
import threading
import sys
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from waitress import serve

APP_VERSION = "PRO 2.3.0 Neon"
if getattr(sys, "frozen", False):
    RUNTIME_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    RUNTIME_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(RUNTIME_DIR, "server_config.json")




def local_ip_for_lan():
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        return "127.0.0.1"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        cfg = {
            "host": "0.0.0.0",
            "port": 7777,
            "owner_token": "SLR-CHANGE-ME-PRO-2026",
            "max_body_mb": 300,
            "request_timeout_seconds": 180,
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return cfg
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


cfg = load_config()
OWNER_TOKEN = str(cfg.get("owner_token", "")).strip()
MAX_BODY_MB = max(int(cfg.get("max_body_mb", 300)), 300)
MAX_BODY = MAX_BODY_MB * 1024 * 1024
REQUEST_TIMEOUT = max(int(cfg.get("request_timeout_seconds", 180)), 180)

app = Flask(__name__)
CORS(app)

# device_id -> device info
DEVICES: Dict[str, Dict[str, Any]] = {}
# device_id -> list of task dicts
TASKS: Dict[str, list] = {}
# request_id -> response dict
RESPONSES: Dict[str, Dict[str, Any]] = {}
COND = threading.Condition()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def clean_token(t: str) -> str:
    return str(t or "").strip()


def token_from_request() -> str:
    return clean_token(request.headers.get("X-SatLink-Token") or request.args.get("token") or "")


def require_token():
    token = token_from_request()
    if not OWNER_TOKEN or token != OWNER_TOKEN:
        return False
    return True


def json_error(message: str, status: int = 400):
    return jsonify({"ok": False, "error": message}), status


@app.get("/")
def home():
    return jsonify({
        "ok": True,
        "app": "SatLink Remote PRO Relay Server",
        "version": APP_VERSION,
        "message": "السيرفر يعمل. استخدم نفس Owner Token في برنامج الحاسبة وتطبيق الموبايل.",
        "online_devices": len([d for d in DEVICES.values() if time.time() - d.get("last_seen_ts", 0) < 45]),
    })


@app.post("/api/agent/register")
def agent_register():
    if not require_token():
        return json_error("Owner Token غير صحيح", 401)
    data = request.get_json(force=True, silent=True) or {}
    device_id = str(data.get("device_id", "")).strip()
    if not device_id:
        return json_error("device_id مفقود", 400)
    info = {
        "device_id": device_id,
        "device_name": str(data.get("device_name", "حاسبتي")),
        "version": str(data.get("version", "PRO")),
        "last_seen": now(),
        "last_seen_ts": time.time(),
        "agent_ip": request.remote_addr,
        "relay_mode": True,
    }
    DEVICES[device_id] = info
    TASKS.setdefault(device_id, [])
    with COND:
        COND.notify_all()
    return jsonify({"ok": True, "device": info})


@app.get("/api/agent/poll")
def agent_poll():
    if not require_token():
        return json_error("Owner Token غير صحيح", 401)
    device_id = str(request.args.get("device_id", "")).strip()
    if not device_id:
        return json_error("device_id مفقود", 400)
    if device_id in DEVICES:
        DEVICES[device_id]["last_seen"] = now()
        DEVICES[device_id]["last_seen_ts"] = time.time()
    else:
        DEVICES[device_id] = {"device_id": device_id, "device_name": device_id, "version": "PRO", "last_seen": now(), "last_seen_ts": time.time(), "relay_mode": True}
    deadline = time.time() + 25
    with COND:
        while time.time() < deadline:
            q = TASKS.setdefault(device_id, [])
            if q:
                task = q.pop(0)
                return jsonify({"ok": True, "task": task})
            COND.wait(timeout=2)
    return jsonify({"ok": True, "task": None})


@app.post("/api/agent/respond")
def agent_respond():
    if not require_token():
        return json_error("Owner Token غير صحيح", 401)
    data = request.get_json(force=True, silent=True) or {}
    request_id = str(data.get("request_id", "")).strip()
    if not request_id:
        return json_error("request_id مفقود", 400)
    with COND:
        RESPONSES[request_id] = data
        COND.notify_all()
    return jsonify({"ok": True})


@app.get("/api/mobile/devices")
def mobile_devices():
    if not require_token():
        return json_error("Owner Token غير صحيح", 401)
    out = []
    now_ts = time.time()
    for d in DEVICES.values():
        dd = dict(d)
        dd["online"] = (now_ts - dd.get("last_seen_ts", 0)) < 45
        out.append(dd)
    out.sort(key=lambda x: (not x.get("online", False), x.get("device_name", "")))
    return jsonify({"ok": True, "version": APP_VERSION, "devices": out})


def enqueue_and_wait(device_id: str, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    request_id = task["request_id"]
    with COND:
        TASKS.setdefault(device_id, []).append(task)
        COND.notify_all()
        deadline = time.time() + REQUEST_TIMEOUT
        while time.time() < deadline:
            if request_id in RESPONSES:
                return RESPONSES.pop(request_id, None)
            COND.wait(timeout=1)
    return None


@app.route("/api/relay/<path_token>/<device_id>/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE"])
def relay_with_path_token(path_token, device_id, subpath):
    if clean_token(path_token) != OWNER_TOKEN:
        return json_error("Owner Token غير صحيح", 401)
    return _relay_core(device_id, subpath)


@app.route("/api/relay/<device_id>/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE"])
def relay(device_id, subpath):
    if not require_token():
        return json_error("Owner Token غير صحيح", 401)
    return _relay_core(device_id, subpath)


def _relay_core(device_id, subpath):
    dev = DEVICES.get(device_id)
    if not dev or time.time() - dev.get("last_seen_ts", 0) > 60:
        return json_error("الجهاز غير متصل بالـ Relay", 503)

    raw_body = request.get_data(cache=False) or b""
    if len(raw_body) > MAX_BODY:
        return json_error(f"حجم الطلب أكبر من الحد المسموح {MAX_BODY_MB}MB", 413)

    safe_headers = {}
    for key in ["Content-Type", "X-SatLink-PIN", "Accept"]:
        value = request.headers.get(key)
        if value:
            safe_headers[key] = value

    # لا نرسل owner token للبرنامج المحلي؛ فقط PIN ورأس المحتوى.
    query = {k: request.args.getlist(k) for k in request.args.keys() if k != "token"}
    task = {
        "request_id": str(uuid.uuid4()),
        "method": request.method,
        "path": "/" + subpath.lstrip("/"),
        "query": query,
        "headers": safe_headers,
        "body_b64": base64.b64encode(raw_body).decode("ascii"),
        "created_at": now(),
    }
    resp = enqueue_and_wait(device_id, task)
    if not resp:
        return json_error("انتهت مهلة انتظار رد الحاسبة", 504)
    status = int(resp.get("status", 500))
    body = base64.b64decode(resp.get("body_b64", "") or b"")
    headers = resp.get("headers", {}) or {}
    content_type = headers.get("Content-Type") or headers.get("content-type") or "application/octet-stream"
    out = Response(body, status=status, content_type=content_type)
    cd = headers.get("Content-Disposition") or headers.get("content-disposition")
    if cd:
        out.headers["Content-Disposition"] = cd
    return out


if __name__ == "__main__":
    print("SatLink Remote PRO Relay Server")
    print("Version:", APP_VERSION)
    print("Host:", cfg.get("host", "0.0.0.0"), "Port:", int(cfg.get("port", 7777)))
    print("Owner Token:", OWNER_TOKEN)
    print("Max upload via Relay:", str(MAX_BODY_MB) + "MB", "Timeout:", str(REQUEST_TIMEOUT) + "s")
    print("افتح من الهاتف/التطبيق:", "http://%s:%s" % (local_ip_for_lan(), int(cfg.get("port", 7777))))
    serve(app, host=cfg.get("host", "0.0.0.0"), port=int(cfg.get("port", 7777)), threads=16)
