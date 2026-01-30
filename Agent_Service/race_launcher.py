import os
import subprocess
import psutil
import time
import configparser
import win32api
import win32con

class RaceLauncher:
    def __init__(self, ac_root):
        print(f"[Launcher] Inicjalizacja dla ścieżki: {ac_root}")
        self.ac_root = ac_root
        self.acs_exe = os.path.join(ac_root, "acs.exe")
        self.race_ini = os.path.join(ac_root, "cfg", "race.ini")
        self.game_process_name = "acs.exe"

    def prepare_config(self, race_data):
        cfg = configparser.ConfigParser()
        cfg.optionxform = str

        cfg['RACE'] = {
            'MODEL': race_data['car_data']['model_id'],
            'MODEL_CONFIG': '',
            'CARS': '1',
            'AI_LEVEL': '98',
            'FIXED_SETUP': '0',
            'PENALTIES': '1'
        }

        cfg['REMOTE'] = {
            'ACTIVE': '1',
            'SERVER_IP': race_data['server_data']['ip'],
            'SERVER_PORT': str(race_data['server_data']['http_port']),
            'NAME': race_data['car_data']['driver_name'],
            'TEAM': '',
            'GUID': '',
            'REQUEST_GUID': '',
            'PASSWORD': race_data['server_data']['password'],
            'SKIN': race_data['car_data'].get('skin', '')
        }

        cfg['GHOST_CAR'] = {'RECORDING': '0', 'PLAYING': '0', 'SECONDS_DELAY': '0', 'LOAD': '1', 'FILE': ''}
        cfg['REPLAY'] = {'FILENAME': '', 'ACTIVE': '0'}

        try:
            with open(self.race_ini, 'w') as configfile:
                cfg.write(configfile)
            return True
        except Exception as e:
            print(f"[ERROR] Nie udało się zapisać race.ini: {e}")
            return False

    def kill_acs_only(self):
        """Zabija proces gry (Hot-Swap)"""
        killed = False
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] == self.game_process_name:
                    proc.kill()
                    killed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return killed

    def simulate_ctrl_e(self):
        """Symuluje Ctrl+E"""
        try:
            win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            win32api.keybd_event(0x45, 0, 0, 0) # 'E'
            time.sleep(0.1)
            win32api.keybd_event(0x45, 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            return True
        except Exception as e:
            print(f"[ERROR] Błąd symulacji klawiszy: {e}")
            return False

    def start_race(self, race_data):
        self.kill_acs_only()
        time.sleep(1.0)

        if not self.prepare_config(race_data):
            return False, "Błąd zapisu race.ini"

        if not os.path.exists(self.acs_exe):
            return False, f"Brak pliku acs.exe w: {self.acs_exe}"

        try:
            subprocess.Popen([self.acs_exe], cwd=self.ac_root)
            return True, "Uruchomiono acs.exe"
        except Exception as e:
            return False, f"Błąd startu procesu: {e}"