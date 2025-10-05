# Copyright (C) 2025 IAMVanilka
# SPDX-License-Identifier: GPL-3.0-or-later

import datetime

from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

from contextlib import contextmanager

engine = create_engine('sqlite:///app_database.db', echo=False)

Base = declarative_base()

class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True)
    game_name = Column(String)
    saves_path = Column(String)
    game_path = Column(String)
    image_path = Column(String)
    last_sync_date = Column(DateTime, default=None)

    def __str__(self):
        return (f"Game(id={self.id}, name='{self.game_name}', saves_path='{self.saves_path}',"
                f" game_path='{self.game_path}', image_path='{self.image_path}', last_sync_date='{self.last_sync_date}')")

    def __repr__(self):
        return f"<Game(id={self.id}, name='{self.game_name}')>"

Base.metadata.create_all(engine)

@contextmanager
def create_session():
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def add_new_game(game_name: str = None, game_path: str = None, saves_path: str = None, image_path: str = None):
    with create_session() as session:
        new_game = Game(game_name=game_name,
                         game_path=game_path, saves_path=saves_path,
                         image_path=image_path)

        session.add(new_game)

        print(f"Игра '{game_name}' добавлена! Путь к сохранениям: '{saves_path}',"
              f"\nпуть к exe файлу: '{game_path}'")

def delete_game(game_id: int):
    with create_session() as session:
        session.query(Game).filter(Game.id==game_id).delete()


def update_game(game_id: int,
                game_name: str = None,
                saves_path: str = None,
                game_path: str = None,
                image_path: str = None) -> bool:
    """
    Изменяет данные игры по ID

    Args:
        game_id: ID игры для изменения
        game_name: Новое имя игры (опционально)
        saves_path: Новый путь к сохранениям (опционально)
        game_path: Новый путь к игре (опционально)
        image_path: Новый путь к изображению (опционально)
    """
    with create_session() as session:
        game = session.query(Game).filter(Game.id == game_id).first()

        if not game:
            print(f"Игра с ID {game_id} не найдена")
            return False

        # Обновляем только переданные поля
        if game_name is not None:
            game.game_name = game_name
        if saves_path is not None:
            game.saves_path = saves_path
        if game_path is not None:
            game.game_path = game_path
        if image_path is not None:
            game.image_path = image_path

        print(f"Игра с ID {game_id} успешно обновлена")

        return True

def update_sync_time(game_id: int, date: datetime.datetime):
    with create_session() as session:
        game = session.query(Game).filter(Game.id == game_id).first()

        if not game:
            print(f"Игра с ID {game_id} не найдена")
            return False

        game.last_sync_date = date

        return True


def get_all_games():
    with create_session() as session:
        games_data = session.query(Game).all()

        return {
            game.id: {
                "game_name": game.game_name,
                "game_path": game.game_path,
                "saves_path": game.saves_path,
                "image_path": game.image_path,
                "last_sync_date": game.last_sync_date
            }
        for game in games_data }

def get_game_by_name(game_name: str):
    with create_session() as session:
        game = session.query(Game).filter(Game.game_name == game_name).first()
        if not game:
            print(f"Игра '{game_name}' не найдена!")
            return False

        return {
            "id": game.id,
            "game_name": game.game_name,
            "saves_path": game.saves_path,
            "last_sync_date": game.last_sync_date
        }