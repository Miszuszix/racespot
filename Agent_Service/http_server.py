import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from race_launcher import RaceLauncher


class AgentRequestHandler(BaseHTTPRequestHandler):
    secret_token = ""
    race_launcher = None

    def do_GET(self):
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"status": "online", "host": os.getenv('COMPUTERNAME', 'Unknown')}
            self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        try:
            if not self.is_authorized():
                self.send_error_response(401, "Unauthorized")
                return

            content_length = int(self.headers.get('Content-Length', 0))
            request_body = self.rfile.read(content_length)

            try:
                request_data = json.loads(request_body)
            except json.JSONDecodeError:
                self.send_error_response(400, "Invalid JSON")
                return

            if self.path == '/run':
                success, message = self.race_launcher.start_race(request_data)
                if success:
                    self.send_success_response({"status": "started", "msg": message})
                else:
                    self.send_error_response(500, message)

            elif self.path == '/stop':
                if self.race_launcher.terminate_game_process():
                    self.send_success_response({"status": "stopped", "msg": "Exit commands sent"})
                else:
                    self.send_error_response(500, "Failed to terminate game")
            else:
                self.send_response(404)
                self.end_headers()

        except Exception as exception:
            # W razie jakiegokolwiek błędu wewnątrz serwera zwracamy czysty tekst błędu
            self.send_error_response(500, f"Agent Crash: {str(exception)}")

    def is_authorized(self):
        if not self.secret_token:
            return True
        authorization_header = self.headers.get("Authorization")
        expected_header = f"Bearer {self.secret_token}"
        return authorization_header == expected_header

    def send_success_response(self, payload):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode('utf-8'))

    def send_error_response(self, status_code, message):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {"status": "error", "msg": message}
        self.wfile.write(json.dumps(response).encode('utf-8'))

    def log_message(self, format, *args):
        pass


class AgentServer:
    def __init__(self, port, secret_token, game_directory):
        self.port = port
        AgentRequestHandler.secret_token = secret_token
        AgentRequestHandler.race_launcher = RaceLauncher(game_directory)

    def start(self):
        server_address = ('0.0.0.0', self.port)
        httpd = HTTPServer(server_address, AgentRequestHandler)
        httpd.serve_forever()