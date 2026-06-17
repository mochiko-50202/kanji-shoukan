import json
import os
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "tunecore_config.json"

_cache: dict | None = None


def load() -> dict:
    global _cache
    if _cache is None:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache


def get_artist(artist_id: str) -> dict | None:
    cfg = load()
    for a in cfg["artists"]:
        if a["id"] == artist_id:
            return a
    return None


def get_genres() -> list[str]:
    return load().get("genres", [])


def get_recording_year() -> int:
    return int(os.environ.get("RECORDING_YEAR", "2026"))


def build_copyright(year: int, artist: dict) -> str:
    holder = artist.get("copyright_holder", "")
    return f"© {year} {holder}" if holder else ""


def build_phonogram(year: int, artist: dict) -> str:
    label = artist.get("label_name", "")
    return f"℗ {year} {label}" if label else ""
