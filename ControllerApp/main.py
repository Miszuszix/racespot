import sys
from PySide6.QtWidgets import QApplication
from config_manager import ConfigManager
from data_provider import DataProvider
from network_manager import NetworkManager
from gui_manager import GuiManager

def main():
    application = QApplication(sys.argv)

    config_manager = ConfigManager()

    assetto_corsa_path = config_manager.get("ac_root_path", "")
    secret_token = config_manager.get("secret_token", "")

    data_provider = DataProvider(assetto_corsa_path)
    network_manager = NetworkManager(secret_token)

    main_window = GuiManager(config_manager, data_provider, network_manager)
    main_window.show()

    sys.exit(application.exec())

if __name__ == "__main__":
    main()