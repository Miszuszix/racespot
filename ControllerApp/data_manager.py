import os
import configparser
import json
import socket  # Import niezbędny do sprawdzania portów


class DataManager:
    def __init__(self, ac_root_path):
        self.ac_root_path = ac_root_path
        self.presets_path = os.path.join(ac_root_path, "server", "presets")
        self.cars_path = os.path.join(ac_root_path, "content", "cars")

        self.car_name_cache = {}
        self.drivers_file = "last_drivers.json"

        if not os.path.exists(self.cars_path):
            print(f"[DEBUG] ❌ UWAGA: Folder 'content/cars' nie istnieje w: {self.cars_path}")

    # --- SPRAWDZANIE PORTÓW (CZY SERWER DZIAŁA) ---
    def is_port_in_use(self, port):
        """Sprawdza czy dany port jest zajęty (czyli czy serwer działa)"""
        if not port: return False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.1)  # Bardzo krótki timeout, żeby nie muliło
                return s.connect_ex(('127.0.0.1', int(port))) == 0
        except:
            return False

    # ----------------------------------------------

    def save_driver_names(self, names_dict):
        try:
            with open(self.drivers_file, 'w', encoding='utf-8') as f:
                json.dump(names_dict, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[ERROR] Błąd zapisu imion: {e}")

    def load_driver_names(self):
        if not os.path.exists(self.drivers_file): return {}
        try:
            with open(self.drivers_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def _read_server_data(self, folder_name):
        cfg_path = os.path.join(self.presets_path, folder_name, "server_cfg.ini")
        entry_list_path = os.path.join(self.presets_path, folder_name, "entry_list.ini")

        if not os.path.isfile(cfg_path): return None

        try:
            config = configparser.ConfigParser()
            config.read(cfg_path)

            udp = config.get('SERVER', 'UDP_PORT', fallback="9600")
            http = config.get('SERVER', 'HTTP_PORT', fallback="8081")
            name = config.get('SERVER', 'NAME', fallback=folder_name)
            password = config.get('SERVER', 'PASSWORD', fallback="")
            track = config.get('SERVER', 'TRACK', fallback="imola")
            track_layout = config.get('SERVER', 'CONFIG_TRACK', fallback="")

            car_ids = []
            if os.path.isfile(entry_list_path):
                try:
                    entry_config = configparser.ConfigParser()
                    entry_config.read(entry_list_path)
                    for section in entry_config.sections():
                        if section.upper().startswith("CAR_"):
                            model = entry_config.get(section, "MODEL", fallback=None)
                            if model: car_ids.append(model.strip())
                except:
                    pass

            if not car_ids:
                cars_str = config.get('SERVER', 'CARS', fallback="")
                car_ids = [c.strip() for c in cars_str.split(';') if c.strip()]

            return {
                "name": name, "folder_id": folder_name, "udp_port": int(udp), "http_port": int(http),
                "car_ids": car_ids, "track": track, "track_layout": track_layout, "password": password
            }
        except Exception:
            return None

    def get_server_presets(self):
        servers = []
        if os.path.exists(self.presets_path):
            for f in os.listdir(self.presets_path):
                data = self._read_server_data(f)
                if data:
                    # Tutaj sprawdzamy status przy pobieraniu listy
                    data['is_running'] = self.is_port_in_use(data['http_port'])
                    servers.append(data)
        return servers

    def refresh_server_config(self, folder_name):
        return self._read_server_data(folder_name)

    def get_car_display_name(self, car_id):
        if car_id in self.car_name_cache: return self.car_name_cache[car_id]
        json_path = os.path.join(self.cars_path, car_id, "ui", "ui_car.json")
        if not os.path.exists(json_path):
            self.car_name_cache[car_id] = car_id
            return car_id
        try:
            content = ""
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(json_path, 'r', encoding='latin-1') as f:
                    content = f.read()
            data = json.loads(content, strict=False)
            name = data.get("name", car_id)
            self.car_name_cache[car_id] = name
            return name
        except:
            self.car_name_cache[car_id] = car_id
            return car_id