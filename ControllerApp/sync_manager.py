import os
import shutil


class SyncManager:
    def __init__(self, config, logger_callback):
        self.config = config
        self.log = logger_callback  # Funkcja do wypisywania logów w GUI

    def perform_sync(self, dry_run):
        mode = "[TEST/DRY-RUN]" if dry_run else "[PEŁNA SYNC]"
        self.log(f"\n{'=' * 10} ROZPOCZYNAM {mode} (Źródło: RIG 1) {'=' * 10}")

        src_cars = self.config.get('master_cars_path', '')
        src_tracks = self.config.get('master_tracks_path', '')

        targets_cars = self.config.get('sync_cars_paths', [])
        targets_tracks = self.config.get('sync_tracks_paths', [])

        if not src_cars or not src_tracks:
            self.log("BŁĄD: Nie zdefiniowano ścieżek 'master' w config.json!")
            return

        self.log(f"\n>>> SYNCHRONIZACJA SAMOCHODÓW {mode}")
        if not os.path.exists(src_cars):
            self.log(f"BŁĄD KRYTYCZNY: Nie widzę folderu źródłowego RIG 1: {src_cars}")
        else:
            for target in targets_cars:
                self.sync_directory(src_cars, target, dry_run)

        self.log(f"\n>>> SYNCHRONIZACJA TORÓW {mode}")
        if not os.path.exists(src_tracks):
            self.log(f"BŁĄD KRYTYCZNY: Nie widzę folderu źródłowego RIG 1: {src_tracks}")
        else:
            for target in targets_tracks:
                self.sync_directory(src_tracks, target, dry_run)

        self.log(f"\n{'=' * 10} ZAKOŃCZONO {mode} {'=' * 10}\n")

    def sync_directory(self, dir_a, dir_b, dry_run):
        if not os.path.exists(dir_b) and not dry_run:
            pass

        try:
            if not os.path.exists(dir_b) and dry_run:
                dirs_b = set()
            elif not os.path.exists(dir_b):
                self.log(f"BŁĄD: Cel nieosiągalny: {dir_b}")
                return
            else:
                dirs_b = set(os.listdir(dir_b))

            try:
                dirs_a = set(os.listdir(dir_a))
            except Exception as e:
                self.log(f"Błąd odczytu MASTER {dir_a}: {e}")
                return

            added = []
            removed = []

            for d in dirs_a - dirs_b:
                src = os.path.join(dir_a, d)
                dst = os.path.join(dir_b, d)

                if os.path.isdir(src):
                    if dry_run:
                        self.log(f"[+] (Test) Skopiowałbym: {d}")
                    else:
                        self.log(f"[+] Kopiuję: {d}")
                        try:
                            shutil.copytree(src, dst)
                        except Exception as e:
                            self.log(f"   BŁĄD kopiowania {d}: {e}")
                    added.append(d)

            for d in dirs_b - dirs_a:
                path = os.path.join(dir_b, d)
                if os.path.isdir(path):
                    if dry_run:
                        self.log(f"[-] (Test) Usunąłbym: {d}")
                    else:
                        self.log(f"[-] Usuwam: {d}")
                        try:
                            shutil.rmtree(path)
                        except Exception as e:
                            self.log(f"   BŁĄD usuwania {d}: {e}")
                    removed.append(d)

            # Raport dla danego stanowiska
            if added or removed:
                self.log(f"--- CEL: {dir_b} ---")
                if added: self.log(f"   Do skopiowania: {len(added)}")
                if removed: self.log(f"   Do usunięcia: {len(removed)}")
            else:
                self.log(f"OK (Zgodne): {dir_b}")

        except Exception as e:
            self.log(f"KRYTYCZNY BŁĄD SYNC na {dir_b}: {e}")