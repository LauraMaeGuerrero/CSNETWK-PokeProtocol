"""Utility functions and constants for PokeProtocol"""
import re
import base64
from typing import Optional

# ----------------------------
# Terminal colors & helpers
# ----------------------------
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"


def color(text: str, col: str) -> str:
    return f"{col}{text}{RESET}"


def emphasize(text: str) -> str:
    return f"{BOLD}{text}{RESET}"


def safe_float(value: Optional[str]) -> float:
    if not value:
        return 0.0
    m = re.search(r'\d+(?:\.\d+)?', str(value))
    return float(m.group()) if m else 0.0


def safe_int(value: Optional[str]) -> int:
    if not value:
        return 0
    m = re.search(r'\d+', str(value))
    return int(m.group()) if m else 0


def validate_sticker_data(sticker_data: str) -> bool:
    """Validate base64 sticker data size"""
    try:
        decoded = base64.b64decode(sticker_data)
        return len(decoded) <= 10 * 1024 * 1024  # 10MB limit
    except Exception:
        return False