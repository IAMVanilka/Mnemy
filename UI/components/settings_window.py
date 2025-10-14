# Copyright (C) 2025 IAMVanilka
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import os

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QLineEdit, QPushButton, QListWidget,
                               QListWidgetItem, QGroupBox, QTextEdit, QSizePolicy)
from PySide6.QtCore import Qt

from modules.ui_controllers.async_runner import AsyncRunner
from modules.ui_controllers.main_controller import get_backups_data_action, restore_backup_action, delete_backup_action
from modules.API_client import APIClient

class SettingsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = APIClient()
        self.expanded_games = set()
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        self.setWindowTitle("Настройки")
        self.setStyleSheet("""
            QWidget {
                background-color: #29292A;
                color: white;
                font-size: 14px;
            }
            QLineEdit {
                background-color: #3A3A3C;
                color: white;
                border: 1px solid #555557;
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #4CAF50;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QGroupBox {
                border: 1px solid #555557;
                border-radius: 5px;
                margin-top: 1ex;
                font-weight: bold;
            }
            QGroupBox::title {
                subline-offset: -2px;
                padding: 0 5px;
                color: #4CAF50;
            }
            QListWidget {
                background-color: #3A3A3C;
                border: 1px solid #555557;
                border-radius: 5px;
                alternate-background-color: #323234;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #1B3CBF;
            }
            QTextEdit {
                background-color: #3A3A3C;
                border: 1px solid #555557;
                border-radius: 5px;
                color: white;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # === Адрес сервера ===
        server_group = QGroupBox("Адрес сервера")
        server_layout = QVBoxLayout()
        server_layout.setContentsMargins(10, 30, 10, 10)
        server_layout.setSpacing(10)

        self.server_address_input = QLineEdit()
        self.server_address_input.setPlaceholderText("Введите адрес сервера...")

        server_button_layout = QHBoxLayout()
        save_server_btn = QPushButton("Сохранить адрес")
        test_server_btn = QPushButton("Проверить адрес")

        save_server_btn.clicked.connect(self.save_server_address_to_config)
        test_server_btn.clicked.connect(self.test_server_address)

        server_button_layout.addWidget(save_server_btn)
        server_button_layout.addWidget(test_server_btn)
        server_button_layout.addStretch()

        server_layout.addWidget(self.server_address_input)
        server_layout.addLayout(server_button_layout)

        server_group.setLayout(server_layout)
        main_layout.addWidget(server_group)

        # === Токен доступа ===
        token_group = QGroupBox("Токен доступа к серверу")
        token_layout = QVBoxLayout()
        token_layout.setContentsMargins(10, 30, 10, 10)
        token_layout.setSpacing(10)

        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Введите ваш токен доступа...")

        token_button_layout = QHBoxLayout()
        save_token_btn = QPushButton("Сохранить токен")
        test_token_btn = QPushButton("Проверить токен")

        save_token_btn.clicked.connect(self.save_token)
        test_token_btn.clicked.connect(self.test_token)

        token_button_layout.addWidget(save_token_btn)
        token_button_layout.addWidget(test_token_btn)
        token_button_layout.addStretch()

        token_layout.addWidget(self.token_input)
        token_layout.addLayout(token_button_layout)

        token_group.setLayout(token_layout)
        main_layout.addWidget(token_group)

        # === Бэкапы ===
        backups_group = QGroupBox("Доступные бэкапы")
        backups_layout = QVBoxLayout()
        backups_layout.setContentsMargins(10, 30, 10, 10)
        backups_layout.setSpacing(10)

        # Список бэкапов
        self.backups_list = QListWidget()
        self.backups_list.setAlternatingRowColors(True)

        # Кнопки управления бэкапами
        backup_buttons_layout = QHBoxLayout()
        refresh_btn = QPushButton("Обновить список")
        restore_btn = QPushButton("Восстановить выбранное")
        delete_btn = QPushButton("Удалить выбранное")

        refresh_btn.clicked.connect(self.load_data)
        restore_btn.clicked.connect(self.restore_backup)
        delete_btn.clicked.connect(self.delete_backup)

        backup_buttons_layout.addWidget(refresh_btn)
        backup_buttons_layout.addWidget(restore_btn)
        backup_buttons_layout.addWidget(delete_btn)
        backup_buttons_layout.addStretch()

        backups_layout.addWidget(self.backups_list)
        backups_layout.addLayout(backup_buttons_layout)

        backups_group.setLayout(backups_layout)
        main_layout.addWidget(backups_group)

        # === Статус ===
        status_group = QGroupBox("Статус")
        status_layout = QVBoxLayout()

        status_layout.setContentsMargins(9, 25, 9, 9)

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        status_layout.addWidget(self.status_text)
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group, stretch=1)

        self.backups_list.itemClicked.connect(self.on_backup_item_clicked)

        self.setLayout(main_layout)

    def load_data(self):
        # Загрузка адреса сервера
        server_address = self.get_server_address()
        self.server_address_input.setText(server_address)

        # Загрузка токена
        token = self.api_client.get_token()
        self.token_input.setText(token)

        async_runner = AsyncRunner()
        async_runner.result.connect(self.refresh_backups)

        async_runner.run_async(get_backups_data_action, self.api_client)

    def get_server_address(self):
        """Загрузка адреса сервера из JSON файла"""
        try:
            config_file = "settings.json"
            if os.path.exists(config_file):
                with open(config_file, 'r+', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get("host", "")
            return ""
        except Exception as e:
            self.update_status(f"❌ Ошибка загрузки адреса сервера: {e}")
            return ""

    def save_server_address_to_config(self):
        """Сохранение адреса сервера в JSON файл"""
        try:
            address = self.server_address_input.text().strip()

            config_file = "settings.json"
            config = {}

            # Загружаем существующий конфиг
            if os.path.exists(config_file):
                with open(config_file, 'r+', encoding='utf-8') as f:
                    config = json.load(f)

            # Обновляем адрес
            config["host"] = address

            # Сохраняем
            with open(config_file, 'w+', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            self.api_client.load_host()
            self.update_status(f"✅ Адрес {address} был сохранен в конфиг!")

        except Exception as e:
            self.update_status(f"❌ Ошибка сохранения адреса сервера: {e}")

    def test_server_address(self):
        """Проверка адреса сервера"""
        server_address = self.server_address_input.text().strip()

        if not server_address:
            self.update_status("❌ Введите адрес сервера для проверки")
            return

        import re
        url_pattern = re.compile(
            r'^https?://'  # http:// или https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # домен
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
            r'(?::\d+)?'  # порт
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        if url_pattern.match(server_address):
            self.test_server_connection(server_address)
        else:
            self.update_status("❌ Неверный формат адреса сервера")

    def test_server_connection(self, server_address):
        """Проверка соединения с сервером"""

        def check_connection(status):
            if status is True:
                self.update_status(f"✅ Сервер {server_address} доступен!")
            else:
                self.update_status(f"❌ Сервер {server_address} недоступен!")

        def errors_handler(error):
            print(error)

        self.async_runner = AsyncRunner()
        self.async_runner.result.connect(check_connection)
        self.async_runner.error.connect(errors_handler)
        self.async_runner.run_async(self.api_client.check_server_health, host_for_check=server_address)

    def on_backup_item_clicked(self, item):
        """Обработчик клика по элементу списка"""
        if item and item.data(Qt.UserRole):
            item_data = item.data(Qt.UserRole)

            if item_data.get("type") == "game_header":
                game_name = item_data["game"]
                if game_name in self.expanded_games:
                    self.expanded_games.remove(game_name)
                else:
                    self.expanded_games.add(game_name)

                self.load_data()

    def save_token(self):
        """Сохранение токена"""
        token = self.token_input.text().strip()
        if token:
            self.api_client.save_token(token)
            self.update_status(f"✅ Токен сохранен")
        else:
            self.update_status("❌ Токен не может быть пустым")

    def test_token(self):
        """Проверка токена"""

        def handle_signal(status):
            if status is True:
                self.update_status("✅ Токен действителен")
            else:
                self.update_status("❌ Токен НЕ действителен или не верный!")

        token = self.token_input.text().strip()

        if token:
            self.async_runner = AsyncRunner()
            self.async_runner.finished.connect(handle_signal)
            self.async_runner.error.connect(handle_signal)
            self.async_runner.run_async(self.api_client.test_token)
        else:
            self.update_status("❌ Введите токен для проверки")

    def refresh_backups(self, backups_data):
        """Обновление списка бэкапов с возможностью сворачивания"""
        self.backups_list.clear()

        for game_name, backups in backups_data.items():
            is_expanded = game_name in self.expanded_games

            if is_expanded:
                game_text = f"📂 {game_name} ({len(backups)} бэкапов)"
            else:
                game_text = f"📁 {game_name} ({len(backups)} бэкапов)"

            game_item = QListWidgetItem(game_text)
            game_item.setData(Qt.UserRole, {"type": "game_header", "game": game_name})
            game_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            game_item.setBackground(Qt.darkGray)
            game_item.setForeground(Qt.white)
            self.backups_list.addItem(game_item)

            def format_bytes(size_bytes):
                """Преобразует размер в байтах в человеко-читаемый формат"""
                if size_bytes < 1024:
                    return f"{size_bytes} Б"
                elif size_bytes < 1024 ** 2:
                    return f"{size_bytes / 1024:.2f} КБ"
                elif size_bytes < 1024 ** 3:
                    return f"{size_bytes / (1024 ** 2):.2f} МБ"
                else:
                    return f"{size_bytes / (1024 ** 3):.2f} ГБ"

            if is_expanded:
                for backup in backups:
                    filename = backup["filename"]
                    size_bytes = backup["size_bytes"]
                    size_str = format_bytes(size_bytes)
                    backup_item = QListWidgetItem(f"   📄 {filename} ({size_str})")
                    backup_item.setData(Qt.UserRole, {"type": "backup", "game": game_name, "backup": backup})
                    backup_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    self.backups_list.addItem(backup_item)

        self.update_status("Данные загружены")

    def restore_backup(self):
        """Восстановление выбранного бэкапа"""

        def restoring_in_progress():
            self.update_status(f"🔄 Восстановление бэкапа {backup_name['filename']} для {game_name}")

        def restoring_is_done(status):
            if status == 200:
                self.update_status(f"✅ Бэкап {backup_name['filename']} для {game_name} успешно востановлен!")
            else:
                self.update_status("❌ Не удалось восстановить бэкап!")

        def restoring_error(error):
            self.update_status(f"❌ Не удалось восстановить бэкап! Ошибка: {error}")

        current_item = self.backups_list.currentItem()
        if current_item and current_item.data(Qt.UserRole):
            backup_info = current_item.data(Qt.UserRole)
            game_name = backup_info["game"]
            backup_name = backup_info["backup"]

            async_runner = AsyncRunner()
            async_runner.progress.connect(restoring_in_progress)
            async_runner.result.connect(restoring_is_done)
            async_runner.error.connect(restoring_error)
            async_runner.run_async(restore_backup_action, game_name, backup_name["filename"], self.api_client)
        else:
            self.update_status("❌ Выберите бэкап для восстановления")

    def delete_backup(self):
        """Удаление выбранного бэкапа"""

        def backup_deleted(status):
            if status == 200:
                self.update_status(f"🗑️ Бэкап {backup_name['filename']} для {game_name} был успешно удалён!")
            elif status == 204:
                self.update_status(
                    f"❌ Невозможно удалить бэкап {backup_name['filename']} для {game_name}! Файл отсутствует на сервере!")
            else:
                self.update_status(f"❌ Ошибка удаления бэкапа {backup_name['filename']} для {game_name}! Код ответа от сервера: {status}")
            self.load_data()

        def backup_delete_error(error):
            self.update_status(
                f"❌ Ошибка удаления бэкапа {backup_name['filename']} для {game_name}! Текст ошибки: {error}")
            self.load_data()

        current_item = self.backups_list.currentItem()
        if current_item and current_item.data(Qt.UserRole):
            backup_info = current_item.data(Qt.UserRole)
            game_name = backup_info["game"]
            backup_name = backup_info["backup"]

            self.async_runner = AsyncRunner()
            self.async_runner.result.connect(backup_deleted)
            self.async_runner.error.connect(backup_delete_error)
            self.async_runner.run_async(delete_backup_action, game_name, backup_name['filename'], self.api_client)
        else:
            self.update_status("❌ Выберите бэкап для удаления")

    def update_status(self, message):
        """Обновление статуса"""
        self.status_text.append(message)
        self.status_text.verticalScrollBar().setValue(
            self.status_text.verticalScrollBar().maximum()
        )