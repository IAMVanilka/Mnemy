# Copyright (C) 2025 IAMVanilka
# SPDX-License-Identifier: GPL-3.0-or-later

import datetime
import logging

from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from contextlib import contextmanager

logger = logging.getLogger(__name__)

engine = create_engine('sqlite:///app_database.db', echo=False)

Base = declarative_base()

class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True)
    game_name = Column(String, unique=True)
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
    except IntegrityError:
        raise
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def add_new_game(game_name: str = None, game_path: str = None, saves_path: str = None, image_path: str = None) -> bool:
    if not game_name:
        logger.error("Game name is required but not provided")
        return False

    try:
        with create_session() as session:
            new_game = Game(
                game_name=game_name,
                game_path=game_path,
                saves_path=saves_path,
                image_path=image_path
            )
            session.add(new_game)

        logger.info(
            f"Game '{game_name}' added successfully. Saves path: '{saves_path}', executable path: '{game_path}'"
        )
        return True

    except IntegrityError as e:
        logger.error("Integrity error while adding game '%s': %s", game_name, e)
        return False
    except SQLAlchemyError as e:
        logger.error("Database error while adding game '%s': %s", game_name, e, exc_info=True)
        return False
    except Exception as e:
        logger.critical("Unexpected error while adding game '%s': %s", game_name, e, exc_info=True)
        return False

def delete_game(game_id: int) -> bool:
    if not isinstance(game_id, int) or game_id <= 0:
        logger.error("Invalid game ID for deletion: %s", game_id)
        return False

    try:
        with create_session() as session:
            result = session.query(Game).filter(Game.id == game_id).delete()
            if result == 0:
                logger.warning("Attempted to delete non-existent game with ID %s", game_id)
                return False

        logger.info("Game with ID %s deleted successfully", game_id)
        return True

    except SQLAlchemyError as e:
        logger.error("Database error while deleting game ID %s: %s", game_id, e, exc_info=True)
        return False
    except Exception as e:
        logger.critical("Unexpected error while deleting game ID %s: %s", game_id, e, exc_info=True)
        return False

def update_game(
    game_id: int,
    game_name: str = None,
    saves_path: str = None,
    game_path: str = None,
    image_path: str = None
) -> bool:
    if not isinstance(game_id, int) or game_id <= 0:
        logger.error("Invalid game ID for update: %s", game_id)
        return False

    try:
        with create_session() as session:
            game = session.query(Game).filter(Game.id == game_id).first()
            if not game:
                logger.warning("Game with ID %s not found for update", game_id)
                return False

            updated_fields = []
            if game_name is not None:
                game.game_name = game_name
                updated_fields.append("game_name")
            if saves_path is not None:
                game.saves_path = saves_path
                updated_fields.append("saves_path")
            if game_path is not None:
                game.game_path = game_path
                updated_fields.append("game_path")
            if image_path is not None:
                game.image_path = image_path
                updated_fields.append("image_path")

            if not updated_fields:
                logger.debug("No fields to update for game ID %s", game_id)
                return True

        logger.info("Game ID %s updated: %s", game_id, ", ".join(updated_fields))
        return True

    except (IntegrityError, sqlite3.IntegrityError) as e:
        logger.error("Integrity error while adding game '%s': %s", game_name, e, exc_info=True)
        return False
    except SQLAlchemyError as e:
        logger.error("Database error while updating game ID %s: %s", game_id, e, exc_info=True)
        return False
    except Exception as e:
        logger.critical("Unexpected error while updating game ID %s: %s", game_id, e, exc_info=True)
        return False

def update_sync_time(game_id: int, date: datetime) -> bool:
    if not isinstance(game_id, int) or game_id <= 0:
        logger.error("Invalid game ID for sync time update: %s", game_id)
        return False

    try:
        with create_session() as session:
            game = session.query(Game).filter(Game.id == game_id).first()
            if not game:
                logger.warning("Game with ID %s not found when updating sync time", game_id)
                return False

            game.last_sync_date = date

        logger.debug("Sync time for game ID %s updated to %s", game_id, date)
        return True

    except SQLAlchemyError as e:
        logger.error("Database error while updating sync time for game ID %s: %s", game_id, e, exc_info=True)
        return False
    except Exception as e:
        logger.critical("Unexpected error while updating sync time for game ID %s: %s", game_id, e, exc_info=True)
        return False


def get_all_games():
    try:
        with create_session() as session:
            games = session.query(Game).all()
            return {
                game.id: {
                    "game_name": game.game_name,
                    "game_path": game.game_path,
                    "saves_path": game.saves_path,
                    "image_path": game.image_path,
                    "last_sync_date": game.last_sync_date
                }
                for game in games
            }
    except SQLAlchemyError as e:
        logger.error("Database error while fetching all games", exc_info=True)
        return {}
    except Exception as e:
        logger.critical("Unexpected error while fetching all games", exc_info=True)
        return {}

def get_game_by_name(game_name: str):
    if not game_name or not isinstance(game_name, str):
        logger.error("Invalid game name provided for lookup: %r", game_name)
        return None

    try:
        with create_session() as session:
            game = session.query(Game).filter(Game.game_name == game_name).first()
            if not game:
                logger.debug("Game '%s' not found in database", game_name)
                return None

            return {
                "id": game.id,
                "game_name": game.game_name,
                "saves_path": game.saves_path,
                "last_sync_date": game.last_sync_date
            }
    except SQLAlchemyError as e:
        logger.error("Database error while searching for game '%s'", game_name, exc_info=True)
        return None
    except Exception as e:
        logger.critical("Unexpected error while searching for game '%s'", game_name, exc_info=True)
        return None