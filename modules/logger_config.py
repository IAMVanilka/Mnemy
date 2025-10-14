import logging
import os.path
from datetime import datetime

def setup_logging():
    if not os.path.exists("logs"):
        os.mkdir("logs")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
        handlers=[
            logging.FileHandler(f"logs/mnemy_{datetime.now().date()}.log", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )