import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt
from config_manager import ConfigManager
from data_provider import DataProvider
from network_manager import NetworkManager
from gui_manager import GuiManager

def apply_dark_theme(application):
    application.setStyle("Fusion")
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(43, 43, 43))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(30, 30, 30))
    dark_palette.setColor(QPalette.AlternateBase, QColor(43, 43, 43))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(60, 60, 60))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    application.setPalette(dark_palette)

def main():
    application = QApplication(sys.argv)
    apply_dark_theme(application)
    
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