# Copyright (C) 2025 IAMVanilka
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import shutil
import tarfile
import hashlib
import threading

async def hash_generator(base_dir) -> dict:
    """Сканирует папку и генерирует словарь {'file_path': 'md5_hash'}"""

    dir_name = base_dir.split("/")[-1]
    files_data = dict()

    def scan_directory(directory):
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.is_file():
                    with open(entry.path, "rb") as file:
                        md5_hash = hashlib.file_digest(file, 'md5')
                        files_data[(entry.path.split(dir_name)[1])] = md5_hash.hexdigest()
                elif entry.is_dir():
                    scan_directory(entry.path)

    scan_directory(base_dir)
    return files_data


async def create_archive_chunk_generator(base_dir: str, files_paths: list, CHUNK_SIZE = 65536):
    """
     Генератор, который потоково создаёт .tar.gz и возвращает чанки.
     Работает в отдельном потоке, чтобы не блокировать async event loop.
     """
    read_fd, write_fd = os.pipe()

    exception_occurred = threading.Event()

    def writer():
        """Функция для рекурсивной загрузки данных в пайпу"""
        try:
            with os.fdopen(write_fd, "wb") as wf:
                with tarfile.open(fileobj=wf, mode="w:gz", compresslevel=6) as tar:
                    for file in files_paths:
                        if os.path.exists(file):
                            relative_path = file.split(base_dir)[1]
                            tar.add(file, arcname=relative_path)
                            print(f"Обрабатываю файл {file}")

                    # def process_directory(dir_path):
                    #     with os.scandir(dir_path) as entries:
                    #         for entry in entries:
                    #             try:
                    #                 if entry.is_file(follow_symlinks=False):
                    #                     relative_path = Path(entry.path).relative_to(folder_path)
                    #                     tar.add(entry.path, arcname=str(relative_path))
                    #                 elif entry.is_dir(follow_symlinks=False):
                    #                     process_directory(entry.path)
                    #             except (OSError, PermissionError) as e:
                    #                 print(f"⚠️  Пропущен элемент {entry.path}: {e}")
                    #                 continue

                    #process_directory(current_folder)

        except BrokenPipeError:
            print("ℹ️  Pipe closed by reader (normal behavior)")
            pass
        except Exception as e:
            print(f"❌ Writer error: {e}")
            exception_occurred.set()

    thread = threading.Thread(target=writer, daemon=True)
    thread.start()

    with os.fdopen(read_fd, "rb") as rf:
        while True:
            chunk = rf.read(CHUNK_SIZE)
            if not chunk:
                break
            yield chunk


async def get_archive_chunks(file, path_to_saves: str):
    file.raise_for_status()

    if not os.path.exists("temp_data"):
        os.mkdir("temp_data")

    with open("temp_data/downloaded_saves.tar.gz", "wb") as f:
        for chunk in file.iter_content(chunk_size=64 * 1024):
            f.write(chunk)

    with tarfile.open("temp_data/downloaded_saves.tar.gz", "r:gz") as tar:
        if not os.path.exists(path_to_saves):
            os.mkdir(path_to_saves)
        else:
            shutil.rmtree(path_to_saves)
            os.mkdir(path_to_saves)

        tar.extractall(path=path_to_saves)

    os.remove('temp_data/downloaded_saves.tar.gz')
