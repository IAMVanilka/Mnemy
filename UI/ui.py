# Copyright (C) 2025 IAMVanilka
# SPDX-License-Identifier: GPL-3.0-or-later

from PySide6.QtCore import QSettings
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QHBoxLayout, QFrame, QWidget, QStackedWidget, QSystemTrayIcon, QMenu, QApplication

from UI.components.side_menu import SideMenu
from UI.components.settings_window import SettingsWindow
from UI.components.games_dashboard import GamesDashboard
from UI.components.games_dashboard import AsyncRunner
from UI.components.loading_window import LoadingDialog

from modules.ui_controllers.main_controller import set_up_games_data
from modules.API_client import APIClient

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.api_client = APIClient()
        self.settings = QSettings("Mnemy")
        self.tray_icon = None
        self.main_layout = None
        self.stacked_widget = None
        self.loading_dialog = LoadingDialog()
        self.setup_tray_icon()
        self.get_games_data()

    def setup_tray_icon(self):
        """Настройка иконки в системном трее"""
        import os

        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("Системный трей недоступен")
            return

        self.tray_icon = QSystemTrayIcon(self)
        icon_path = "UI/resources/icon.ico"
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(self.style().SP_ComputerIcon))

        tray_menu = QMenu()

        show_action = QAction("Показать", self)
        quit_action = QAction("Выход", self)

        show_action.triggered.connect(self.show_window)
        quit_action.triggered.connect(self.quit_application)

        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.setToolTip("Mnemy")
        self.tray_icon.show()

    def tray_icon_activated(self, reason):
        """Обработчик клика по иконке в трее"""
        if reason == QSystemTrayIcon.Trigger:  # Левый клик
            self.show_window()
        elif reason == QSystemTrayIcon.DoubleClick:  # Двойной клик
            self.show_window()

    def show_window(self):
        """Показать окно приложения"""
        self.games_dashboard.refresh_dashboard()
        self.show()
        self.raise_()
        self.activateWindow()

    def hide_window(self):
        """Скрыть окно приложения"""
        self.hide()

    def quit_application(self):
        """Закрыть приложение"""
        # Убираем иконку из трея перед выходом
        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.quit()

    def minimize_to_tray(self):
        """Свернуть в трей программно"""
        if self.tray_icon and self.tray_icon.isVisible():
            self.hide_window()

    def get_games_data(self):
        self.show_loading_dialog()

        get_games_runner = AsyncRunner()
        get_games_runner.finished.connect(self.on_data_loaded)
        get_games_runner.error.connect(self.on_data_error)

        get_games_runner.run_async(set_up_games_data, self.api_client)

    def show_loading_dialog(self):
        """Показать модальное окно загрузки"""
        if self.loading_dialog:
            self.loading_dialog.message_label.setText("Синхронизация с сервером...")
            self.loading_dialog.setFixedSize(270, 120)
            self.loading_dialog.show()
            self.loading_dialog.raise_()
            self.loading_dialog.activateWindow()
            self.setEnabled(False)

    def hide_loading_dialog(self):
        """Скрыть окно загрузки"""
        if self.loading_dialog:
            self.loading_dialog.close()
            self.setEnabled(True)

    def on_data_loaded(self, result):
        """Данные загружены успешно"""
        self.hide_loading_dialog()
        self.initializeUI()

    def on_data_error(self, error_info):
        """Ошибка при загрузке данных"""
        self.hide_loading_dialog()
        print(f"Ошибка загрузки: {error_info['exception']}")
        self.initializeUI()

    def initializeUI(self):
        self.setWindowTitle('Mnemy')
        self.setStyleSheet("background-color: #222222;")
        self.setGeometry(600, 600, 1200, 600)
        self.load_window_state()
        self.createWindow()
        self.show()

    def create_separator(self):
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #FFFFFF;")
        return separator

    def createWindow(self):
        menu_widget = SideMenu(self)
        separator = self.create_separator()

        self.stacked_widget = QStackedWidget()
        self.games_dashboard = GamesDashboard(self)
        self.settings_widget = SettingsWindow(self)

        self.stacked_widget.addWidget(self.games_dashboard)  # Index 0
        self.stacked_widget.addWidget(self.settings_widget)  # Index 1

        menu_widget.games_clicked.connect(self.show_games)
        menu_widget.settings_clicked.connect(self.show_settings)
        menu_widget.about_clicked.connect(self.show_about)

        self.main_layout = QHBoxLayout()
        self.main_layout.addWidget(menu_widget)
        self.main_layout.addWidget(separator)
        self.main_layout.addWidget(self.stacked_widget)

        self.setLayout(self.main_layout)

    def show_games(self):
        self.stacked_widget.setCurrentIndex(0)

    def show_settings(self):
        self.stacked_widget.setCurrentIndex(1)

    def show_about(self):
        print("Показать 'О программе'")

    def send_notif(self, text):
        self.tray_icon.showMessage(
            "Mnemy",
            text,
            QSystemTrayIcon.Information,
            5000  # 2 секунды
        )

    def save_window_state(self):
        self.settings.setValue("window_size", self.size())
        self.settings.setValue("window_position", self.pos())

    def load_window_state(self):
        size = self.settings.value("window_size", self.size())
        pos = self.settings.value("window_position", self.pos())

        self.resize(size)
        self.move(pos)

    def closeEvent(self, event):
        """Обработчик закрытия окна"""
        if self.loading_dialog:
            self.loading_dialog.close()

        if self.tray_icon and self.tray_icon.isVisible():
            self.hide_window()
            self.send_notif("Приложение свернуто в системный трей")
            event.ignore()
        else:
            self.save_window_state()
            event.accept()