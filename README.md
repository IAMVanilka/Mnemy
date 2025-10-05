# 🖥️ Mnemy Client (ru 🇷🇺)

![Mnemy Logo](logo.png)

**Mnemy** автоматически синхронизирует ваши игровые сохранения с личным сервером — чтобы вы никогда не потеряли свой прогресс.

> 💡 **Требуется сервер**: разверните [mnemy-server](https://github.com/IAMVanilka/mnemy-server) у себя дома, на VPS или в облаке.

---

## 🌟 Основные функции

- Подключение к вашему серверу по адресу и токену
- Добавление игр: указание `.exe` и пути к сохранениям
- **Автоматическая синхронизация** после каждой игровой сессии
- **Ручная синхронизация** в один клик
- Просмотр истории бэкапов и **восстановление любого сохранения**

## 📥 Установка

1. Клонируйте данный репозиторий: `git clone https://github.com/IAMVanilka/Mnemy.git`
2. Создайте виртуальное окружение python: `python -m venv venv`
3. Запустите виртуальное окружение: `source venv/bin/activate` (bash) | `source venv/scripts/activate` (power shell) | `call venv/scripts/activate` (cmd)
4. Установите зависимости: `pip install -r requirements.txt`
5. Запустите приложение: `python main.py`

P.S Если вы на Linux можете просто запустить `start_mnemy.sh`

## 🔒 Приватность и контроль

- Все данные хранятся **только на вашем сервере**
- Никакой передачи данных третьим лицам
- Полный контроль над тем, что, когда и как архивируется

## 📜 Лицензия

Проект распространяется под лицензией [GPL-3.0](LICENSE).

## ❓ Помощь и поддержка

Перед созданием Issue проверьте:
- Доступен ли сервер по указанному адресу
- Корректен ли токен
- Есть ли права на чтение папки с сохранениями

Нашли баг или хотите новую функцию?
Откройте [Issue](https://github.com/IAMVanilka/Mnemy/issues)!

## ⚠️ Проблемы с UI в Mnemy

В данный момент UI Mnemy написан на PySide6 с помощью ИИ (так как я не Frontend разработчик).
Если вы разбираетесь в разработке UI и у вас есть желание помочь я всегда буду рад вашим **Pull Requests**!

> *Carefully archived. Faithfully remembered. Mnemy.*

---

# 🖥️ Mnemy Client (en 🇬🇧)
**Mnemy** automatically syncs your game saves with your personal server — so you never lose your progress.

> 💡 Server required: deploy mnemy-server at home, on a VPS, or in the cloud. 


## 🌟 Key Features
 - Connect to your server using its address and personal token
 - Add games by specifying the .exe file and save directory
 - Automatic sync after every gaming session
 - Manual sync with one click
 - View backup history and restore any save
 

## 📥 Installation
Clone this repository: `git clone https://github.com/IAMVanilka/Mnemy.git`

Create a Python virtual environment: `python -m venv venv`

Activate the virtual environment: 
 - Linux/macOS (bash/zsh): `source venv/bin/activate`
 - Windows (PowerShell): `source venv/scripts/activate`
 - Windows (CMD): `call venv/scripts/activate`
 
Install dependencies: `pip install -r requirements.txt`

Launch the app: `python main.py`

P.S. On Linux, you can simply run `./start_mnemy.sh`. 

## 🔒 Privacy & Control
* All your data is stored only on your own server
* No data is ever sent to third parties
* Full control over what, when, and how is archived

## 📜 License
This project is licensed under [GPL-3.0](LICENSE).

## ❓ Help & Support
Before opening an issue, please check:
- Is your server reachable at the specified address?
- Is your token correct?
- Do you have read permissions for the save directory?

Found a bug or have a feature request?
Open an [Issue](https://github.com/IAMVanilka/Mnemy/issues)!

## ⚠️ UI Contribution Welcome!
The current UI of Mnemy was generated with AI assistance using **PySide6**, as I’m primarily a backend developer and **not** a frontend specialist.

If you have experience with desktop UI development (especially PySide6/Qt) and would like to improve the interface — I’d be very grateful for your **Pull Requests**!

Even small UX tweaks or visual enhancements would make a big difference.

> *Carefully archived. Faithfully remembered. Mnemy.*

