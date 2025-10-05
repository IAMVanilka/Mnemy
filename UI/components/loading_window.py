# Copyright (C) 2025 IAMVanilka
# SPDX-License-Identifier: GPL-3.0-or-later

from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont


class LoadingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.animation_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.animation_index = 0
        self.timer = QTimer()
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Загрузка")
        self.setFixedSize(250, 120)
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)

        # Устанавливаем флаг, чтобы диалог всегда был поверх других окон
        if self.parent():
            self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Анимация загрузки
        self.animation_label = QLabel(self.animation_chars[0])
        self.animation_label.setAlignment(Qt.AlignCenter)
        font = QFont("Monospace", 24)
        self.animation_label.setFont(font)
        self.animation_label.setStyleSheet("""
            color: #4CAF50;
            font-size: 24px;
            font-weight: bold;
        """)

        # Сообщение
        self.message_label = QLabel("Загрузка данных...")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet("""
            color: white;
            font-size: 16px;
            font-weight: normal;
        """)

        layout.addWidget(self.animation_label)
        layout.addWidget(self.message_label)

        self.setLayout(layout)

        # Стиль окна
        self.setStyleSheet("""
            QDialog {
                background-color: #222222;
                border: 2px solid #444444;
                border-radius: 10px;
            }
        """)

        # Настройка анимации
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(100)  # Обновляем каждые 100 мс

    def update_animation(self):
        """Обновить анимацию"""
        self.animation_index = (self.animation_index + 1) % len(self.animation_chars)
        self.animation_label.setText(self.animation_chars[self.animation_index])

    def setMessage(self, message):
        """Установить сообщение"""
        self.message_label.setText(message)

    def showEvent(self, event):
        """Центрируем диалог при показе"""
        super().showEvent(event)
        if self.parent():
            # Центрируем относительно родителя
            parent_geo = self.parent().geometry()
            x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - self.height()) // 2
            self.move(x, y)

    def closeEvent(self, event):
        """Остановить таймер при закрытии"""
        self.timer.stop()
        event.accept()