import sys
import json
import os
from http_server import AgentServer
from startup_manager import StartupManager


def load_configuration():
    configuration_path = 'config.json'
    default_configuration = {
        "game_executable_path": ".",
        "agent_port": 5000,
        "secret_token": ""
    }

    if not os.path.exists(configuration_path):
        return default_configuration

    try:
        with open(configuration_path, 'r') as configuration_file:
            loaded_configuration = json.load(configuration_file)
            default_configuration.update(loaded_configuration)
    except Exception:
        pass

    return default_configuration


def main():
    if "--install" in sys.argv:
        startup_manager = StartupManager("RaceSpotAgent")
        startup_manager.install_to_autostart()
        sys.exit(0)

    configuration = load_configuration()
    game_path = configuration.get('game_executable_path')

    if game_path.lower().endswith('acs.exe'):
        game_directory = os.path.dirname(game_path)
    else:
        game_directory = game_path

    port = configuration.get('agent_port')
    secret_token = configuration.get('secret_token')

    agent_server = AgentServer(port, secret_token, game_directory)
    agent_server.start()


if __name__ == '__main__':
    main()