# Copyright (C) 2025 IAMVanilka
# SPDX-License-Identifier: GPL-3.0-or-later

import os.path

from PySide6.QtCore import QRect, QSize, Qt, QPoint, Signal
from PySide6.QtGui import QPixmap, QAction, QIcon
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QScrollArea, QLayout, QLabel, QFrame, QMenu, QDialog, QCheckBox, \
    QFormLayout, QLineEdit, QFileDialog, QHBoxLayout, QMessageBox

from modules.sqls import get_all_games, add_new_game, delete_game, update_game
from modules.ui_controllers.async_runner import AsyncRunner
from modules.API_client import APIClient
from modules.ui_controllers.main_controller import (sync_saves_action, delete_from_server_action, load_games_covers,
                                                    update_game_data_on_server_action, download_saves_action)


class DynamicButtonDialog(QDialog):
    def __init__(self, title, message, parent=None,
                 buttons=None,
                 checkbox_text=None,
                 default_button=0):
        """
        buttons: список кортежей [(текст, стиль), ...]
        стиль: "primary", "secondary", "danger", "success" или пользовательский CSS
        """
        super().__init__(parent)
        self.checkbox_checked = False
        self.user_choice = None
        self.title = title
        self.message = message
        self.buttons_config = buttons or [("OK", "primary")]
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

class ClickableFrame(QFrame):
    """Класс, который создает кликабельную карточку игры с изображением и контекстным меню.
    Поддерживает клик левой кнопкой мыши и контекстное меню по правой кнопке.
    Может принимать функцию, которая будет вызываться при нажатии левой кнопкой мыши.
    Для передачи аргументов функции используйте *args, **kwargs используются для внутренних настроек карточек."""

    game_deleted_signal = Signal(str)
    game_update_signal = Signal(str)

    def __init__(self, func=None, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.api_client = APIClient()
        self.setFixedSize(420, 220)

        self.setup_card_ui()

        self.create_context_menu()

    def on_delete_error(self, error):
        if error is not True:
            msg = QMessageBox()
            msg.setWindowTitle("Ошибка")
            msg.setText("Не удалось удалить игру на сервере! Сервер ответил False!" if error is False else
                        f"Не удалось удалить игру на сервере! Текст ошибки: {error}")
            msg.setIcon(QMessageBox.Critical)
            msg.setModal(True)
            msg.exec()

    def on_sync_progress(self):
        self.sync_label.setText("Синхронизация...")
        self.sync_label.setStyleSheet("""
                QLabel {
                    color: #141414;
                    font-size: 12px;
                    background-color: rgba(4, 82, 199, 0.55);
                    border-radius: 3px;
                    padding: 2px 5px;
                }
            """)
        self.sync_label.setFixedSize(120, 20)

    def on_sync_error(self, error):
        self.sync_label.setText("Не удалось синхронизировать!")
        self.sync_label.setStyleSheet("""
                QLabel {
                    color: #141414;
                    font-size: 12px;
                    background-color: rgba(199, 4, 40, 0.55);
                    border-radius: 3px;
                    padding: 2px 5px;
                }
            """)
        self.sync_label.setFixedSize(190, 20)

        print(error)

    def setup_card_ui(self):
        """Создание интерфейса карточки игры"""
        self.setStyleSheet("""
            QFrame {
                background-color: #333333;
                border: 2px solid #444444;
                border-radius: 10px;
            }
            QFrame:hover {
                border-color: #1B3CBF;
                background-color: #3a3a3a;
            }
        """)

        # Основной layout для карточки
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(8)

        # Контейнер для изображения
        self.image_container = QWidget()
        self.image_container.setFixedSize(390, 160)
        self.image_container.setStyleSheet("background-color: transparent; border: none;")
        self.image_container.setLayout(QVBoxLayout())
        self.image_container.layout().setContentsMargins(0, 0, 0, 0)

        # Изображение игры
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("""
            background-color: transparent;
            border: none;
        """)

        # Загружаем и масштабируем изображение
        image_path = self.kwargs.get('image_path', '')
        if image_path == "" or not os.path.exists(image_path):
            if os.path.exists(f"UI/resources/{self.kwargs.get("game_name")}.jpg"):
                pixmap = QPixmap(f"UI/resources/{self.kwargs.get("game_name")}.jpg")
            else:
                pixmap = QPixmap()
        else:
            pixmap = QPixmap(image_path)

        if not pixmap.isNull():
            pixmap = pixmap.scaled(390, 160, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(pixmap)
        else:
            self.image_label.setText("🖼️ No picture")
            self.image_label.setStyleSheet("""
                color: #888888;
                font-size: 24px;
                background-color: #2a2a2a;
                border-radius: 5px;
                border: none;
            """)

        self.image_container.layout().addWidget(self.image_label)

        label_text =  "Не синхронизировалось!" if self.kwargs['last_sync_date'] is None else\
            f"Синхронизировано: {self.kwargs['last_sync_date'].strftime("%Y-%m-%d %H:%M:%S")}"
        self.sync_label = QLabel(label_text)
        self.sync_label.setParent(self.image_container)
        self.sync_label.move(10, 10)

        # Надпись о синхронизации (в левом верхнем углу)
        if self.kwargs['last_sync_date'] is None:
            self.sync_label.setStyleSheet("""
                QLabel {
                    color: #141414;
                    font-size: 12px;
                    background-color: rgba(199, 166, 4, 0.55);
                    border-radius: 3px;
                    padding: 2px 5px;
                }
            """)
            label_size = 160
        else:
            self.sync_label.setStyleSheet("""
                QLabel {
                    color: #141414;
                    font-size: 12px;
                    background-color: rgba(4, 199, 46, 0.55);
                    border-radius: 3px;
                    padding: 2px 5px;
                }
            """)
            label_size = 250

        self.sync_label.setFixedSize(label_size, 20)
        self.sync_label.raise_()

        # Кнопка синхронизации (в правом нижнем углу контейнера)
        icon = QIcon("UI/resources/refresh.svg")
        self.sync_button = QPushButton()
        self.sync_button.setFixedSize(50, 50)
        self.sync_button.setIcon(icon)
        self.sync_button.setIconSize(QSize(50, 50))
        self.sync_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(71, 71, 71, 0.6);
                color: white;
                border-radius: 15px;
                border: none;
                font-size: 60px;
            }
            QPushButton:hover {
                background-color: rgba(100, 100, 100, 0.8);
            }
            QPushButton:pressed {
                background-color: rgba(100, 100, 100, 1);
            }
        """)
        self.sync_button.setToolTip("Синхронизировать данные игры")
        self.sync_button.setParent(self.image_container)
        self.sync_button.move(335, 105)
        self.sync_button.clicked.connect(self.on_sync)
        self.sync_button.raise_()

        card_layout.addWidget(self.image_container)

        # Название игры (внизу)
        game_name = self.kwargs.get('game_name', 'Unknown Game')
        self.game_label = QLabel(game_name)
        self.game_label.setStyleSheet("""
            color: white;
            font-size: 16px;
            font-weight: bold;
            background-color: transparent;
            border: none;
            text-align: center;
        """)
        self.game_label.setWordWrap(True)
        self.game_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.game_label.setFixedHeight(25)

        card_layout.addWidget(self.game_label)
        self.setLayout(card_layout)
        self.setCursor(Qt.PointingHandCursor)

    def create_context_menu(self):
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # Создаем меню
        self.context_menu = QMenu(self)

        # Добавляем стили для меню
        self.context_menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
                color: white;
                font-size: 14px;
            }
            QMenu::item:selected {
                background-color: #1B3CBF;
                border-radius: 3px;
            }
            QMenu::separator {
                height: 1px;
                background-color: #555555;
                margin: 5px 0px;
            }
        """)

        # Добавляем действия
        self.action_open = QAction("Открыть папку сохранений", self)
        self.action_edit = QAction("Изменить", self)
        self.action_delete = QAction("Удалить", self)

        # Подключаем сигналы
        self.action_open.triggered.connect(self.on_open)
        self.action_edit.triggered.connect(self.on_edit)
        self.action_delete.triggered.connect(self.on_delete)

        # Добавляем действия в меню
        self.context_menu.addAction(self.action_open)
        self.context_menu.addAction(self.action_edit)
        self.context_menu.addSeparator()
        self.context_menu.addAction(self.action_delete)

    def show_context_menu(self, position):
        # Показываем контекстное меню
        self.context_menu.exec(self.mapToGlobal(position))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.on_click()
        else:
            super().mousePressEvent(event)

    def on_click(self):
        if self.func is None:
            pass
        else:
            if self.func and callable(self.func):
                if self.args:
                    self.func(*self.args, **self.kwargs)
                else:
                    self.func(**self.kwargs)

    def on_open(self):
        import subprocess
        import platform
        import os

        path = self.kwargs['saves_path']

        system = platform.system()

        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":  # macOS
            subprocess.Popen(['open', path])
        elif system == "Linux":
            file_managers = [
                'xdg-open',  # стандартный способ
                'dolphin',  # KDE
                'nautilus',  # GNOME
                'thunar',  # XFCE
                'pcmanfm',  # LXDE
                'nemo',  # Cinnamon (Linux Mint)
                'caja'  # MATE
            ]

            opened = False
            for fm in file_managers:
                try:
                    subprocess.Popen([fm, path])
                    opened = True
                    break
                except Exception:
                    continue

            if not opened:
                raise FileNotFoundError("Не удалось открыть папку: не найден подходящий файловый менеджер")

    def on_edit(self):
        print("Выбрано: Редактировать")
        game_update_status = AddNewGameWindow(
            edit=True,
            game_name=self.kwargs.get('game_name', ''),
            saves_path=self.kwargs.get('saves_path', ''),
            game_path=self.kwargs.get('game_path', ''),
            image_path=self.kwargs.get('image_path', ''),
            game_id=self.kwargs.get('game_id', ''),
        )

        self.game_update_signal.emit(game_update_status.game_update.emit)

    def on_delete(self):
        game_id = self.kwargs.get('game_id')
        game_name = self.kwargs.get('game_name')

        if game_id:
            dialog = DynamicButtonDialog(
                title="Подтверждение удаления",
                message=f"Вы действительно хотите удалить игру \"{game_name}\"?",
                buttons=[("Удалить", "danger"), ("Отмена", "secondary")],
                checkbox_text="Удалить данные на сервере со всеми бэкапами",
                default_button=0
            )
            result = dialog.exec()

            if result == QDialog.Accepted:
                delete_from_server = dialog.checkbox_checked
                user_choose = dialog.user_choice
                try:
                    if user_choose == 0:
                        delete_game(game_id=game_id)
                        self.game_deleted_signal.emit(game_id)
                        print(f"Игра {game_name} удалена")

                        if delete_from_server:
                            self.delete_runner = AsyncRunner()
                            self.delete_runner.finished.connect(lambda x: print(f"ERROR signal received: {x}") or self.on_delete_error(x))
                            self.delete_runner.error.connect(lambda x: print(f"ERROR signal received: {x}") or self.on_delete_error(x))
                            self.delete_runner.run_async(delete_from_server_action, game_name, True, self.api_client)

                except Exception as e:
                    print(f"Exception: {e}")  # <-- Отладка
                    QMessageBox.critical(self, "Ошибка", f"Не удалось удалить игру: {str(e)}")

    def handle_result(self, result, error):
        """Callback получает 2 параметра: результат и ошибка"""
        if error:
            # Была ошибка
            print("Ошибка!")
            print(f"Exception: {error['exception']}")
            print(f"Traceback:\n{error['traceback']}")
            # Можно показать сообщение пользователю
            QMessageBox.critical(self, "Ошибка", str(error['exception']))
        else:
            # Успех
            print(f"Результат: {result}")

    def on_sync(self):
        """Обработчик клика по кнопке синхронизации"""
        import os
        game_id = self.kwargs.get('game_id')

        self.sync_runner = AsyncRunner()
        self.sync_runner.finished.connect(self.game_update_signal.emit)
        self.sync_runner.error.connect(self.on_sync_error)
        self.sync_runner.progress.connect(self.on_sync_progress)

        saves_path = self.kwargs.get("saves_path")
        game_path = self.kwargs.get("game_path")

        if not saves_path or not os.path.exists(saves_path):
            missing = "путь к папке сохранений"
        elif not game_path or not os.path.exists(game_path):
            missing = "путь к exe-файлу игры"
        else:
            missing = None

        if missing:
            warning_window = DynamicButtonDialog(
                title="Невозможно синхронизировать сохранения.",
                message=f"У данной игры не настроен или не существует {missing}.\n\n"
                        "Открыть меню редактирования, чтобы вы могли указать правильные пути?",
                buttons=[('Да', 'success'), ('Нет', 'secondary')],
                default_button=0
            )
            warning_window.setFixedSize(400, 240)
            result = warning_window.exec()
            if result == QDialog.Accepted and warning_window.user_choice == 0:
                self.on_edit()

        elif self.kwargs["last_sync_date"] is None:
            warning_window = DynamicButtonDialog(
                title="Первичная синхронизация",
                message=f"""
                    <p>Игра <b>{self.kwargs["game_name"]}</b> еще ни разу не синхронизировалась 
                    с сервером на этом компьютере</p>

                    <p><b>Какое действие вы хотите совершить:</b></p>

                    <p><span style="color: #2196F3;">1. Скачать сохранения с сервера</span></p>

                    <p style="border: 1px solid #f44336; border-radius: 5px; padding: 8px; background-color: #2d0000; margin-top: 0;">
                    <span style="color: #ff5252; font-weight: bold;">⚠ ВНИМАНИЕ: ТЕКУЩИЕ СОХРАНЕНИЯ БУДУТ ПОТЕРЯНЫ!</span><br/>
                    <span style="color: #ffffff;">Папка "{self.kwargs["saves_path"]}" будет полностью перезаписана</span>
                    </p>

                    <p><span style="color: #4CAF50;">2. Загрузить локальные данные на сервер</span><br/>
                    <i>Создаст бэкап и заменит текущие данные на сервере</i></p>
                """,
                buttons=[('Скачать сохранения с сервера', 'primary'),
                         ('Загрузить локальные сохранения на сервер', 'success'),
                         ('Отмена', 'secondary')],
                default_button=2
            )
            warning_window.setFixedSize(400, 440)
            result = warning_window.exec()
            if result == QDialog.Accepted:
                if warning_window.user_choice == 0:
                    confirmation_dialog = DynamicButtonDialog(
                        title='ВНИМАНИЕ!',
                        message=f"""
                            <p><b>Пожалуйста, подтвердите ваш выбор:</b></p>

                            <p style="color: #ff5252; font-weight: bold; text-align: center; margin: 15px 0;">
                            ⚠ ВСЕ ЛОКАЛЬНЫЕ СОХРАНЕНИЯ БУДУТ ПОТЕРЯНЫ!
                            </p>

                            <p>Папка <u>"{self.kwargs["saves_path"]}"</u> будет полностью перезаписана 
                            данными с сервера.</p>

                            <p><b>Вы уверены, что хотите продолжить?</b></p>
                        """,
                        buttons=[('Да, скачать с сервера', 'danger'),
                                 ('Отмена', 'secondary')],
                        default_button=1
                    )
                    confirmation_dialog.setFixedSize(400, 300)
                    confirm_result = confirmation_dialog.exec()
                    if confirm_result == QDialog.Accepted:
                        if confirmation_dialog.user_choice == 0:
                            self.sync_runner.run_async(download_saves_action,self.kwargs['game_name'],
                                                       self.kwargs['saves_path'], game_id, api_client=self.api_client)
                elif warning_window.user_choice == 1:
                    self.sync_runner.run_async(sync_saves_action, game_name=self.kwargs['game_name'],
                                               saves_path=self.kwargs['saves_path'], game_id=game_id, api_client=self.api_client)
        else:
            if game_id:
                print(f"Синхронизация игры с ID: {game_id}")

                self.sync_runner.run_async(sync_saves_action, game_name=self.kwargs['game_name'],
                                       saves_path=self.kwargs['saves_path'], game_id=game_id, api_client=self.api_client)

class FlowLayout(QLayout):
    """Кастомный layout, который автоматически располагает виджеты в сетке с переносом строк.
    Адаптируется под размер родительского контейнера."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._item_list = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self._item_list.append(item)

    def count(self):
        return len(self._item_list)

    def itemAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self._do_layout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())
        margin, _, _, _ = self.getContentsMargins()
        size += QSize(2 * margin, 2 * margin)
        return size

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()

        for item in self._item_list:
            wid = item.widget()
            space_x = spacing
            space_y = spacing
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()

class AddNewGameWindow(QDialog):
    """Модальное окно для добавления новой игры или редактирования существующей.
    Содержит поля для ввода названия игры, путей к exe-файлу, сохранениям и изображению."""

    game_update = Signal(str)

    def __init__(self, parent = None, edit=None, **kwargs):
        super().__init__(parent)
        self.kwargs = kwargs
        self.api_client = APIClient()
        self.edit = edit
        self.setWindowTitle("Добавить новую игру" if self.edit is None else "Редактирование игры")
        self.setModal(True)
        self.setFixedSize(500, 300)
        self.setStyleSheet("""
            QDialog {
                background-color: #29292A;
                color: white;
            }
            QLabel {
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
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton#cancelButton {
                background-color: #666666;
            }
            QPushButton#cancelButton:hover {
                background-color: #777777;
            }
            QPushButton#cancelButton:pressed {
                background-color: #555555;
            }
        """)
        self.create_add_new_game_window()

    def create_add_new_game_window(self):
        # Основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Форма
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignLeft)

        # Поля ввода
        if self.edit is not None:
            game_name_edit = QLineEdit(text=self.kwargs['game_name'])
            saves_path_edit = QLineEdit(text=self.kwargs['saves_path'])
            exe_path_edit = QLineEdit(text=self.kwargs['game_path'])
            image_path_edit = QLineEdit(text=self.kwargs['image_path'])
        else:
            game_name_edit = QLineEdit()
            saves_path_edit = QLineEdit()
            exe_path_edit = QLineEdit()
            image_path_edit = QLineEdit()

        # Кнопки выбора путей
        saves_browse_button = QPushButton("Обзор")
        exe_browse_button = QPushButton("Обзор")
        image_browse_button = QPushButton("Обзор")

        # Подключаем кнопки обзора
        def browse_saves():
            directory = QFileDialog.getExistingDirectory(self, "Выберите папку сохранений")
            if directory:
                saves_path_edit.setText(directory)

        def browse_exe():
            file_path, _ = QFileDialog.getOpenFileName(self, "Выберите exe файл", "", "Executable Files (*.exe)")
            if file_path:
                exe_path_edit.setText(file_path)

        def browse_image():
            file_path, _ = QFileDialog.getOpenFileName(self, "Выберите изображение", "",
                                                       "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)")
            if file_path:
                image_path_edit.setText(file_path)

        saves_browse_button.clicked.connect(browse_saves)
        exe_browse_button.clicked.connect(browse_exe)
        image_browse_button.clicked.connect(browse_image)

        # Добавляем поля в форму
        form_layout.addRow(QLabel("Название игры:"), game_name_edit)

        # Путь к сохранениям с кнопкой обзора
        saves_layout = QHBoxLayout()
        saves_layout.addWidget(saves_path_edit)
        saves_layout.addWidget(saves_browse_button)
        form_layout.addRow(QLabel("Путь к сохранениям:"), saves_layout)

        # Путь к exe файлу с кнопкой обзора
        exe_layout = QHBoxLayout()
        exe_layout.addWidget(exe_path_edit)
        exe_layout.addWidget(exe_browse_button)
        form_layout.addRow(QLabel("Путь к exe файлу:"), exe_layout)

        # Путь к изображению с кнопкой обзора

        image_layout = QHBoxLayout()
        image_layout.addWidget(image_path_edit)
        image_layout.addWidget(image_browse_button)
        form_layout.addRow(QLabel("Путь к изображению:"), image_layout)

        main_layout.addLayout(form_layout)

        # Кнопки действия
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        add_button = QPushButton("Добавить" if self.edit is None else "Изменить")
        add_button.setObjectName("addButton")
        cancel_button = QPushButton("Отмена")
        cancel_button.setObjectName("cancelButton")

        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(cancel_button)

        main_layout.addLayout(buttons_layout)

        # Подключаем кнопки
        def accept_dialog():
            game_name = game_name_edit.text().strip()
            saves_path = saves_path_edit.text().strip()
            exe_path = exe_path_edit.text().strip()
            image_path = image_path_edit.text().strip()  # Получаем путь к изображению

            # Проверка заполнения обязательных полей
            if not game_name:
                # Можно показать сообщение об ошибке
                return
            if not saves_path:
                # Можно показать сообщение об ошибке
                return
            if not exe_path:
                # Можно показать сообщение об ошибке
                return

            # Здесь ваша логика сохранения данных игры
            # Передаем также путь к изображению
            if self.edit is None:
                add_new_game(game_name=game_name, saves_path=saves_path, game_path=exe_path, image_path=image_path)
            else:
                update_game(game_name=game_name, saves_path=saves_path, game_path=exe_path,
                            image_path=image_path, game_id=self.kwargs["game_id"])

                self.update_game_runner = AsyncRunner()
                self.update_game_runner.run_async(update_game_data_on_server_action,
                                                  self.kwargs["game_name"], game_name, self.api_client)

                self.game_update.emit(self.kwargs['game_id'])

            self.accept()

        def cancel_dialog():
            self.reject()

        add_button.clicked.connect(accept_dialog)
        cancel_button.clicked.connect(cancel_dialog)

        # Показываем диалог
        self.exec()

class GamesDashboard(QWidget):
    """Основной дашборд для отображения карточек игр в виде сетки.
    Использует ClickableFrame для отображения каждой игры и FlowLayout для компоновки."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = APIClient()
        self.setStyleSheet("background-color: #29292A;")

        # === СКРОЛЛИРУЕМАЯ ОБЛАСТЬ ===
        self.scroll_area = QScrollArea()
        self.scroll_area.setStyleSheet("background-color: #29292A; border: none;")
        self.scroll_area.setWidgetResizable(True)

        # === КОНТЕЙНЕР ДЛЯ КАРТОЧЕК ===
        self.container_widget = QWidget()
        self.container_widget.setStyleSheet("background-color: #29292A;")

        # Используем FlowLayout для адаптивного размещения
        self.flow_layout = FlowLayout()
        self.flow_layout.setSpacing(15)
        self.flow_layout.setContentsMargins(20, 20, 20, 20)

        self.setup_widget()

    def setup_widget(self):
        """Инициализация интерфейса dashboard'а"""
        # Заполняем карточки игр
        self.populate_game_cards()

        self.container_widget.setLayout(self.flow_layout)
        self.scroll_area.setWidget(self.container_widget)

        # === КНОПКА "+" ===
        self.add_button = QPushButton("+")
        self.add_button.setFixedSize(60, 60)
        self.add_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(36, 66, 189, 0.3);
                color: white;
                border-radius: 30px;
                font-size: 66px;
                font-weight: semi-bold;
            }
            QPushButton:hover {
                background-color: rgba(36, 66, 189, 0.7);
            }
            QPushButton:pressed {
                background-color: rgba(28, 51, 145, 0.9);
            }
        """)
        self.add_button.clicked.connect(self.add_new_game)

        # === РАЗМЕЩЕНИЕ ЭЛЕМЕНТОВ ===
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.scroll_area)

        # Добавляем кнопку поверх scroll_area
        self.add_button.setParent(self)
        self.add_button.raise_()

        self.update_button_position()

    def populate_game_cards(self):
        """Заполняет dashboard карточками игр"""
        games_data = get_all_games()

        # Очищаем существующие карточки
        while self.flow_layout.count():
            child = self.flow_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Создаем новые карточки
        for game_id, data in games_data.items():
            card_widget = self.create_game_card(
                game_id=game_id,
                game_name=data["game_name"],
                image_path=data["image_path"],
                game_path=data["game_path"],
                saves_path=data["saves_path"],
                last_sync_date=data["last_sync_date"]
            )
            self.flow_layout.addWidget(card_widget)

    def create_error_message(self, error_msg):
        QMessageBox.critical(self, "Ошибка", error_msg)


    def create_game_card(self, game_id, game_name, image_path, game_path, saves_path, last_sync_date):
        """Создаёт карточку игры с фиксированным размером"""
        card = ClickableFrame(game_id=game_id, game_name=game_name, game_path=game_path, saves_path=saves_path,
                              image_path=image_path, last_sync_date=last_sync_date)

        card.game_deleted_signal.connect(self.on_dashboard_changed)
        card.game_update_signal.connect(self.on_dashboard_changed)

        card_style = """
            QFrame {
                background-color: #333333;
                border: 2px solid #444444;
                border-radius: 10px;
            }
            QFrame:hover {
                border-color: #1B3CBF;
                background-color: #3a3a3a;
            }
        """

        card.setStyleSheet(card_style)
        card.setFixedSize(420, 220)

        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setStyleSheet("""
            background-color: transparent;
            border: none;
        """)
        image_label.setFixedSize(390, 160)

        game_label = QLabel(game_name)
        game_label.setStyleSheet("""
            color: white;
            font-size: 16px;
            font-weight: bold;
            text-align: center;
            background-color: transparent;
            border: none;
        """)
        game_label.setWordWrap(True)
        game_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        game_label.setFixedHeight(25)

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(8)
        card_layout.addWidget(image_label)
        card_layout.addWidget(game_label)

        card.setLayout(card_layout)
        card.setCursor(Qt.PointingHandCursor)

        return card

    def setup_card_ui(self):
        """Создание элементов интерфейса карточки"""
        # Надпись о синхронизации (левый верхний угол)
        self.sync_label = QLabel("not sync")
        self.sync_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 12px;
                background-color: transparent;
            }
        """)
        self.sync_label.setParent(self)
        self.sync_label.move(10, 10)  # Позиционируем в левом верхнем угл

    def update_button_position(self):
        """Обновляет позицию кнопки '+'"""
        if hasattr(self, 'add_button'):
            button_size = self.add_button.size()
            parent_size = self.size()
            x = parent_size.width() - button_size.width() - 20
            y = parent_size.height() - button_size.height() - 20
            self.add_button.move(max(20, x), max(20, y))

    def on_dashboard_changed(self, game_id):
        """Обработчик сигнала удаления игры"""
        print(f"Dashboard был обновлён! Изменения затронули игру с id {game_id}.")
        # Обновляем dashboard
        self.refresh_dashboard()

    def refresh_dashboard(self):
        """Обновляет dashboard после добавления новой игры"""
        async_runner = AsyncRunner()
        async_runner.finished.connect(self.populate_game_cards)
        async_runner.error.connect(self.populate_game_cards)
        async_runner.run_async(load_games_covers, self.api_client)
        self.populate_game_cards()

    def resizeEvent(self, event):
        """Обработчик изменения размера виджета"""
        super().resizeEvent(event)
        self.update_button_position()

    def showEvent(self, event):
        """Обработчик показа виджета"""
        super().showEvent(event)
        self.update_button_position()

    def add_new_game(self):
        """Открывает диалог добавления новой игры"""
        print("Открытие диалога добавления игры")
        AddNewGameWindow()
        self.refresh_dashboard()

