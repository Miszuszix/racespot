import os
import shutil
from PySide6.QtCore import QThread, Signal


class SyncWorker(QThread):
    log_signal = Signal(str)
    finished_signal = Signal()

    def __init__(self, config_manager, dry_run=False):
        super().__init__()
        self.config_manager = config_manager
        self.dry_run = dry_run

    def run(self):
        mode_text = "[TEST MODE]" if self.dry_run else "[ACTUAL SYNC]"
        self.log_signal.emit(f"\n=== STARTING {mode_text} ===")

        master_cars_directory = self.config_manager.get('master_cars_path', '')
        master_tracks_directory = self.config_manager.get('master_tracks_path', '')
        target_cars_directories = self.config_manager.get('sync_cars_paths', [])
        target_tracks_directories = self.config_manager.get('sync_tracks_paths', [])

        if not master_cars_directory or not master_tracks_directory:
            self.log_signal.emit("ERROR: Master paths not defined in configuration.")
            self.finished_signal.emit()
            return

        self.log_signal.emit(">>> CHECKING CARS & SKINS")
        if not os.path.exists(master_cars_directory):
            self.log_signal.emit(f"CRITICAL ERROR: Master cars directory not found: {master_cars_directory}")
        else:
            for target_directory in target_cars_directories:
                if target_directory.strip():
                    self.sync_cars_directory(master_cars_directory, target_directory)

        self.log_signal.emit(">>> CHECKING TRACKS")
        if not os.path.exists(master_tracks_directory):
            self.log_signal.emit(f"CRITICAL ERROR: Master tracks directory not found: {master_tracks_directory}")
        else:
            for target_directory in target_tracks_directories:
                if target_directory.strip():
                    self.sync_basic_directory(master_tracks_directory, target_directory)

        self.log_signal.emit(f"=== FINISHED {mode_text} ===\n")
        self.finished_signal.emit()

    def sync_basic_directory(self, source_directory, target_directory):
        if not os.path.exists(target_directory):
            self.log_signal.emit(f"ERROR: Target unreachable: {target_directory}")
            return

        try:
            source_items = set(os.listdir(source_directory))
            target_items = set(os.listdir(target_directory))

            missing_items = source_items - target_items
            if not missing_items:
                self.log_signal.emit(f"[OK] Tracks up to date for: {target_directory}")
                return

            for item in missing_items:
                source_path = os.path.join(source_directory, item)
                target_path = os.path.join(target_directory, item)

                if os.path.isdir(source_path):
                    if self.dry_run:
                        self.log_signal.emit(f"[TEST] Would copy track: '{item}' to {target_directory}")
                    else:
                        self.log_signal.emit(f"[+] Copying track: '{item}' to {target_directory}")
                        try:
                            shutil.copytree(source_path, target_path)
                        except Exception as exception:
                            self.log_signal.emit(f"    COPY ERROR '{item}': {exception}")
        except Exception as exception:
            self.log_signal.emit(f"SYNC ERROR on {target_directory}: {exception}")

    def sync_cars_directory(self, source_directory, target_directory):
        if not os.path.exists(target_directory):
            self.log_signal.emit(f"ERROR: Target unreachable: {target_directory}")
            return

        try:
            source_cars = set(os.listdir(source_directory))
            target_cars = set(os.listdir(target_directory))

            missing_cars = source_cars - target_cars
            common_cars = source_cars.intersection(target_cars)

            changes_found = False

            for car in missing_cars:
                source_path = os.path.join(source_directory, car)
                target_path = os.path.join(target_directory, car)

                if os.path.isdir(source_path):
                    changes_found = True
                    if self.dry_run:
                        self.log_signal.emit(f"[TEST] Would copy car: '{car}' to {target_directory}")
                    else:
                        self.log_signal.emit(f"[+] Copying car: '{car}' to {target_directory}")
                        try:
                            shutil.copytree(source_path, target_path)
                        except Exception as exception:
                            self.log_signal.emit(f"    COPY ERROR '{car}': {exception}")

            for car in common_cars:
                source_skins_directory = os.path.join(source_directory, car, "skins")
                target_skins_directory = os.path.join(target_directory, car, "skins")

                if os.path.exists(source_skins_directory) and os.path.exists(target_skins_directory):
                    source_skins = set(os.listdir(source_skins_directory))
                    target_skins = set(os.listdir(target_skins_directory))

                    missing_skins = source_skins - target_skins
                    for skin in missing_skins:
                        source_skin_path = os.path.join(source_skins_directory, skin)
                        target_skin_path = os.path.join(target_skins_directory, skin)

                        if os.path.isdir(source_skin_path):
                            changes_found = True
                            if self.dry_run:
                                self.log_signal.emit(
                                    f"[TEST] Would copy skin: '{skin}' for car '{car}' to {target_directory}")
                            else:
                                self.log_signal.emit(
                                    f"[+] Copying skin: '{skin}' for car '{car}' to {target_directory}")
                                try:
                                    shutil.copytree(source_skin_path, target_skin_path)
                                except Exception as exception:
                                    self.log_signal.emit(f"    COPY ERROR '{skin}': {exception}")

            if not changes_found:
                self.log_signal.emit(f"[OK] Cars & skins up to date for: {target_directory}")

        except Exception as exception:
            self.log_signal.emit(f"SYNC ERROR on {target_directory}: {exception}")