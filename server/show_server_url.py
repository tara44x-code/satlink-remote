import socket, json, os

def local_ip_for_lan():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

cfg_path = os.path.join(os.path.dirname(__file__), "server_config.json")
port = 7777
try:
    with open(cfg_path, "r", encoding="utf-8") as f:
        port = int(json.load(f).get("port", 7777))
except Exception:
    pass
print("http://%s:%s" % (local_ip_for_lan(), port))
