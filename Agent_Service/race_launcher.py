import os
import subprocess
import psutil
import time
import threading
import ctypes
import win32gui
import win32con
import win32process
import win32api
import configparser


# --- ZAAWANSOWANE FUNKCJE OKIENNE ---

def _force_window_to_foreground(target_hwnd):
    """
    Agresywna metoda wymuszania okna na wierzch.
    Wersja cicha - nie zgłasza błędów, gdy okno znika.
    """
    try:
        if not win32gui.IsWindow(target_hwnd):
            return False

        foreground_hwnd = win32gui.GetForegroundWindow()
        if foreground_hwnd == target_hwnd: return True

        foreground_thread_id = win32process.GetWindowThreadProcessId(foreground_hwnd)[0]
        current_thread_id = win32api.GetCurrentThreadId()

        if foreground_thread_id != current_thread_id:
            ctypes.windll.user32.AttachThreadInput(foreground_thread_id, current_thread_id, True)

        ctypes.windll.user32.SystemParametersInfoW(0x2001, 0, 0, 0x0002 | 0x0001)

        win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(target_hwnd)
        win32gui.BringWindowToTop(target_hwnd)
        win32gui.ShowWindow(target_hwnd, win32con.SW_MAXIMIZE)

        if foreground_thread_id != current_thread_id:
            ctypes.windll.user32.AttachThreadInput(foreground_thread_id, current_thread_id, False)
        return True
    except Exception:
        return False


def _ensure_focus_worker():
    """Wątek pilnujący, by gra wyskoczyła na pierwszy plan"""
    print('--> Focus Worker: Szukam okna Assetto Corsa...')
    for i in range(60):
        hwnd = win32gui.FindWindow(None, 'Assetto Corsa')
        if hwnd and win32gui.IsWindowVisible(hwnd):
            _force_window_to_foreground(hwnd)
            time.sleep(1)
            _force_window_to_foreground(hwnd)
            print(f'--> Focus Worker: SUKCES (próba {i})')
            return
        time.sleep(0.5)


def _send_exit_keys():
    """
    Symulacja Ctrl+E z użyciem Scan Codes (wymagane dla gier DirectX).
    Zwykłe VK_... często nie działają w grach.
    """
    VK_CONTROL = 0x11
    VK_E = 0x45

    # Scan Codes (Kluczowe dla Assetto Corsa)
    SC_CONTROL = 0x1D
    SC_E = 0x12

    try:
        # Wciśnij Ctrl
        win32api.keybd_event(VK_CONTROL, SC_CONTROL, 0, 0)
        time.sleep(0.05)

        # Wciśnij E
        win32api.keybd_event(VK_E, SC_E, 0, 0)
        time.sleep(0.05)  # Przytrzymaj chwilę

        # Puść E
        win32api.keybd_event(VK_E, SC_E, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.05)

        # Puść Ctrl
        win32api.keybd_event(VK_CONTROL, SC_CONTROL, win32con.KEYEVENTF_KEYUP, 0)
    except:
        pass


# --- KLASA GŁÓWNA ---

class RaceLauncher:
    def __init__(self, game_path_input, steam_id_fallback=""):
        if game_path_input.lower().endswith("acs.exe"):
            self.game_exe_path = game_path_input
            self.game_dir = os.path.dirname(game_path_input)
        else:
            self.game_dir = game_path_input
            self.game_exe_path = os.path.join(game_path_input, "acs.exe")

        try:
            import ctypes.wintypes
            buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf)
            user_documents = buf.value
        except:
            user_documents = os.path.join(os.path.expanduser('~'), 'Documents')

        self.ini_path = os.path.join(user_documents, 'Assetto Corsa', 'cfg', 'race.ini')
        self.python_ini_path = os.path.join(user_documents, 'Assetto Corsa', 'cfg', 'python.ini')
        self.steam_id_fallback = steam_id_fallback

    def configure_apps(self):
        try:
            if not os.path.exists(self.python_ini_path): return
            config = configparser.ConfigParser()
            config.optionxform = str
            config.read(self.python_ini_path)
            if 'APPS' not in config: config['APPS'] = {}
            # config['APPS']['ac_essentials'] = '1'
            with open(self.python_ini_path, 'w') as f:
                config.write(f)
        except Exception as e:
            print(f"--> Błąd configure_apps: {e}")

    def generate_race_ini(self, data):
        server_data = data['server_data']
        car_data = data['car_data']
        track_data = data.get('track_data', {'track': 'imola', 'config_track': ''})

        guid = data.get('steam_data', {}).get('steam_id') or self.steam_id_fallback

        ip = server_data['ip']
        if ip == "192.168.55.101" or ip == "localhost":
            ip = "127.0.0.1"

        http_port = server_data['http_port']
        udp_port = server_data.get('udp_port', 9600)

        content = f"""[RACE]
TRACK={track_data['track']}
CONFIG_TRACK={track_data['config_track']}
MODEL={car_data['model_id']}
MODEL_CONFIG=
CARS=1
AI_LEVEL=98
FIXED_SETUP=0
PENALTIES=0

[REMOTE]
ACTIVE=1
SERVER_IP={ip}
SERVER_PORT={udp_port}
SERVER_HTTP_PORT={http_port}
REQUESTED_CAR={car_data['model_id']}
GUID={guid}
PASSWORD={server_data.get('password', '')}
NAME={car_data.get('driver_name', 'Player')}
TEAM=
CHECKSUM=
SERVER_NAME={server_data.get('server_name', 'AC Server')}

[GHOST_CAR]
RECORDING=0
PLAYING=0
ACTIVE=0

[REPLAY]
FILENAME=
ACTIVE=0
"""
        try:
            os.makedirs(os.path.dirname(self.ini_path), exist_ok=True)
            with open(self.ini_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"--> Zapisano race.ini (IP: {ip}, P:{udp_port}/{http_port})")
        except Exception as e:
            print(f"--> Błąd ini: {e}")

    def kill_game(self):
        """
        Najpierw próbuje Ctrl+E, czeka na zamknięcie.
        Jeśli nie zamknie się w 5s, ubija proces.
        """
        # 1. Próba Ctrl+E (Graceful Exit)
        hwnd = win32gui.FindWindow(None, 'Assetto Corsa')
        if hwnd:
            _force_window_to_foreground(hwnd)
            time.sleep(0.5)
            _send_exit_keys()  # Teraz z obsługą DirectX Scan Codes

            # Czekamy na zamknięcie przez grę
            for _ in range(10):  # 5 sekund
                running = False
                for p in psutil.process_iter(['name']):
                    if p.info['name'] in ['acs.exe', 'acs_x86.exe']:
                        running = True
                        break
                if not running: return True
                time.sleep(0.5)

        # 2. Force Kill (jeśli Ctrl+E nie zadziałało lub gry nie widać w oknie)
        targets = ['acs.exe', 'acs_x86.exe', 'AssettoCorsa.exe']
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] in targets:
                try:
                    proc.kill()
                except:
                    pass
        return True

    def start_race(self, data):
        try:
            self.kill_game()
            time.sleep(1)
            self.configure_apps()
            self.generate_race_ini(data)

            if not os.path.exists(self.game_exe_path):
                return False, f"Brak pliku: {self.game_exe_path}"

            print(f"--> Uruchamiam: {self.game_exe_path}")
            subprocess.Popen([self.game_exe_path], cwd=self.game_dir)
            threading.Thread(target=_ensure_focus_worker, daemon=True).start()
            return True, "Uruchomiono grę"
        except Exception as e:
            return False, str(e)