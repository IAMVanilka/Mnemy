# Copyright (C) 2025 IAMVanilka
# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
import os
import threading
import time
from datetime import datetime

import psutil
import logging

from modules.ui_controllers.main_controller import sync_saves_action
from modules.sqls import get_all_games

# Настройка логирования
if not os.path.exists("logs"):
    os.mkdir("logs")

logger = logging.getLogger(__name__)
logger.propagate = False
logger_handler = logging.FileHandler(f"logs/mnemy_pw_{datetime.now().date()}.log", encoding="utf-8")
logger_handler.setFormatter(logging.Formatter(datefmt='%Y-%m-%d %H:%M:%S', fmt="%(asctime)s — %(levelname)s — %(message)s"))
logger.addHandler(logging.StreamHandler())
logger.addHandler(logger_handler)

class ProcessWatcher:
    def __init__(self, main_window):
        self.games_data = dict()
        self.main_window = main_window

    def _normalize_name(self, name):
        if name.lower().endswith('.exe'):
            return name[:-4]  # Отбрасываем последние 4 символа (.exe)
        elif name.lower().endswith('.'):
            return name[:-1]
        return name

    def _check_process(self, process_name):
        """Проверяет, запущен ли процесс"""
        target_name = self._normalize_name(process_name).lower()

        for proc in psutil.process_iter(['name']):
            try:
                proc_name = self._normalize_name(proc.info['name']).lower()
                if target_name == proc_name:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False

    def _check_any_process_from_list(self):
        """Проверяет, запущен ли хотя бы один процесс из списка"""
        for game_id, game_data in self.games_data.items():
            process_name = game_data['game_path'].split("/")[-1] if game_data["game_path"] is not None else None
            if process_name is None:
                continue
            if self._check_process(process_name):
                return process_name, game_id, game_data
        return None

    def _wait_for_any_process_start(self):
        """Ждет запуска любого процесса из списка"""
        while True:
            running_process_data = self._check_any_process_from_list()
            if running_process_data:
                return running_process_data
            logger.info('Still waiting for any process to start...')
            self._get_all_processes()
            time.sleep(10)

    def _wait_for_process_exit(self, process_name):
        """Ждет завершения конкретного процесса"""
        target_name = self._normalize_name(process_name).lower()

        while True:
            process_found = False
            for proc in psutil.process_iter(['name']):
                try:
                    proc_name = self._normalize_name(proc.info['name']).lower()
                    if target_name == proc_name:
                        process_found = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            if not process_found:
                return

            time.sleep(1)

    def _get_all_processes(self):
        self.games_data = get_all_games()

        process_names = [game_data['game_path'].split("/")[-1] for game_data in self.games_data.values() if
                         game_data["game_path"] is not None]
        logger.info(f"Processes to monitor: {process_names}")
        return self.games_data

    def _monitor_processes(self):
        """Основная функция мониторинга списка процессов"""
        from modules.API_client import APIClient
        api_client = APIClient()

        logger.info('Process watcher started!')

        try:
            while True:
                logger.info("Waiting for any process to start...")
                running_process, game_id, game_data = self._wait_for_any_process_start()
                logger.info(f'Process "{running_process}" has been detected! Waiting for it to exit...')

                self._wait_for_process_exit(running_process)
                logger.info(f'Process "{running_process}" has been killed!')
                self.main_window.send_notif(f"Игра {game_data['game_name']} завершена.\n"
                                            f"Начинаю синхронизацию сохранений...")

                logger.info(f'Starting saves synchronizing...')
                asyncio.run(sync_saves_action(game_name=game_data['game_name'], saves_path=game_data['saves_path'] ,
                                              game_id=game_id, api_client=api_client))
                logger.info(f'Synchronizing successfully done!')
                self.main_window.send_notif(f"Синхронизация для {game_data['game_name']} завершена!")

        except KeyboardInterrupt:
            logger.info("\nProcess watcher stopped...")
        except Exception as e:
            logger.error(e)

    def _start_threading(self):
        self._get_all_processes()
        self._monitor_processes()

    def run(self):
        thread = threading.Thread(target=self._start_threading, daemon=True)
        thread.start()
        return thread
