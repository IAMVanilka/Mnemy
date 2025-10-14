# Copyright (C) 2025 IAMVanilka
# SPDX-License-Identifier: GPL-3.0-or-later
import logging
import traceback

from PySide6.QtCore import QObject, Signal
from concurrent.futures import ThreadPoolExecutor
import asyncio

logger = logging.getLogger(__name__)

class AsyncRunner(QObject):
    finished = Signal(bool)
    error = Signal(object)
    progress = Signal(str)
    result = Signal(object)

    def __init__(self):
        super().__init__()
        self.executor = ThreadPoolExecutor(max_workers=2)

    def run_async(self, coro_func, *args, **kwargs):
        """Запуск асинхронной функции"""

        def run_in_thread():
            try:
                self.progress.emit("")

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                if kwargs:
                    coro = coro_func(*args, **kwargs)
                else:
                    coro = coro_func(*args)

                result = loop.run_until_complete(coro)
                loop.close()

                print("Inside async runner:", result)

                self.result.emit(result)
                self.finished.emit(result)

            except Exception as e:
                error_info = {
                    'exception': e,
                    'traceback': traceback.format_exc()
                }
                self.error.emit(error_info)

        self.executor.submit(run_in_thread)