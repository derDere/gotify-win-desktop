import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import yaml
import websocket
from datetime import datetime, timedelta
from plyer import notification
import pystray
from pystray import MenuItem, Menu
from PIL import Image
from urllib.parse import urlparse, parse_qs
import traceback
import os
import ssl
import sys
import shutil
import subprocess
import argparse

def get_config_path():
    try:
        home = os.path.expanduser("~")
        return os.path.join(home, "gotify-win-client-config.yaml")
    except Exception:
        return "gotify-win-client-config.yaml"

CONFIG_FILE = get_config_path()
ICON_FILE = "notify_client.ico"

def get_icon_path():
    # When bundled with PyInstaller, data files are under sys._MEIPASS
    try:
        if hasattr(sys, "_MEIPASS"):
            p = os.path.join(sys._MEIPASS, ICON_FILE)
            if os.path.exists(p):
                return p
    except Exception:
        pass
    # Fallback to repo root or current working dir
    repo = os.path.join(os.path.dirname(os.path.abspath(__file__)), ICON_FILE)
    if os.path.exists(repo):
        return repo
    cwd = os.path.join(os.getcwd(), ICON_FILE)
    return cwd

# global runtime state
ws_threads = []
connection_states = {}        # url -> True/False
connection_states_lock = threading.Lock()
last_errors = {}              # url -> short error info

verboseagain = datetime.now()  # silent mode end
running = True

CONFIG = {
    "urls": [],
    "notify_timeout": 30,
    "silent_time": 10
}

def log(*args):
    try:
        print(datetime.now().strftime("[%Y-%m-%d %H:%M:%S]"), *args, flush=True)
    except Exception:
        try:
            print("[log]", *args, flush=True)
        except Exception:
            pass


def load_config():
    global CONFIG
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            CONFIG = yaml.safe_load(f)
        log("Config loaded:", CONFIG_FILE, "urls=", len(CONFIG.get("urls", [])), "timeout=", CONFIG.get("notify_timeout"), "silent=", CONFIG.get("silent_time"))
    else:
        save_config()
        log("Config created with defaults:", CONFIG_FILE)


def save_config():
    # ensure parent directory exists if user changed to a path with folders
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    except Exception:
        pass
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump(CONFIG, f)
    log("Config saved:", CONFIG_FILE)


def extract_display_and_url(line):
    line = line.strip()
    if not line:
        return None, None
    if line.startswith("[") and "]" in line:
        idx = line.index("]")
        name = line[1:idx]
        url = line[idx+1:].strip()
        return name, url
    return line, line


def extract_domain(url):
    try:
        p = urlparse(url)
        return p.netloc
    except:
        return url


def ws_thread_func(url, display):
    global running
    while running:
        try:
            with connection_states_lock:
                connection_states[url] = False
                last_errors.pop(url, None)
            log("Connecting:", display or url, "->", url)

            # pre-check token presence
            try:
                p = urlparse(url)
                token = parse_qs(p.query).get('token', [None])[0]
                if not token:
                    log("Warning: missing 'token' query parameter for:", url)
            except Exception as e:
                log("Token parse warning:", repr(e))

            sleep_seconds = 10

            def on_message(ws, msg):
                try:
                    title, msg_text = parse_gotify_message(msg)
                except:
                    return

                if datetime.now() < verboseagain:
                    return

                notification.notify(
                    title=title,
                    message=msg_text,
                    app_name=display,
                    timeout=CONFIG.get("notify_timeout", 30)
                )

            def on_open(ws):
                with connection_states_lock:
                    connection_states[url] = True
                log("Connected:", display or url, "->", url)

            def on_close(ws, code, reason):
                with connection_states_lock:
                    connection_states[url] = False
                log("Disconnected:", display or url, "->", url, "code=", code, "reason=", reason)

            def on_error(ws, error):
                nonlocal sleep_seconds
                status = getattr(error, 'status_code', None)
                headers = getattr(error, 'response_headers', None)
                info = f"status={status} error={repr(error)}"
                with connection_states_lock:
                    last_errors[url] = info
                log("WebSocket error:", display or url, "->", url, info)
                if headers:
                    try:
                        log("Response headers:", dict(headers))
                    except Exception:
                        pass
                # backoff more on unauthorized
                try:
                    if status == 401 or (isinstance(error, Exception) and 'Unauthorized' in repr(error)):
                        sleep_seconds = 60
                        log("Auth error detected. Increasing backoff to", sleep_seconds, "seconds")
                except Exception:
                    pass

            ws = websocket.WebSocketApp(
                url,
                on_message=on_message,
                on_open=on_open,
                on_close=on_close,
                on_error=on_error
            )
            sslopt = {}
            if CONFIG.get("ignore_ssl_errors"):
                sslopt = {"cert_reqs": ssl.CERT_NONE}
            ws.run_forever(ping_interval=30, ping_timeout=10, sslopt=sslopt)
        except Exception as e:
            log("Connection error:", display or url, "->", url, "error=", repr(e))

        if not running:
            break
        try:
            log("Reconnecting in", sleep_seconds, "s:", display or url)
            time.sleep(sleep_seconds)
        except Exception:
            time.sleep(10)

    with connection_states_lock:
        connection_states[url] = False
    log("Stopped thread:", display or url)


def parse_gotify_message(msg):
    import json
    data = json.loads(msg)
    title = data.get("title", "Gotify")
    message = data.get("message", "")
    return title, message


def restart_connections():
    global ws_threads
    log("Restarting connections. URLs:", len(CONFIG.get("urls", [])))
    for t in ws_threads:
        try:
            t.daemon = True
        except:
            pass
    ws_threads.clear()

    with connection_states_lock:
        for url in CONFIG["urls"]:
            _, u = extract_display_and_url(url)
            connection_states[u] = False
            last_errors.pop(u, None)

    for line in CONFIG["urls"]:
        name, url = extract_display_and_url(line)
        if not url:
            continue
        t = threading.Thread(target=ws_thread_func, args=(url, name), daemon=True)
        t.start()
        ws_threads.append(t)
        log("Started thread for:", name or url)


class ConfigWindow:
    def __init__(self, icon_ref):
        self.icon_ref = icon_ref
        self.root = tk.Tk()
        self.root.title("Notify Client Configuration")
        try:
            # Set window icon if available (Windows .ico supported)
            if os.path.exists(ICON_FILE):
                self.root.iconbitmap(ICON_FILE)
        except Exception:
            pass

        # Make window wider for easier URL editing
        try:
            self.root.geometry("1000x700")
        except Exception:
            pass

        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Notify Timeout:").pack(anchor="w")
        self.timeout_var = tk.StringVar()
        timeout_values = [
            "5s", "10s", "30s", "1m", "5m", "10m", "30m",
            "1h", "2h", "4h", "8h"
        ]
        cmb1 = ttk.Combobox(frame, textvariable=self.timeout_var, values=timeout_values, state="readonly")
        cmb1.pack(fill="x")
        self.timeout_var.set(self.seconds_to_label(CONFIG.get("notify_timeout", 30)))

        ttk.Label(frame, text="Silent Duration:").pack(anchor="w", pady=(10,0))
        self.silent_var = tk.StringVar()
        silent_values = ["5m","10m","30m","1h","2h","4h","8h","12h","24h"]
        cmb2 = ttk.Combobox(frame, textvariable=self.silent_var, values=silent_values, state="readonly")
        cmb2.pack(fill="x")
        self.silent_var.set(self.minutes_to_label(CONFIG.get("silent_time", 10)))

        ttk.Label(frame, text="Enter URLs (one per line, optional [Name]prefix):").pack(anchor="w", pady=(10,0))
        self.text = tk.Text(frame, height=16, width=100)
        self.text.pack(fill="both", expand=True)
        self.text.insert("1.0", "\n".join(CONFIG["urls"]))

        ttk.Label(frame, text="Status dot (green=all ok, yellow=partial, red=down):").pack(anchor="w", pady=(10,0))
        self.status_canvas = tk.Canvas(frame, width=16, height=16)
        self.status_canvas.pack(anchor="w")
        self.status_canvas.bind("<Enter>", self.tooltip_enter)
        self.status_canvas.bind("<Leave>", self.tooltip_leave)

        self.tooltip = None
        self.update_status_dot()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.schedule_status_update()

    def schedule_status_update(self):
        self.update_status_dot()
        self.root.after(1000, self.schedule_status_update)

    def update_status_dot(self):
        self.status_canvas.delete("all")
        with connection_states_lock:
            states = list(connection_states.values())
        if not states:
            color = "red"
        else:
            if all(states):
                color = "green"
            elif any(states):
                color = "yellow"
            else:
                color = "red"
        self.status_canvas.create_oval(2,2,14,14, fill=color)

    def tooltip_enter(self, event):
        with connection_states_lock:
            items = list(connection_states.items())

        online = [u for u,v in items if v]
        offline = [u for u,v in items if not v]

        text = f"{len(online)}/{len(items)} connections online\n"
        if offline:
            text += "offline:\n"
            for u in offline[:10]:
                reason = last_errors.get(u)
                text += f"  - {u}\n"
                if reason:
                    # keep oneliners short
                    if len(reason) > 120:
                        reason = reason[:117] + "..."
                    text += f"      reason: {reason}\n"
            if len(offline) > 10:
                text += "  ...\n"

        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{self.root.winfo_pointerx()+10}+{self.root.winfo_pointery()+10}")
        lbl = ttk.Label(self.tooltip, text=text, background="#ffffe0", relief="solid", borderwidth=1)
        lbl.pack()

    def tooltip_leave(self, event):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

    def on_close(self):
        try:
            CONFIG["urls"] = [line.strip() for line in self.text.get("1.0", "end").split("\n") if line.strip()]
            CONFIG["notify_timeout"] = self.label_to_seconds(self.timeout_var.get())
            CONFIG["silent_time"] = self.label_to_minutes(self.silent_var.get())
            save_config()
            log("Config window saved. urls=", len(CONFIG["urls"]), "timeout=", CONFIG["notify_timeout"], "silent=", CONFIG["silent_time"])
        except:
            messagebox.showerror("Error", traceback.format_exc())

        restart_connections()
        update_tray_menu(self.icon_ref)
        log("Reloaded connections and tray menu after config change")
        self.root.destroy()

    @staticmethod
    def seconds_to_label(sec):
        if sec < 60:
            return f"{sec}s"
        m = sec // 60
        if m < 60:
            return f"{m}m"
        h = m // 60
        return f"{h}h"

    @staticmethod
    def minutes_to_label(minutes):
        if minutes < 60:
            return f"{minutes}m"
        h = minutes // 60
        return f"{h}h"

    @staticmethod
    def label_to_seconds(label):
        if label.endswith("s"):
            return int(label[:-1])
        if label.endswith("m"):
            return int(label[:-1]) * 60
        if label.endswith("h"):
            return int(label[:-1]) * 3600
        return 30

    @staticmethod
    def label_to_minutes(label):
        if label.endswith("m"):
            return int(label[:-1])
        if label.endswith("h"):
            return int(label[:-1]) * 60
        return 10


def open_config_window(icon):
    def run():
        ConfigWindow(icon).root.mainloop()
    threading.Thread(target=run, daemon=True).start()


def set_silent(icon):
    global verboseagain
    m = CONFIG.get("silent_time", 10)
    verboseagain = datetime.now() + timedelta(minutes=m)
    update_tray_menu(icon)
    log("Silent enabled until:", verboseagain.strftime('%Y-%m-%d %H:%M:%S'))


def clear_silent(icon):
    global verboseagain
    verboseagain = datetime.now()
    update_tray_menu(icon)
    log("Silent disabled")


def open_server_page(host):
    scheme = "https://" 
    webbrowser.open(scheme + host)
    log("Opening server page:", scheme + host)


def update_tray_menu(icon):
    silent_active = datetime.now() < verboseagain

    urls = CONFIG.get("urls", [])
    hosts = sorted({extract_domain(extract_display_and_url(u)[1]) for u in urls if extract_display_and_url(u)[1]})

    servers_menu = [MenuItem(h, lambda _, host=h: open_server_page(host)) for h in hosts]

    if silent_active:
        silent_label = f"Silent until {verboseagain.strftime('%H:%M')}"
    else:
        silent_label = "Silent"

    menu = Menu(
        MenuItem("Show Window", lambda: open_config_window(icon)),
        MenuItem(silent_label, lambda: set_silent(icon), enabled=not silent_active),
        MenuItem("Silent Off", lambda: clear_silent(icon), enabled=silent_active),
        MenuItem("Servers", Menu(*servers_menu)),
        MenuItem("Exit", lambda: exit_app(icon))
    )
    icon.menu = menu
    log("Tray menu updated. silent=", silent_active, "servers=", len(servers_menu))


def exit_app(icon):
    global running
    running = False
    icon.stop()
    log("Exiting app, stopping tray icon")


def run_tray():
    icon_path = get_icon_path()
    image = Image.open(icon_path)
    icon = pystray.Icon("notify_client", image, "Notify Client")
    update_tray_menu(icon)
    icon.run()
    log("Tray icon started")


def install_to_user_programs_and_startup():
    try:
        local_appdata = os.environ.get("LOCALAPPDATA")
        if not local_appdata:
            raise RuntimeError("LOCALAPPDATA not found")
        target_dir = os.path.join(local_appdata, "Programs", "GotifyWinClient")
        os.makedirs(target_dir, exist_ok=True)

        # Source exe: when packaged, sys.executable is the exe
        src = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
        exe_name = "GotifyClient.exe"
        dst_exe = os.path.join(target_dir, exe_name)
        shutil.copy2(src, dst_exe)
        log("Copied executable to:", dst_exe)

        # Copy icon into install folder (from bundled data or repo)
        try:
            src_icon = get_icon_path()
            dst_icon = os.path.join(target_dir, ICON_FILE)
            if os.path.exists(src_icon):
                shutil.copy2(src_icon, dst_icon)
                log("Copied icon to:", dst_icon)
        except Exception:
            log("Icon copy failed:", traceback.format_exc())

        # Create Startup shortcut via PowerShell (no admin required)
        # Using WScript.Shell COM to generate .lnk
        ps = (
            "$startup = [Environment]::GetFolderPath('Startup');"
            f"$target = '{dst_exe.replace('\\', '/') }';"
            "$lnk = Join-Path $startup 'GotifyClient.lnk';"
            "$ws = New-Object -ComObject WScript.Shell;"
            "$sc = $ws.CreateShortcut($lnk);"
            "$sc.TargetPath = $target;"
            "$sc.WorkingDirectory = (Split-Path $target);"
            "$sc.WindowStyle = 7;"
            "$iconFile = Join-Path (Split-Path $target) 'notify_client.ico';"
            "if (Test-Path $iconFile) { $sc.IconLocation = $iconFile } else { $sc.IconLocation = $target }"
            "$sc.Save();"
        )
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], check=False)
        log("Startup shortcut created.")
        messagebox.showinfo("Installation", "Installed GotifyClient.exe to AppData\\Local\\Programs and added Startup shortcut.")
    except Exception:
        messagebox.showerror("Installation failed", traceback.format_exc())


def uninstall_from_user_programs_and_startup():
    try:
        local_appdata = os.environ.get("LOCALAPPDATA")
        if not local_appdata:
            raise RuntimeError("LOCALAPPDATA not found")
        target_dir = os.path.join(local_appdata, "Programs", "GotifyWinClient")
        exe_path = os.path.join(target_dir, "GotifyClient.exe")
        icon_path = os.path.join(target_dir, ICON_FILE)

        # Remove Startup shortcut
        ps_remove = (
            "$startup = [Environment]::GetFolderPath('Startup');"
            "$lnk = Join-Path $startup 'GotifyClient.lnk';"
            "if (Test-Path $lnk) { Remove-Item $lnk -Force }"
        )
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_remove], check=False)

        # Remove exe and icon
        for p in [exe_path, icon_path]:
            try:
                if os.path.exists(p):
                    os.remove(p)
                    log("Removed:", p)
            except Exception:
                log("Failed to remove:", p)

        # Remove folder if empty
        try:
            if os.path.isdir(target_dir) and not os.listdir(target_dir):
                os.rmdir(target_dir)
                log("Removed empty folder:", target_dir)
        except Exception:
            pass

        messagebox.showinfo("Uninstall", "Removed GotifyClient from Programs and Startup.")
    except Exception:
        messagebox.showerror("Uninstall failed", traceback.format_exc())


def main():
    parser = argparse.ArgumentParser(description="Gotify Windows Tray Client")
    parser.add_argument("--install", action="store_true", help="Install to user Programs and add Startup shortcut")
    parser.add_argument("--uninstall", action="store_true", help="Remove from user Programs and Startup")
    args = parser.parse_args()

    log("Notify Client starting...")
    if args.install:
        install_to_user_programs_and_startup()
        return
    if args.uninstall:
        uninstall_from_user_programs_and_startup()
        return

    load_config()
    restart_connections()
    run_tray()
    log("Notify Client stopped")


if __name__ == "__main__":
    main()
