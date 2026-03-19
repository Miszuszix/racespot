import os
import subprocess
import psutil
import time
import threading
import ctypes
import ctypes.wintypes
import win32gui
import win32con
import win32process
import win32api
import configparser

class RaceLauncher:
    def __init__(self, game_directory, steam_id_fallback=""):
        if game_directory.lower().endswith("acs.exe"):
            self.game_executable_path = game_directory
            self.game_directory = os.path.dirname(game_directory)
        else:
            self.game_directory = game_directory
            self.game_executable_path = os.path.join(game_directory, "acs.exe")

        buffer = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer)
        user_documents_directory = buffer.value

        self.race_configuration_path = os.path.join(user_documents_directory, 'Assetto Corsa', 'cfg', 'race.ini')
        self.python_configuration_path = os.path.join(user_documents_directory, 'Assetto Corsa', 'cfg', 'python.ini')
        self.steam_id_fallback = steam_id_fallback

    def configure_applications(self):
        if not os.path.exists(self.python_configuration_path):
            return
        configuration_parser = configparser.ConfigParser()
        configuration_parser.optionxform = str
        configuration_parser.read(self.python_configuration_path)
        if 'APPS' not in configuration_parser:
            configuration_parser['APPS'] = {}
        with open(self.python_configuration_path, 'w') as configuration_file:
            configuration_parser.write(configuration_file)

    def generate_race_configuration(self, data):
        server_data = data['server_data']
        car_data = data['car_data']
        track_data = data.get('track_data', {'track': 'imola', 'config_track': ''})
        guid = data.get('steam_data', {}).get('steam_id') or self.steam_id_fallback
        server_ip = server_data['ip']

        if server_ip in ["192.168.55.101", "localhost"]:
            server_ip = "127.0.0.1"

        http_port = server_data['http_port']
        udp_port = server_data.get('udp_port', 9600)
        password = server_data.get('password', '')
        driver_name = car_data.get('driver_name', 'Player')
        server_name = server_data.get('server_name', 'AC Server')
        model_id = car_data['model_id']

        content = f"""[RACE]
TRACK={track_data['track']}
CONFIG_TRACK={track_data['config_track']}
MODEL={model_id}
MODEL_CONFIG=
CARS=1
AI_LEVEL=98
FIXED_SETUP=0
PENALTIES=0

[REMOTE]
ACTIVE=1
SERVER_IP={server_ip}
SERVER_PORT={udp_port}
SERVER_HTTP_PORT={http_port}
REQUESTED_CAR={model_id}
GUID={guid}
PASSWORD={password}
NAME={driver_name}
TEAM=
CHECKSUM=
SERVER_NAME={server_name}

[GHOST_CAR]
RECORDING=0
PLAYING=0
ACTIVE=0

[REPLAY]
FILENAME=
ACTIVE=0
"""
        os.makedirs(os.path.dirname(self.race_configuration_path), exist_ok=True)
        with open(self.race_configuration_path, 'w', encoding='utf-8') as configuration_file:
            configuration_file.write(content)

    def force_window_to_foreground(self, target_window_handle):
        try:
            if not win32gui.IsWindow(target_window_handle):
                return False
            foreground_window_handle = win32gui.GetForegroundWindow()
            if foreground_window_handle == target_window_handle:
                return True

            if foreground_window_handle == 0:
                win32gui.ShowWindow(target_window_handle, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(target_window_handle)
                return True

            foreground_thread_id = win32process.GetWindowThreadProcessId(foreground_window_handle)[0]
            current_thread_id = win32api.GetCurrentThreadId()
            if foreground_thread_id != current_thread_id:
                ctypes.windll.user32.AttachThreadInput(foreground_thread_id, current_thread_id, True)
            ctypes.windll.user32.SystemParametersInfoW(0x2001, 0, 0, 0x0002 | 0x0001)
            win32gui.ShowWindow(target_window_handle, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(target_window_handle)
            win32gui.BringWindowToTop(target_window_handle)
            win32gui.ShowWindow(target_window_handle, win32con.SW_MAXIMIZE)
            if foreground_thread_id != current_thread_id:
                ctypes.windll.user32.AttachThreadInput(foreground_thread_id, current_thread_id, False)
            return True
        except Exception:
            return False

    def ensure_window_focus_worker(self):
        for _ in range(60):
            window_handle = win32gui.FindWindow(None, 'Assetto Corsa')
            if window_handle and win32gui.IsWindowVisible(window_handle):
                self.force_window_to_foreground(window_handle)
                time.sleep(1)
                self.force_window_to_foreground(window_handle)
                return
            time.sleep(0.5)

    def send_exit_keys(self):
        virtual_key_control = 0x11
        virtual_key_e = 0x45
        scan_code_control = 0x1D
        scan_code_e = 0x12
        try:
            win32api.keybd_event(virtual_key_control, scan_code_control, 0, 0)
            time.sleep(0.05)
            win32api.keybd_event(virtual_key_e, scan_code_e, 0, 0)
            time.sleep(0.05)
            win32api.keybd_event(virtual_key_e, scan_code_e, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.05)
            win32api.keybd_event(virtual_key_control, scan_code_control, win32con.KEYEVENTF_KEYUP, 0)
        except Exception:
            pass

    def terminate_game_process(self):
        try:
            window_handle = win32gui.FindWindow(None, 'Assetto Corsa')
            if window_handle:
                self.force_window_to_foreground(window_handle)
                time.sleep(0.5)
                self.send_exit_keys()
                for _ in range(10):
                    is_running = False
                    for process in psutil.process_iter(['name']):
                        try:
                            if process.info.get('name') in ['acs.exe', 'acs_x86.exe']:
                                is_running = True
                                break
                        except Exception:
                            pass
                    if not is_running:
                        return True
                    time.sleep(0.5)

            target_processes = ['acs.exe', 'acs_x86.exe', 'AssettoCorsa.exe']
            for process in psutil.process_iter(['pid', 'name']):
                try:
                    if process.info.get('name') in target_processes:
                        process.kill()
                except Exception:
                    pass
            return True
        except Exception as exception:
            raise Exception(f"Failed to kill process: {str(exception)}")

    def start_race(self, data):
        try:
            self.terminate_game_process()
            time.sleep(1)
            self.configure_applications()
            self.generate_race_configuration(data)

            if not os.path.exists(self.game_executable_path):
                return False, f"Missing file: {self.game_executable_path}"

            subprocess.Popen([self.game_executable_path], cwd=self.game_directory)
            threading.Thread(target=self.ensure_window_focus_worker, daemon=True).start()
            return True, "Game started successfully"
        except Exception as exception:
            return False, str(exception)