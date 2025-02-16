import json
import subprocess
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,  # type: ignore
                             QPushButton, QLineEdit, QLabel, QTextEdit, 
                             QMessageBox, QComboBox, QGridLayout, QInputDialog, 
                             QTabWidget, QFileDialog, QCheckBox)
from PyQt5.QtCore import QTimer # type: ignore
from PyQt5.QtGui import QFont # type: ignore
from flask_app import app
import requests # type: ignore
import os
import urllib.parse
import shlex
import base64

CUSTOM_TEXT_FILE = 'custom_text.json'

class MosysBillingGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.custom_text = self.load_custom_text()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Mosys Billing')
        self.setGeometry(100, 100, 400, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        
        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        # Home Tab
        home_tab = QWidget()
        home_layout = QVBoxLayout()
        
        guide_text = QTextEdit()
        guide_text.setReadOnly(True)
        guide_text.setHtml("""
        <h2>Panduan Penggunaan Mosys Billing</h2>
        <p>Selamat datang di aplikasi Mosys Billing. Berikut adalah panduan singkat penggunaan:</p>
        <ol>
            <li>Wajib mengaktifkan debug mode WIFI di android tv </li>
            <li>Wajib mendownload Android ADB https://developer.android.com/studio/releases/platform-tools?hl=id</li>
            <li>Untuk menambahkan TV baru, gunakan tab "Remote" dan isi nama serta IP TV.</li>
            <li>Anda dapat melihat status semua TV pada daftar di tab "Remote".</li>
            <li>Untuk mengontrol TV, pilih TV dari daftar dan gunakan tombol kontrol yang tersedia.</li>
            <li>Untuk streaming media, pilih TV dan klik tombol "STREAM".</li>
            <li>Untuk mengatur timer, isi durasi, pilih aksi, dan klik "Set Timer".</li>
        </ol>
        """)
        home_layout.addWidget(guide_text)

        home_tab.setLayout(home_layout)
        tabs.addTab(home_tab, "Home")

        # Remote Tab
        remote_tab = QWidget()
        remote_layout = QVBoxLayout()
        
        # TV Selector
        self.tv_selector = QComboBox()
        remote_layout.addWidget(self.tv_selector)

        # TV List
        self.tv_list = QTextEdit()
        self.tv_list.setReadOnly(True)
        self.tv_list.setMaximumHeight(100)
        remote_layout.addWidget(self.tv_list)

        # Remote Control Layout
        remote_control_layout = QGridLayout()

        # Power buttons
        on_button = QPushButton("ON")
        off_button = QPushButton("OFF")
        on_button.clicked.connect(lambda: self.control_tv('on'))
        off_button.clicked.connect(lambda: self.control_tv('off'))
        remote_control_layout.addWidget(on_button, 0, 0)
        remote_control_layout.addWidget(off_button, 0, 2)

         # Home button
        home_button = QPushButton("HOME")
        home_button.clicked.connect(lambda: self.control_tv('home'))
        remote_control_layout.addWidget(home_button, 0, 1)

        # Volume buttons
        volume_up_button = QPushButton("VOL+")
        volume_down_button = QPushButton("VOL-")
        volume_up_button.clicked.connect(lambda: self.control_tv('volume_up'))
        volume_down_button.clicked.connect(lambda: self.control_tv('volume_down'))
        remote_control_layout.addWidget(volume_up_button, 1, 1)
        remote_control_layout.addWidget(volume_down_button, 3, 1)

        # Stream button
        stream_button = QPushButton("STREAM")
        stream_button.clicked.connect(self.stream_media)
        remote_control_layout.addWidget(stream_button, 2, 1)

        # Timer controls
        self.timer_duration = QLineEdit()
        self.timer_duration.setPlaceholderText("Timer (seconds)")
        self.timer_action = QComboBox()
        self.timer_action.addItems(['off', 'sleep', 'volume_up', 'volume_down'])
        set_timer_button = QPushButton("Set Timer")
        set_timer_button.clicked.connect(self.set_timer)

        remote_control_layout.addWidget(self.timer_duration, 4, 0, 1, 3)
        remote_control_layout.addWidget(self.timer_action, 5, 0, 1, 3)
        remote_control_layout.addWidget(set_timer_button, 6, 0, 1, 3)

        # Custom text for timer
        self.show_on_tv_checkbox = QCheckBox("Show on TV")
        self.custom_text_input = QLineEdit()
        self.custom_text_input.setPlaceholderText("Custom text for timer")
        self.custom_text_input.setText(self.custom_text)
        save_custom_text_button = QPushButton("Save Custom Text")
        save_custom_text_button.clicked.connect(self.save_custom_text)

        remote_control_layout.addWidget(self.show_on_tv_checkbox, 7, 0, 1, 3)
        remote_control_layout.addWidget(self.custom_text_input, 8, 0, 1, 3)
        remote_control_layout.addWidget(save_custom_text_button, 9, 0, 1, 3)

        remote_control_widget = QWidget()
        remote_control_widget.setLayout(remote_control_layout)
        remote_layout.addWidget(remote_control_widget)

        # Add TV controls
        add_layout = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("TV Name")
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("TV IP")
        add_button = QPushButton("Add TV")
        add_button.clicked.connect(self.add_tv)
        add_layout.addWidget(self.name_input)
        add_layout.addWidget(self.ip_input)
        add_layout.addWidget(add_button)
        remote_layout.addLayout(add_layout)

        # Edit and Delete buttons
        edit_delete_layout = QHBoxLayout()
        edit_button = QPushButton("Edit TV")
        delete_button = QPushButton("Delete TV")
        edit_button.clicked.connect(self.edit_tv)
        delete_button.clicked.connect(self.delete_tv)
        edit_delete_layout.addWidget(edit_button)
        edit_delete_layout.addWidget(delete_button)
        remote_layout.addLayout(edit_delete_layout)

        remote_tab.setLayout(remote_layout)
        tabs.addTab(remote_tab, "Remote")
        # API Tab
        api_tab = QWidget()
        api_layout = QVBoxLayout()
        api_info = QTextEdit()
        api_info.setReadOnly(True)
        api_info.setHtml("""
        <h2>API Information</h2>
        <p>The Mosys Billing application provides the following API endpoints:</p>
        <ul>
            <li><code>POST /add_tv</code>: Add a new TV</li>
            <li><code>POST /remove_tv</code>: Remove a TV</li>
            <li><code>POST /edit_tv</code>: Edit TV information</li>
            <li><code>GET /tv_status</code>: Get status of all TVs</li>
            <li><code>POST /control_tv</code>: Control a TV (on, off, volume)</li>
            <li><code>POST /stream_media/{ip}</code>: Stream media to a TV</li>
            <li><code>POST /set_timer</code>: Set a timer for TV control</li>
        </ul>
        <p>For more details on how to use these endpoints, please refer to the API documentation.</p>
        """)
        api_layout.addWidget(api_info)
        api_tab.setLayout(api_layout)
        tabs.addTab(api_tab, "API")

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

        central_widget.setLayout(main_layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_tv_list)
        self.timer.start(5000)

        self.update_tv_list()

    def add_tv(self):
        name = self.name_input.text()
        ip = self.ip_input.text()
        if name and ip:
            response = app.test_client().post('/add_tv', json={'name': name, 'ip': ip})
            if response.status_code == 200:
                QMessageBox.information(self, "Success", "TV added successfully")
                self.name_input.clear()
                self.ip_input.clear()
                self.update_tv_list()
            else:
                QMessageBox.warning(self, "Error", f"Failed to add TV: {response.json.get('error', 'Unknown error')}")
        else:
            QMessageBox.warning(self, "Error", "Please enter both name and IP")

    def update_tv_list(self):
        response = app.test_client().get('/tv_status')
        if response.status_code == 200:
            tvs = response.json
            tv_list_text = ""
            self.tv_selector.clear()
            for ip, tv_info in tvs.items():
                tv_list_text += f"Name: {tv_info['name']}, IP: {ip}, Status: {tv_info['status']}, Response Time: {tv_info['response_time']}\n"
                self.tv_selector.addItem(f"{tv_info['name']} ({ip})", ip)
            self.tv_list.setText(tv_list_text)
        else:
            self.tv_list.setText("Failed to fetch TV list")

    def control_tv(self, action):
        selected_ip = self.tv_selector.currentData()
        if selected_ip:
            try:
                control_response = app.test_client().post('/control_tv', json={'ip': selected_ip, 'action': action})
                if control_response.status_code == 200:
                    action_display = "Returned to home screen" if action == 'home' else f"{action.capitalize()} command sent"
                    QMessageBox.information(self, "Success", f"{action_display} successfully")
                else:
                    error_message = control_response.json.get('error', 'Unknown error') if control_response.json else 'Unknown error'
                    QMessageBox.warning(self, "Error", f"Failed to send {action} command: {error_message}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"An error occurred: {str(e)}")
        else:
            QMessageBox.warning(self, "Error", "Please select a TV")

    def edit_tv(self):
        selected_ip = self.tv_selector.currentData()
        if selected_ip:
            tv_info = app.test_client().get('/tv_status').json.get(selected_ip)
            if tv_info:
                new_name, ok1 = QInputDialog.getText(self, "Edit TV", "Enter new name:", QLineEdit.Normal, tv_info['name'])
                if ok1 and new_name:
                    new_ip, ok2 = QInputDialog.getText(self, "Edit TV", "Enter new IP:", QLineEdit.Normal, selected_ip)
                    if ok2 and new_ip:
                        if new_name == tv_info['name'] and new_ip == selected_ip:
                            QMessageBox.information(self, "No Changes", "No changes were made to the TV information.")
                        else:
                            response = app.test_client().post('/edit_tv', json={'old_ip': selected_ip, 'new_name': new_name, 'new_ip': new_ip})
                            if response.status_code == 200:
                                QMessageBox.information(self, "Success", "TV edited successfully")
                                self.update_tv_list()
                            else:
                                QMessageBox.warning(self, "Error", f"Failed to edit TV: {response.json.get('error', 'Unknown error')}")
                    else:
                        QMessageBox.warning(self, "Cancelled", "TV edit was cancelled or IP was empty.")
                else:
                    QMessageBox.warning(self, "Cancelled", "TV edit was cancelled or name was empty.")
            else:
                QMessageBox.warning(self, "Error", "Failed to get TV information")
        else:
            QMessageBox.warning(self, "Error", "Please select a TV to edit")

    def delete_tv(self):
        selected_ip = self.tv_selector.currentData()
        if selected_ip:
            reply = QMessageBox.question(self, "Confirm Deletion", f"Are you sure you want to delete the TV with IP {selected_ip}?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                response = app.test_client().post('/remove_tv', json={'ip': selected_ip})
                if response.status_code == 200:
                    QMessageBox.information(self, "Success", "TV deleted successfully")
                    self.update_tv_list()
                else:
                    QMessageBox.warning(self, "Error", f"Failed to delete TV: {response.json.get('error', 'Unknown error')}")
        else:
            QMessageBox.warning(self, "Error", "Please select a TV to delete")

    def stream_media(self):
        selected_ip = self.tv_selector.currentData()
        if selected_ip:
            file_path, _ = QFileDialog.getOpenFileName(self, "Select Media File", "", "Media Files (*.mp4 *.mkv *.avi *.mp3 *.jpg *.png)")
            if file_path:
                with open(file_path, 'rb') as file:
                    files = {'file': (os.path.basename(file_path), file, 'application/octet-stream')}
                    try:
                        stream_response = requests.post(f'http://localhost:1616/stream_media/{selected_ip}', files=files)
                        if stream_response.status_code == 200:
                            QMessageBox.information(self, "Success", "Media file transferred and streaming started")
                        else:
                            QMessageBox.warning(self, "Error", f"Failed to start media streaming: {stream_response.json().get('error', 'Unknown error')}")
                    except requests.RequestException as e:
                        QMessageBox.warning(self, "Error", f"Failed to connect to server: {str(e)}")
        else:
            QMessageBox.warning(self, "Error", "Please select a TV")

    def load_custom_text(self):
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
        custom_text = self.custom_text_input.text()
        with open(CUSTOM_TEXT_FILE, 'w') as f:
            json.dump({'custom_text': custom_text}, f)
        self.custom_text = custom_text
        QMessageBox.information(self, "Success", "Custom text saved successfully")

    def set_timer(self):
        selected_ip = self.tv_selector.currentData()
        duration = self.timer_duration.text()
        action = self.timer_action.currentText()
        show_on_tv = self.show_on_tv_checkbox.isChecked()
        custom_text = self.custom_text_input.text()
        
        if not selected_ip or not duration:
            QMessageBox.warning(self, "Error", "Please select a TV and enter duration")
            return

        try:
            duration = int(duration)
            if show_on_tv:
                encoded_text = base64.b64encode(custom_text.encode()).decode()
                adb_command = f"adb -s {selected_ip}:5555 shell am start -n com.mosys.billing/.MainActivity --ei seconds {duration} --es customText {shlex.quote(encoded_text)}"
                result = subprocess.run(adb_command, shell=True, check=True, capture_output=True, text=True)
                if result.returncode == 0:
                    message = f"Timer set for {duration} seconds and shown on TV with custom text: '{custom_text}'"
                    QMessageBox.information(self, "Success", message)
                else:
                    QMessageBox.warning(self, "Error", f"Failed to set timer: {result.stderr}")
            else:
                response = app.test_client().post('/set_timer', json={
                    'ip': selected_ip,
                    'seconds': duration,
                    'action': action
                })
                if response.status_code == 200:
                    message = f"Timer set for {duration} seconds to {action}"
                    QMessageBox.information(self, "Success", message)
                else:
                    error_message = response.json.get('error', 'Unknown error') if response.json else 'Unknown error'
                    QMessageBox.warning(self, "Error", f"Failed to set timer: {error_message}")
        except ValueError:
            QMessageBox.warning(self, "Error", "Please enter a valid number for timer duration")
        except subprocess.CalledProcessError as e:
            QMessageBox.warning(self, "Error", f"Failed to execute ADB command: {e}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"An unexpected error occurred: {str(e)}")




if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    ex = MosysBillingGUI()
    ex.show()
    sys.exit(app.exec_())