import json
import os
from datetime import datetime

class ConfigManager:
    def __init__(self, configuration_file_path="config.json"):
        self.configuration_file_path = configuration_file_path
        self.log_file_path = "logs_controller_data.txt"
        self.configuration_data = self.load_configuration()

    def load_configuration(self):
        default_configuration = {
            "ac_root_path": "",
            "secret_token": "",
            "master_server_ip": "127.0.0.1",
            "clients": [],
            "master_cars_path": "",
            "master_tracks_path": "",
            "sync_cars_paths": [],
            "sync_tracks_paths": []
        }

        if not os.path.exists(self.configuration_file_path):
            self.save_configuration(default_configuration)
            return default_configuration

        try:
            with open(self.configuration_file_path, 'r', encoding='utf-8') as file:
                loaded_configuration = json.load(file)
                default_configuration.update(loaded_configuration)
                return default_configuration
        except Exception as exception:
            self.write_log("SYSTEM", f"Critical error loading config: {exception}")
            return default_configuration

    def save_configuration(self, configuration_data):
        self.configuration_data = configuration_data
        try:
            with open(self.configuration_file_path, 'w', encoding='utf-8') as file:
                json.dump(self.configuration_data, file, indent=4, ensure_ascii=False)
        except Exception as exception:
            self.write_log("SYSTEM", f"Failed to save configuration: {exception}")

    def get(self, key, default_value=None):
        return self.configuration_data.get(key, default_value)

    def write_log(self, target_identifier, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [TARGET: {target_identifier}] {message}\n"

        try:
            with open(self.log_file_path, 'a', encoding='utf-8') as file:
                file.write(log_entry)
        except Exception:
            pass