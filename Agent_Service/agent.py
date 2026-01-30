from flask import Flask, request, jsonify
import json
import os
from race_launcher import RaceLauncher

app = Flask(__name__)

# Wczytanie konfiguracji
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
        # Inteligentne pobieranie ścieżki (folder vs plik exe)
        game_path = config.get('game_exe_path', '.')
        if game_path.lower().endswith('acs.exe'):
            AC_ROOT = os.path.dirname(game_path)
        else:
            AC_ROOT = game_path

        PORT = config.get('agent_port', 5000)
        SECRET_TOKEN = config.get('secret_token', '')
except Exception as e:
    print(f"BŁĄD KRYTYCZNY: Nie można załadować config.json! {e}")
    input("Naciśnij Enter aby wyjść...")
    exit(1)

print(f"--- RACESPOT AGENT ---")
print(f"Folder gry: {AC_ROOT}")
print(f"Port: {PORT}")

try:
    launcher = RaceLauncher(AC_ROOT)
except Exception as e:
    print(f"Błąd inicjalizacji Launchera: {e}")
    input("Enter...")
    exit(1)


def check_auth():
    token = request.headers.get("Authorization")
    # Jeśli token w configu jest pusty, to nie sprawdzamy (tryb dev)
    if not SECRET_TOKEN: return True
    return token == f"Bearer {SECRET_TOKEN}"


@app.route('/run', methods=['POST'])
def run_race():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    print(f"Otrzymano polecenie START dla: {data.get('car_data', {}).get('driver_name')}")
    success, msg = launcher.start_race(data)

    if success:
        return jsonify({"status": "started", "msg": msg})
    else:
        print(f"Błąd startu: {msg}")
        return jsonify({"status": "error", "msg": msg}), 500


@app.route('/stop', methods=['POST'])
def stop_race():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401

    print("Otrzymano polecenie STOP (Ctrl+E)")
    if launcher.simulate_ctrl_e():
        return jsonify({"status": "stopped", "msg": "Wysłano Ctrl+E"})
    else:
        return jsonify({"status": "error", "msg": "Błąd symulacji klawiszy"}), 500


@app.route('/status', methods=['GET'])
def get_status():
    return jsonify({"status": "online", "host": os.getenv('COMPUTERNAME', 'Unknown')})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)