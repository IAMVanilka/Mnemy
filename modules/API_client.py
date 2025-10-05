# Copyright (C) 2025 IAMVanilka
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import os
import logging
from datetime import datetime

import requests
import aiohttp
import keyring
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self, app_name="SavingApp", config_file="settings.json"):
        self.app_name = app_name
        self.token_name = "x_api_token"
        self.config_file = config_file
        self.host = self.load_host()

    def load_host(self) -> str:
        """Загрузка адреса сервера из JSON файла"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get("host", "")
            return ""
        except Exception as e:
            logger.error(f"Ошибка загрузки адреса сервера: {e}")
            return ""

    def set_host(self, host: str):
        """Установка адреса сервера"""
        try:
            config = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

            config["host"] = host

            with open(self.config_file, 'w+', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            self.host = host
        except Exception as e:
            logger.error(f"Ошибка сохранения адреса сервера: {e}")

    def save_token(self, token: str):
        """Сохранить API токен"""
        keyring.set_password(self.app_name, self.token_name, token)

    def get_token(self) -> Optional[str]:
        """Получить API токен"""
        return keyring.get_password(self.app_name, self.token_name)

    def clear_token(self):
        """Удалить API токен"""
        try:
            keyring.delete_password(self.app_name, self.token_name)
        except keyring.errors.PasswordDeleteError:
            pass

    def _make_request(self, endpoint: str, method: str, **kwargs):
        """Сделать защищенный запрос"""
        self.host = self.load_host()

        if not self.host:
            raise ValueError("Server host not configured")

        token = self.get_token()
        if not token:
            raise ValueError("API token not found")

        url = f"{self.host}{endpoint}"
        headers = kwargs.get('headers', {})
        headers['x-api-token'] = token
        kwargs['headers'] = headers

        try:
            method = method.upper()
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")

    async def check_files(self, base_dir: str, game_name: str, date: datetime):
        """Проверка файлов"""
        from modules.file_manager import hash_generator

        files_data = await hash_generator(base_dir)
        files_to_upload = list()

        data = {
            "game_name": game_name,
            "files_data": files_data,
            "last_sync_date": date if date is None else date.isoformat()
        }

        response = self._make_request('/files/check_files', method="post", data=json.dumps(data), allow_redirects=False)

        if response.status_code == 307:
            return "redirect"

        response_data = response.json()

        missing_files = response_data['files_data']['missing_on_server']
        mismatched_files = response_data['files_data']['mismatched_hashes']

        for file in list(missing_files + mismatched_files):
            files_to_upload.append(f"{base_dir}{file}")

        return files_to_upload

    async def upload_files_streaming(self, base_dir: str, files_paths: list, game_name: str):
        """Загрузка файлов стримингом"""
        if not os.path.exists(base_dir) or not os.path.isdir(base_dir):
            print("❌ Folder not found or not a directory")
            return False

        upload_url = f"{self.host}/files/upload_data"

        from modules.file_manager import create_archive_chunk_generator
        chunk_generator = create_archive_chunk_generator(base_dir, files_paths)

        async def data_stream():
            async for chunk in chunk_generator:
                yield chunk

        data = aiohttp.FormData()
        data.add_field(
            "file",
            data_stream(),
            filename="files.tar.gz",
            content_type="application/gzip"
        )
        data.add_field("game_name", game_name)

        async with aiohttp.ClientSession() as session:
            print("📤 Streaming archive to server...")
            api_token = self.get_token()
            async with session.post(
                    upload_url,
                    data=data,
                    headers={"x-api-token": api_token}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print("✅ Success:", result)
                else:
                    text = await response.text()
                    print("❌ Failed:", response.status, text)

        return True

    async def download_files(self, game_name: str, path_to_saves: str):
        """Скачивание файлов"""
        try:
            from modules.file_manager import get_archive_chunks

            with self._make_request("/files/download_data", method="get", params={'game_name': game_name},
                                         stream=True) as file:
                await get_archive_chunks(file, path_to_saves)

            print(f"Сохранения для игры {game_name} успешно загружены!")
            return True
        except Exception as e:
            print("Ошибка! Не удалось скачать сохранения! ", e)
            return False

    async def delete_game(self, game_name: str, delete_backups: bool = False):
        """Удаление игры"""
        try:
            if not delete_backups:
                response = self._make_request(f'/manage/delete/game/{game_name}', method="delete")
                print(f"Сохранения для игры {game_name} успешно удалены!")
                print(response.json())
            else:
                response = self._make_request(
                    f'/manage/delete/game/{game_name}',
                    method="delete",
                    params={"delete_backups": delete_backups}
                )
                print(f"Сохранения для игры {game_name} успешно удалены!")
                print(response.json())

            return True
        except Exception as e:
            print("Ошибка! Не удалось удалить сохранения на сервере! ", e)
            return False

    async def update_game_data(self, game_name: str, new_game_name: str):
        """Обновление данных игры"""
        try:
            response = self._make_request(
                f'/manage/update_game/{game_name}',
                method="patch",
                params={"new_game_name": new_game_name}
            )
            print(f"Метаданные игры {game_name} успешно обновлены!")
            print(response.json())
            return True
        except Exception as e:
            print(f"Ошибка! Не удалось обновить метаданные игры {game_name}! ", e)
            return False

    async def get_games_data(self) -> List[Dict[str, Any]]:
        """Получение данных игр"""
        try:
            response = self._make_request(
                '/manage/get_games_data',
                method='get',
                timeout=30
            )
            response.raise_for_status()

            if not response.headers.get('content-type', '').startswith('application/json'):
                logger.error(f"Unexpected content type: {response.headers.get('content-type')}")
                raise Exception("Server returned non-JSON response")

            return response.json()["games_list"]

        except requests.exceptions.Timeout:
            logger.error("Request to get_games_data timed out")
            raise Exception("Request timeout - server not responding")

        except requests.exceptions.ConnectionError:
            logger.error("Connection error when requesting get_games_data")
            raise Exception("Failed to connect to server")

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            raise Exception(f"Server error: {e.response.status_code}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception: {str(e)}")
            raise Exception(f"Network error: {str(e)}")

        except ValueError as e:  # JSON decode error
            logger.error(f"JSON decode error: {str(e)}")
            raise Exception("Invalid response format from server")

        except Exception as e:
            logger.error(f"Unexpected error in get_games_data: {str(e)}")
            raise Exception(f"Unknown error: {str(e)}")

    async def get_games_images(self, games_list: list, steam: bool = False):
        """Получение изображений игр"""
        for game_name in games_list:
            if not os.path.exists(f"UI/resources/{game_name}.jpg"):
                if steam:
                    image_url = self._get_steam_cover_url(game_name)
                    if image_url:
                        response = requests.get(image_url, timeout=30)
                    else:
                        continue
                else:
                    response = self._make_request(f'/files/get_image/{game_name}', method="get", timeout=30)

                if response.status_code == 200:
                    with open(f"UI/resources/{game_name}.jpg", "wb") as image_file:
                        image_file.write(response.content)
                else:
                    print(f"Error: {response.status_code}, {response.json()}")

    def _get_steam_cover_url(self, game_name: str) -> Optional[str]:
        """Получение URL обложки из Steam"""
        search_url = f"https://store.steampowered.com/api/storesearch/?term={game_name}&l=english&cc=US"
        try:
            response = requests.get(search_url)
            data = response.json()

            if data['items']:
                app_id = data['items'][0]['id']
                cover_url = f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/header.jpg"
                return cover_url
            else:
                return None
        except Exception as e:
            print(f"Ошибка: {e}")
            return None

    async def get_backups_data(self) -> Dict[str, Any]:
        """Получение данных бэкапов"""
        response = self._make_request("/files/get_backups_data", method='get')
        return response.json()

    async def restore_backup(self, game_name: str, backup_name: str) -> bool:
        """Восстановление бэкапа"""
        response = self._make_request(
            "/files/restore_backup",
            method="post",
            json={"game_name": game_name, "backup_name": backup_name}
        )

        return response.status_code == 200

    async def delete_backup(self, game_name: str, backup_name: str) -> Optional[bool]:
        """Удаление бэкапа"""
        response = self._make_request(
            "/files/delete_backup",
            method="delete",
            json={"game_name": game_name, "backup_name": backup_name}
        )

        if response.status_code == 200:
            return True
        elif response.status_code == 204:
            return None  # Файл отсутствует
        else:
            return False

    async def test_token(self) -> bool:
        """Проверка токена"""
        response = self._make_request('/manage/check_x_token', method='get')
        print(response.status_code)
        if response.status_code == 200 and response.json()['token_status'] == True:
            return True
        else:
            print('Token invalid')
            return False

    async def check_server_health(self, host_for_check=None) -> bool:
        """Проверка здоровья сервера"""
        try:
            if host_for_check:
                response = requests.get(f"{host_for_check}/manage/health", timeout=5)
            else:
                if not self.host:
                    return False
                response = requests.get(f"{self.host}/manage/health", timeout=5)
            return response.status_code == 200
        except requests.exceptions.ConnectionError:
            return False
        except Exception:
            return False