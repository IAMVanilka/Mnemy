import os
import json
import shutil

import aiohttp
import keyring
import logging
import requests
from requests.exceptions import HTTPError

from datetime import datetime
from typing import List, Dict, Any, Optional

from aiohttp.abc import HTTPException

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self, app_name="Mnemy", config_file="settings.json"):
        self.app_name = app_name
        self.token_name = "x_api_token"
        self.config_file = config_file
        self.host = self.load_host()

    def load_host(self) -> bool:
        """Load server host from JSON config file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get("host", "")
            return True
        except Exception as e:
            logger.error(f"Failed to load server host from {self.config_file}: {e}", exc_info=True)
            return False

    def set_host(self, host: str) -> bool:
        """Save server host to config file."""
        try:
            config = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

            config["host"] = host

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            self.host = host
            logger.info(f"Server host updated to: {host}")
            return True
        except Exception as e:
            logger.error(f"Failed to save server host to {self.config_file}: {e}", exc_info=True)
            return False

    def save_token(self, token: str):
        """Save API token securely."""
        try:
            keyring.set_password(self.app_name, self.token_name, token)
            logger.debug("API token saved securely")
        except Exception as e:
            logger.error(f"Failed to save API token: {e}", exc_info=True)
            raise

    def get_token(self) -> Optional[str]:
        """Retrieve API token."""
        try:
            token = keyring.get_password(self.app_name, self.token_name)
            if not token:
                logger.debug("No API token found in keyring")
            return token
        except Exception as e:
            logger.error(f"Error retrieving API token: {e}", exc_info=True)
            return None

    def clear_token(self):
        """Remove stored API token."""
        try:
            keyring.delete_password(self.app_name, self.token_name)
            logger.info("API token cleared from keyring")
        except keyring.errors.PasswordDeleteError:
            logger.debug("Attempted to delete non-existent token — ignored")
        except Exception as e:
            logger.error(f"Error clearing API token: {e}", exc_info=True)

    def _make_request(self, endpoint: str, method: str, **kwargs):
        """Make an authenticated HTTP request."""
        self.host = self.load_host()

        if not self.host:
            logger.error("Can't make request: Server host is not configured")
            raise ValueError("Server host not configured")

        token = self.get_token()
        if not token:
            logger.error("Can't make request: API token is missing!")
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
            raise

    async def check_files(self, base_dir: str, game_name: str, date: datetime):
        """Check which files need to be uploaded."""
        try:
            from modules.file_manager import hash_generator

            if not os.path.isdir(base_dir):
                logger.error(f"Base directory does not exist or is not a folder: {base_dir}")
                return []

            files_data = await hash_generator(base_dir)
            data = {
                "game_name": game_name,
                "files_data": files_data,
                "last_sync_date": date.isoformat() if date else None
            }

            response = self._make_request(
                '/files/check_files',
                method="post",
                data=json.dumps(data),
                allow_redirects=False
            )

            if response.status_code == 307:
                logger.info("Received redirect (307) from /files/check_files")
                return response.status_code

            response_data = response.json()
            missing = response_data['files_data']['missing_on_server']
            mismatched = response_data['files_data']['mismatched_hashes']
            files_to_upload = [os.path.join(base_dir, f.lstrip('/\\')) for f in missing + mismatched]
            logger.info(f"Found {len(files_to_upload)} files to upload for game '{game_name}'")
            return files_to_upload

        except Exception as e:
            logger.error(f"Error in check_files for game '{game_name}': {e}", exc_info=True)
            return []

    async def upload_files_streaming(self, base_dir: str, files_paths: list, game_name: str) -> int|None:
        """Upload files as a streaming archive."""
        if not os.path.exists(base_dir) or not os.path.isdir(base_dir):
            logger.error(f"Upload folder not found or invalid: {base_dir}")
            return None

        try:
            from modules.file_manager import create_archive_chunk_generator
            if files_paths is None:
                return 200
            chunk_generator = create_archive_chunk_generator(base_dir, files_paths)

            async def data_stream():
                async for chunk in chunk_generator:
                    yield chunk

            data = aiohttp.FormData()
            data.add_field("file", data_stream(), filename="files.tar.gz", content_type="application/gzip")
            data.add_field("game_name", game_name)

            async with aiohttp.ClientSession() as session:
                logger.info(f"📤 Streaming archive for game '{game_name}' to server...")
                api_token = self.get_token()
                if not api_token:
                    logger.error("Cannot upload: API token missing")
                    return None

                async with session.post(
                    f"{self.host}/files/upload_data",
                    data=data,
                    headers={"x-api-token": api_token}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ Upload successful for game '{game_name}': {result}")
                        return response.status
                    else:
                        text = await response.text()
                        logger.error(f"❌ Upload failed for game '{game_name}': {response.status} {text}")
                        return response.status

        except Exception as e:
            logger.error(f"Unexpected error during upload for game '{game_name}': {e}", exc_info=True)
            return None

    async def download_files(self, game_name: str, path_to_saves: str, delete_saves_folder: bool) -> int|None:
        """Download game saves from server."""
        try:
            os.makedirs(path_to_saves, exist_ok=True)

            from modules.file_manager import get_archive_chunks

            with self._make_request(
                "/files/download_data",
                method="get",
                params={'game_name': game_name},
                stream=True
            ) as response:
                if delete_saves_folder:
                    shutil.rmtree(path_to_saves)
                    os.mkdir(path_to_saves)
                await get_archive_chunks(response, path_to_saves)

            logger.info(f"Game saves for '{game_name}' downloaded successfully to {path_to_saves}")
            return 200

        except requests.exceptions.HTTPError as e:
            if "404" in str(e):
                logger.error(f"Can't download saves for game '{game_name}'. Saves doesn't exist on server!.")
                return 404
            else:
                logger.error(f"Can't download saves for game '{game_name}': {e}.", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Failed to download saves for game '{game_name}': {e}", exc_info=True)
            return None

    async def delete_game(self, game_name: str, delete_backups: bool = False) -> int|None:
        """Delete game data on server."""
        try:
            params = {"delete_backups": delete_backups} if delete_backups else None
            response = self._make_request(
                f'/manage/delete/game/{game_name}',
                method="delete",
                params=params
            )
            if response.status_code == 204:
                logger.info(f"Game '{game_name}' doesn't exist on server")
                return response.status_code
            logger.info(f"Game '{game_name}' deleted successfully (backups deleted: {delete_backups})")
            logger.debug(f"Server response: {response.json()}")
            return response.status_code
        except Exception as e:
            logger.error(f"Failed to delete game '{game_name}' on server: {e}", exc_info=True)
            return None

    async def update_game_data(self, game_name: str, new_game_name: str) -> int|None:
        """Update game metadata on server."""
        try:
            if game_name == new_game_name:
                return 200
            response = self._make_request(
                f'/manage/update_game/{game_name}',
                method="patch",
                params={"new_game_name": new_game_name}
            )
            logger.info(f"Game metadata updated: '{game_name}' → '{new_game_name}'")
            logger.debug(f"Server response: {response.json()}")
            return response.status_code
        except Exception as e:
            logger.error(f"Failed to update game '{game_name}': {e}", exc_info=True)
            return None

    async def get_games_data(self) -> List[Dict[str, Any]]:
        """Fetch list of games from server."""
        try:
            response = self._make_request('/manage/get_games_data', method='get', timeout=30)
            response.raise_for_status()
            logger.debug(f"Server response: {response.json()}")

            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('application/json'):
                logger.error(f"Unexpected content type: {content_type}")
                raise ValueError("Server returned non-JSON response")

            data = response.json()
            games = data.get("games_list", [])
            logger.info(f"Retrieved {len(games)} games from server")
            return games

        except requests.exceptions.Timeout:
            logger.error("Request to get_games_data timed out")
            raise Exception("Request timeout — server not responding")
        except requests.exceptions.ConnectionError:
            logger.error("Connection error when requesting get_games_data")
            raise Exception("Failed to connect to server")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            raise Exception(f"Server error: {e.response.status_code}")
        except ValueError as e:
            logger.error(f"JSON decode error: {e}")
            raise Exception("Invalid response format from server")
        except Exception as e:
            logger.error(f"Unexpected error in get_games_data: {e}", exc_info=True)
            raise Exception(f"Unknown error: {e}")

    async def get_games_images(self, games_list: list, steam: bool = False):
        """Download game cover images."""
        for game_name in games_list:
            image_path = f"UI/resources/{game_name}.jpg"
            if os.path.exists(image_path):
                logger.debug(f"Image already exists for game '{game_name}', skipping")
                continue

            try:
                if steam:
                    image_url = self._get_steam_cover_url(game_name)
                    if not image_url:
                        logger.warning(f"No Steam cover found for game '{game_name}'")
                        continue
                    response = requests.get(image_url, timeout=30)
                else:
                    response = self._make_request(
                        f'/files/get_image/{game_name}',
                        method="get",
                        timeout=30
                    )

                if response.status_code == 200:
                    os.makedirs("UI/resources", exist_ok=True)
                    with open(image_path, "wb") as image_file:
                        image_file.write(response.content)
                    logger.info(f"Cover image saved for game '{game_name}'")
                else:
                    logger.warning(f"Image download failed for '{game_name}': HTTP {response.status_code}")

            except Exception as e:
                logger.error(f"Error downloading image for game '{game_name}': {e}", exc_info=True)

    def _get_steam_cover_url(self, game_name: str) -> Optional[str]:
        """Fetch Steam cover image URL."""
        search_url = f"https://store.steampowered.com/api/storesearch/?term={game_name}&l=english&cc=US"
        try:
            response = requests.get(search_url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get('items'):
                app_id = data['items'][0]['id']
                cover_url = f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/header.jpg"
                return cover_url
            return None
        except Exception as e:
            logger.error(f"Steam API error for game '{game_name}': {e}", exc_info=True)
            return None

    async def get_backups_data(self) -> Dict[str, Any]:
        """Get backup metadata from server."""
        try:
            response = self._make_request("/files/get_backups_data", method='get')
            data = response.json()
            logger.debug("Backups metadata retrieved successfully")
            logger.debug(f"Server response: {response.json()}")
            return data
        except Exception as e:
            logger.error(f"Failed to retrieve backups data: {e}", exc_info=True)
            return {}

    async def restore_backup(self, game_name: str, backup_name: str) -> int|None:
        """Restore a specific backup."""
        try:
            response = self._make_request(
                "/files/restore_backup",
                method="post",
                json={"game_name": game_name, "backup_name": backup_name}
            )

            logger.debug(f"Server response: {response.json()}")
            if response.status_code == 200:
                logger.info(f"Backup '{backup_name}' for game '{game_name}' restored successfully")
                return response.status_code
            else:
                logger.error(f"Backup restore failed: {response.status_code} {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error restoring backup '{backup_name}' for game '{game_name}': {e}", exc_info=True)
            return None

    async def delete_backup(self, game_name: str, backup_name: str) -> int|None:
        """Delete a backup on server."""
        try:
            response = self._make_request(
                "/files/delete_backup",
                method="delete",
                json={"game_name": game_name, "backup_name": backup_name}
            )
            logger.debug(f"Server response: {response.json()}")
            if response.status_code == 200:
                logger.info(f"Backup '{backup_name}' for game '{game_name}' deleted")
                return response.status_code
            elif response.status_code == 204:
                logger.warning(f"Backup '{backup_name}' not found on server")
                return response.status_code
            else:
                logger.error(f"Unexpected status when deleting backup: {response.status_code}")
                return response.status_code
        except Exception as e:
            logger.error(f"Error deleting backup '{backup_name}' for game '{game_name}': {e}", exc_info=True)
            return None

    async def test_token(self) -> bool:
        """Validate API token."""
        try:
            response = self._make_request('/manage/check_x_token', method='get')
            if response.status_code == 200 and response.json().get('token_status') is True:
                logger.info("API token is valid")
                return response.status_code
            else:
                logger.warning("API token is invalid or expired")
                return response.status_code
        except Exception as e:
            logger.error(f"Token validation failed: {e}", exc_info=True)
            return None

    async def check_server_health(self, host_for_check: Optional[str] = None) -> bool:
        """Check if server is alive."""
        url = f"{host_for_check or self.host}/manage/health"
        try:
            response = requests.get(url, timeout=5)
            is_healthy = response.status_code == 200
            if is_healthy:
                logger.debug("Server health check passed")
            else:
                logger.warning(f"Server health check failed: HTTP {response.status_code}")
            return is_healthy
        except requests.exceptions.RequestException as e:
            logger.error(f"Server health check failed: {e}")
            return False
