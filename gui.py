import json
import subprocess
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QLabel, QTextEdit, 
                             QMessageBox, QComboBox, QGridLayout, QInputDialog, 
                             QTabWidget, QFileDialog, QCheckBox, QGroupBox,
                             QRadioButton, QSpinBox, QScrollArea)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont, QIcon
import requests
import os
import urllib.parse
import shlex
import base64
import socket

# Konstanta
CUSTOM_TEXT_FILE = 'custom_text.json'
SETTINGS_FILE = 'mosys_settings.json'

class MosysBillingGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.custom_text = self.load_custom_text()
        self.connection_type = "adb"  # Default connection type
        self.settings = self.load_settings()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Mosys Billing')
        self.setGeometry(100, 100, 800, 600)  # Default size

        # Buat main widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Connection Type Selection
        connection_group = QGroupBox("Connection Type")
        connection_layout = QHBoxLayout()
        
        self.adb_radio = QRadioButton("ADB Connection")
        self.cec_radio = QRadioButton("HDMI-CEC Connection")
        
        # Set the default based on settings
        if self.settings.get('connection_type') == 'cec':
            self.cec_radio.setChecked(True)
            self.connection_type = 'cec'
        else:
            self.adb_radio.setChecked(True)
            self.connection_type = 'adb'
            
        self.adb_radio.toggled.connect(self.toggle_connection)
        self.cec_radio.toggled.connect(self.toggle_connection)
        
        connection_layout.addWidget(self.adb_radio)
        connection_layout.addWidget(self.cec_radio)
        connection_group.setLayout(connection_layout)
        
        main_layout.addWidget(connection_group)
        
        # Server status indicator
        status_layout = QHBoxLayout()
        self.adb_status = QLabel("ADB Server: Checking...")
        self.cec_status = QLabel("CEC Server: Checking...")
        status_layout.addWidget(self.adb_status)
        status_layout.addWidget(self.cec_status)
        main_layout.addLayout(status_layout)
        
        # Buat tab widget
        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        # Tab Home
        home_tab = QWidget()
        home_layout = QVBoxLayout()
        
        guide_text = QTextEdit()
        guide_text.setReadOnly(True)
        guide_text.setHtml("""
        <h2>Panduan Penggunaan Mosys Billing</h2>
        <p>Selamat datang di aplikasi Mosys Billing. Berikut adalah panduan singkat penggunaan:</p>
        <ol>
            <li><strong>Mode Koneksi:</strong>
                <ul>
                    <li><strong>ADB:</strong> Untuk TV Android, wajib mengaktifkan debug mode WIFI di android TV</li>
                    <li><strong>HDMI-CEC:</strong> Untuk TV yang mendukung HDMI-CEC, tidak perlu konfigurasi khusus</li>
                </ul>
            </li>
            <li>Untuk koneksi ADB, wajib mengunduh Android ADB: <a href="https://developer.android.com/studio/releases/platform-tools?hl=id">Download di sini</a></li>
            <li>Untuk menambahkan TV baru, gunakan tab "Remote" dan isi nama serta IP TV.</li>
            <li>Anda dapat melihat status semua TV pada daftar di tab "Remote".</li>
            <li>Untuk mengontrol TV, pilih TV dari daftar dan gunakan tombol kontrol yang tersedia.</li>
            <li>Anda dapat menggunakan fitur scan network untuk menemukan TV di jaringan.</li>
            <li>Untuk mengatur timer, isi durasi, pilih aksi, dan klik "Set Timer".</li>
        </ol>
        """)
        home_layout.addWidget(guide_text)
        home_tab.setLayout(home_layout)
        tabs.addTab(home_tab, "Home")

        # Tab Remote (Dengan Scroll Area)
        remote_tab = QWidget()
        remote_scroll = QScrollArea()
        remote_scroll.setWidgetResizable(True)
        remote_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        remote_scroll.setWidget(remote_tab)
        
        remote_layout = QVBoxLayout(remote_tab)
        
        # Network Scanner
        scan_group = QGroupBox("Network Scanner")
        scan_layout = QHBoxLayout()
        
        subnet_label = QLabel("Subnet:")
        self.subnet_input = QLineEdit("192.168.1")
        
        range_label = QLabel("Range:")
        self.start_range = QSpinBox()
        self.start_range.setRange(1, 254)
        self.start_range.setValue(1)
        
        to_label = QLabel("to")
        
        self.end_range = QSpinBox()
        self.end_range.setRange(1, 254)
        self.end_range.setValue(254)
        
        scan_button = QPushButton("Scan Network")
        scan_button.clicked.connect(self.scan_network)
        
        scan_layout.addWidget(subnet_label)
        scan_layout.addWidget(self.subnet_input)
        scan_layout.addWidget(range_label)
        scan_layout.addWidget(self.start_range)
        scan_layout.addWidget(to_label)
        scan_layout.addWidget(self.end_range)
        scan_layout.addWidget(scan_button)
        
        scan_group.setLayout(scan_layout)
        remote_layout.addWidget(scan_group)
        
        # TV Selector
        selector_layout = QHBoxLayout()
        selector_label = QLabel("Select TV:")
        self.tv_selector = QComboBox()
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.update_tv_list)
        
        selector_layout.addWidget(selector_label)
        selector_layout.addWidget(self.tv_selector)
        selector_layout.addWidget(refresh_button)
        remote_layout.addLayout(selector_layout)

        # TV List
        list_label = QLabel("TV Status:")
        remote_layout.addWidget(list_label)
        self.tv_list = QTextEdit()
        self.tv_list.setReadOnly(True)
        self.tv_list.setMaximumHeight(100)
        remote_layout.addWidget(self.tv_list)

        # Remote Control Layout
        remote_control_group = QGroupBox("Remote Control")
        remote_control_layout = QGridLayout()

        # Power buttons
        on_button = QPushButton("POWER ON")
        off_button = QPushButton("POWER OFF")
        on_button.clicked.connect(lambda: self.control_tv('on' if self.connection_type == 'adb' else 'power_on'))
        off_button.clicked.connect(lambda: self.control_tv('off' if self.connection_type == 'adb' else 'power_off'))
        remote_control_layout.addWidget(on_button, 0, 0)
        remote_control_layout.addWidget(off_button, 0, 2)

        # Home button
        home_button = QPushButton("HOME")
        home_button.clicked.connect(lambda: self.control_tv('home'))
        remote_control_layout.addWidget(home_button, 0, 1)

        # Volume buttons
        volume_up_button = QPushButton("VOL+")
        volume_down_button = QPushButton("VOL-")
        mute_button = QPushButton("MUTE")
        volume_up_button.clicked.connect(lambda: self.control_tv('volume_up'))
        volume_down_button.clicked.connect(lambda: self.control_tv('volume_down'))
        mute_button.clicked.connect(lambda: self.control_tv('mute'))
        remote_control_layout.addWidget(volume_up_button, 1, 0)
        remote_control_layout.addWidget(mute_button, 1, 1)
        remote_control_layout.addWidget(volume_down_button, 1, 2)
        
        # Navigation buttons (only for HDMI-CEC mode)
        self.nav_group = QGroupBox("Navigation")
        nav_layout = QGridLayout()
        
        up_button = QPushButton("▲")
        down_button = QPushButton("▼")
        left_button = QPushButton("◄")
        right_button = QPushButton("►")
        select_button = QPushButton("OK")
        back_button = QPushButton("BACK")
        
        up_button.clicked.connect(lambda: self.control_tv('up'))
        down_button.clicked.connect(lambda: self.control_tv('down'))
        left_button.clicked.connect(lambda: self.control_tv('left'))
        right_button.clicked.connect(lambda: self.control_tv('right'))
        select_button.clicked.connect(lambda: self.control_tv('select'))
        back_button.clicked.connect(lambda: self.control_tv('back'))
        
        nav_layout.addWidget(up_button, 0, 1)
        nav_layout.addWidget(left_button, 1, 0)
        nav_layout.addWidget(select_button, 1, 1)
        nav_layout.addWidget(right_button, 1, 2)
        nav_layout.addWidget(down_button, 2, 1)
        nav_layout.addWidget(back_button, 3, 0, 1, 3)
        
        self.nav_group.setLayout(nav_layout)
        remote_control_layout.addWidget(self.nav_group, 2, 0, 3, 3)
        
        # HDMI Input selector (only for HDMI-CEC mode)
        self.input_group = QGroupBox("HDMI Input")
        input_layout = QHBoxLayout()
        
        hdmi1_button = QPushButton("HDMI 1")
        hdmi2_button = QPushButton("HDMI 2")
        hdmi3_button = QPushButton("HDMI 3")
        
        hdmi1_button.clicked.connect(lambda: self.control_tv('input_hdmi1'))
        hdmi2_button.clicked.connect(lambda: self.control_tv('input_hdmi2'))
        hdmi3_button.clicked.connect(lambda: self.control_tv('input_hdmi3'))
        
        input_layout.addWidget(hdmi1_button)
        input_layout.addWidget(hdmi2_button)
        input_layout.addWidget(hdmi3_button)
        
        self.input_group.setLayout(input_layout)
        remote_control_layout.addWidget(self.input_group, 5, 0, 1, 3)
        
        # Stream button (only for ADB mode)
        self.stream_button = QPushButton("STREAM MEDIA")
        self.stream_button.clicked.connect(self.stream_media)
        remote_control_layout.addWidget(self.stream_button, 6, 0, 1, 3)

        # Timer controls
        timer_group = QGroupBox("Timer")
        timer_layout = QVBoxLayout()
        
        duration_layout = QHBoxLayout()
        duration_label = QLabel("Duration (seconds):")
        self.timer_duration = QLineEdit()
        duration_layout.addWidget(duration_label)
        duration_layout.addWidget(self.timer_duration)
        
        action_layout = QHBoxLayout()
        action_label = QLabel("Action at end:")
        self.timer_action = QComboBox()
        action_layout.addWidget(action_label)
        action_layout.addWidget(self.timer_action)
        
        # Custom text for timer
        self.show_on_tv_checkbox = QCheckBox("Show countdown on TV")
        self.custom_text_input = QLineEdit()
        self.custom_text_input.setPlaceholderText("Custom text for timer")
        self.custom_text_input.setText(self.custom_text)
        
        save_custom_text_button = QPushButton("Save Custom Text")
        save_custom_text_button.clicked.connect(self.save_custom_text)
        
        set_timer_button = QPushButton("Set Timer")
        set_timer_button.clicked.connect(self.set_timer)
        
        timer_layout.addLayout(duration_layout)
        timer_layout.addLayout(action_layout)
        timer_layout.addWidget(self.show_on_tv_checkbox)
        timer_layout.addWidget(self.custom_text_input)
        timer_layout.addWidget(save_custom_text_button)
        timer_layout.addWidget(set_timer_button)
        
        timer_group.setLayout(timer_layout)
        remote_control_layout.addWidget(timer_group, 7, 0, 1, 3)

        remote_control_group.setLayout(remote_control_layout)
        remote_layout.addWidget(remote_control_group)

        # Add TV controls
        add_group = QGroupBox("Add/Edit TV")
        add_layout = QVBoxLayout()
        
        add_form_layout = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("TV Name")
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("TV IP")
        add_button = QPushButton("Add TV")
        add_button.clicked.connect(self.add_tv)
        add_form_layout.addWidget(self.name_input)
        add_form_layout.addWidget(self.ip_input)
        add_form_layout.addWidget(add_button)
        
        # Edit and Delete buttons
        edit_delete_layout = QHBoxLayout()
        edit_button = QPushButton("Edit TV")
        delete_button = QPushButton("Delete TV")
        edit_button.clicked.connect(self.edit_tv)
        delete_button.clicked.connect(self.delete_tv)
        edit_delete_layout.addWidget(edit_button)
        edit_delete_layout.addWidget(delete_button)
        
        add_layout.addLayout(add_form_layout)
        add_layout.addLayout(edit_delete_layout)
        add_group.setLayout(add_layout)
        remote_layout.addWidget(add_group)
        
        # Tambahkan spacer untuk pengaturan scroll
        remote_layout.addStretch()
        
        # Tambahkan scroll area ke tabs
        tabs.addTab(remote_scroll, "Remote")
        
        # Batch Control Tab (dengan Scroll Area)
        batch_tab = QWidget()
        batch_scroll = QScrollArea()
        batch_scroll.setWidgetResizable(True)
        batch_scroll.setWidget(batch_tab)
        
        batch_layout = QVBoxLayout(batch_tab)
        
        batch_description = QLabel("Use batch control to send the same command to multiple TVs at once.")
        batch_layout.addWidget(batch_description)
        
        # TV selection list with checkboxes
        self.batch_tv_list = QTextEdit()
        self.batch_tv_list.setReadOnly(True)
        self.batch_tv_list.setMinimumHeight(200)
        batch_layout.addWidget(self.batch_tv_list)
        
        # Command selection
        batch_command_layout = QHBoxLayout()
        command_label = QLabel("Command:")
        self.batch_command = QComboBox()
        batch_command_layout.addWidget(command_label)
        batch_command_layout.addWidget(self.batch_command)
        batch_layout.addLayout(batch_command_layout)
        
        # Send batch command button
        send_batch_button = QPushButton("Send Command to All TVs")
        send_batch_button.clicked.connect(self.send_batch_command)
        batch_layout.addWidget(send_batch_button)
        
        # Tambahkan spacer untuk pengaturan scroll
        batch_layout.addStretch()
        
        # Tambahkan scroll area ke tabs
        tabs.addTab(batch_scroll, "Batch Control")

        # API Tab
        api_tab = QWidget()
        api_scroll = QScrollArea()
        api_scroll.setWidgetResizable(True)
        api_scroll.setWidget(api_tab)
        
        api_layout = QVBoxLayout(api_tab)
        api_info = QTextEdit()
        api_info.setReadOnly(True)
        api_info.setHtml("""
        <h2>API Information</h2>
        <p>The Mosys Billing application provides the following API endpoints for both connection types:</p>
        
        <h3>ADB API (Port 1616)</h3>
        <ul>
            <li><code>POST /add_tv</code>: Add a new TV</li>
            <li><code>POST /remove_tv</code>: Remove a TV</li>
            <li><code>POST /edit_tv</code>: Edit TV information</li>
            <li><code>GET /tv_status</code>: Get status of all TVs</li>
            <li><code>POST /control_tv</code>: Control a TV (on, off, volume)</li>
            <li><code>POST /stream_media/{ip}</code>: Stream media to a TV</li>
            <li><code>POST /set_timer</code>: Set a timer for TV control</li>
        </ul>
        
        <h3>HDMI-CEC API (Port 1618)</h3>
        <ul>
            <li><code>POST /add_device</code>: Add a new TV</li>
            <li><code>POST /remove_device</code>: Remove a TV</li>
            <li><code>POST /edit_device</code>: Edit TV information</li>
            <li><code>GET /device_status</code>: Get status of all TVs</li>
            <li><code>POST /send_command</code>: Send a command to a TV</li>
            <li><code>POST /batch_command</code>: Send a command to multiple TVs</li>
            <li><code>POST /scan_network</code>: Scan network for HDMI-CEC devices</li>
            <li><code>GET /available_commands</code>: Get list of available commands</li>
            <li><code>POST /set_timer</code>: Set a timer for TV control</li>
        </ul>
        
        <p>For more details on how to use these endpoints, please refer to the API documentation.</p>
        """)
        api_layout.addWidget(api_info)
        
        # Tambahkan spacer untuk pengaturan scroll
        api_layout.addStretch()
        
        # Tambahkan scroll area ke tabs
        tabs.addTab(api_scroll, "API")

        # About Tab
        about_tab = QWidget()
        about_layout = QVBoxLayout()
        about_info = QTextEdit()
        about_info.setReadOnly(True)
        about_info.setHtml("""
        <h2>About Mosys Billing</h2>
        <p><strong>Developer:</strong> Kurniawan</p>
        <p><strong>Instagram:</strong> @sedotphp</p>
        <p><strong>Website:</strong> <a href="https://sedot.dev">https://sedot.dev</a></p>
        <p><strong>Contact:</strong> 081373350813</p>
        """)
        about_layout.addWidget(about_info)
        about_tab.setLayout(about_layout)
        tabs.addTab(about_tab, "About")

        # Setup timers
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_tv_list)
        self.timer.start(5000)
        
        self.server_check_timer = QTimer(self)
        self.server_check_timer.timeout.connect(self.check_server_status)
        self.server_check_timer.start(10000)  # Check server status every 10 seconds

        # Initial updates
        self.update_tv_list()
        self.check_server_status()
        self.update_connection_ui()

    # Metode-metode fungsionalitas yang sama dengan versi sebelumnya
    def toggle_connection(self):
        if self.adb_radio.isChecked():
            self.connection_type = "adb"
        else:
            self.connection_type = "cec"
        
        # Save settings
        self.settings['connection_type'] = self.connection_type
        self.save_settings()
        
        # Update UI for connection type
        self.update_connection_ui()
        self.update_tv_list()
    
    def update_connection_ui(self):
        """Update UI elements based on the connection type"""
        if self.connection_type == "adb":
            # ADB specific controls
            self.stream_button.setVisible(True)
            self.nav_group.setVisible(False)
            self.input_group.setVisible(False)
            
            # Update timer actions for ADB
            self.timer_action.clear()
            self.timer_action.addItems(['off', 'sleep', 'volume_up', 'volume_down'])
            
            # Update batch commands for ADB
            self.batch_command.clear()
            self.batch_command.addItems(['off', 'sleep', 'volume_up', 'volume_down', 'home'])
            
        else:  # HDMI-CEC
            # CEC specific controls
            self.stream_button.setVisible(False)
            self.nav_group.setVisible(True)
            self.input_group.setVisible(True)
            
            # Update timer actions for CEC
            self.timer_action.clear()
            self.timer_action.addItems([
                'power_off', 'mute', 'volume_up', 'volume_down', 
                'menu', 'back', 'home', 'play', 'pause', 'stop'
            ])
            
            # Update batch commands for CEC
            self.batch_command.clear()
            self.batch_command.addItems([
                'power_on', 'power_off', 'volume_up', 'volume_down', 'mute',
                'input_hdmi1', 'input_hdmi2', 'input_hdmi3', 'menu', 'home'
            ])

    def check_server_status(self):
        """Check if the servers are running"""
        try:
            # Check ADB server
            response = requests.get('http://localhost:1616/tv_status', timeout=1)
            self.adb_status.setText("ADB Server: Online")
            self.adb_status.setStyleSheet("color: green;")
        except:
            self.adb_status.setText("ADB Server: Offline")
            self.adb_status.setStyleSheet("color: red;")
        
        try:
            # Check CEC server
            response = requests.get('http://localhost:1618/device_status', timeout=1)
            self.cec_status.setText("CEC Server: Online")
            self.cec_status.setStyleSheet("color: green;")
        except:
            self.cec_status.setText("CEC Server: Offline")
            self.cec_status.setStyleSheet("color: red;")

    def scan_network(self):
        """Scan the network for TVs"""
        subnet = self.subnet_input.text()
        start = self.start_range.value()
        end = self.end_range.value()
        
        if end - start > 254:
            QMessageBox.warning(self, "Error", "Scan range too large")
            return
        
        try:
            if self.connection_type == "adb":
                url = f'http://localhost:1617/scan_network'  # Using the LAN optimized ADB server
            else:
                url = f'http://localhost:1618/scan_network'
                
            response = requests.post(url, json={
                'subnet': subnet,
                'start': start,
                'end': end
            }, timeout=2)
            
            if response.status_code == 200:
                QMessageBox.information(self, "Scan Started", 
                                        f"Network scan started for range {subnet}.{start}-{end}. " +
                                        "Check scan results tab in a few minutes.")
            else:
                QMessageBox.warning(self, "Error", 
                                    f"Failed to start scan: {response.json().get('error', 'Unknown error')}")
        except requests.RequestException as e:
            QMessageBox.warning(self, "Connection Error", 
                                f"Could not connect to server: {str(e)}")

    def add_tv(self):
        name = self.name_input.text()
        ip = self.ip_input.text()
        
        if not name or not ip:
            QMessageBox.warning(self, "Error", "Please enter both name and IP")
            return
            
        try:
            if self.connection_type == "adb":
                url = 'http://localhost:1616/add_tv'
                data = {'name': name, 'ip': ip}
            else:
                url = 'http://localhost:1618/add_device'
                data = {'name': name, 'ip': ip}
                
            response = requests.post(url, json=data)
            
            if response.status_code == 200:
                QMessageBox.information(self, "Success", "TV added successfully")
                self.name_input.clear()
                self.ip_input.clear()
                self.update_tv_list()
            else:
                QMessageBox.warning(self, "Error", 
                                    f"Failed to add TV: {response.json().get('error', 'Unknown error')}")
        except requests.RequestException as e:
            QMessageBox.warning(self, "Connection Error", 
                                f"Could not connect to server: {str(e)}")

    def update_tv_list(self):
        try:
            if self.connection_type == "adb":
                url = 'http://localhost:1616/tv_status'
            else:
                url = 'http://localhost:1618/device_status'
                
            response = requests.get(url)
            
            if response.status_code == 200:
                devices = response.json()
                
                # Update TV selector combobox
                self.tv_selector.clear()
                
                # Update TV list text
                tv_list_text = ""
                batch_list_text = ""
                
                for ip, device_info in devices.items():
                    name = device_info.get('name', 'Unknown')
                    status = device_info.get('status', 'Unknown')
                    response_time = device_info.get('response_time', 'N/A')
                    
                    # Add to dropdown
                    self.tv_selector.addItem(f"{name} ({ip})", ip)
                    
                    # Add to TV list display
                    tv_list_text += f"Name: {name}, IP: {ip}, Status: {status}, Response Time: {response_time}\n"
                    
                    # Add to batch list with checkbox
                    batch_list_text += f"□ {name} ({ip}) - Status: {status}\n"
                
                self.tv_list.setText(tv_list_text)
                self.batch_tv_list.setText(batch_list_text)
            else:
                self.tv_list.setText("Failed to fetch TV list")
                self.batch_tv_list.setText("Failed to fetch TV list")
        except requests.RequestException as e:
            self.tv_list.setText(f"Connection error: {str(e)}")
            self.batch_tv_list.setText(f"Connection error: {str(e)}")

    def control_tv(self, action):
        selected_ip = self.tv_selector.currentData()
        if not selected_ip:
            QMessageBox.warning(self, "Error", "Please select a TV")
            return
            
        try:
            if self.connection_type == "adb":
                url = 'http://localhost:1616/control_tv'
                data = {'ip': selected_ip, 'action': action}
            else:
                url = 'http://localhost:1618/send_command'
                data = {'ip': selected_ip, 'command': action}
                
            response = requests.post(url, json=data)
            
            if response.status_code == 200:
                action_display = action.replace('_', ' ').title()
                QMessageBox.information(self, "Success", f"{action_display} command sent successfully")
            else:
                error_message = response.json().get('error', 'Unknown error')
                QMessageBox.warning(self, "Error", f"Failed to send {action} command: {error_message}")
        except requests.RequestException as e:
            QMessageBox.warning(self, "Connection Error", f"Could not connect to server: {str(e)}")

    def edit_tv(self):
        selected_ip = self.tv_selector.currentData()
        if not selected_ip:
            QMessageBox.warning(self, "Error", "Please select a TV to edit")
            return
            
        try:
            if self.connection_type == "adb":
                status_url = 'http://localhost:1616/tv_status'
            else:
                status_url = 'http://localhost:1618/device_status'
                
            status_response = requests.get(status_url)
            
            if status_response.status_code != 200:
                QMessageBox.warning(self, "Error", "Failed to get TV information")
                return
                
            device_info = status_response.json().get(selected_ip)
            if not device_info:
                QMessageBox.warning(self, "Error", "Failed to get TV information")
                return
                
            new_name, ok1 = QInputDialog.getText(self, "Edit TV", "Enter new name:", 
                                               QLineEdit.Normal, device_info['name'])
            if not ok1 or not new_name:
                return
                
            new_ip, ok2 = QInputDialog.getText(self, "Edit TV", "Enter new IP:", 
                                             QLineEdit.Normal, selected_ip)
            if not ok2 or not new_ip:
                return
                
            if new_name == device_info['name'] and new_ip == selected_ip:
                QMessageBox.information(self, "No Changes", "No changes were made to the TV information.")
                return
                
            if self.connection_type == "adb":
                url = 'http://localhost:1616/edit_tv'
                data = {'old_ip': selected_ip, 'new_name': new_name, 'new_ip': new_ip}
            else:
                url = 'http://localhost:1618/edit_device'
                data = {'old_ip': selected_ip, 'new_name': new_name, 'new_ip': new_ip}
                
            response = requests.post(url, json=data)
            
            if response.status_code == 200:
                QMessageBox.information(self, "Success", "TV edited successfully")
                self.update_tv_list()
            else:
                QMessageBox.warning(self, "Error", 
                                  f"Failed to edit TV: {response.json().get('error', 'Unknown error')}")
        except requests.RequestException as e:
            QMessageBox.warning(self, "Connection Error", f"Could not connect to server: {str(e)}")
    
    def delete_tv(self):
        selected_ip = self.tv_selector.currentData()
        if not selected_ip:
            QMessageBox.warning(self, "Error", "Please select a TV to delete")
            return
            
        reply = QMessageBox.question(self, "Confirm Deletion", 
                                   f"Are you sure you want to delete the TV with IP {selected_ip}?",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply != QMessageBox.Yes:
            return
            
        try:
            if self.connection_type == "adb":
                url = 'http://localhost:1616/remove_tv'
                data = {'ip': selected_ip}
            else:
                url = 'http://localhost:1618/remove_device'
                data = {'ip': selected_ip}
                
            response = requests.post(url, json=data)
            
            if response.status_code == 200:
                QMessageBox.information(self, "Success", "TV deleted successfully")
                self.update_tv_list()
            else:
                QMessageBox.warning(self, "Error", 
                                  f"Failed to delete TV: {response.json().get('error', 'Unknown error')}")
        except requests.RequestException as e:
            QMessageBox.warning(self, "Connection Error", f"Could not connect to server: {str(e)}")
    
    def stream_media(self):
        # Only available in ADB mode
        if self.connection_type != "adb":
            QMessageBox.warning(self, "Not Available", "Media streaming is only available in ADB mode")
            return
            
        selected_ip = self.tv_selector.currentData()
        if not selected_ip:
            QMessageBox.warning(self, "Error", "Please select a TV")
            return
            
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Media File", "", 
                                                "Media Files (*.mp4 *.mkv *.avi *.mp3 *.jpg *.png)")
        if not file_path:
            return
            
        try:
            with open(file_path, 'rb') as file:
                files = {'file': (os.path.basename(file_path), file, 'application/octet-stream')}
                stream_response = requests.post(f'http://localhost:1616/stream_media/{selected_ip}', 
                                              files=files)
                
                if stream_response.status_code == 200:
                    QMessageBox.information(self, "Success", "Media file transferred and streaming started")
                else:
                    QMessageBox.warning(self, "Error", 
                                      f"Failed to start media streaming: {stream_response.json().get('error', 'Unknown error')}")
        except requests.RequestException as e:
            QMessageBox.warning(self, "Connection Error", f"Failed to connect to server: {str(e)}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"An unexpected error occurred: {str(e)}")
    
    def send_batch_command(self):
        """Send command to all checked TVs in batch mode"""
        # Parse checked TVs from batch list text
        checked_ips = []
        batch_text = self.batch_tv_list.toPlainText()
        
        # This is a simplified parsing - in a real app you'd use checkboxes
        for line in batch_text.split('\n'):
            if line.startswith('☑'):  # Checked box
                # Extract IP from format "☑ Name (192.168.1.x) - Status: Online"
                start_idx = line.find('(') + 1
                end_idx = line.find(')')
                if start_idx > 0 and end_idx > start_idx:
                    ip = line[start_idx:end_idx]
                    checked_ips.append(ip)
        
        if not checked_ips:
            QMessageBox.warning(self, "No TVs Selected", 
                              "Please select at least one TV by checking the box")
            return
            
        command = self.batch_command.currentText()
        
        try:
            if self.connection_type == "adb":
                # ADB doesn't have native batch command, so we loop through TVs
                for ip in checked_ips:
                    url = 'http://localhost:1616/control_tv'
                    data = {'ip': ip, 'action': command}
                    requests.post(url, json=data)
            else:
                # HDMI-CEC has native batch command
                url = 'http://localhost:1618/batch_command'
                data = {'ips': checked_ips, 'command': command}
                response = requests.post(url, json=data)
                
                if response.status_code != 200:
                    QMessageBox.warning(self, "Error", 
                                      f"Failed to send batch command: {response.json().get('error', 'Unknown error')}")
                    return
            
            QMessageBox.information(self, "Success", 
                                  f"Command '{command}' sent to {len(checked_ips)} TVs")
        except requests.RequestException as e:
            QMessageBox.warning(self, "Connection Error", f"Could not connect to server: {str(e)}")
    
    def load_custom_text(self):
        """Load custom text from file"""
        default_text = "Waktu rental mu sudah habis, silahkan ke kasir jika ingin menambah waktu!"
        
        if not os.path.exists(CUSTOM_TEXT_FILE):
            return default_text
        
        try:
            with open(CUSTOM_TEXT_FILE, 'r') as f:
                content = f.read().strip()
                if not content:  # File is empty
                    return default_text
                data = json.loads(content)
                return data.get('custom_text', default_text)
        except json.JSONDecodeError:
            return default_text
        except Exception as e:
            print(f"Error loading custom text: {str(e)}")
            return default_text

    def save_custom_text(self):
        """Save custom text to file"""
        custom_text = self.custom_text_input.text()
        
        try:
            with open(CUSTOM_TEXT_FILE, 'w') as f:
                json.dump({'custom_text': custom_text}, f)
            
            self.custom_text = custom_text
            QMessageBox.information(self, "Success", "Custom text saved successfully")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save custom text: {str(e)}")
    
    def load_settings(self):
        """Load application settings"""
        default_settings = {
            'connection_type': 'adb',
            'subnet': '192.168.1',
            'start_range': 1,
            'end_range': 254
        }
        
        if not os.path.exists(SETTINGS_FILE):
            return default_settings
        
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                return settings
        except:
            return default_settings
    
    def save_settings(self):
        """Save application settings"""
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self.settings, f)
        except Exception as e:
            print(f"Error saving settings: {str(e)}")
    
    def set_timer(self):
        """Set a timer for a TV"""
        selected_ip = self.tv_selector.currentData()
        duration_text = self.timer_duration.text()
        
        if not selected_ip:
            QMessageBox.warning(self, "Error", "Please select a TV")
            return
            
        if not duration_text:
            QMessageBox.warning(self, "Error", "Please enter a duration for the timer")
            return
            
        try:
            duration = int(duration_text)
            if duration <= 0:
                QMessageBox.warning(self, "Error", "Duration must be a positive number")
                return
                
            action = self.timer_action.currentText()
            show_on_tv = self.show_on_tv_checkbox.isChecked()
            custom_text = self.custom_text_input.text()
            
            if show_on_tv and self.connection_type == "adb":
                # Show countdown on TV (only works with ADB)
                try:
                    encoded_text = base64.b64encode(custom_text.encode()).decode()
                    url = 'http://localhost:1616/start_tv_timer'
                    data = {
                        'ip': selected_ip,
                        'seconds': duration,
                        'custom_text': custom_text
                    }
                    
                    response = requests.post(url, json=data)
                    
                    if response.status_code == 200:
                        QMessageBox.information(self, "Success", 
                                              f"Timer set for {duration} seconds and countdown shown on TV")
                    else:
                        QMessageBox.warning(self, "Error", 
                                          f"Failed to set timer on TV: {response.json().get('error', 'Unknown error')}")
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to set timer: {str(e)}")
            else:
                # Backend-only timer
                if self.connection_type == "adb":
                    url = 'http://localhost:1616/set_timer'
                    data = {
                        'ip': selected_ip,
                        'seconds': duration,
                        'action': action
                    }
                else:
                    url = 'http://localhost:1618/set_timer'
                    data = {
                        'ip': selected_ip,
                        'seconds': duration,
                        'command': action
                    }
                
                response = requests.post(url, json=data)
                
                if response.status_code == 200:
                    QMessageBox.information(self, "Success", 
                                          f"Timer set for {duration} seconds to {action}")
                else:
                    QMessageBox.warning(self, "Error", 
                                      f"Failed to set timer: {response.json().get('error', 'Unknown error')}")
        except ValueError:
            QMessageBox.warning(self, "Error", "Please enter a valid number for timer duration")
        except requests.RequestException as e:
            QMessageBox.warning(self, "Connection Error", f"Could not connect to server: {str(e)}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"An unexpected error occurred: {str(e)}")


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    ex = MosysBillingGUI()
    ex.show()
    sys.exit(app.exec_())