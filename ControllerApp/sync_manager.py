import os
import shutil
from PySide6.QtCore import QThread, Signal

class SyncWorker(QThread):
    log_signal = Signal(str)
    finished_signal = Signal()

    def __init__(self, config_manager, sync_type="cars_tracks", dry_run=False):
        super().__init__()
        self.config_manager = config_manager
        self.sync_type = sync_type  # Oczekiwane: "cars_tracks" lub "skins"
        self.dry_run = dry_run

        self.summary = {}
        for client in self.config_manager.get("clients", []):
            rig_name = client.get("name", "Unknown")
            self.summary[rig_name] = {
                "cars_copy": 0,
                "cars_del": 0,
                "skins_add": 0,
                "skins_del": 0,
                "tracks_copy": 0,
                "tracks_del": 0
            }

    def run(self):
        mode_text = "[TEST MODE]" if self.dry_run else "[ACTUAL SYNC]"
        self.log_signal.emit(f"\n=== STARTING {mode_text} ===")

        master_cars_directory = self.config_manager.get('master_cars_path', '')
        master_tracks_directory = self.config_manager.get('master_tracks_path', '')
        target_cars_directories = self.config_manager.get('sync_cars_paths', [])
        target_tracks_directories = self.config_manager.get('sync_tracks_paths', [])
        clients = self.config_manager.get('clients', [])

        if not master_cars_directory or not master_tracks_directory:
            self.log_signal.emit("ERROR: Master paths not defined in configuration.")
            self.finished_signal.emit()
            return

        if self.sync_type == "cars_tracks":
            self.log_signal.emit(">>> CHECKING CARS (NO SKINS)")
            if not os.path.exists(master_cars_directory):
                self.log_signal.emit(f"CRITICAL ERROR: Master cars directory not found: {master_cars_directory}")
            else:
                for i, target_directory in enumerate(target_cars_directories):
                    if target_directory.strip():
                        rig_name = clients[i].get("name", f"RIG {i + 1}") if i < len(clients) else f"RIG {i + 1}"
                        self.sync_cars_only(master_cars_directory, target_directory, rig_name)

            self.log_signal.emit(">>> CHECKING TRACKS")
            if not os.path.exists(master_tracks_directory):
                self.log_signal.emit(f"CRITICAL ERROR: Master tracks directory not found: {master_tracks_directory}")
            else:
                for i, target_directory in enumerate(target_tracks_directories):
                    if target_directory.strip():
                        rig_name = clients[i].get("name", f"RIG {i + 1}") if i < len(clients) else f"RIG {i + 1}"
                        self.sync_basic_directory(master_tracks_directory, target_directory, rig_name)

        elif self.sync_type == "skins":
            self.log_signal.emit(">>> CHECKING SKINS (ONLY)")
            if not os.path.exists(master_cars_directory):
                self.log_signal.emit(f"CRITICAL ERROR: Master cars directory not found: {master_cars_directory}")
            else:
                for i, target_directory in enumerate(target_cars_directories):
                    if target_directory.strip():
                        rig_name = clients[i].get("name", f"RIG {i + 1}") if i < len(clients) else f"RIG {i + 1}"
                        self.sync_skins_only(master_cars_directory, target_directory, rig_name)

        # Generowanie raportu końcowego w trybie DRY RUN
        if self.dry_run:
            summary_lines = ["\n=== PODSUMOWANIE TESTU SYNCHRONIZACJI ==="]

            for rig_name, stats in self.summary.items():
                if self.sync_type == "cars_tracks":
                    # Wyświetlamy statystyki tylko dla aut i torów
                    if stats['cars_copy'] == 0 and stats['cars_del'] == 0 and stats['tracks_copy'] == 0 and stats['tracks_del'] == 0:
                        continue # Puste przebiegi
                    summary_lines.append(f"--{rig_name}--")
                    summary_lines.append("--Auta--")
                    summary_lines.append(f"Do skopiowania: {stats['cars_copy']}")
                    summary_lines.append(f"Do usunięcia: {stats['cars_del']}")
                    summary_lines.append("--Tory--")
                    summary_lines.append(f"Do skopiowania: {stats['tracks_copy']}")
                    summary_lines.append(f"Do usunięcia: {stats['tracks_del']}")
                    summary_lines.append("")
                else:
                    # Wyświetlamy statystyki tylko dla skinów
                    if stats['skins_add'] == 0 and stats['skins_del'] == 0:
                        continue
                    summary_lines.append(f"--{rig_name}--")
                    summary_lines.append("--Skiny--")
                    summary_lines.append(f"Do skopiowania: {stats['skins_add']}")
                    summary_lines.append(f"Do usunięcia: {stats['skins_del']}")
                    summary_lines.append("")

            if len(summary_lines) == 1:
                summary_lines.append("Wszystko aktualne!")
            self.log_signal.emit("\n".join(summary_lines))

        self.log_signal.emit(f"=== FINISHED {mode_text} ===\n")
        self.finished_signal.emit()

    def sync_basic_directory(self, source_directory, target_directory, rig_name):
        """Kopiuje i usuwa całe foldery (używane głównie do torów)."""
        if not os.path.exists(target_directory):
            self.log_signal.emit(f"ERROR: Target unreachable: {target_directory}")
            return

        try:
            source_items = set(os.listdir(source_directory))
            target_items = set(os.listdir(target_directory))

            missing_items = source_items - target_items
            excess_items = target_items - source_items

            for item in missing_items:
                source_path = os.path.join(source_directory, item)
                target_path = os.path.join(target_directory, item)

                if os.path.isdir(source_path):
                    self.summary[rig_name]["tracks_copy"] += 1
                    if self.dry_run:
                        self.log_signal.emit(f"[TEST] Would copy track: '{item}' to {target_directory}")
                    else:
                        self.log_signal.emit(f"[+] Copying track: '{item}' to {target_directory}")
                        try:
                            shutil.copytree(source_path, target_path)
                        except Exception as exception:
                            self.log_signal.emit(f"    COPY ERROR '{item}': {exception}")

            for item in excess_items:
                target_path = os.path.join(target_directory, item)
                self.summary[rig_name]["tracks_del"] += 1
                if self.dry_run:
                    self.log_signal.emit(f"[TEST] Would delete track: '{item}' from {target_directory}")
                else:
                    self.log_signal.emit(f"[-] Deleting track: '{item}' from {target_directory}")
                    try:
                        if os.path.isdir(target_path):
                            shutil.rmtree(target_path)
                        else:
                            os.remove(target_path)
                    except Exception as exception:
                        self.log_signal.emit(f"    DELETE ERROR '{item}': {exception}")

        except Exception as exception:
            self.log_signal.emit(f"SYNC ERROR on {target_directory}: {exception}")

    def sync_cars_only(self, source_directory, target_directory, rig_name):
        """Kopiuje brakujące i usuwa nadmiarowe auta (ale pomija badanie skinów)."""
        if not os.path.exists(target_directory):
            self.log_signal.emit(f"ERROR: Target unreachable: {target_directory}")
            return

        try:
            source_cars = set(os.listdir(source_directory))
            target_cars = set(os.listdir(target_directory))

            missing_cars = source_cars - target_cars
            excess_cars = target_cars - source_cars

            for car in missing_cars:
                source_path = os.path.join(source_directory, car)
                target_path = os.path.join(target_directory, car)

                if os.path.isdir(source_path):
                    self.summary[rig_name]["cars_copy"] += 1
                    if self.dry_run:
                        self.log_signal.emit(f"[TEST] Would copy car: '{car}' to {target_directory}")
                    else:
                        self.log_signal.emit(f"[+] Copying car: '{car}' to {target_directory}")
                        try:
                            shutil.copytree(source_path, target_path)
                        except Exception as exception:
                            self.log_signal.emit(f"    COPY ERROR '{car}': {exception}")

            for car in excess_cars:
                target_path = os.path.join(target_directory, car)
                self.summary[rig_name]["cars_del"] += 1
                if self.dry_run:
                    self.log_signal.emit(f"[TEST] Would delete car: '{car}' from {target_directory}")
                else:
                    self.log_signal.emit(f"[-] Deleting car: '{car}' from {target_directory}")
                    try:
                        if os.path.isdir(target_path):
                            shutil.rmtree(target_path)
                        else:
                            os.remove(target_path)
                    except Exception as exception:
                        self.log_signal.emit(f"    DELETE ERROR '{car}': {exception}")

        except Exception as exception:
            self.log_signal.emit(f"SYNC ERROR on {target_directory}: {exception}")

    def sync_skins_only(self, source_directory, target_directory, rig_name):
        """Zagląda w głąb TYLKO tych aut, które istnieją na obu maszynach i bada tylko folder skins."""
        if not os.path.exists(target_directory):
            self.log_signal.emit(f"ERROR: Target unreachable: {target_directory}")
            return

        try:
            source_cars = set(os.listdir(source_directory))
            target_cars = set(os.listdir(target_directory))
            common_cars = source_cars.intersection(target_cars)

            for car in common_cars:
                source_skins_directory = os.path.join(source_directory, car, "skins")
                target_skins_directory = os.path.join(target_directory, car, "skins")

                if os.path.exists(source_skins_directory) and os.path.exists(target_skins_directory):
                    source_skins = set(os.listdir(source_skins_directory))
                    target_skins = set(os.listdir(target_skins_directory))

                    missing_skins = source_skins - target_skins
                    excess_skins = target_skins - source_skins

                    for skin in missing_skins:
                        source_skin_path = os.path.join(source_skins_directory, skin)
                        target_skin_path = os.path.join(target_skins_directory, skin)

                        if os.path.isdir(source_skin_path):
                            self.summary[rig_name]["skins_add"] += 1
                            if self.dry_run:
                                self.log_signal.emit(f"[TEST] Would copy skin: '{skin}' for car '{car}' to {target_directory}")
                            else:
                                self.log_signal.emit(f"[+] Copying skin: '{skin}' for car '{car}' to {target_directory}")
                                try:
                                    shutil.copytree(source_skin_path, target_skin_path)
                                except Exception as exception:
                                    self.log_signal.emit(f"    COPY ERROR '{skin}': {exception}")

                    for skin in excess_skins:
                        target_skin_path = os.path.join(target_skins_directory, skin)
                        self.summary[rig_name]["skins_del"] += 1
                        if self.dry_run:
                            self.log_signal.emit(f"[TEST] Would delete skin: '{skin}' for car '{car}' from {target_directory}")
                        else:
                            self.log_signal.emit(f"[-] Deleting skin: '{skin}' for car '{car}' from {target_directory}")
                            try:
                                if os.path.isdir(target_skin_path):
                                    shutil.rmtree(target_skin_path)
                                else:
                                    os.remove(target_skin_path)
                            except Exception as exception:
                                self.log_signal.emit(f"    DELETE ERROR '{skin}': {exception}")

        except Exception as exception:
            self.log_signal.emit(f"SYNC ERROR on {target_directory}: {exception}")