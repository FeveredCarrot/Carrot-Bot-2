import sys
import json
import logging
from pathlib import Path

SETTINGS_FILE_PATH = "settings.json"

logger = logging.getLogger("discord")


def load_settings():
    with open(SETTINGS_FILE_PATH, "rb") as settings_file:
        try:
            settings = json.load(settings_file)
            settings["ffmpeg_path"] = Path(settings["ffmpeg_path"])
            settings["download_path"] = Path(settings["download_path"])
            logger.info("Loaded settings")
            return settings
        except json.JSONDecodeError:
            logger.error("Failed to load settings.json. Aborting...")
            sys.exit(1)
