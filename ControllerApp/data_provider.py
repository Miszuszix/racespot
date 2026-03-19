import os
import json
import configparser
import socket


class DataProvider:
    def __init__(self, assetto_corsa_directory):
        self.assetto_corsa_directory = assetto_corsa_directory
        self.presets_directory = os.path.join(assetto_corsa_directory, "server", "presets")
        self.cars_directory = os.path.join(assetto_corsa_directory, "content", "cars")
        self.car_names_cache = {}
        self.drivers_history_file = "last_drivers.json"

    def check_if_port_is_active(self, port_number):
        if not port_number:
            return False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as network_socket:
                network_socket.settimeout(0.1)
                return network_socket.connect_ex(('127.0.0.1', int(port_number))) == 0
        except Exception:
            return False

    def save_drivers_history(self, drivers_dictionary):
        try:
            with open(self.drivers_history_file, 'w', encoding='utf-8') as file:
                json.dump(drivers_dictionary, file, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def load_drivers_history(self):
        if not os.path.exists(self.drivers_history_file):
            return {}
        try:
            with open(self.drivers_history_file, 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception:
            return {}

    def fetch_server_presets(self):
        servers_list = []
        if not os.path.exists(self.presets_directory):
            return servers_list

        for folder_name in os.listdir(self.presets_directory):
            configuration_path = os.path.join(self.presets_directory, folder_name, "server_cfg.ini")
            entry_list_path = os.path.join(self.presets_directory, folder_name, "entry_list.ini")

            if not os.path.isfile(configuration_path):
                continue

            try:
                configuration_parser = configparser.ConfigParser()
                configuration_parser.read(configuration_path)

                udp_port = configuration_parser.get('SERVER', 'UDP_PORT', fallback="9600")
                http_port = configuration_parser.get('SERVER', 'HTTP_PORT', fallback="8081")
                server_name = configuration_parser.get('SERVER', 'NAME', fallback=folder_name)
                password = configuration_parser.get('SERVER', 'PASSWORD', fallback="")
                track_name = configuration_parser.get('SERVER', 'TRACK', fallback="imola")
                track_layout = configuration_parser.get('SERVER', 'CONFIG_TRACK', fallback="")

                car_slots = []
                if os.path.isfile(entry_list_path):
                    entry_configuration_parser = configparser.ConfigParser()
                    entry_configuration_parser.read(entry_list_path)
                    for section in entry_configuration_parser.sections():
                        if section.upper().startswith("CAR_"):
                            model_id = entry_configuration_parser.get(section, "MODEL", fallback=None)
                            skin = entry_configuration_parser.get(section, "SKIN", fallback="")
                            if model_id:
                                car_slots.append({
                                    "slot_id": section,
                                    "model_id": model_id.strip(),
                                    "skin": skin.strip()
                                })

                if not car_slots:
                    cars_string = configuration_parser.get('SERVER', 'CARS', fallback="")
                    for index, car in enumerate(cars_string.split(';')):
                        if car.strip():
                            car_slots.append({
                                "slot_id": f"CAR_{index}",
                                "model_id": car.strip(),
                                "skin": ""
                            })

                is_server_running = self.check_if_port_is_active(http_port)

                server_data = {
                    "name": server_name,
                    "folder_id": folder_name,
                    "udp_port": int(udp_port),
                    "http_port": int(http_port),
                    "car_slots": car_slots,
                    "track": track_name,
                    "track_layout": track_layout,
                    "password": password,
                    "is_running": is_server_running
                }
                servers_list.append(server_data)
            except Exception:
                continue

        return servers_list

    def fetch_car_display_name(self, car_identifier):
        if car_identifier in self.car_names_cache:
            return self.car_names_cache[car_identifier]

        json_path = os.path.join(self.cars_directory, car_identifier, "ui", "ui_car.json")
        if not os.path.exists(json_path):
            self.car_names_cache[car_identifier] = car_identifier
            return car_identifier

        try:
            with open(json_path, 'r', encoding='utf-8', errors='ignore') as file:
                car_data = json.load(file, strict=False)
                display_name = car_data.get("name", car_identifier)
                self.car_names_cache[car_identifier] = display_name
                return display_name
        except Exception:
            self.car_names_cache[car_identifier] = car_identifier
            return car_identifier

    def fetch_available_skins(self, car_identifier):
        skins_directory = os.path.join(self.cars_directory, car_identifier, "skins")
        skins_list = []

        if not os.path.exists(skins_directory):
            return skins_list

        for skin_folder in os.listdir(skins_directory):
            skin_path = os.path.join(skins_directory, skin_folder)
            if not os.path.isdir(skin_path):
                continue

            ui_skin_path = os.path.join(skin_path, "ui_skin.json")
            display_name = skin_folder.replace("_", " ").title()

            if os.path.exists(ui_skin_path):
                try:
                    with open(ui_skin_path, 'r', encoding='utf-8', errors='ignore') as file:
                        skin_data = json.load(file, strict=False)
                        if "skinname" in skin_data and str(skin_data["skinname"]).strip():
                            display_name = str(skin_data["skinname"]).strip()
                except Exception:
                    pass

            skins_list.append({
                "folder_name": skin_folder,
                "display_name": display_name
            })

        return sorted(skins_list, key=lambda skin: skin["display_name"])