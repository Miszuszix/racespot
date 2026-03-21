import os
import json
from collections import Counter
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox, QTextEdit,
    QGroupBox, QScrollArea, QGridLayout, QMessageBox
)
from PySide6.QtCore import Qt, Slot
from sync_manager import SyncWorker


class GuiManager(QMainWindow):
    def __init__(self, config_manager, data_provider, network_manager):
        super().__init__()
        self.config_manager = config_manager
        self.data_provider = data_provider
        self.network_manager = network_manager

        # Wczytanie tekstów GUI
        self.strings = {}
        self.load_strings()

        # Pamięć dla LAN
        self.server_presets = []
        self.rig_checkboxes = {}
        self.rig_name_inputs = {}
        self.rig_car_comboboxes = {}
        self.rig_skin_comboboxes = {}
        self.current_server_slots = []
        self.rig_assigned_slots = {}

        # Pamięć dla ONLINE
        self.current_online_slots = []
        self.online_assigned_slots = {}
        self.current_online_info = None
        self.online_rig_checkboxes = {}
        self.online_rig_name_inputs = {}
        self.online_rig_car_comboboxes = {}
        self.online_rig_skin_comboboxes = {}

        self.settings_inputs = {}
        self.rig_ip_inputs = []

        self.setWindowTitle(self.t("window_title"))
        self.resize(1200, 900)
        self.setup_user_interface()
        self.refresh_servers_list()

        # Inicjujemy pobranie danych dla serwerów Online
        self.refresh_online_servers_list()
        self.load_drivers_history()

    def load_strings(self):
        try:
            with open("strings.json", "r", encoding="utf-8") as f:
                self.strings = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load strings.json: {e}")

    def t(self, key, *args):
        text = self.strings.get(key, key)
        if args:
            try:
                text = text.format(*args)
            except Exception:
                pass
        return text

    def setup_user_interface(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        self.tabs_container = QTabWidget()
        main_layout.addWidget(self.tabs_container)

        self.lan_tab = QWidget()
        self.online_tab = QWidget()
        self.settings_tab = QWidget()

        self.tabs_container.addTab(self.lan_tab, self.t("tab_lan"))
        self.tabs_container.addTab(self.online_tab, self.t("tab_online"))
        self.tabs_container.addTab(self.settings_tab, self.t("tab_settings"))

        self.build_lan_tab()
        self.build_online_tab()
        self.build_settings_tab()

        self.log_display_area = QTextEdit()
        self.log_display_area.setReadOnly(True)
        self.log_display_area.setMaximumHeight(200)
        main_layout.addWidget(self.log_display_area)

    def build_lan_tab(self):
        layout = QVBoxLayout(self.lan_tab)

        server_selection_group = QGroupBox(self.t("lan_server_config"))
        server_selection_layout = QHBoxLayout(server_selection_group)

        server_selection_layout.addWidget(QLabel(self.t("lan_select_server")))
        self.server_combobox = QComboBox()
        self.server_combobox.setMinimumWidth(300)
        self.server_combobox.currentIndexChanged.connect(self.on_server_selection_changed)
        self.server_combobox.activated.connect(self.on_server_selection_changed)
        server_selection_layout.addWidget(self.server_combobox)

        refresh_button = QPushButton(self.t("lan_btn_refresh"))
        refresh_button.clicked.connect(self.refresh_servers_list)
        server_selection_layout.addWidget(refresh_button)
        server_selection_layout.addStretch()
        layout.addWidget(server_selection_group)

        rigs_group = QGroupBox(self.t("lan_rigs_config"))
        rigs_layout = QVBoxLayout(rigs_group)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        self.scroll_layout = QGridLayout(scroll_content)

        headers = [self.t("table_select"), self.t("table_rig"), self.t("table_driver"), self.t("table_car"),
                   self.t("table_skin")]
        for column_index, header_text in enumerate(headers):
            self.scroll_layout.addWidget(QLabel(header_text), 0, column_index)

        clients_list = self.config_manager.get("clients", [])
        for row_index, client_data in enumerate(clients_list, start=1):
            ip_address = client_data.get("ip")
            rig_name = client_data.get("name")

            self.rig_assigned_slots[ip_address] = None

            checkbox = QCheckBox()
            self.rig_checkboxes[ip_address] = checkbox
            checkbox.toggled.connect(lambda state, ip=ip_address: self.on_rig_checkbox_toggled(ip, state))
            self.scroll_layout.addWidget(checkbox, row_index, 0)

            self.scroll_layout.addWidget(QLabel(rig_name), row_index, 1)

            name_input = QLineEdit()
            self.rig_name_inputs[ip_address] = name_input
            self.scroll_layout.addWidget(name_input, row_index, 2)

            car_combobox = QComboBox()
            car_combobox.setMinimumWidth(300)
            car_combobox.currentIndexChanged.connect(lambda index, ip=ip_address: self.on_car_selection_changed(ip))
            self.rig_car_comboboxes[ip_address] = car_combobox
            self.scroll_layout.addWidget(car_combobox, row_index, 3)

            skin_combobox = QComboBox()
            skin_combobox.setMinimumWidth(250)
            skin_combobox.setPlaceholderText(self.t("combo_no_skin"))
            skin_combobox.currentIndexChanged.connect(lambda index, ip=ip_address: self.on_skin_selection_changed(ip))
            self.rig_skin_comboboxes[ip_address] = skin_combobox
            self.scroll_layout.addWidget(skin_combobox, row_index, 4)

        self.scroll_layout.setRowStretch(len(clients_list) + 1, 1)

        scroll_area.setWidget(scroll_content)
        rigs_layout.addWidget(scroll_area)

        buttons_layout = QHBoxLayout()
        select_all_button = QPushButton(self.t("btn_select_all"))
        select_all_button.clicked.connect(lambda: self.toggle_all_checkboxes(True))
        deselect_all_button = QPushButton(self.t("btn_deselect_all"))
        deselect_all_button.clicked.connect(lambda: self.toggle_all_checkboxes(False))

        test_sync_button = QPushButton(self.t("btn_test_sync"))
        test_sync_button.setStyleSheet("background-color: #555555; color: white;")
        test_sync_button.clicked.connect(self.start_test_synchronization)

        full_sync_button = QPushButton(self.t("btn_full_sync"))
        full_sync_button.setStyleSheet("background-color: #f57c00; color: white; font-weight: bold;")
        full_sync_button.clicked.connect(self.start_synchronization)

        buttons_layout.addWidget(select_all_button)
        buttons_layout.addWidget(deselect_all_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(test_sync_button)
        buttons_layout.addWidget(full_sync_button)
        rigs_layout.addLayout(buttons_layout)

        layout.addWidget(rigs_group)

        action_buttons_layout = QHBoxLayout()
        start_race_button = QPushButton(self.t("lan_btn_start"))
        start_race_button.setMinimumHeight(50)
        start_race_button.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold;")
        start_race_button.clicked.connect(self.execute_start_race_lan)

        stop_race_button = QPushButton(self.t("lan_btn_stop"))
        stop_race_button.setMinimumHeight(50)
        stop_race_button.setStyleSheet("background-color: #c62828; color: white; font-weight: bold;")
        stop_race_button.clicked.connect(self.execute_stop_race)

        action_buttons_layout.addWidget(start_race_button)
        action_buttons_layout.addWidget(stop_race_button)
        layout.addLayout(action_buttons_layout)

    def build_online_tab(self):
        layout = QVBoxLayout(self.online_tab)

        connection_group = QGroupBox(self.t("online_server_selection"))
        connection_layout = QVBoxLayout(connection_group)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel(self.t("online_select_server")))

        self.online_server_combobox = QComboBox()
        self.online_server_combobox.setMinimumWidth(400)

        # BAZA TWOICH SERWERÓW: Zmienione IP na poprawne 146...
        self.hardcoded_online_servers = [
            {"ip": "146.59.35.158", "http_port": "8011", "password": "twoje_haslo_1"},
            {"ip": "146.59.35.158", "http_port": "8012", "password": "twoje_haslo_2"},
            {"ip": "146.59.35.158", "http_port": "8013", "password": "twoje_haslo_3"}
        ]

        self.online_server_combobox.currentIndexChanged.connect(self.fetch_online_data)
        self.online_server_combobox.activated.connect(self.fetch_online_data)
        top_row.addWidget(self.online_server_combobox)

        fetch_button = QPushButton(self.t("online_btn_refresh"))
        fetch_button.clicked.connect(self.refresh_online_servers_list)
        top_row.addWidget(fetch_button)
        top_row.addStretch()

        connection_layout.addLayout(top_row)

        self.online_server_info_label = QLabel(self.t("online_connecting"))
        self.online_server_info_label.setStyleSheet("color: #aaaaaa; font-style: italic; margin-top: 5px;")
        connection_layout.addWidget(self.online_server_info_label)

        layout.addWidget(connection_group)

        rigs_group = QGroupBox(self.t("online_rigs_selection"))
        rigs_layout = QVBoxLayout(rigs_group)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        self.online_scroll_layout = QGridLayout(scroll_content)

        headers = [self.t("table_select"), self.t("table_rig"), self.t("table_driver"), self.t("table_car"),
                   self.t("table_skin")]
        for column_index, header_text in enumerate(headers):
            self.online_scroll_layout.addWidget(QLabel(header_text), 0, column_index)

        clients_list = self.config_manager.get("clients", [])
        for row_index, client_data in enumerate(clients_list, start=1):
            ip_address = client_data.get("ip")
            rig_name = client_data.get("name")

            self.online_assigned_slots[ip_address] = None

            checkbox = QCheckBox()
            checkbox.toggled.connect(lambda state, ip=ip_address: self.on_online_rig_checkbox_toggled(ip, state))
            self.online_rig_checkboxes[ip_address] = checkbox
            self.online_scroll_layout.addWidget(checkbox, row_index, 0)

            self.online_scroll_layout.addWidget(QLabel(rig_name), row_index, 1)

            name_input = QLineEdit()
            self.online_rig_name_inputs[ip_address] = name_input
            self.online_scroll_layout.addWidget(name_input, row_index, 2)

            car_combobox = QComboBox()
            car_combobox.setMinimumWidth(300)
            car_combobox.currentIndexChanged.connect(
                lambda index, ip=ip_address: self.on_online_car_selection_changed(ip))
            self.online_rig_car_comboboxes[ip_address] = car_combobox
            self.online_scroll_layout.addWidget(car_combobox, row_index, 3)

            skin_combobox = QComboBox()
            skin_combobox.setMinimumWidth(250)
            skin_combobox.setPlaceholderText(self.t("combo_no_skin"))
            skin_combobox.currentIndexChanged.connect(
                lambda index, ip=ip_address: self.on_online_skin_selection_changed(ip))
            self.online_rig_skin_comboboxes[ip_address] = skin_combobox
            self.online_scroll_layout.addWidget(skin_combobox, row_index, 4)

        self.online_scroll_layout.setRowStretch(len(clients_list) + 1, 1)
        scroll_area.setWidget(scroll_content)
        rigs_layout.addWidget(scroll_area)

        buttons_layout = QHBoxLayout()
        select_all_button = QPushButton(self.t("btn_select_all"))
        select_all_button.clicked.connect(lambda: self.toggle_all_checkboxes_online(True))
        deselect_all_button = QPushButton(self.t("btn_deselect_all"))
        deselect_all_button.clicked.connect(lambda: self.toggle_all_checkboxes_online(False))
        buttons_layout.addWidget(select_all_button)
        buttons_layout.addWidget(deselect_all_button)
        buttons_layout.addStretch()
        rigs_layout.addLayout(buttons_layout)

        layout.addWidget(rigs_group)

        action_buttons_layout = QHBoxLayout()
        start_online_button = QPushButton(self.t("online_btn_start"))
        start_online_button.setMinimumHeight(50)
        start_online_button.setStyleSheet("background-color: #1565c0; color: white; font-weight: bold;")
        start_online_button.clicked.connect(self.execute_start_race_online)

        stop_online_button = QPushButton(self.t("online_btn_stop"))
        stop_online_button.setMinimumHeight(50)
        stop_online_button.setStyleSheet("background-color: #c62828; color: white; font-weight: bold;")
        stop_online_button.clicked.connect(self.execute_stop_race)

        action_buttons_layout.addWidget(start_online_button)
        action_buttons_layout.addWidget(stop_online_button)
        layout.addLayout(action_buttons_layout)

    def build_settings_tab(self):
        layout = QVBoxLayout(self.settings_tab)

        paths_group = QGroupBox(self.t("settings_paths_group"))
        paths_layout = QGridLayout(paths_group)

        settings_keys = [
            ("ac_root_path", self.t("settings_ac_root")),
            ("master_server_ip", self.t("settings_master_ip")),
            ("secret_token", self.t("settings_token")),
            ("master_cars_path", self.t("settings_cars_path")),
            ("master_tracks_path", self.t("settings_tracks_path"))
        ]

        for row_index, (config_key, label_text) in enumerate(settings_keys):
            paths_layout.addWidget(QLabel(label_text), row_index, 0)
            input_field = QLineEdit(self.config_manager.get(config_key, ""))
            self.settings_inputs[config_key] = input_field
            paths_layout.addWidget(input_field, row_index, 1)

        layout.addWidget(paths_group)

        rigs_ip_group = QGroupBox(self.t("settings_rigs_ip"))
        rigs_ip_layout = QGridLayout(rigs_ip_group)

        clients_list = self.config_manager.get("clients", [])
        client_ips_map = {client.get("name"): client.get("ip") for client in clients_list}

        for i in range(1, 10):
            rig_name = f"RIG {i}"
            label = QLabel(self.t("settings_rig_ip_label", rig_name))
            ip_input = QLineEdit(client_ips_map.get(rig_name, ""))
            self.rig_ip_inputs.append((rig_name, ip_input))

            row = (i - 1) % 5
            col = ((i - 1) // 5) * 2

            rigs_ip_layout.addWidget(label, row, col)
            rigs_ip_layout.addWidget(ip_input, row, col + 1)

        layout.addWidget(rigs_ip_group)
        layout.addStretch()

        save_button = QPushButton(self.t("settings_btn_save"))
        save_button.setMinimumHeight(40)
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)

    def append_log_message(self, message):
        self.log_display_area.append(message)
        self.config_manager.write_log("GUI", message)

    def update_row_highlight(self, ip_address, state, is_online=False):
        if is_online:
            name_input = self.online_rig_name_inputs.get(ip_address)
        else:
            name_input = self.rig_name_inputs.get(ip_address)

        if name_input:
            if state:
                name_input.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold;")
            else:
                name_input.setStyleSheet("")

    # --- LAN LOGIC ---

    def toggle_all_checkboxes(self, state):
        for ip, checkbox in self.rig_checkboxes.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(state)
            checkbox.blockSignals(False)
            self.update_row_highlight(ip, state)

        if state:
            self.smart_distribute_cars()
        else:
            for ip_address in self.rig_assigned_slots:
                self.rig_assigned_slots[ip_address] = None
            self.recalc_labels_only()

    def refresh_servers_list(self):
        self.append_log_message(self.t("log_refreshing_lan"))

        current_index = self.server_combobox.currentIndex()
        saved_folder_id = None
        if current_index >= 0:
            old_data = self.server_combobox.itemData(current_index)
            if old_data:
                saved_folder_id = old_data.get("folder_id")

        self.server_presets = self.data_provider.fetch_server_presets()

        self.server_combobox.blockSignals(True)
        self.server_combobox.clear()

        index_to_restore = 0
        for idx, server_data in enumerate(self.server_presets):
            status_indicator = "●" if server_data.get("is_running") else "○"
            display_text = f"{status_indicator} {server_data['name']}"
            self.server_combobox.addItem(display_text, server_data)

            if saved_folder_id and server_data.get("folder_id") == saved_folder_id:
                index_to_restore = idx

        if self.server_combobox.count() > 0:
            self.server_combobox.setCurrentIndex(index_to_restore)

        self.server_combobox.blockSignals(False)
        self.append_log_message(self.t("log_found_servers", len(self.server_presets)))
        self.on_server_selection_changed()

    def on_server_selection_changed(self, *args):
        current_index = self.server_combobox.currentIndex()
        if current_index < 0:
            return

        selected_server = self.server_combobox.itemData(current_index)
        self.current_server_slots = selected_server.get("car_slots", [])

        for ip_address in self.rig_car_comboboxes.keys():
            self.rig_assigned_slots[ip_address] = None

        self.smart_distribute_cars()

    def smart_distribute_cars(self):
        if not self.current_server_slots:
            return

        assigned_slots = [slot for slot in self.rig_assigned_slots.values() if slot is not None]
        unassigned_slots = [slot for slot in self.current_server_slots if slot not in assigned_slots]

        for ip_address, checkbox in self.rig_checkboxes.items():
            if checkbox.isChecked():
                if not self.rig_assigned_slots.get(ip_address):
                    if unassigned_slots:
                        self.rig_assigned_slots[ip_address] = unassigned_slots.pop(0)
            else:
                if self.rig_assigned_slots.get(ip_address):
                    unassigned_slots.append(self.rig_assigned_slots[ip_address])
                    self.rig_assigned_slots[ip_address] = None

        self.recalc_labels_only()

    def recalc_labels_only(self):
        if not self.current_server_slots:
            for ip_address, combobox in self.rig_car_comboboxes.items():
                combobox.blockSignals(True)
                combobox.clear()
                combobox.setCurrentIndex(-1)
                combobox.blockSignals(False)

                skin_combobox = self.rig_skin_comboboxes[ip_address]
                skin_combobox.blockSignals(True)
                skin_combobox.clear()
                skin_combobox.setCurrentIndex(-1)
                skin_combobox.blockSignals(False)
            return

        model_totals = Counter(slot["model_id"] for slot in self.current_server_slots)
        assigned_slots = [slot for slot in self.rig_assigned_slots.values() if slot is not None]
        model_used = Counter(slot["model_id"] for slot in assigned_slots)
        unique_model_ids = sorted(model_totals.keys())

        for ip_address, car_combobox in self.rig_car_comboboxes.items():
            car_combobox.blockSignals(True)
            car_combobox.clear()

            is_checked = self.rig_checkboxes[ip_address].isChecked()
            current_slot = self.rig_assigned_slots.get(ip_address)

            if is_checked:
                index_to_select = -1
                for idx, model_id in enumerate(unique_model_ids):
                    total = model_totals[model_id]
                    used = model_used[model_id]
                    left = total - used
                    if left < 0: left = 0

                    display_name = self.data_provider.fetch_car_display_name(model_id)
                    item_text = f"{display_name} ({left}/{total})"
                    car_combobox.addItem(item_text, model_id)

                    if current_slot and current_slot["model_id"] == model_id:
                        index_to_select = idx

                car_combobox.setCurrentIndex(index_to_select)
            else:
                car_combobox.setCurrentIndex(-1)

            car_combobox.blockSignals(False)

            skin_combobox = self.rig_skin_comboboxes[ip_address]
            skin_combobox.blockSignals(True)
            skin_combobox.clear()

            if is_checked and current_slot:
                current_model = current_slot["model_id"]
                current_skin = current_slot["skin"]

                model_slots = [s for s in self.current_server_slots if s["model_id"] == current_model]
                skin_totals = Counter(s["skin"] for s in model_slots)

                assigned_model_slots = [s for s in assigned_slots if s["model_id"] == current_model]
                skin_used = Counter(s["skin"] for s in assigned_model_slots)

                unique_skins = sorted(skin_totals.keys())
                available_nice_skins = self.data_provider.fetch_available_skins(current_model)
                skin_name_map = {skin_data["folder_name"]: skin_data["display_name"] for skin_data in
                                 available_nice_skins}

                index_to_select_skin = -1
                for idx, skin in enumerate(unique_skins):
                    total_s = skin_totals[skin]
                    used_s = skin_used[skin]
                    left_s = total_s - used_s
                    if left_s < 0: left_s = 0

                    raw_skin_name = skin if skin else "default"
                    display_name = skin_name_map.get(skin, raw_skin_name.replace("_", " ").title())

                    item_text = f"{display_name} ({left_s}/{total_s})"
                    skin_combobox.addItem(item_text, skin)

                    if skin == current_skin:
                        index_to_select_skin = idx

                skin_combobox.setCurrentIndex(index_to_select_skin)
            else:
                skin_combobox.setCurrentIndex(-1)

            skin_combobox.blockSignals(False)

    def on_car_selection_changed(self, ip_address):
        combobox = self.rig_car_comboboxes.get(ip_address)
        if not combobox: return

        current_index = combobox.currentIndex()
        if current_index < 0: return

        new_model_id = combobox.itemData(current_index)
        current_slot = self.rig_assigned_slots.get(ip_address)

        if current_slot and current_slot["model_id"] == new_model_id:
            return

        assigned_slots = list(self.rig_assigned_slots.values())
        target_slot = None

        for slot in self.current_server_slots:
            if slot["model_id"] == new_model_id and slot not in assigned_slots:
                target_slot = slot
                break

        if target_slot:
            self.rig_assigned_slots[ip_address] = target_slot
        else:
            for other_ip, other_slot in self.rig_assigned_slots.items():
                if other_slot and other_slot["model_id"] == new_model_id:
                    self.rig_assigned_slots[other_ip] = current_slot
                    self.rig_assigned_slots[ip_address] = other_slot
                    break

        self.recalc_labels_only()

    def on_skin_selection_changed(self, ip_address):
        combobox = self.rig_skin_comboboxes.get(ip_address)
        if not combobox: return
        current_index = combobox.currentIndex()
        if current_index < 0: return

        new_skin = combobox.itemData(current_index)
        current_slot = self.rig_assigned_slots.get(ip_address)

        if not current_slot or current_slot["skin"] == new_skin: return

        model_id = current_slot["model_id"]
        assigned_slots = list(self.rig_assigned_slots.values())
        target_slot = None

        for slot in self.current_server_slots:
            if slot["model_id"] == model_id and slot["skin"] == new_skin and slot not in assigned_slots:
                target_slot = slot
                break

        if target_slot:
            self.rig_assigned_slots[ip_address] = target_slot
        else:
            for other_ip, other_slot in self.rig_assigned_slots.items():
                if other_slot and other_slot["model_id"] == model_id and other_slot["skin"] == new_skin:
                    self.rig_assigned_slots[other_ip] = current_slot
                    self.rig_assigned_slots[ip_address] = other_slot
                    break

        self.recalc_labels_only()

    def on_rig_checkbox_toggled(self, ip_address, state):
        self.update_row_highlight(ip_address, state)
        if state and not self.rig_assigned_slots.get(ip_address):
            assigned_slots = list(self.rig_assigned_slots.values())
            for slot in self.current_server_slots:
                if slot not in assigned_slots:
                    self.rig_assigned_slots[ip_address] = slot
                    break
        elif not state:
            self.rig_assigned_slots[ip_address] = None
        self.recalc_labels_only()

    # --- ONLINE LOGIC ---

    def refresh_online_servers_list(self):
        self.append_log_message(self.t("log_fetching_online_names"))

        current_index = self.online_server_combobox.currentIndex()
        saved_port = None
        if current_index >= 0:
            old_data = self.online_server_combobox.itemData(current_index)
            if old_data:
                saved_port = old_data.get("http_port")

        self.online_server_combobox.blockSignals(True)
        self.online_server_combobox.clear()

        index_to_restore = 0

        for idx, srv in enumerate(self.hardcoded_online_servers):
            ip = srv["ip"]
            port = srv["http_port"]

            data = self.data_provider.fetch_online_server_info(ip, port)
            if data and "error" not in data:
                name = data.get("name", f"Serwer (Port {port})")
            else:
                name = self.t("online_server_offline", port)

            self.online_server_combobox.addItem(name, srv)

            if saved_port and port == saved_port:
                index_to_restore = idx

        if self.online_server_combobox.count() > 0:
            self.online_server_combobox.setCurrentIndex(index_to_restore)

        self.online_server_combobox.blockSignals(False)
        self.fetch_online_data()

    def fetch_online_data(self, *args):
        current_index = self.online_server_combobox.currentIndex()
        if current_index < 0: return

        srv = self.online_server_combobox.itemData(current_index)
        ip = srv["ip"]
        port = srv["http_port"]
        password = srv["password"]

        self.append_log_message(self.t("log_connecting_online", ip, port))
        data = self.data_provider.fetch_online_server_info(ip, port)

        if not data or "error" in data:
            self.append_log_message(self.t("log_fetch_failed", data.get('error', 'Unknown error')))
            self.online_server_info_label.setText(self.t("online_err_connection"))
            self.current_online_slots = []
            self.recalc_labels_only_online()
            return

        name = data.get("name", "Unknown Server")
        track = data.get("track", "unknown")
        cars = data.get("cars", [])
        udp_port = data.get("port", 9600)
        tcp_port = data.get("tport", 9600)
        clients = data.get("clients", 0)
        maxclients = data.get("maxclients", 0)

        self.current_online_info = {
            "ip": ip,
            "udp_port": udp_port,
            "tcp_port": tcp_port,
            "http_port": int(port),
            "password": password,
            "track": track,
            "name": name
        }

        self.online_server_info_label.setText(self.t("online_connected_info", name, track, clients, maxclients))
        self.append_log_message(self.t("log_online_loaded", len(cars)))

        self.current_online_slots = []
        slot_idx = 0

        slots_to_create = maxclients if maxclients > 0 else 10

        for car in cars:
            for _ in range(slots_to_create):
                self.current_online_slots.append({
                    "slot_id": f"CAR_{slot_idx}",
                    "model_id": car,
                    "skin": ""
                })
                slot_idx += 1

        for ip_address in self.online_rig_car_comboboxes.keys():
            self.online_assigned_slots[ip_address] = None

        self.smart_distribute_cars_online()

    def toggle_all_checkboxes_online(self, state):
        for ip, checkbox in self.online_rig_checkboxes.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(state)
            checkbox.blockSignals(False)
            self.update_row_highlight(ip, state, is_online=True)

        if state:
            self.smart_distribute_cars_online()
        else:
            for ip_address in self.online_assigned_slots:
                self.online_assigned_slots[ip_address] = None
            self.recalc_labels_only_online()

    def smart_distribute_cars_online(self):
        if not self.current_online_slots:
            return

        assigned_slots = [slot for slot in self.online_assigned_slots.values() if slot is not None]
        unassigned_slots = [slot for slot in self.current_online_slots if slot not in assigned_slots]

        for ip_address, checkbox in self.online_rig_checkboxes.items():
            if checkbox.isChecked():
                if not self.online_assigned_slots.get(ip_address):
                    if unassigned_slots:
                        self.online_assigned_slots[ip_address] = unassigned_slots.pop(0)
            else:
                if self.online_assigned_slots.get(ip_address):
                    unassigned_slots.append(self.online_assigned_slots[ip_address])
                    self.online_assigned_slots[ip_address] = None

        self.recalc_labels_only_online()

    def recalc_labels_only_online(self):
        if not self.current_online_slots:
            for ip_address, combobox in self.online_rig_car_comboboxes.items():
                combobox.blockSignals(True)
                combobox.clear()
                combobox.setCurrentIndex(-1)
                combobox.blockSignals(False)

                skin_combobox = self.online_rig_skin_comboboxes[ip_address]
                skin_combobox.blockSignals(True)
                skin_combobox.clear()
                skin_combobox.setCurrentIndex(-1)
                skin_combobox.blockSignals(False)
            return

        model_totals = Counter(slot["model_id"] for slot in self.current_online_slots)
        assigned_slots = [slot for slot in self.online_assigned_slots.values() if slot is not None]
        model_used = Counter(slot["model_id"] for slot in assigned_slots)
        unique_model_ids = sorted(model_totals.keys())

        for ip_address, car_combobox in self.online_rig_car_comboboxes.items():
            car_combobox.blockSignals(True)
            car_combobox.clear()

            is_checked = self.online_rig_checkboxes[ip_address].isChecked()
            current_slot = self.online_assigned_slots.get(ip_address)

            if is_checked:
                index_to_select = -1
                for idx, model_id in enumerate(unique_model_ids):
                    total = model_totals[model_id]
                    used = model_used[model_id]
                    left = total - used
                    if left < 0: left = 0

                    display_name = self.data_provider.fetch_car_display_name(model_id)
                    item_text = f"{display_name} ({left}/{total})"
                    car_combobox.addItem(item_text, model_id)

                    if current_slot and current_slot["model_id"] == model_id:
                        index_to_select = idx

                car_combobox.setCurrentIndex(index_to_select)
            else:
                car_combobox.setCurrentIndex(-1)

            car_combobox.blockSignals(False)

            skin_combobox = self.online_rig_skin_comboboxes[ip_address]
            skin_combobox.blockSignals(True)
            skin_combobox.clear()

            if is_checked and current_slot:
                current_model = current_slot["model_id"]
                current_skin = current_slot.get("skin", "")

                available_nice_skins = self.data_provider.fetch_available_skins(current_model)

                index_to_select_skin = -1
                for idx, skin_data in enumerate(available_nice_skins):
                    skin_folder = skin_data["folder_name"]
                    display_name = skin_data["display_name"]

                    skin_combobox.addItem(display_name, skin_folder)

                    if skin_folder == current_skin or (not current_skin and idx == 0):
                        index_to_select_skin = idx
                        if not current_skin:
                            current_slot["skin"] = skin_folder

                skin_combobox.setCurrentIndex(index_to_select_skin)
            else:
                skin_combobox.setCurrentIndex(-1)

            skin_combobox.blockSignals(False)

    def on_online_car_selection_changed(self, ip_address):
        combobox = self.online_rig_car_comboboxes.get(ip_address)
        if not combobox: return
        current_index = combobox.currentIndex()
        if current_index < 0: return

        new_model_id = combobox.itemData(current_index)
        current_slot = self.online_assigned_slots.get(ip_address)

        if current_slot and current_slot["model_id"] == new_model_id:
            return

        assigned_slots = list(self.online_assigned_slots.values())
        target_slot = None
        for slot in self.current_online_slots:
            if slot["model_id"] == new_model_id and slot not in assigned_slots:
                target_slot = slot
                break

        if target_slot:
            self.online_assigned_slots[ip_address] = target_slot
        else:
            for other_ip, other_slot in self.online_assigned_slots.items():
                if other_slot and other_slot["model_id"] == new_model_id:
                    self.online_assigned_slots[other_ip] = current_slot
                    self.online_assigned_slots[ip_address] = other_slot
                    break

        self.recalc_labels_only_online()

    def on_online_skin_selection_changed(self, ip_address):
        combobox = self.online_rig_skin_comboboxes.get(ip_address)
        if not combobox: return
        current_index = combobox.currentIndex()
        if current_index < 0: return

        new_skin = combobox.itemData(current_index)
        current_slot = self.online_assigned_slots.get(ip_address)

        if current_slot:
            current_slot["skin"] = new_skin

    def on_online_rig_checkbox_toggled(self, ip_address, state):
        self.update_row_highlight(ip_address, state, is_online=True)
        if state and not self.online_assigned_slots.get(ip_address):
            assigned_slots = list(self.online_assigned_slots.values())
            for slot in self.current_online_slots:
                if slot not in assigned_slots:
                    self.online_assigned_slots[ip_address] = slot
                    break
        elif not state:
            self.online_assigned_slots[ip_address] = None
        self.recalc_labels_only_online()

    # --- GENERAL ---

    def load_drivers_history(self):
        history = self.data_provider.load_drivers_history()
        for ip_address, name_input in self.rig_name_inputs.items():
            if ip_address in history:
                name_input.setText(history[ip_address])
        for ip_address, name_input in self.online_rig_name_inputs.items():
            if ip_address in history:
                name_input.setText(history[ip_address])

    def save_drivers_history(self):
        history = {}
        for ip_address, name_input in self.rig_name_inputs.items():
            driver_name = name_input.text().strip()
            if driver_name:
                history[ip_address] = driver_name
        self.data_provider.save_drivers_history(history)

    def execute_start_race_lan(self):
        current_index = self.server_combobox.currentIndex()
        if current_index < 0:
            self.append_log_message(self.t("log_err_no_server"))
            return

        selected_server = self.server_combobox.itemData(current_index)
        master_server_ip = self.config_manager.get("master_server_ip", "127.0.0.1")

        targets_data = []
        for ip_address, checkbox in self.rig_checkboxes.items():
            if checkbox.isChecked():
                driver_name = self.rig_name_inputs[ip_address].text().strip()
                assigned_slot = self.rig_assigned_slots.get(ip_address)

                if not assigned_slot:
                    continue

                model_id = assigned_slot["model_id"]
                skin = assigned_slot["skin"] if assigned_slot["skin"] else "default"

                targets_data.append({
                    "ip": ip_address,
                    "payload": {
                        "server_data": {
                            "ip": master_server_ip,
                            "udp_port": selected_server['udp_port'],
                            "http_port": selected_server['http_port'],
                            "password": selected_server.get('password', ''),
                            "server_name": selected_server['name']
                        },
                        "track_data": {
                            "track": selected_server.get('track', 'imola'),
                            "config_track": selected_server.get('track_layout', '')
                        },
                        "car_data": {
                            "model_id": model_id,
                            "driver_name": driver_name,
                            "skin": skin
                        }
                    }
                })

        self.save_drivers_history()
        self.dispatch_network_commands(targets_data, "run")

    def execute_start_race_online(self):
        if not self.current_online_info:
            self.append_log_message(self.t("log_no_online_data"))
            return

        password = self.current_online_info["password"]

        targets_data = []
        for ip_address, checkbox in self.online_rig_checkboxes.items():
            if checkbox.isChecked():
                driver_name = self.online_rig_name_inputs[ip_address].text().strip()
                assigned_slot = self.online_assigned_slots.get(ip_address)

                if not assigned_slot:
                    continue

                model_id = assigned_slot["model_id"]
                skin = assigned_slot.get("skin", "default")

                targets_data.append({
                    "ip": ip_address,
                    "payload": {
                        "server_data": {
                            "ip": self.current_online_info["ip"],
                            "udp_port": self.current_online_info["udp_port"],
                            "tcp_port": self.current_online_info["tcp_port"],
                            "http_port": self.current_online_info["http_port"],
                            "password": password,
                            "server_name": self.current_online_info["name"]
                        },
                        "track_data": {
                            "track": self.current_online_info["track"],
                            "config_track": ""
                        },
                        "car_data": {
                            "model_id": model_id,
                            "driver_name": driver_name,
                            "skin": skin
                        }
                    }
                })

        self.save_drivers_history()
        self.dispatch_network_commands(targets_data, "run")

    def execute_stop_race(self):
        targets_data = []
        for ip_address, checkbox in self.rig_checkboxes.items():
            if checkbox.isChecked():
                targets_data.append({"ip": ip_address, "payload": {}})

        for ip_address, checkbox in self.online_rig_checkboxes.items():
            if checkbox.isChecked() and ip_address not in [t["ip"] for t in targets_data]:
                targets_data.append({"ip": ip_address, "payload": {}})

        if not targets_data:
            self.append_log_message(self.t("log_no_rigs_stop"))
            return

        self.dispatch_network_commands(targets_data, "stop")

    def dispatch_network_commands(self, targets_data, action):
        self.append_log_message(self.t("log_dispatching", action, len(targets_data)))

        for target in targets_data:
            self.network_manager.broadcast_command(
                [{"ip": target["ip"]}],
                action,
                target["payload"],
                self.on_network_progress,
                None
            )

    @Slot(str, bool, str)
    def on_network_progress(self, ip_address, success, message):
        status_text = "SUCCESS" if success else "FAILED"
        self.append_log_message(f"[{ip_address}] {status_text}: {message}")

    def start_test_synchronization(self):
        self.append_log_message(self.t("log_test_sync_init"))
        self.sync_worker = SyncWorker(self.config_manager, dry_run=True)
        self.sync_worker.log_signal.connect(self.append_log_message)
        self.sync_worker.finished_signal.connect(lambda: self.append_log_message(self.t("log_test_sync_done")))
        self.sync_worker.start()

    def start_synchronization(self):
        reply = QMessageBox.question(self, self.t("dialog_sync_title"), self.t("dialog_sync_msg"),
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.append_log_message(self.t("log_full_sync_init"))
            self.sync_worker = SyncWorker(self.config_manager, dry_run=False)
            self.sync_worker.log_signal.connect(self.append_log_message)
            self.sync_worker.finished_signal.connect(lambda: self.append_log_message(self.t("log_full_sync_done")))
            self.sync_worker.start()

    def save_settings(self):
        configuration_data = self.config_manager.configuration_data

        for key, input_field in self.settings_inputs.items():
            configuration_data[key] = input_field.text().strip()

        new_clients_list = []
        for rig_name, input_field in self.rig_ip_inputs:
            ip_address = input_field.text().strip()
            if ip_address:
                new_clients_list.append({"name": rig_name, "ip": ip_address})

        configuration_data["clients"] = new_clients_list
        self.config_manager.save_configuration(configuration_data)

        self.append_log_message(self.t("log_config_saved"))

    def closeEvent(self, event):
        self.save_drivers_history()
        event.accept()