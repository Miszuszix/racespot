import json
import urllib.request
import urllib.error
import socket  # DODANY IMPORT
from PySide6.QtCore import QThread, Signal

class NetworkWorker(QThread):
    progress_signal = Signal(str, bool, str)
    finished_signal = Signal()

    def __init__(self, targets, action, payload=None, token=""):
        super().__init__()
        self.targets = targets
        self.action = action
        self.payload = payload
        self.token = token

    def run(self):
        for target in self.targets:
            original_target_ip = target.get("ip")
            try:
                resolved_ip = socket.gethostbyname(original_target_ip)
            except Exception:
                resolved_ip = original_target_ip

            url = f"http://{resolved_ip}:5000/{self.action}"
            headers = {"Content-Type": "application/json"}

            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            safe_payload = self.payload if self.payload is not None else {}
            request_data = json.dumps(safe_payload).encode('utf-8')

            try:
                request = urllib.request.Request(url, data=request_data, headers=headers, method="POST")
                with urllib.request.urlopen(request, timeout=10) as response:
                    response_body = json.loads(response.read().decode('utf-8'))
                    self.progress_signal.emit(original_target_ip, True, response_body.get("msg", "OK"))
            except urllib.error.HTTPError as http_error:
                try:
                    error_body = json.loads(http_error.read().decode('utf-8'))
                    self.progress_signal.emit(original_target_ip, False, error_body.get("msg", str(http_error)))
                except Exception:
                    self.progress_signal.emit(original_target_ip, False, str(http_error))
            except Exception as exception:
                self.progress_signal.emit(original_target_ip, False, str(exception))

        self.finished_signal.emit()


class NetworkManager:
    def __init__(self, token):
        self.token = token
        self.active_workers = []

    def broadcast_command(self, targets, action, payload, progress_callback, finished_callback):
        worker = NetworkWorker(targets, action, payload, self.token)
        worker.progress_signal.connect(progress_callback)
        worker.finished_signal.connect(lambda: self.cleanup_worker(worker, finished_callback))
        self.active_workers.append(worker)
        worker.start()

    def cleanup_worker(self, worker, finished_callback):
        if worker in self.active_workers:
            self.active_workers.remove(worker)
        if finished_callback:
            finished_callback()