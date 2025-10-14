from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QCheckBox, QPushButton, QFrame


class DynamicButtonDialog(QDialog):
    """Модальное окно с динамическим кол-во кнопок и чекбоксом"""
    def __init__(self, title, message, parent=None,
                 buttons=None,
                 checkbox_text=None,
                 default_button=0):
        """
        buttons: список кортежей [(текст, стиль), ...]
        стиль: "primary", "secondary", "danger", "success" или пользовательский CSS
        """
        super().__init__(parent)
        self.setWindowIcon(QPixmap("UI/resources/icon.ico"))
        self.checkbox_checked = False
        self.user_choice = None
        self.title = title
        self.message = message
        self.buttons_config = buttons or [("OK", "secondary")]
        self.checkbox_text = checkbox_text
        self.default_button = default_button
        self.button_objects = []  # Список созданных кнопок
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle(self.title)
        self.setModal(True)
        self.setStyleSheet("background-color: #29292A;")

        height = 150 + (30 if self.checkbox_text else 0) + (len(self.buttons_config) * 25)
        self.setFixedSize(450, min(height, 400))

        layout = QVBoxLayout()

        # Сообщение
        message_label = QLabel(self.message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("""
            color: white; 
            font-size: 14px;
            margin-bottom: 10px;
        """)
        message_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        # Чекбокс (опционально)
        self.checkbox = None
        if self.checkbox_text:
            self.checkbox = QCheckBox(self.checkbox_text)
            self.checkbox.setStyleSheet("""
                QCheckBox {
                    color: white;
                    font-size: 13px;
                    margin: 10px 0;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                }
            """)

        # Кнопки
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(8)

        self.button_objects = []

        for i, (text, style) in enumerate(self.buttons_config):
            button = QPushButton(text)
            button.setStyleSheet(self.get_button_style(style))
            button.setFixedHeight(35)

            button.clicked.connect(lambda checked, idx=i: self.button_clicked(idx))

            buttons_layout.addWidget(button)
            self.button_objects.append(button)

            # Устанавливаем кнопку по умолчанию
            if i == self.default_button:
                button.setDefault(True)

        # Добавляем элементы в layout
        layout.addWidget(message_label)
        if self.checkbox:
            layout.addWidget(self.checkbox)

        # Добавляем разделитель
        if self.buttons_config:
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            separator.setStyleSheet("color: #555555;")
            layout.addWidget(separator)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)

        # Подключаем чекбокс (если есть)
        if self.checkbox:
            self.checkbox.stateChanged.connect(self.on_checkbox_changed)

    def get_button_style(self, style):
        """Получить стиль для кнопки"""
        styles = {
            "primary": """
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
            """,
            "secondary": """
                QPushButton {
                    background-color: #666666;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #777777;
                }
                QPushButton:pressed {
                    background-color: #555555;
                }
            """,
            "danger": """
                QPushButton {
                    background-color: #d32f2f;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #f44336;
                }
                QPushButton:pressed {
                    background-color: #c62828;
                }
            """,
            "success": """
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
                QPushButton:pressed {
                    background-color: #388E3C;
                }
            """
        }

        if style in styles:
            return styles[style]
        else:
            return style  # Пользовательский CSS

    def button_clicked(self, button_index):
        self.user_choice = button_index
        self.done(button_index)
        self.accept()

    def on_checkbox_changed(self, state):
        self.checkbox_checked = bool(state)

    def get_result(self):
        """Получить результат: (user_choice, checkbox_state)"""
        return self.user_choice, self.checkbox_checked
