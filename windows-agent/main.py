import os
import socket
import sys
import threading
import json
import time
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog

import qrcode
from PIL import Image, ImageDraw, ImageTk

from device_identity import (
    APP_DIR,
    APP_VERSION,
    check_master_pin,
    change_master_pin,
    load_config,
    pythonw_executable,
    rename_device,
    rotate_pin,
    save_config,
    set_bool_option,
)
from remote_server import ServerController, read_recent_logs, safe_files_dir, server_state, log_event
from neon_theme import apply_neon, neon_line, BG as NEON_BG
import relay_client

try:
    import winreg
except Exception:  # pragma: no cover
    winreg = None

try:
    import pystray
except Exception:  # pragma: no cover
    pystray = None

controller = ServerController()
APP_NAME = "SatLink Remote PRO"
REG_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_VALUE_NAME = "SatLinkRemotePRO"


def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def autostart_command() -> str:
    # When packaged, register the real EXE path, not PyInstaller's temporary path.
    if getattr(sys, "frozen", False):
        return f'"{os.path.abspath(sys.executable)}" --minimized --autostart'
    pythonw = pythonw_executable()
    script = os.path.abspath(__file__)
    return f'"{pythonw}" "{script}" --minimized --autostart'


def is_autostart_enabled() -> bool:
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, REG_VALUE_NAME)
            return bool(value)
    except Exception:
        return False


def registered_autostart_command() -> str:
    if winreg is None:
        return ""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, REG_VALUE_NAME)
            return str(value or "")
    except Exception:
        return ""


def ensure_default_autostart():
    """2.3.0: the program registers itself to start with Windows on first launch.
    The user can still turn it off from the button (with Master PIN) and it stays off.
    If the program folder was moved, the registered path is fixed automatically."""
    if winreg is None:
        return
    try:
        cfg = load_config()
        if not cfg.get("autostart_initialized", False):
            set_windows_autostart(True)
            cfg = load_config()
            cfg["autostart_initialized"] = True
            cfg["auto_start_windows"] = True
            save_config(cfg)
            log_event("autostart", "تم تفعيل التشغيل التلقائي مع Windows", "localhost")
        elif is_autostart_enabled() and registered_autostart_command() != autostart_command():
            set_windows_autostart(True)
    except Exception:
        pass


def set_windows_autostart(enabled: bool):
    if winreg is None:
        raise RuntimeError("تشغيل Windows التلقائي متاح فقط على Windows")
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, REG_VALUE_NAME, 0, winreg.REG_SZ, autostart_command())
        else:
            try:
                winreg.DeleteValue(key, REG_VALUE_NAME)
            except FileNotFoundError:
                pass



def runtime_folder() -> Path:
    """Folder containing the packaged EXE, or the project root in source mode."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def relay_server_port() -> int:
    cfg_path_candidates = [
        runtime_folder() / "server_config.json",
        runtime_folder() / "server" / "server_config.json",
        Path(__file__).resolve().parent.parent / "server" / "server_config.json",
    ]
    for path in cfg_path_candidates:
        try:
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                return int(data.get("port", 7777))
        except Exception:
            pass
    return 7777


def is_local_port_open(port: int, timeout: float = 0.35) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def _server_exe_candidates():
    base = runtime_folder()
    project = Path(__file__).resolve().parent.parent
    return [
        base / "SatLinkRelayServer.exe",
        base / "server" / "SatLinkRelayServer.exe",
        project / "server" / "dist" / "SatLinkRelayServer.exe",
        project / "server" / "dist-x64" / "SatLinkRelayServer_x64.exe",
        project / "server" / "dist-x86" / "SatLinkRelayServer_x86.exe",
    ]


def _server_script_candidates():
    project = Path(__file__).resolve().parent.parent
    return [
        runtime_folder() / "server" / "server_tray.py",
        project / "server" / "server_tray.py",
    ]


def start_adjacent_relay_server(wait_seconds: float = 8.0):
    """Start SatLinkRelayServer beside the main app and prevent duplicate instances."""
    port = relay_server_port()
    if is_local_port_open(port):
        return True, f"SatLinkRelayServer already running on port {port}", None

    flags = 0
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

    for exe in _server_exe_candidates():
        if exe.exists():
            try:
                proc = subprocess.Popen(
                    [str(exe), "--minimized", "--started-by-agent"],
                    cwd=str(exe.parent),
                    creationflags=flags,
                    close_fds=True,
                )
                break
            except Exception:
                proc = None
    else:
        proc = None
        for script in _server_script_candidates():
            if script.exists():
                try:
                    pyw = pythonw_executable()
                    proc = subprocess.Popen(
                        [pyw, str(script), "--minimized", "--started-by-agent"],
                        cwd=str(script.parent),
                        creationflags=flags,
                        close_fds=True,
                    )
                    break
                except Exception:
                    proc = None

    if proc is None:
        return False, "SatLinkRelayServer.exe or server_tray.py was not found beside the program", None

    deadline = time.time() + max(1.0, wait_seconds)
    while time.time() < deadline:
        if is_local_port_open(port):
            return True, f"SatLinkRelayServer started on port {port}", proc
        if proc.poll() is not None:
            return False, "SatLinkRelayServer stopped during startup", proc
        time.sleep(0.25)
    return False, f"SatLinkRelayServer did not open port {port}", proc

def make_tray_image():
    img = Image.new("RGB", (64, 64), "#05060f")
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((6, 6, 58, 58), radius=14, fill="#0e1022", outline="#00f0ff", width=3)
    d.rounded_rectangle((10, 10, 54, 54), radius=11, outline="#ff2bd6", width=1)
    d.text((22, 18), "SL", fill="#39ff88")
    d.rectangle((16, 42, 32, 46), fill="#00f0ff")
    d.rectangle((32, 42, 48, 46), fill="#ff2bd6")
    return img


def read_relay_status():
    path = os.path.join(APP_DIR, "relay_status.json")
    try:
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}


def is_relay_status_alive(data, max_age=60):
    try:
        ts = float(data.get("time", 0))
        state = str(data.get("state", ""))
        return state in ("starting", "online") and (time.time() - ts) <= max_age
    except Exception:
        return False


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SatLink Remote PRO - Windows Agent")
        self.geometry("940x845")
        self.configure(bg="#07111f")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_window_close)
        self.qr_img = None
        self.tray_icon = None
        self.relay_proc = None
        self.relay_server_proc = None
        self.relay_thread = None
        self.relay_stop_event = None
        self.cfg = load_config()
        self.port = self.cfg.get("port", 47655)
        self._watchdog_busy = False
        ensure_default_autostart()
        self.build_ui()
        apply_neon(self)
        self.refresh()
        self.setup_tray_icon()
        if self.cfg.get("start_relay_server_with_agent", True):
            self.after(100, lambda: self.ensure_relay_server(silent=True))
        if self.cfg.get("run_server_on_app_start", True) or "--autostart" in sys.argv:
            self.start_server(silent=True)
        if self.cfg.get("relay_auto_start", True) or "--autostart" in sys.argv:
            self.after(2600, lambda: self.start_relay_client(silent=True))
        if "--minimized" in sys.argv:
            self.after(800, self.hide_to_tray)
        self.after(2500, self.refresh_log_loop)
        self.after(20000, self.watchdog_loop)

    # ---------------- Watchdog 2.3.0 ----------------
    def watchdog_loop(self):
        """Every 15 seconds: restart SatLinkRelayServer / local connection / Relay client if they stopped."""
        try:
            if not self._watchdog_busy:
                threading.Thread(target=self._watchdog_check, daemon=True).start()
        finally:
            self.after(15000, self.watchdog_loop)

    def _watchdog_check(self):
        self._watchdog_busy = True
        try:
            cfg = load_config()
            if cfg.get("start_relay_server_with_agent", True) and not is_local_port_open(relay_server_port()):
                ok, message, proc = start_adjacent_relay_server()
                if proc is not None:
                    self.relay_server_proc = proc
                log_event("watchdog", ("أعاد تشغيل السيرفر: " if ok else "فشل إعادة تشغيل السيرفر: ") + message, "localhost")
            if server_state.get("enabled") and controller.http_thread is not None and not controller.http_thread.is_alive():
                controller.http_thread = None
                controller.start()
                log_event("watchdog", "أعاد تشغيل خدمة الاتصال المحلي", "localhost")
            relay_dead = self.relay_stop_event is not None and not self.relay_stop_event.is_set() and (
                self.relay_thread is None or not self.relay_thread.is_alive())
            if cfg.get("relay_auto_start", True) and relay_dead:
                self.relay_thread = None
                self.after(0, lambda: self.start_relay_client(silent=True))
                log_event("watchdog", "أعاد تشغيل Relay Client", "localhost")
        except Exception as e:
            log_event("watchdog", f"خطأ: {e}", "localhost")
        finally:
            self._watchdog_busy = False

    def build_ui(self):
        header = tk.Frame(self, bg="#07111f")
        header.place(x=20, y=15, width=885, height=72)
        tk.Label(header, text="SatLink Remote PRO", bg="#07111f", fg="#4aa3ff", font=("Segoe UI", 24, "bold")).place(x=0, y=0)
        tk.Label(header, text="Windows Agent", bg="#07111f", fg="#5ff59a", font=("Segoe UI", 12, "bold")).place(x=320, y=12)
        tk.Label(header, text="آمن • سريع • اتصال مباشر أو Relay", bg="#07111f", fg="#8ebeff", font=("Segoe UI", 10)).place(x=320, y=38)
        tk.Label(self, text=f"المطور: مهند سات لنك   |   الإصدار: {APP_VERSION}", bg="#07111f", fg="#c7d7ec", font=("Segoe UI", 11)).place(x=25, y=76)
        neon_line(self, 25, 101, 860)

        self.name_var = tk.StringVar()
        self.id_var = tk.StringVar()
        self.pin_var = tk.StringVar()
        self.status_var = tk.StringVar(value="متوقف")
        self.ip_var = tk.StringVar()
        self.folder_var = tk.StringVar()
        self.autostart_var = tk.StringVar()
        self.server_start_var = tk.StringVar()
        self.relay_server_start_var = tk.StringVar()
        self.tray_var = tk.StringVar()
        self.master_hint_var = tk.StringVar()
        self.relay_status_var = tk.StringVar(value="Relay غير مشغل")
        self.relay_info_var = tk.StringVar()

        info = tk.Frame(self, bg="#0d1b2f", highlightbackground="#1c416b", highlightthickness=1)
        info.place(x=25, y=110, width=520, height=385)

        tk.Label(info, text="اسم الحاسبة", bg="#0d1b2f", fg="#8ebeff", font=("Segoe UI", 11)).place(x=20, y=18)
        tk.Label(info, textvariable=self.name_var, bg="#0d1b2f", fg="#ffffff", font=("Segoe UI", 18, "bold")).place(x=20, y=43)
        tk.Button(info, text="تغيير الاسم", command=self.change_name, bg="#1f6feb", fg="white", relief="flat", font=("Segoe UI", 10)).place(x=382, y=45, width=105, height=32)

        tk.Label(info, text="هوية الجهاز الثابتة", bg="#0d1b2f", fg="#8ebeff", font=("Segoe UI", 11)).place(x=20, y=92)
        tk.Label(info, textvariable=self.id_var, bg="#0d1b2f", fg="#ffffff", font=("Segoe UI", 17, "bold")).place(x=20, y=117)

        tk.Label(info, text="PIN الدخول", bg="#0d1b2f", fg="#8ebeff", font=("Segoe UI", 11)).place(x=20, y=165)
        tk.Label(info, textvariable=self.pin_var, bg="#0d1b2f", fg="#5ff59a", font=("Segoe UI", 22, "bold")).place(x=20, y=188)
        tk.Button(info, text="تغيير PIN", command=self.change_pin, bg="#17263d", fg="white", relief="flat", font=("Segoe UI", 10)).place(x=382, y=196, width=105, height=32)

        tk.Label(info, text="مجلد تبادل الملفات", bg="#0d1b2f", fg="#8ebeff", font=("Segoe UI", 11)).place(x=20, y=246)
        tk.Label(info, textvariable=self.folder_var, bg="#0d1b2f", fg="#c7d7ec", font=("Segoe UI", 9), wraplength=355, justify="left").place(x=20, y=270)
        tk.Button(info, text="فتح المجلد", command=self.open_files_folder, bg="#17263d", fg="white", relief="flat", font=("Segoe UI", 10)).place(x=382, y=270, width=105, height=32)

        tk.Label(info, text="الحالة", bg="#0d1b2f", fg="#8ebeff", font=("Segoe UI", 11)).place(x=20, y=316)
        tk.Label(info, textvariable=self.status_var, bg="#0d1b2f", fg="#5ff59a", font=("Segoe UI", 13, "bold")).place(x=20, y=339)
        tk.Label(info, textvariable=self.ip_var, bg="#0d1b2f", fg="#c7d7ec", font=("Segoe UI", 10)).place(x=240, y=342)

        self.qr_label = tk.Label(self, bg="#07111f")
        self.qr_label.place(x=635, y=120)
        tk.Label(self, text="امسح QR أو استخدم البحث التلقائي من التطبيق", bg="#07111f", fg="#c7d7ec", font=("Segoe UI", 10)).place(x=590, y=355)
        tk.Label(self, text="v2.3.0 Neon: تشغيل تلقائي مع Windows + حارس للسيرفر", bg="#07111f", fg="#8ebeff", font=("Segoe UI", 10)).place(x=580, y=382)

        settings = tk.Frame(self, bg="#0d1b2f", highlightbackground="#1c416b", highlightthickness=1)
        settings.place(x=25, y=500, width=520, height=185)
        tk.Label(settings, text="إعدادات التشغيل والحماية", bg="#0d1b2f", fg="#8ebeff", font=("Segoe UI", 13, "bold")).place(x=20, y=15)
        tk.Label(settings, textvariable=self.autostart_var, bg="#0d1b2f", fg="#c7d7ec", font=("Segoe UI", 10)).place(x=20, y=44)
        tk.Label(settings, textvariable=self.server_start_var, bg="#0d1b2f", fg="#c7d7ec", font=("Segoe UI", 10)).place(x=20, y=68)
        tk.Label(settings, textvariable=self.relay_server_start_var, bg="#0d1b2f", fg="#c7d7ec", font=("Segoe UI", 10)).place(x=20, y=92)
        tk.Label(settings, textvariable=self.tray_var, bg="#0d1b2f", fg="#c7d7ec", font=("Segoe UI", 10)).place(x=20, y=116)
        tk.Label(settings, textvariable=self.master_hint_var, bg="#0d1b2f", fg="#ffcc66", font=("Segoe UI", 9)).place(x=20, y=145)

        tk.Button(settings, text="تشغيل مع Windows", command=self.toggle_autostart, bg="#1f6feb", fg="white", relief="flat", font=("Segoe UI", 10)).place(x=350, y=14, width=135, height=30)
        tk.Button(settings, text="الاتصال مع البرنامج", command=self.toggle_server_start, bg="#17263d", fg="white", relief="flat", font=("Segoe UI", 9)).place(x=350, y=50, width=135, height=30)
        tk.Button(settings, text="السيرفر مع البرنامج", command=self.toggle_relay_server_with_agent, bg="#6f42c1", fg="white", relief="flat", font=("Segoe UI", 9)).place(x=350, y=86, width=135, height=30)
        tk.Button(settings, text="تغيير Master", command=self.change_master, bg="#17263d", fg="white", relief="flat", font=("Segoe UI", 10)).place(x=350, y=122, width=135, height=30)

        logs = tk.Frame(self, bg="#0d1b2f", highlightbackground="#1c416b", highlightthickness=1)
        logs.place(x=575, y=430, width=310, height=230)
        tk.Label(logs, text="آخر العمليات", bg="#0d1b2f", fg="#8ebeff", font=("Segoe UI", 13, "bold")).place(x=15, y=12)
        self.log_text = tk.Text(logs, bg="#07111f", fg="#c7d7ec", relief="flat", height=8, width=34, font=("Segoe UI", 8))
        self.log_text.place(x=15, y=45, width=250, height=165)
        self.log_text.configure(state="disabled")

        relay = tk.Frame(self, bg="#0d1b2f", highlightbackground="#1c416b", highlightthickness=1)
        relay.place(x=25, y=700, width=860, height=65)
        tk.Label(relay, text="Relay الاتصال من أي مكان", bg="#0d1b2f", fg="#8ebeff", font=("Segoe UI", 12, "bold")).place(x=15, y=8)
        tk.Label(relay, textvariable=self.relay_status_var, bg="#0d1b2f", fg="#5ff59a", font=("Segoe UI", 10, "bold")).place(x=15, y=35)
        tk.Label(relay, textvariable=self.relay_info_var, bg="#0d1b2f", fg="#c7d7ec", font=("Segoe UI", 9)).place(x=250, y=37)
        tk.Button(relay, text="Relay تلقائي", command=self.toggle_relay_auto_start, bg="#17263d", fg="white", relief="flat", font=("Segoe UI", 9)).place(x=405, y=16, width=105, height=34)
        tk.Button(relay, text="إعدادات Relay", command=self.edit_relay_settings, bg="#17263d", fg="white", relief="flat", font=("Segoe UI", 10)).place(x=520, y=16, width=110, height=34)
        tk.Button(relay, text="تشغيل Relay", command=self.start_relay_client, bg="#6f42c1", fg="white", relief="flat", font=("Segoe UI", 10, "bold")).place(x=645, y=16, width=95, height=34)
        tk.Button(relay, text="إيقاف Relay", command=self.stop_relay_client, bg="#792e2e", fg="white", relief="flat", font=("Segoe UI", 10, "bold")).place(x=750, y=16, width=95, height=34)

        tk.Button(self, text="تشغيل الاتصال", command=self.start_server, bg="#238636", fg="white", relief="flat", font=("Segoe UI", 13, "bold")).place(x=25, y=785, width=155, height=42)
        tk.Button(self, text="إيقاف الاتصال", command=self.stop_server, bg="#b1442f", fg="white", relief="flat", font=("Segoe UI", 13, "bold")).place(x=195, y=785, width=155, height=42)
        tk.Button(self, text="تصغير بجانب الساعة", command=self.hide_to_tray, bg="#17263d", fg="white", relief="flat", font=("Segoe UI", 12, "bold")).place(x=365, y=785, width=190, height=42)
        tk.Button(self, text="تحديث", command=self.refresh, bg="#1f6feb", fg="white", relief="flat", font=("Segoe UI", 12, "bold")).place(x=570, y=785, width=130, height=42)
        tk.Button(self, text="خروج", command=self.exit_app, bg="#792e2e", fg="white", relief="flat", font=("Segoe UI", 12, "bold")).place(x=715, y=785, width=170, height=42)

    def refresh(self):
        self.cfg = load_config()
        self.name_var.set(self.cfg["device_name"])
        self.id_var.set(self.cfg["device_id"])
        self.pin_var.set(str(self.cfg.get("pin", "")))
        self.ip_var.set(f"IP الحالي: {local_ip()}:{self.cfg.get('port', 47655)}")
        self.folder_var.set(safe_files_dir())
        enabled = bool(server_state.get("enabled", False))
        running = bool(server_state.get("running", False))
        if enabled:
            self.status_var.set(f"متصل ويقبل الاتصالات - Port {self.cfg.get('port', 47655)}")
        elif running:
            self.status_var.set("متوقف عن قبول الاتصالات")
        else:
            self.status_var.set("لم يتم تشغيل الاتصال")
        self.autostart_var.set("✓ تشغيل مع Windows مفعل" if is_autostart_enabled() else "× تشغيل مع Windows غير مفعل")
        self.server_start_var.set("✓ يبدأ الاتصال عند فتح البرنامج" if self.cfg.get("run_server_on_app_start", True) else "× لا يبدأ الاتصال إلا يدوياً")
        start_server_with_agent = self.cfg.get("start_relay_server_with_agent", True)
        server_running = is_local_port_open(relay_server_port())
        if start_server_with_agent and server_running:
            self.relay_server_start_var.set("✓ السيرفر يعمل ومحمي بالحارس")
        elif start_server_with_agent:
            self.relay_server_start_var.set("◌ SatLinkRelayServer سيبدأ تلقائياً مع البرنامج")
        else:
            self.relay_server_start_var.set("× تشغيل SatLinkRelayServer مع البرنامج معطل")
        self.tray_var.set("✓ زر الإغلاق يصغّر بجانب الساعة" if self.cfg.get("minimize_to_tray_on_close", True) else "× زر الإغلاق يغلق البرنامج")
        if self.cfg.get("master_pin") == "1234":
            self.master_hint_var.set("تنبيه: Master PIN الافتراضي هو 1234، غيّره من زر تغيير Master")
        else:
            self.master_hint_var.set("Master PIN مخصص ومحفوظ")
        relay_status = read_relay_status()
        relay_proc_running = self.relay_thread is not None and self.relay_thread.is_alive()
        relay_alive = relay_proc_running or is_relay_status_alive(relay_status)
        if relay_alive:
            self.relay_status_var.set("✓ Relay Client فعال ومتصل")
        elif relay_status.get("state") == "error":
            self.relay_status_var.set("⚠ Relay Client فيه خطأ")
        else:
            self.relay_status_var.set("× Relay Client غير فعال")
        relay_url = relay_status.get("relay_server_url") or self.cfg.get("relay_server_url", "")
        relay_msg = relay_status.get("message", "")
        auto_txt = "تلقائي" if self.cfg.get("relay_auto_start", False) else "يدوي"
        self.relay_info_var.set(f"{relay_url} | {relay_msg or 'Token محفوظ'} | {auto_txt}")
        data = f"satlink://add?ip={local_ip()}&port={self.cfg.get('port',47655)}&id={self.cfg['device_id']}&name={self.cfg['device_name']}"
        img = qrcode.make(data).resize((210, 210))
        self.qr_img = ImageTk.PhotoImage(img)
        self.qr_label.configure(image=self.qr_img)
        self.update_logs()

    def update_logs(self):
        logs = read_recent_logs(12)
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        if not logs:
            self.log_text.insert("end", "لا توجد عمليات بعد.\n")
        else:
            for row in logs:
                self.log_text.insert("end", f"{row.get('time','')}\n")
                self.log_text.insert("end", f"{row.get('type','')} - {row.get('message','')}\n")
                if row.get("client"):
                    self.log_text.insert("end", f"من: {row.get('client')}\n")
                self.log_text.insert("end", "-------------------------\n")
        self.log_text.configure(state="disabled")

    def refresh_log_loop(self):
        try:
            self.refresh()
        finally:
            self.after(3500, self.refresh_log_loop)

    def _ask_master(self, title="Master PIN") -> bool:
        cfg = load_config()
        if not cfg.get("lock_exit_with_master", True):
            return True
        pin = simpledialog.askstring(title, "أدخل Master PIN للحماية:", show="*")
        if pin is None:
            return False
        if check_master_pin(pin):
            return True
        messagebox.showerror("SatLink Remote PRO", "Master PIN غير صحيح")
        return False

    def start_server(self, silent=False):
        port = controller.enable()
        self.status_var.set(f"متصل ويقبل الاتصالات - Port {port}")
        self.refresh()
        if not silent:
            messagebox.showinfo("SatLink Remote PRO", "تم تشغيل الاتصال. ابحث من تطبيق الموبايل داخل نفس Wi‑Fi.")

    def stop_server(self):
        if not self._ask_master("إيقاف الاتصال"):
            return
        controller.disable()
        self.refresh()
        messagebox.showinfo("SatLink Remote PRO", "تم إيقاف قبول الاتصالات. البرنامج ما زال مفتوحاً ويمكن تشغيله من جديد.")

    def change_name(self):
        name = simpledialog.askstring("اسم الحاسبة", "اكتب الاسم الذي تريده للجهاز:", initialvalue=self.cfg.get("device_name", "حاسبتي"))
        if name:
            rename_device(name)
            self.refresh()

    def change_pin(self):
        if not self._ask_master("تغيير PIN"):
            return
        rotate_pin()
        self.refresh()
        messagebox.showinfo("PIN", "تم تغيير رمز الدخول. استخدم الرمز الجديد في التطبيق.")

    def change_master(self):
        if not self._ask_master("تغيير Master PIN"):
            return
        new_pin = simpledialog.askstring("Master PIN جديد", "اكتب Master PIN جديد 4 أرقام أو أكثر:", show="*")
        if not new_pin:
            return
        confirm = simpledialog.askstring("تأكيد Master PIN", "أعد كتابة Master PIN الجديد:", show="*")
        if new_pin != confirm:
            messagebox.showerror("SatLink Remote PRO", "الرمزان غير متطابقين")
            return
        try:
            change_master_pin(new_pin)
            self.refresh()
            messagebox.showinfo("SatLink Remote PRO", "تم تغيير Master PIN بنجاح")
        except Exception as e:
            messagebox.showerror("SatLink Remote PRO", str(e))

    def toggle_autostart(self):
        if not self._ask_master("تشغيل مع Windows"):
            return
        try:
            new_state = not is_autostart_enabled()
            set_windows_autostart(new_state)
            set_bool_option("auto_start_windows", new_state)
            self.refresh()
            msg = "تم تفعيل تشغيل البرنامج مع Windows" if new_state else "تم إلغاء تشغيل البرنامج مع Windows"
            messagebox.showinfo("SatLink Remote PRO", msg)
        except Exception as e:
            messagebox.showerror("SatLink Remote PRO", str(e))

    def toggle_server_start(self):
        if not self._ask_master("تشغيل الاتصال تلقائياً"):
            return
        cfg = load_config()
        cfg["run_server_on_app_start"] = not cfg.get("run_server_on_app_start", True)
        save_config(cfg)
        self.refresh()

    def ensure_relay_server(self, silent=False):
        ok, message, proc = start_adjacent_relay_server()
        if proc is not None:
            self.relay_server_proc = proc
        self.refresh()
        if not ok and not silent:
            messagebox.showerror("SatLinkRelayServer", message)
        elif ok and not silent:
            messagebox.showinfo("SatLinkRelayServer", message)
        return ok

    def toggle_relay_server_with_agent(self):
        if not self._ask_master("تشغيل SatLinkRelayServer مع البرنامج"):
            return
        cfg = load_config()
        enabled = not cfg.get("start_relay_server_with_agent", True)
        cfg["start_relay_server_with_agent"] = enabled
        save_config(cfg)
        if enabled:
            self.ensure_relay_server(silent=False)
        self.refresh()


    def _write_relay_config(self):
        cfg = load_config()
        path = os.path.join(APP_DIR, "relay_config.json")
        data = {
            "enabled": True,
            "relay_server_url": str(cfg.get("relay_server_url", "http://127.0.0.1:7777")).strip(),
            "owner_token": str(cfg.get("owner_token", "SLR-CHANGE-ME-PRO-2026")).strip(),
            "local_agent_url": f"http://127.0.0.1:{cfg.get('port', 47655)}"
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data

    def edit_relay_settings(self):
        if not self._ask_master("إعدادات Relay"):
            return
        cfg = load_config()
        url = simpledialog.askstring("Relay Server", "اكتب رابط السيرفر مثل:\nhttp://192.168.0.188:7777", initialvalue=cfg.get("relay_server_url", "http://127.0.0.1:7777"))
        if not url:
            return
        token = simpledialog.askstring("Owner Token", "اكتب نفس Owner Token الموجود بالسيرفر:", initialvalue=cfg.get("owner_token", "SLR-CHANGE-ME-PRO-2026"))
        if not token:
            return
        cfg["relay_server_url"] = url.strip().rstrip("/")
        cfg["owner_token"] = token.strip()
        save_config(cfg)
        self._write_relay_config()
        self.refresh()
        messagebox.showinfo("SatLink Remote PRO", "تم حفظ إعدادات Relay. الآن اضغط تشغيل Relay.")

    def start_relay_client(self, silent=False):
        try:
            cfg = load_config()
            if cfg.get("start_relay_server_with_agent", True):
                self.ensure_relay_server(silent=True)
            if self.relay_thread is not None and self.relay_thread.is_alive():
                if not silent:
                    messagebox.showinfo("Relay", "Relay Client شغال فعلاً")
                return
            self._write_relay_config()
            self.relay_stop_event = threading.Event()
            self.relay_thread = threading.Thread(target=relay_client.main, args=(self.relay_stop_event,), daemon=True)
            self.relay_thread.start()
            self.refresh()
            if not silent:
                messagebox.showinfo("Relay", "تم تشغيل Relay Client مدمج داخل البرنامج. افتح التطبيق واضغط تحديث أجهزة Relay.")
        except Exception as e:
            messagebox.showerror("Relay", str(e))

    def stop_relay_client(self):
        if not self._ask_master("إيقاف Relay"):
            return
        try:
            if self.relay_stop_event is not None:
                self.relay_stop_event.set()
            self.relay_thread = None
            self.relay_stop_event = None
            try:
                with open(os.path.join(APP_DIR, "relay_status.json"), "w", encoding="utf-8") as f:
                    json.dump({"state": "stopped", "message": "تم الإيقاف من البرنامج", "time": time.time()}, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            self.refresh()
            messagebox.showinfo("Relay", "تم إيقاف Relay Client")
        except Exception as e:
            messagebox.showerror("Relay", str(e))

    def toggle_relay_auto_start(self):
        if not self._ask_master("تشغيل Relay تلقائياً"):
            return
        cfg = load_config()
        cfg["relay_auto_start"] = not cfg.get("relay_auto_start", False)
        save_config(cfg)
        self.refresh()

    def open_files_folder(self):
        folder = safe_files_dir()
        try:
            os.startfile(folder)
        except Exception as e:
            messagebox.showerror("خطأ", str(e))

    def setup_tray_icon(self):
        if pystray is None:
            return
        def show_window(icon=None, item=None):
            self.after(0, self.show_window)
        def start_conn(icon=None, item=None):
            self.after(0, self.start_server)
        def stop_conn(icon=None, item=None):
            self.after(0, self.stop_server)
        def exit_program(icon=None, item=None):
            self.after(0, self.exit_app)
        menu = pystray.Menu(
            pystray.MenuItem("إظهار SatLink Remote PRO", show_window),
            pystray.MenuItem("تشغيل الاتصال", start_conn),
            pystray.MenuItem("إيقاف الاتصال", stop_conn),
            pystray.MenuItem("تشغيل Relay", lambda icon=None, item=None: self.after(0, self.start_relay_client)),
            pystray.MenuItem("خروج", exit_program),
        )
        self.tray_icon = pystray.Icon("SatLinkRemotePRO", make_tray_image(), "SatLink Remote PRO", menu)
        t = threading.Thread(target=self.tray_icon.run, daemon=True)
        t.start()

    def hide_to_tray(self):
        self.withdraw()
        if pystray is None:
            messagebox.showinfo("SatLink Remote PRO", "pystray غير مثبت. ثبّت requirements ثم أعد التشغيل حتى يظهر بجانب الساعة.")

    def show_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def on_window_close(self):
        cfg = load_config()
        if cfg.get("minimize_to_tray_on_close", True):
            self.hide_to_tray()
        else:
            self.exit_app()

    def exit_app(self):
        if not self._ask_master("خروج من البرنامج"):
            return
        try:
            if self.relay_stop_event is not None:
                self.relay_stop_event.set()
        except Exception:
            pass
        try:
            if self.tray_icon is not None:
                self.tray_icon.stop()
        except Exception:
            pass
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
