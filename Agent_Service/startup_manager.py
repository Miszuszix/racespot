import os
import sys
import winreg

class StartupManager:
    def __init__(self, application_name):
        self.application_name = application_name
        self.registry_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

    def install_to_autostart(self):
        executable_path = sys.executable
        script_path = os.path.abspath(sys.argv[0])
        command = f'"{executable_path}" "{script_path}"'

        registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.registry_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(registry_key, self.application_name, 0, winreg.REG_SZ, command)
        winreg.CloseKey(registry_key)