import os
import sys
import threading
import subprocess
import time
import webbrowser
from pathlib import Path

try:
    import winreg
except Exception:
    winreg = None

try:
    import tkinter as tk
    from tkinter import messagebox
except Exception:
    tk = None
    messagebox = None

try:
    import pystray
    from pystray import MenuItem as item
    from PIL import Image, ImageDraw
except Exception:
    pystray = None
    Image = None
    ImageDraw = None

from waitress import serve
from relay_server import app, cfg, APP_VERSION, OWNER_TOKEN, local_ip_for_lan
try:
    from neon_theme import apply_neon, style_button, neon_line
except Exception:  # theme is optional
    apply_neon = style_button = neon_line = None

SERVER_NAME = "SatLinkRelayServer"
PORT = int(cfg.get("port", 7777))
HOST = str(cfg.get("host", "0.0.0.0"))
SERVER_URL = f"http://{local_ip_for_lan()}:{PORT}"
if getattr(sys, "frozen", False):
    SERVER_DIR = Path(sys.executable).resolve().parent
    ROOT_DIR = SERVER_DIR
    AGENT_DIR = SERVER_DIR
else:
    SERVER_DIR = Path(__file__).resolve().parent
    ROOT_DIR = SERVER_DIR.parent
    AGENT_DIR = ROOT_DIR / "windows-agent"
_running = False
_tray_icon = None
_root = None
_status_label = None
_server_autostart_btn = None
_agent_autostart_btn = None
START_MINIMIZED = ("--minimized" in sys.argv) or ("--autostart" in sys.argv)

SERVER_STARTUP_FILE = "SatLinkRelayServer_AutoStart.vbs"
SERVER_TASK_NAME = "SatLinkRelayServer"
AGENT_STARTUP_FILE = "SatLinkRemotePRO_Agent_AutoStart.bat"


def startup_dir() -> Path:
    base = os.environ.get("APPDATA", "")
    if not base:
        return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    return Path(base) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def server_startup_path() -> Path:
    return startup_dir() / SERVER_STARTUP_FILE


def server_autostart_launcher_path() -> Path:
    return SERVER_DIR / "start_relay_server_autostart.bat"


def agent_startup_path() -> Path:
    return startup_dir() / AGENT_STARTUP_FILE


def task_exists(name: str) -> bool:
    try:
        result = subprocess.run(["schtasks", "/Query", "/TN", name],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)
        return result.returncode == 0
    except Exception:
        return False


def create_logon_task(vbs_path: Path) -> bool:
    try:
        task_cmd = f'wscript.exe "{vbs_path}"'
        result = subprocess.run(["schtasks", "/Create", "/TN", SERVER_TASK_NAME, "/SC", "ONLOGON",
                                 "/TR", task_cmd, "/RL", "LIMITED", "/F"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)
        return result.returncode == 0
    except Exception:
        return False


def delete_logon_task() -> None:
    try:
        subprocess.run(["schtasks", "/Delete", "/TN", SERVER_TASK_NAME, "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)
    except Exception:
        pass


def is_server_autostart_enabled() -> bool:
    return server_startup_path().exists() or task_exists(SERVER_TASK_NAME)


def is_agent_autostart_enabled() -> bool:
    startup_file = agent_startup_path().exists()
    registry_enabled = False
    if winreg is not None:
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, "SatLinkRemotePRO")
                registry_enabled = bool(value)
        except Exception:
            registry_enabled = False
    return startup_file or registry_enabled


def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def enable_server_autostart():
    launcher = server_autostart_launcher_path()
    if not launcher.exists():
        fallback = f'''@echo off
setlocal EnableExtensions
cd /d "{SERVER_DIR}"
where pyw >nul 2>&1
if errorlevel 1 (
    start "" py -3.11 "{SERVER_DIR}\\server_tray.py" --minimized --autostart
) else (
    start "" pyw -3.11 "{SERVER_DIR}\\server_tray.py" --minimized --autostart
)
exit /b 0
'''
        write_text(launcher, fallback)

    vbs = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """{launcher}""", 0, False
'''
    write_text(server_startup_path(), vbs)
    task_ok = create_logon_task(server_startup_path())
    refresh_autostart_buttons()
    if task_ok:
        show_info("SatLinkRelayServer AutoStart enabled using Startup folder + Scheduled Task.")
    else:
        show_info("SatLinkRelayServer AutoStart enabled using Startup folder. Task Scheduler fallback was not created.")


def disable_server_autostart():
    try:
        server_startup_path().unlink(missing_ok=True)
    except TypeError:
        if server_startup_path().exists():
            server_startup_path().unlink()
    delete_logon_task()
    refresh_autostart_buttons()
    show_info("SatLinkRelayServer autostart disabled.")


def _agent_launch_command() -> str:
    candidates = [
        AGENT_DIR / "SatLinkRemotePRO.exe",
        AGENT_DIR / "dist" / "SatLinkRemotePRO.exe",
        AGENT_DIR / "dist-x64" / "SatLinkRemotePRO_x64.exe",
        AGENT_DIR / "dist-x86" / "SatLinkRemotePRO_x86.exe",
    ]
    for exe in candidates:
        if exe.exists():
            return f'"{exe}" --minimized --autostart'
    script = AGENT_DIR / "main.py"
    return f'pyw -3.11 "{script}" --minimized --autostart'


def enable_agent_autostart():
    command = _agent_launch_command()
    registry_ok = False
    if winreg is not None:
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "SatLinkRemotePRO", 0, winreg.REG_SZ, command)
            registry_ok = True
        except Exception:
            registry_ok = False
    if not registry_ok:
        text = f'''@echo off
start "" {command}
exit /b 0
'''
        write_text(agent_startup_path(), text)
    refresh_autostart_buttons()
    show_info("SatLink Remote PRO will start with Windows. The main program will start SatLinkRelayServer automatically.")

def disable_agent_autostart():
    try:
        agent_startup_path().unlink(missing_ok=True)
    except TypeError:
        if agent_startup_path().exists():
            agent_startup_path().unlink()
    if winreg is not None:
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, "SatLinkRemotePRO")
        except Exception:
            pass
    refresh_autostart_buttons()
    show_info("SatLink Remote PRO autostart disabled.")


def toggle_server_autostart():
    if is_server_autostart_enabled():
        disable_server_autostart()
    else:
        enable_server_autostart()


def toggle_agent_autostart():
    if is_agent_autostart_enabled():
        disable_agent_autostart()
    else:
        enable_agent_autostart()


def enable_both_autostart():
    enable_server_autostart()
    enable_agent_autostart()
    refresh_autostart_buttons()


def refresh_autostart_buttons():
    try:
        if _agent_autostart_btn is not None:
            enabled = is_agent_autostart_enabled()
            _agent_autostart_btn.config(
                text=("Disable Main Program AutoStart" if enabled else "Enable Main Program AutoStart"))
            if style_button is not None:
                style_button(_agent_autostart_btn, "#5a2b14" if enabled else "#145a3a")
            else:
                _agent_autostart_btn.config(bg=("#5a2b14" if enabled else "#145a3a"))
        update_status_label()
    except Exception:
        pass



def open_main_program(*args):
    command = _agent_launch_command()
    try:
        if command.lower().startswith("pyw "):
            script = AGENT_DIR / "main.py"
            subprocess.Popen(["pyw", "-3.11", str(script)], cwd=str(AGENT_DIR), close_fds=True)
        else:
            exe_text = command.split(' --minimized', 1)[0].strip().strip('"')
            subprocess.Popen([exe_text], cwd=str(Path(exe_text).parent), close_fds=True)
    except Exception as exc:
        show_info(f"Could not open main program: {exc}")

def show_info(text: str):
    if messagebox is not None and _root is not None:
        try:
            messagebox.showinfo("SatLinkRelayServer", text)
            return
        except Exception:
            pass
    print(text)


def make_icon_image():
    icon_path = Path(__file__).with_name("satlink_server_icon.ico")
    if Image is not None and icon_path.exists():
        try:
            return Image.open(str(icon_path))
        except Exception:
            pass
    if Image is None:
        return None
    img = Image.new("RGBA", (64, 64), (7, 14, 30, 255))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((6, 10, 58, 46), radius=8, outline=(0, 240, 255, 255), width=4)
    draw.rectangle((24, 48, 40, 54), fill=(255, 43, 214, 255))
    draw.rectangle((18, 55, 46, 59), fill=(0, 240, 255, 255))
    draw.ellipse((42, 6, 60, 24), fill=(57, 255, 136, 255))
    return img


def start_waitress_server():
    global _running
    _running = True
    try:
        serve(app, host=HOST, port=PORT, threads=16)
    except Exception as exc:
        _running = False
        if _status_label is not None:
            try:
                _status_label.config(text=f"Server error: {exc}")
            except Exception:
                pass


def open_server_page(*args):
    try:
        webbrowser.open(SERVER_URL)
    except Exception:
        pass


def show_window(*args):
    global _root
    if _root is None:
        return
    try:
        _root.deiconify()
        _root.lift()
        _root.focus_force()
    except Exception:
        pass


def hide_window(*args):
    global _root
    if _root is None:
        return
    try:
        _root.withdraw()
    except Exception:
        pass


def exit_server(*args):
    try:
        if _tray_icon is not None:
            _tray_icon.stop()
    except Exception:
        pass
    os._exit(0)


def start_tray_icon():
    global _tray_icon
    if pystray is None:
        return
    image = make_icon_image()
    menu = pystray.Menu(
        item("Show SatLinkRelayServer", show_window, default=True),
        item("Open Server Page", open_server_page),
        item("Hide to Tray", hide_window),
        pystray.Menu.SEPARATOR,
        item("Exit Server", exit_server),
    )
    _tray_icon = pystray.Icon(SERVER_NAME, image, SERVER_NAME + " - Running", menu)
    _tray_icon.run()


def status_text() -> str:
    return (
        f"Status: Running\n"
        f"Version: {APP_VERSION}\n"
        f"Server URL: {SERVER_URL}\n"
        f"Port: {PORT}\n"
        f"Owner Token: {OWNER_TOKEN}\n\n"
        f"Main Program AutoStart: {'Enabled' if is_agent_autostart_enabled() else 'Disabled'}\n"
        "Unified mode: SatLink Remote PRO starts this server automatically.\n\n"
        "Press X to hide this window to the system tray.\n"
        "Use Main Program AutoStart; separate server AutoStart is no longer needed."
    )


def update_status_label():
    if _status_label is not None:
        try:
            _status_label.config(text=status_text())
        except Exception:
            pass


def build_gui():
    global _root, _status_label, _agent_autostart_btn
    if tk is None:
        return None
    root = tk.Tk()
    _root = root
    root.title("SatLinkRelayServer - PRO 2.3.0 Neon")
    root.geometry("680x430")
    root.minsize(600, 420)
    root.configure(bg="#0b1220")
    try:
        icon_path = Path(__file__).with_name("satlink_server_icon.ico")
        if icon_path.exists():
            root.iconbitmap(str(icon_path))
    except Exception:
        pass

    def label(text, size=11, fg="#e6f3ff", bold=False):
        font = ("Segoe UI", size, "bold" if bold else "normal")
        return tk.Label(root, text=text, bg="#0b1220", fg=fg, font=font, justify="left", anchor="w")

    title = label("SatLinkRelayServer", 20, "#66d9ff", True)
    title.pack(fill="x", padx=24, pady=(18, 4))
    subtitle = label("SatLink Remote PRO Relay Server - Developer: Muhannad Sat Link", 10, "#b9c7d8")
    subtitle.pack(fill="x", padx=24, pady=(0, 14))

    _status_label = label(status_text(), 11, "#e6f3ff")
    _status_label.pack(fill="both", expand=True, padx=24, pady=8)

    autobar = tk.Frame(root, bg="#0b1220")
    autobar.pack(fill="x", padx=24, pady=(0, 10))

    def button(parent, text, command, bg="#14345a"):
        return tk.Button(parent, text=text, command=command, font=("Segoe UI", 10, "bold"),
                         bg=bg, fg="#ffffff", activebackground="#1f4d82",
                         activeforeground="#ffffff", relief="flat", padx=12, pady=8)

    _agent_autostart_btn = button(autobar, "Enable Main Program AutoStart", toggle_agent_autostart, "#145a3a")
    _agent_autostart_btn.pack(side="left", padx=(0, 8), pady=3)
    button(autobar, "Open Main Program", open_main_program, "#164b83").pack(side="left", padx=(0, 8), pady=3)

    bar = tk.Frame(root, bg="#0b1220")
    bar.pack(fill="x", padx=24, pady=(0, 18))
    button(bar, "Open Server Page", open_server_page).pack(side="left", padx=(0, 10))
    button(bar, "Hide to Tray", hide_window).pack(side="left", padx=(0, 10))
    button(bar, "Exit Server", exit_server, "#5a1414").pack(side="right")

    root.protocol("WM_DELETE_WINDOW", hide_window)
    if apply_neon is not None:
        apply_neon(root)
    refresh_autostart_buttons()

    if START_MINIMIZED:
        try:
            root.after(800, hide_window)
        except Exception:
            pass
    return root


def main():
    threading.Thread(target=start_waitress_server, daemon=True).start()
    time.sleep(0.5)

    if pystray is not None:
        threading.Thread(target=start_tray_icon, daemon=True).start()

    root = build_gui()
    if root is None:
        while True:
            time.sleep(60)
    root.mainloop()


if __name__ == "__main__":
    main()
