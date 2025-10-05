# Copyright (C) 2025 IAMVanilka
# SPDX-License-Identifier: GPL-3.0-or-later

import datetime
import os
import shutil

from modules.sqls import update_sync_time, add_new_game, get_all_games, get_game_by_name
from modules.API_client import APIClient

def get_utc_time(date: datetime):
    import time
    import datetime
    import pytz

    local_offset = time.timezone if time.daylight == 0 else time.altzone
    local_tz = pytz.FixedOffset(-local_offset // 60)  # в минутах

    last_sync_aware = local_tz.localize(date)
    last_sync_utc = last_sync_aware.astimezone(datetime.timezone.utc)
    return last_sync_utc

async def sync_saves_action(game_name: str, saves_path: str, game_id: int, api_client: APIClient):
    last_sync_date = get_game_by_name(game_name)["last_sync_date"]
    utc_date = get_utc_time(last_sync_date)

    files_data = await api_client.check_files(game_name=game_name, base_dir=saves_path, date=utc_date)
    if files_data != "redirect":
        print("Данные клиента устарели. Обновляю...")
        upload_status = await api_client.upload_files_streaming(saves_path, files_data, game_name)
        update_sync_time(game_id=game_id, date=datetime.datetime.now())
        return upload_status
    else:
        return await download_saves_action(game_name, saves_path, game_id, api_client)

async def download_saves_action(game_name: str, saves_path: str, game_id: int, api_client: APIClient):
    shutil.rmtree(saves_path)
    os.mkdir(saves_path)
    status = await api_client.download_files(game_name, saves_path)
    update_sync_time(game_id=game_id, date=datetime.datetime.now())
    return status

async def delete_from_server_action(game_name: str, delete_backups: bool, api_client: APIClient):
    return await api_client.delete_game(game_name, delete_backups=True if delete_backups else False)

async def update_game_data_on_server_action(game_name: str, new_game_name: str, api_client: APIClient):
    return await api_client.update_game_data(game_name, new_game_name)

async def set_up_games_data(api_client: APIClient):
    games_list = await api_client.get_games_data()
    games_list_local = get_all_games()

    local_game_names = {game_item['game_name'] for game_item in games_list_local.values()}

    new_games_list = [game_name for game_name in games_list if game_name not in local_game_names]
    for game in new_games_list:
        add_new_game(game_name=game['game_name'], image_path=f"UI/resources/{game['game_name']}.jpg")

    await load_games_covers(api_client)

    return True

async def load_games_covers(api_client: APIClient):
    games_data = get_all_games()
    games_data = [game["game_name"] for game in games_data.values()]
    await api_client.get_games_images(games_data, steam=True)

async def get_backups_data_action(api_client: APIClient):
    backups_data = await api_client.get_backups_data()
    return backups_data

async def delete_backup_action(game_name: str, backup_name: str, api_client: APIClient):
    status = await api_client.delete_backup(game_name, backup_name)
    return status

async def restore_backup_action(game_name: str, backup_name: str, api_client: APIClient):
    status = await api_client.restore_backup(game_name, backup_name)
    if status:
        game_data = get_game_by_name(game_name)
        download_status = await api_client.download_files(game_name, game_data["saves_path"])
        return download_status
    else:
        return False
