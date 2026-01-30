import tkinter as tk
from tkinter import ttk, messagebox
import json
import concurrent.futures
from collections import Counter
import threading
from data_manager import DataManager
from network_client import NetworkClient
from sync_manager import SyncManager


class ACManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Racespot - Race Control Center")
        self.root.geometry("1100x850")

        try:
            with open('config.json', 'r') as f:
                self.config = json.load(f)
        except Exception as e:
            messagebox.showerror("Błąd Krytyczny", f"Nie można załadować config.json!\n{e}")
            root.destroy()
            return

        self.data_manager = DataManager(self.config['ac_root_path'])
        self.net_client = NetworkClient(self.config['secret_token'])
        self.sync_manager = SyncManager(self.config, self.log_safe)

        self.servers = self.data_manager.get_server_presets()
        self.rigs = self.config['clients']

        self.rig_vars = {}
        self.name_vars = {}
        self.name_entries = {}
        self.car_combos = {}
        self.selected_car_ids = {}
        self.current_server_raw_ids = []

        saved_names = self.data_manager.load_driver_names()

        for i, client in enumerate(self.rigs):
            ip = client['ip']
            self.selected_car_ids[ip] = None
            initial_name = saved_names.get(ip, "")
            name_var = tk.StringVar(value=initial_name)
            self.name_vars[ip] = name_var

        self.is_dark_mode = True
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.apply_theme()

        self.setup_ui()
        self.apply_theme()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        self.save_current_names()
        self.root.destroy()

    def save_current_names(self):
        current_names = {}
        for ip, var in self.name_vars.items():
            val = var.get().strip()
            if val:
                current_names[ip] = val
        self.data_manager.save_driver_names(current_names)

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()

    def apply_theme(self):
        if self.is_dark_mode:
            bg_color = "#2b2b2b";
            fg_color = "#ffffff";
            darker_bg = "#1e1e1e";
            button_bg = "#3c3c3c"
            button_active = "#505050";
            accent = "#4caf50";
            entry_bg = darker_bg;
            selected_entry_bg = "#1b5e20"
            log_bg = "#1e1e1e";
            log_fg = "#00ff00"
        else:
            bg_color = "#f0f0f0";
            fg_color = "#000000";
            darker_bg = "#ffffff";
            button_bg = "#e0e0e0"
            button_active = "#c0c0c0";
            accent = "#4caf50";
            entry_bg = "#ffffff";
            selected_entry_bg = "#c8e6c9"
            log_bg = "#ffffff";
            log_fg = "#000000"

        self.root.configure(bg=bg_color)
        self.root.option_add('*TCombobox*Listbox.background', darker_bg)
        self.root.option_add('*TCombobox*Listbox.foreground', fg_color)
        self.root.option_add('*TCombobox*Listbox.selectBackground', accent)
        self.root.option_add('*TCombobox*Listbox.selectForeground', fg_color if self.is_dark_mode else "#000000")

        self.style.configure(".", background=bg_color, foreground=fg_color)
        self.style.configure("TFrame", background=bg_color)
        self.style.configure("TLabelframe", background=bg_color, foreground=fg_color, bordercolor="#999999")
        self.style.configure("TLabelframe.Label", background=bg_color, foreground=fg_color, font=('Arial', 9, 'bold'))
        self.style.configure("TLabel", background=bg_color, foreground=fg_color)
        self.style.configure("TButton", background=button_bg, foreground=fg_color, borderwidth=1, bordercolor="#999999")
        self.style.map("TButton", background=[('active', button_active), ('pressed', accent)],
                       foreground=[('disabled', '#777777')])
        self.style.configure("TEntry", fieldbackground=entry_bg, foreground=fg_color, insertcolor=fg_color,
                             bordercolor="#999999")
        self.style.configure("Selected.TEntry", fieldbackground=selected_entry_bg, foreground=fg_color,
                             insertcolor=fg_color, bordercolor=accent)
        self.style.configure("TCombobox", fieldbackground=darker_bg, background=button_bg, foreground=fg_color,
                             arrowcolor=fg_color, bordercolor="#999999")
        self.style.map("TCombobox", fieldbackground=[('readonly', darker_bg)],
                       selectbackground=[('readonly', darker_bg)], selectforeground=[('readonly', fg_color)])
        self.style.configure("TCheckbutton", background=bg_color, foreground=fg_color)
        self.style.map("TCheckbutton", background=[('active', bg_color)], indicatorcolor=[('selected', accent)])
        self.style.configure("TProgressbar", background=accent, troughcolor=darker_bg, bordercolor="#999999")

        if hasattr(self, 'log_text') and self.log_text is not None:
            try:
                self.log_text.configure(bg=log_bg, fg=log_fg, insertbackground=fg_color)
            except:
                pass

    def setup_ui(self):
        top_frame = ttk.LabelFrame(self.root, text="Konfiguracja Serwera (Wspólna)", padding=10)
        top_frame.pack(fill="x", padx=10, pady=5)
        top_frame.columnconfigure(1, weight=0);
        top_frame.columnconfigure(99, weight=1)

        ttk.Label(top_frame, text="Wybierz Serwer:").grid(row=0, column=0, padx=5, sticky="w")
        self.srv_combo = ttk.Combobox(top_frame, values=[s['name'] for s in self.servers], state="readonly",
                                      font=('Arial', 10, 'bold'), width=45)
        self.srv_combo.grid(row=0, column=1, padx=5, sticky="w")
        self.srv_combo.bind("<<ComboboxSelected>>", self.on_server_change)

        top_btns = ttk.Frame(top_frame)
        top_btns.grid(row=0, column=2, padx=5, sticky="w")
        ttk.Button(top_btns, text="🔄 Odśwież Listę", command=self.refresh_app_state).pack(side="left", padx=2)
        ttk.Button(top_btns, text="🌗 Motyw", width=10, command=self.toggle_theme).pack(side="left", padx=2)

        rig_frame = ttk.LabelFrame(self.root, text="Lista Stanowisk", padding=10)
        rig_frame.pack(fill="both", expand=True, padx=10, pady=5)

        headers_frame = ttk.Frame(rig_frame)
        headers_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(headers_frame, text="Wybór", width=10).pack(side="left", padx=5)
        ttk.Label(headers_frame, text="Stanowisko", width=15).pack(side="left", padx=5)
        ttk.Label(headers_frame, text="Imię Kierowcy", width=25).pack(side="left", padx=5)
        ttk.Label(headers_frame, text="Samochód (Wolne / Razem)", width=40).pack(side="left", padx=5)

        list_container = ttk.Frame(rig_frame)
        list_container.pack(fill="both", expand=True)

        for i, client in enumerate(self.rigs):
            ip = client['ip']
            row_frame = ttk.Frame(list_container)
            row_frame.pack(fill="x", pady=2)

            var = tk.BooleanVar()
            self.rig_vars[ip] = var
            cb = ttk.Checkbutton(row_frame, variable=var, command=lambda ip=ip: self.on_rig_check(ip))
            cb.pack(side="left", padx=(15, 5))

            ttk.Label(row_frame, text=client['name'], width=15, anchor="w").pack(side="left", padx=5)

            entry = ttk.Entry(row_frame, textvariable=self.name_vars[ip], width=25)
            entry.pack(side="left", padx=5)
            self.name_entries[ip] = entry

            car_combo = ttk.Combobox(row_frame, state="readonly", width=45)
            car_combo.pack(side="left", padx=5, fill="x", expand=True)
            car_combo.bind("<<ComboboxSelected>>", lambda event, ip=ip: self.on_car_selected_manually(event, ip))
            self.car_combos[ip] = car_combo

        btn_frame = ttk.Frame(rig_frame)
        btn_frame.pack(fill="x", pady=10)
        ttk.Button(btn_frame, text="Zaznacz Wszystkie", command=lambda: self.set_all_rigs(True)).pack(side="left",
                                                                                                      padx=5)
        ttk.Button(btn_frame, text="Odznacz Wszystkie", command=lambda: self.set_all_rigs(False)).pack(side="left",
                                                                                                       padx=5)
        ttk.Separator(btn_frame, orient="vertical").pack(side="left", padx=30, fill="y")
        ttk.Button(btn_frame, text="🔍 TEST SYNCHRONIZACJI", command=self.run_sync_test).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="📂 PEŁNA SYNCHRONIZACJA", command=self.run_sync_full).pack(side="left", padx=5)

        act_frame = ttk.Frame(self.root, padding=20)
        act_frame.pack(fill="x")
        start_btn = ttk.Button(act_frame, text="🚀 DOŁĄCZ NA SERWER", command=self.start_race)
        start_btn.pack(side="left", fill="x", expand=True, padx=5)
        stop_btn = ttk.Button(act_frame, text="🛑 ZATRZYMAJ WSZYSTKIE ZAZNACZONE", command=self.stop_all)
        stop_btn.pack(side="right", fill="x", expand=True, padx=5)

        log_frame = tk.Frame(self.root)
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.log_text = tk.Text(log_frame, height=15, font=("Consolas", 9), bd=0)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def smart_distribute_cars(self):
        if not self.current_server_raw_ids: return
        available_pool = list(self.current_server_raw_ids)
        for ip, var in self.rig_vars.items():
            if var.get():
                if available_pool:
                    self.selected_car_ids[ip] = available_pool.pop(0)
                else:
                    self.selected_car_ids[ip] = None
            else:
                self.selected_car_ids[ip] = None
        self.recalc_labels_only()

    def recalc_labels_only(self):
        if not self.current_server_raw_ids: return
        total_counts = Counter(self.current_server_raw_ids)
        unique_car_ids = sorted(total_counts.keys())
        current_usage = Counter()
        for ip, var in self.rig_vars.items():
            if var.get():
                sel = self.selected_car_ids.get(ip)
                if sel: current_usage[sel] += 1

        display_data = {}
        for car_id in unique_car_ids:
            total = total_counts[car_id]
            used = current_usage[car_id]
            left = total - used
            if left < 0: left = 0
            friendly_name = self.data_manager.get_car_display_name(car_id)
            display_data[car_id] = f"{friendly_name} ({left}/{total})"

        for ip, combo in self.car_combos.items():
            current_id = self.selected_car_ids.get(ip)
            is_checked = self.rig_vars[ip].get()
            my_values = []
            my_map = {}
            for car_id in unique_car_ids:
                total = total_counts[car_id]
                used = current_usage[car_id]
                left = total - used
                if left > 0 or car_id == current_id:
                    text = display_data[car_id]
                    my_values.append(text)
                    my_map[text] = car_id
            combo.display_map = my_map
            combo['values'] = my_values
            if is_checked and current_id and current_id in display_data:
                combo.set(display_data[current_id])
            else:
                combo.set('')

    def on_car_selected_manually(self, event, ip):
        combo = self.car_combos[ip]
        selected_text = combo.get()
        if hasattr(combo, 'display_map') and selected_text in combo.display_map:
            car_id = combo.display_map[selected_text]
            self.selected_car_ids[ip] = car_id
            self.recalc_labels_only()

    def on_rig_check(self, ip):
        self.update_entry_style(ip)
        if self.rig_vars[ip].get() and not self.selected_car_ids.get(ip):
            self.assign_next_available_car(ip)
        self.recalc_labels_only()

    def assign_next_available_car(self, target_ip):
        total_counts = Counter(self.current_server_raw_ids)
        current_usage = Counter()
        for ip, var in self.rig_vars.items():
            if var.get():
                sel = self.selected_car_ids.get(ip)
                if sel: current_usage[sel] += 1
        unique_car_ids = sorted(total_counts.keys())
        for car_id in unique_car_ids:
            if total_counts[car_id] > current_usage[car_id]:
                self.selected_car_ids[target_ip] = car_id
                return

    def set_all_rigs(self, state):
        for ip, var in self.rig_vars.items():
            var.set(state)
            self.update_entry_style(ip)
        if state:
            self.smart_distribute_cars()
        else:
            self.recalc_labels_only()

    def update_entry_style(self, ip):
        is_checked = self.rig_vars[ip].get()
        entry = self.name_entries[ip]
        if is_checked:
            entry.configure(style="Selected.TEntry")
        else:
            entry.configure(style="TEntry")

    def run_sync_test(self):
        if not self.config.get('master_cars_path'):
            messagebox.showwarning("Błąd", "Brak ścieżek Master w config.json!")
            return
        if messagebox.askyesno("Test Sync", "Uruchomić test (brak zmian)?"):
            threading.Thread(target=self.sync_manager.perform_sync, args=(True,), daemon=True).start()

    def run_sync_full(self):
        if not self.config.get('master_cars_path'):
            messagebox.showwarning("Błąd", "Brak ścieżek Master w config.json!")
            return
        if messagebox.askyesno("PEŁNA Synchronizacja", "UWAGA: Nadpisanie danych!\nKontynuować?"):
            threading.Thread(target=self.sync_manager.perform_sync, args=(False,), daemon=True).start()

    def log_safe(self, msg):
        self.root.after(0, lambda: self.log(msg))

    def log(self, msg):
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")

    # --- ZMIANY DOTYCZĄCE WYŚWIETLANIA LISTY SERWERÓW (ZIELONA KROPKA) ---

    def refresh_app_state(self):
        current_selection = self.srv_combo.get()

        # ZMIANA: Usuwamy "● " (dużą kropkę) zamiast "• "
        clean_selection = current_selection.replace("● ", "").replace("• ", "").strip()

        self.log("Odświeżanie listy serwerów...")
        self.servers = self.data_manager.get_server_presets()

        display_values = []
        for s in self.servers:
            # ZMIANA: Używamy dużej kropki "● " dla aktywnych
            # Dla nieaktywnych dajemy dwie spacje, żeby wyrównać tekst w pionie
            prefix = "● " if s.get('is_running', False) else "  "
            display_values.append(f"{prefix}{s['name']}")

        self.srv_combo['values'] = display_values
        self.log(f"Znaleziono {len(self.servers)} serwerów.")

        found = False
        for val in display_values:
            if clean_selection in val:
                self.srv_combo.set(val)
                self.on_server_change(None)
                found = True
                break

        if not found:
            self.srv_combo.set('')
            self.current_server_raw_ids = []
            for ip in self.car_combos:
                self.selected_car_ids[ip] = None
                self.car_combos[ip].set('')
                self.car_combos[ip]['values'] = []

    def on_server_change(self, event=None):
        sel_display_name = self.srv_combo.get()

        # ZMIANA: Usuwamy "● "
        clean_name = sel_display_name.replace("● ", "").strip()

        selected_server = None
        for s in self.servers:
            if s['name'] == clean_name:
                selected_server = s
                break

        if selected_server:
            fresh = self.data_manager.refresh_server_config(selected_server['folder_id'])
            if fresh:
                fresh['is_running'] = selected_server.get('is_running', False)
                selected_server = fresh
                for i, s in enumerate(self.servers):
                    if s['folder_id'] == fresh['folder_id']:
                        self.servers[i] = fresh

            self.update_ui_for_server(selected_server)

    def update_ui_for_server(self, server):
        self.current_server_raw_ids = server['car_ids']
        for ip in self.car_combos: self.selected_car_ids[ip] = None
        self.smart_distribute_cars()

        # Dodatkowy bajer: Wypisz status w logu
        status_txt = "[ONLINE]" if server.get('is_running', False) else "[OFFLINE]"
        self.log(f"Załadowano: {server['name']} {status_txt} ({len(self.current_server_raw_ids)} slotów)")

    # -----------------------------------------------------------------------

    def start_race(self):
        srv_name_display = self.srv_combo.get()
        # ZMIANA: Usuwamy "● "
        clean_name = srv_name_display.replace("● ", "").strip()

        server = None
        for s in self.servers:
            if s['name'] == clean_name:
                server = s
                break

        if not server:
            messagebox.showerror("Błąd", "Wybierz serwer!")
            return

        for ip, var in self.rig_vars.items():
            if var.get():
                if not self.name_vars[ip].get().strip():
                    messagebox.showwarning("Błąd", "Wypełnij imiona dla zaznaczonych!")
                    return

        self.save_current_names()

        targets = []
        for ip, var in self.rig_vars.items():
            if var.get():
                name = self.name_vars[ip].get().strip()
                car_id = self.selected_car_ids.get(ip)
                if not car_id:
                    self.log(f"POMINIĘTO {ip}: Brak auta!")
                    continue
                targets.append({"ip": ip, "driver_name": name, "car_id": car_id})

        if not targets:
            messagebox.showwarning("Błąd", "Brak celów do uruchomienia.")
            return

        self.log(f"Startowanie {len(targets)} maszyn...")
        srv_ip = self.config.get("master_server_ip", "192.168.0.11")

        def send_single(target_data):
            payload = {
                "server_data": {
                    "ip": srv_ip,
                    "udp_port": server['udp_port'],
                    "http_port": server['http_port'],
                    "password": server.get('password', ''),
                    "server_name": server['name']
                },
                "track_data": {
                    "track": server.get('track', 'imola'),
                    "config_track": server.get('track_layout', '')
                },
                "car_data": {
                    "model_id": target_data['car_id'],
                    "driver_name": target_data['driver_name'],
                    "skin": "default"
                }
            }
            return self.net_client.send_command_to_host(target_data['ip'], payload)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ip = {executor.submit(send_single, t): t['ip'] for t in targets}
            for future in concurrent.futures.as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    success, msg = future.result()
                    status = "OK" if success else "BŁĄD"
                    self.log(f"{ip}: {status} - {msg}")
                except Exception as e:
                    self.log(f"{ip}: ERROR - {str(e)}")

    def stop_all(self):
        selected_ips = [ip for ip, var in self.rig_vars.items() if var.get()]
        if not selected_ips:
            messagebox.showwarning("Info", "Zaznacz komputery do zatrzymania")
            return
        self.log(f"Zatrzymywanie {len(selected_ips)} maszyn (Ctrl+E)...")

        def stop_single(ip):
            return self.net_client.stop_host(ip)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            for future in concurrent.futures.as_completed(
                    {executor.submit(stop_single, ip): ip for ip in selected_ips}):
                pass
        self.log(f"Wysłano STOP")