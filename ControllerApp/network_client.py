import requests
import concurrent.futures

class NetworkClient:
    def __init__(self, token):
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}

    def send_command_to_host(self, host_ip, payload):
        url = f"http://{host_ip}:5000/run"
        try:
            resp = requests.post(url, json=payload, headers=self.headers, timeout=5)
            if resp.status_code == 200:
                return True, f"OK: {resp.json().get('msg')}"
            else:
                return False, f"Błąd HTTP {resp.status_code}"
        except Exception as e:
            return False, f"Błąd połączenia: {str(e)}"

    def stop_host(self, host_ip):
        url = f"http://{host_ip}:5000/stop"
        try:
            requests.post(url, headers=self.headers, timeout=3)
            return True
        except Exception as e:
            print(f"ERROR: {e}")
            return False

    def broadcast_start(self, selected_hosts, payload):
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ip = {
                executor.submit(self.send_command_to_host, ip, payload): ip 
                for ip in selected_hosts
            }
            for future in concurrent.futures.as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    success, msg = future.result()
                    results[ip] = (success, msg)
                except Exception as e:
                    results[ip] = (False, str(e))
        return results