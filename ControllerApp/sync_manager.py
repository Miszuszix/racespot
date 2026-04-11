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
        self.details = {}

    def get_rig_name(self, index):
        clients = self.config_manager.get("clients", [])
        rig_name = f"RIG {index + 1}"
        if index < len(clients):
            rig_name = clients[index].get("name", rig_name)

        # Nadpisujemy RIG 1 jako Komputer Serwerowy
        if rig_name == "RIG 1":
            return "Komputer Serwerowy"
        return rig_name

    def run(self):
        mode_text = "[TRYB TESTOWY]" if self.dry_run else "[WŁAŚCIWA SYNCHRONIZACJA]"
        self.log_signal.emit(f"\n=== ROZPOCZĘCIE {mode_text} ===")

        master_cars_directory = self.config_manager.get('master_cars_path', '')
        master_tracks_directory = self.config_manager.get('master_tracks_path', '')
        target_cars_directories = self.config_manager.get('sync_cars_paths', [])
        target_tracks_directories = self.config_manager.get('sync_tracks_paths', [])

        # Inicjalizacja słowników na podstawie ilości ścieżek
        max_paths = max(len(target_cars_directories), len(target_tracks_directories))
        for i in range(max_paths):
            rig_name = self.get_rig_name(i)
            if rig_name not in self.summary:
                self.summary[rig_name] = {
                    "cars_copy": 0, "cars_del": 0,
                    "skins_add": 0, "skins_del": 0,
                    "tracks_copy": 0, "tracks_del": 0
                }
                self.details[rig_name] = {
                    "cars_copy": [], "cars_del": [],
                    "skins_add": [], "skins_del": [],
                    "tracks_copy": [], "tracks_del": []
                }

        if not master_cars_directory or not master_tracks_directory:
            self.log_signal.emit("BŁĄD: Nie zdefiniowano głównych ścieżek (Master) w konfiguracji.")
            self.finished_signal.emit()
            return

        if self.sync_type == "cars_tracks":
            self.log_signal.emit(">>> SPRAWDZANIE AUT (BEZ SKINÓW)")
            if not os.path.exists(master_cars_directory):
                self.log_signal.emit(f"BŁĄD KRYTYCZNY: Nie znaleziono głównego folderu aut: {master_cars_directory}")
            else:
                for i, target_directory in enumerate(target_cars_directories):
                    if target_directory.strip():
                        rig_name = self.get_rig_name(i)
                        self.sync_cars_only(master_cars_directory, target_directory, rig_name)

            self.log_signal.emit(">>> SPRAWDZANIE TORÓW")
            if not os.path.exists(master_tracks_directory):
                self.log_signal.emit(f"BŁĄD KRYTYCZNY: Nie znaleziono głównego folderu torów: {master_tracks_directory}")
            else:
                for i, target_directory in enumerate(target_tracks_directories):
                    if target_directory.strip():
                        rig_name = self.get_rig_name(i)
                        self.sync_basic_directory(master_tracks_directory, target_directory, rig_name)

        elif self.sync_type == "skins":
            self.log_signal.emit(">>> SPRAWDZANIE SKINÓW (TYLKO)")
            if not os.path.exists(master_cars_directory):
                self.log_signal.emit(f"BŁĄD KRYTYCZNY: Nie znaleziono głównego folderu aut: {master_cars_directory}")
            else:
                for i, target_directory in enumerate(target_cars_directories):
                    if target_directory.strip():
                        rig_name = self.get_rig_name(i)
                        self.sync_skins_only(master_cars_directory, target_directory, rig_name)

        # Generowanie raportu końcowego w trybie DRY RUN
        if self.dry_run:
            # 1. ZGRUPOWANE SZCZEGÓŁY
            details_lines = ["\n=== SZCZEGÓŁY DO ZMIANY ==="]
            has_any_changes = False

            for rig_name, rig_details in self.details.items():
                if not any(len(lst) > 0 for lst in rig_details.values()):
                    continue

                has_any_changes = True
                details_lines.append(f"\n---- {rig_name} ----")

                if self.sync_type == "cars_tracks":
                    if rig_details["cars_copy"]:
                        details_lines.append("Skopiowałbym auta:")
                        for item in rig_details["cars_copy"]: details_lines.append(f"  + {item}")
                    if rig_details["cars_del"]:
                        details_lines.append("Usunąłbym auta:")
                        for item in rig_details["cars_del"]: details_lines.append(f"  - {item}")
                    if rig_details["tracks_copy"]:
                        details_lines.append("Skopiowałbym tory:")
                        for item in rig_details["tracks_copy"]: details_lines.append(f"  + {item}")
                    if rig_details["tracks_del"]:
                        details_lines.append("Usunąłbym tory:")
                        for item in rig_details["tracks_del"]: details_lines.append(f"  - {item}")
                else:
                    if rig_details["skins_add"]:
                        details_lines.append("Skopiowałbym skiny:")
                        for item in rig_details["skins_add"]: details_lines.append(f"  + {item}")
                    if rig_details["skins_del"]:
                        details_lines.append("Usunąłbym skiny:")
                        for item in rig_details["skins_del"]: details_lines.append(f"  - {item}")

            if not has_any_changes:
                details_lines.append("Brak plików do skopiowania lub usunięcia.")

            self.log_signal.emit("\n".join(details_lines))

            # 2. PODSUMOWANIE LICZBOWE
            summary_lines = ["\n=== PODSUMOWANIE TESTU SYNCHRONIZACJI ==="]

            for rig_name, stats in self.summary.items():
                if self.sync_type == "cars_tracks":
                    if stats['cars_copy'] == 0 and stats['cars_del'] == 0 and stats['tracks_copy'] == 0 and stats['tracks_del'] == 0:
                        continue
                    summary_lines.append(f"-- {rig_name} --")
                    summary_lines.append("-- Auta --")
                    summary_lines.append(f"Do skopiowania: {stats['cars_copy']}")
                    summary_lines.append(f"Do usunięcia: {stats['cars_del']}")
                    summary_lines.append("-- Tory --")
                    summary_lines.append(f"Do skopiowania: {stats['tracks_copy']}")
                    summary_lines.append(f"Do usunięcia: {stats['tracks_del']}")
                    summary_lines.append("")
                else:
                    if stats['skins_add'] == 0 and stats['skins_del'] == 0:
                        continue
                    summary_lines.append(f"-- {rig_name} --")
                    summary_lines.append("-- Skiny --")
                    summary_lines.append(f"Do skopiowania: {stats['skins_add']}")
                    summary_lines.append(f"Do usunięcia: {stats['skins_del']}")
                    summary_lines.append("")

            if len(summary_lines) == 1:
                summary_lines.append("Wszystko aktualne!")
            self.log_signal.emit("\n".join(summary_lines))

        self.log_signal.emit(f"=== ZAKOŃCZONO {mode_text} ===\n")
        self.finished_signal.emit()

    def sync_basic_directory(self, source_directory, target_directory, rig_name):
        if not os.path.exists(target_directory):
            self.log_signal.emit(f"BŁĄD: Ścieżka docelowa niedostępna: {target_directory} ({rig_name})")
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
                    self.details[rig_name]["tracks_copy"].append(item)
                    if not self.dry_run:
                        self.log_signal.emit(f"[+] Kopiowanie toru: '{item}' na {rig_name}")
                        try:
                            shutil.copytree(source_path, target_path)
                        except Exception as exception:
                            self.log_signal.emit(f"    BŁĄD KOPIOWANIA '{item}': {exception}")

            for item in excess_items:
                target_path = os.path.join(target_directory, item)
                self.summary[rig_name]["tracks_del"] += 1
                self.details[rig_name]["tracks_del"].append(item)
                if not self.dry_run:
                    self.log_signal.emit(f"[-] Usuwanie toru: '{item}' z {rig_name}")
                    try:
                        if os.path.isdir(target_path):
                            shutil.rmtree(target_path)
                        else:
                            os.remove(target_path)
                    except Exception as exception:
                        self.log_signal.emit(f"    BŁĄD USUWANIA '{item}': {exception}")

        except Exception as exception:
            self.log_signal.emit(f"BŁĄD SYNCHRONIZACJI dla {rig_name}: {exception}")

    def sync_cars_only(self, source_directory, target_directory, rig_name):
        if not os.path.exists(target_directory):
            self.log_signal.emit(f"BŁĄD: Ścieżka docelowa niedostępna: {target_directory} ({rig_name})")
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
                    self.details[rig_name]["cars_copy"].append(car)
                    if not self.dry_run:
                        self.log_signal.emit(f"[+] Kopiowanie auta: '{car}' na {rig_name}")
                        try:
                            shutil.copytree(source_path, target_path)
                        except Exception as exception:
                            self.log_signal.emit(f"    BŁĄD KOPIOWANIA '{car}': {exception}")

            for car in excess_cars:
                target_path = os.path.join(target_directory, car)
                self.summary[rig_name]["cars_del"] += 1
                self.details[rig_name]["cars_del"].append(car)
                if not self.dry_run:
                    self.log_signal.emit(f"[-] Usuwanie auta: '{car}' z {rig_name}")
                    try:
                        if os.path.isdir(target_path):
                            shutil.rmtree(target_path)
                        else:
                            os.remove(target_path)
                    except Exception as exception:
                        self.log_signal.emit(f"    BŁĄD USUWANIA '{car}': {exception}")

        except Exception as exception:
            self.log_signal.emit(f"BŁĄD SYNCHRONIZACJI dla {rig_name}: {exception}")

    def sync_skins_only(self, source_directory, target_directory, rig_name):
        if not os.path.exists(target_directory):
            self.log_signal.emit(f"BŁĄD: Ścieżka docelowa niedostępna: {target_directory} ({rig_name})")
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
                            self.details[rig_name]["skins_add"].append(f"{car} -> {skin}")
                            if not self.dry_run:
                                self.log_signal.emit(f"[+] Kopiowanie skina: '{skin}' (auto: {car}) na {rig_name}")
                                try:
                                    shutil.copytree(source_skin_path, target_skin_path)
                                except Exception as exception:
                                    self.log_signal.emit(f"    BŁĄD KOPIOWANIA '{skin}': {exception}")

                    for skin in excess_skins:
                        target_skin_path = os.path.join(target_skins_directory, skin)
                        self.summary[rig_name]["skins_del"] += 1
                        self.details[rig_name]["skins_del"].append(f"{car} -> {skin}")
                        if not self.dry_run:
                            self.log_signal.emit(f"[-] Usuwanie skina: '{skin}' (auto: {car}) z {rig_name}")
                            try:
                                if os.path.isdir(target_skin_path):
                                    shutil.rmtree(target_skin_path)
                                else:
                                    os.remove(target_skin_path)
                            except Exception as exception:
                                self.log_signal.emit(f"    BŁĄD USUWANIA '{skin}': {exception}")

        except Exception as exception:
            self.log_signal.emit(f"BŁĄD SYNCHRONIZACJI dla {rig_name}: {exception}")