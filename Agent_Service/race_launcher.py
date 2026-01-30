import os
import subprocess
import configparser
import psutil
import time
import threading
import ctypes
import win32gui
import win32con
import win32process
import win32api


class RaceLauncher:
    def __init__(self, game_path_input, steam_id_fallback="76561198330229570"):
        # 1. Obsługa folderu vs pliku .exe
        if game_path_input.lower().endswith("acs.exe"):
            self.game_exe_path = game_path_input
            self.game_dir = os.path.dirname(game_path_input)
        else:
            self.game_dir = game_path_input
            self.game_exe_path = os.path.join(game_path_input, "acs.exe")

        # 2. Bezpieczne pobieranie Dokumentów
        try:
            CSIDL_PERSONAL = 5
            SHGFP_TYPE_CURRENT = 0
            buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
            user_documents = buf.value
        except:
            user_documents = os.path.join(os.path.expanduser('~'), 'Documents')

        self.ini_path = os.path.join(user_documents, 'Assetto Corsa', 'cfg', 'race.ini')
        self.steam_id_fallback = steam_id_fallback

    # --- FUNKCJE POMOCNICZE ---

    def _send_exit_keys(self):
        """Symuluje Ctrl+E"""
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        time.sleep(0.05)
        win32api.keybd_event(0x45, 0, 0, 0)  # E
        time.sleep(0.05)
        win32api.keybd_event(0x45, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.05)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)

    def _force_window_to_foreground(self, target_hwnd):
        try:
            win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(target_hwnd)
            return True
        except:
            return False

    def _ensure_focus_worker(self):
        print("--> Focus Worker: Szukam okna AC...")
        for i in range(30):
            hwnd = win32gui.FindWindow(None, "Assetto Corsa")
            if hwnd:
                self._force_window_to_foreground(hwnd)
                return
            time.sleep(1)

    # --- KONFIGURACJA ---

    def generate_race_ini(self, data):
        server_data = data['server_data']
        car_data = data['car_data']
        track_data = data.get('track_data', {'track': 'imola', 'config_track': ''})

        guid = data.get('steam_data', {}).get('steam_id')
        if not guid:
            guid = self.steam_id_fallback

        ip = server_data['ip']
        my_lan_ip = "192.168.55.101"
        if ip == my_lan_ip or ip == "localhost":
            print(f"--> Wykryto połączenie lokalne ({ip}). Wymuszam 127.0.0.1")
            ip = "127.0.0.1"

        # Rozdzielenie portów HTTP i UDP
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
LOAD=0
FILE=
ACTIVE=0

[REPLAY]
FILENAME=
ACTIVE=0
"""
        try:
            os.makedirs(os.path.dirname(self.ini_path), exist_ok=True)
            with open(self.ini_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"--> Zapisano race.ini (IP: {ip}, Porty: {http_port}/{udp_port})")
        except Exception as e:
            print(f"--> Błąd zapisu ini: {e}")

    # --- ZARZĄDZANIE GRĄ ---

    def kill_game(self):
        # 1. Próba Ctrl+E
        hwnd = win32gui.FindWindow(None, "Assetto Corsa")
        if hwnd:
            self._send_exit_keys()
            time.sleep(1)

        # 2. Zabijanie procesów (ACS i Launcher)
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
            self.generate_race_ini(data)

            if not os.path.exists(self.game_exe_path):
                return False, f"Brak pliku: {self.game_exe_path}"

            print(f"--> Uruchamiam: {self.game_exe_path}")
            subprocess.Popen([self.game_exe_path], cwd=self.game_dir)
            threading.Thread(target=self._ensure_focus_worker, daemon=True).start()
            return True, "Uruchomiono grę"
        except Exception as e:
            return False, str(e)

    # --- NOWA METODA (FIX DLA AGENT.PY) ---
    def simulate_ctrl_e(self):
        return self.kill_game()