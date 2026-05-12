"""Leaderboard persistence and management."""

import json
import os

from src.config import LEADERBOARD_FILE, MAX_LEADERBOARD_ENTRIES


def _get_path() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), LEADERBOARD_FILE)


def load_leaderboard() -> list[dict]:
    path = _get_path()
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        try:
            data = json.load(f)
        except (json.JSONDecodeError, ValueError):
            return []
    return sorted(data, key=lambda e: e.get("score", 0), reverse=True)


def save_entry(name: str, score: int, time_sec: float, mode: str, grid_size: int):
    entries = load_leaderboard()
    entries.append({
        "name": name,
        "score": score,
        "time": round(time_sec, 1),
        "mode": mode,
        "grid": grid_size,
    })
    entries = sorted(entries, key=lambda e: e.get("score", 0), reverse=True)
    entries = entries[:MAX_LEADERBOARD_ENTRIES]
    path = _get_path()
    with open(path, "w") as f:
        json.dump(entries, f, indent=2)
