# Copyright (C) 2025 IAMVanilka
# SPDX-License-Identifier: GPL-3.0-or-later

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton

class SettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #29292A;")
        self.setup_widget()

    def setup_widget(self):
        layout = QVBoxLayout()

        title = QLabel("Настройки")
        title.setStyleSheet("""
            color: white;
            font-size: 24px;
            font-weight: bold;
        """)

        layout.addWidget(title)
        layout.addStretch()

        self.setLayout(layout)


class SideMenu(QWidget):
    games_clicked = Signal()
    settings_clicked = Signal()
    about_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.create_side_menu()

    def create_side_menu(self):
        logo_label = QLabel("Mnemy\nver. 0.0.1")
        logo_label.setStyleSheet("""
                            color: white;
                            font-size: 16px;
                            font-weight: bold;
                            text-align: center;
                        """)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Кнопки меню
        menu_btn_games = QPushButton("Игры")
        menu_btn_settings = QPushButton("Настройки")
        menu_btn_about = QPushButton("О программе")

        button_style = """
                            QPushButton {
                                background-color: transparent;
                                border: none;
                                color: white;
                                padding: 12px;
                                text-align: left;
                                font-size: 16px;
                            }
                            QPushButton:hover {
                                background-color: rgba(27, 60, 191, 0.2);
                                border-radius: 8px;
                            }
                        """

        menu_btn_games.setStyleSheet(button_style)
        menu_btn_settings.setStyleSheet(button_style)
        menu_btn_about.setStyleSheet(button_style)

        menu_btn_settings.clicked.connect(self.settings_clicked.emit)
        menu_btn_games.clicked.connect(self.games_clicked.emit)
        menu_btn_about.clicked.connect(self.about_clicked.emit)

        # Вертикальный layout для кнопок с отступами
        menu_v_box = QVBoxLayout()
        menu_v_box.addWidget(logo_label)
        menu_v_box.addWidget(menu_btn_games)
        menu_v_box.addWidget(menu_btn_settings)
        menu_v_box.addWidget(menu_btn_about)
        menu_v_box.setSpacing(5)
        menu_v_box.addStretch()  # Растягиваем внизу

        self.setLayout(menu_v_box)
        self.setFixedWidth(180)