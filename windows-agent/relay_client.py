import base64
import json
import os
import time
from urllib.parse import urlencode

import requests

from device_identity import load_config, APP_DIR

APP_VERSION = "PRO 2.2.4 Relay Client"
CONFIG_FILE = os.path.join(APP_DIR, "relay_config.json")
STATUS_FILE = os.path.join(APP_DIR, "relay_status.json")


def write_status(state, message="", relay_url="", local_url=""):
    try:
        os.makedirs(APP_DIR, exist_ok=True)
        data = {
            "state": state,
            "message": message,
            "relay_server_url": relay_url,
            "local_agent_url": local_url,
            "time": time.time(),
        }
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_relay_config():
    os.makedirs(APP_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_FILE):
        cfg = {
            "enabled": True,
            "relay_server_url": "http://127.0.0.1:7777",
            "owner_token": "SLR-CHANGE-ME-PRO-2026",
            "local_agent_url": "http://127.0.0.1:47655",
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return cfg
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def norm_url(url):
    return str(url or "").strip().rstrip("/")


def headers(token):
    return {"X-SatLink-Token": token, "Content-Type": "application/json; charset=utf-8"}


def register(relay_url, token, local_url):
    cfg = load_config()
    payload = {
        "device_id": cfg.get("device_id", ""),
        "device_name": cfg.get("device_name", "حاسبتي"),
        "version": "PRO 2.2.4",
        "local_url": local_url,
    }
    r = requests.post(relay_url + "/api/agent/register", headers=headers(token), json=payload, timeout=10)
    r.raise_for_status()
    return payload


def build_local_url(local_url, path, query):
    url = local_url + "/" + str(path or "").lstrip("/")
    pairs = []
    if isinstance(query, dict):
        for k, vals in query.items():
            if isinstance(vals, list):
                for v in vals:
                    pairs.append((k, v))
            else:
                pairs.append((k, vals))
    if pairs:
        url += "?" + urlencode(pairs)
    return url


def execute_task(local_url, task):
    method = str(task.get("method", "GET")).upper()
    url = build_local_url(local_url, task.get("path", "/api/status"), task.get("query", {}))
    req_headers = task.get("headers", {}) or {}
    # Remove unsafe hop-by-hop headers if any slipped in.
    for h in ["Host", "Content-Length", "Connection", "Transfer-Encoding"]:
        req_headers.pop(h, None)
    body = base64.b64decode(task.get("body_b64", "") or b"")
    try:
        resp = requests.request(method, url, headers=req_headers, data=body if body else None, timeout=240)
        body_bytes = resp.content or b""
        out_headers = {}
        for k in ["Content-Type", "content-type", "Content-Disposition", "content-disposition"]:
            if k in resp.headers:
                out_headers[k] = resp.headers.get(k)
        return {
            "request_id": task.get("request_id"),
            "ok": True,
            "status": resp.status_code,
            "headers": out_headers,
            "body_b64": base64.b64encode(body_bytes).decode("ascii"),
        }
    except Exception as e:
        msg = json.dumps({"ok": False, "error": "Relay Client: " + str(e)}, ensure_ascii=False).encode("utf-8")
        return {
            "request_id": task.get("request_id"),
            "ok": False,
            "status": 502,
            "headers": {"Content-Type": "application/json; charset=utf-8"},
            "body_b64": base64.b64encode(msg).decode("ascii"),
        }


def main(stop_event=None):
    rcfg = load_relay_config()
    if not rcfg.get("enabled", True):
        print("Relay Client متوقف من relay_config.json")
        return
    relay_url = norm_url(rcfg.get("relay_server_url"))
    token = str(rcfg.get("owner_token", "")).strip()
    local_url = norm_url(rcfg.get("local_agent_url", "http://127.0.0.1:47655"))
    if not relay_url or not token:
        print("اكتب relay_server_url و owner_token داخل relay_config.json")
        return
    print("SatLink Remote PRO Relay Client")
    print("Version:", APP_VERSION)
    print("Relay:", relay_url)
    print("Local Agent:", local_url)
    print("مهم: شغل برنامج الحاسبة أولاً واضغط تشغيل الاتصال.")
    write_status("starting", "Relay Client بدأ التشغيل", relay_url, local_url)
    last_register = 0
    while stop_event is None or not stop_event.is_set():
        try:
            if time.time() - last_register > 20:
                info = register(relay_url, token, local_url)
                print("مسجل على السيرفر:", info.get("device_name"), info.get("device_id"))
                write_status("online", "متصل بالسيرفر ومسجل", relay_url, local_url)
                last_register = time.time()
            write_status("online", "ينتظر طلبات التطبيق", relay_url, local_url)
            cfg = load_config()
            device_id = cfg.get("device_id", "")
            r = requests.get(
                relay_url + "/api/agent/poll",
                headers={"X-SatLink-Token": token},
                params={"device_id": device_id},
                timeout=240,
            )
            r.raise_for_status()
            data = r.json()
            task = data.get("task")
            if not task:
                continue
            print("طلب من التطبيق:", task.get("method"), task.get("path"), "الحجم:", len(task.get("body_b64", "") or ""), "b64")
            result = execute_task(local_url, task)
            rr = requests.post(relay_url + "/api/agent/respond", headers=headers(token), json=result, timeout=90)
            rr.raise_for_status()
        except KeyboardInterrupt:
            print("تم إيقاف Relay Client")
            write_status("stopped", "تم الإيقاف من المستخدم", relay_url, local_url)
            break
        except Exception as e:
            print("خطأ Relay:", e)
            write_status("error", str(e), relay_url, local_url)
            time.sleep(4)

    write_status("stopped", "تم إيقاف Relay Client", relay_url, local_url)


if __name__ == "__main__":
    main()
