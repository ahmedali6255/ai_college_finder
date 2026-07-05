"""
utils.py
--------
Shared constants, the StudentProfile data model, input validation helpers,
and a tiny local config store for the Gemini API key.

Keeping all of this in one place avoids duplicating logic between gui.py,
ai.py and pdf_export.py.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


# ---------------------------------------------------------------------------
# App-wide constants
# ---------------------------------------------------------------------------

APP_NAME = "AI College Finder"
APP_VERSION = "1.0.0"

DEGREE_LEVELS = ["Bachelor's", "Master's", "PhD"]
BUDGET_LEVELS = ["Low", "Medium", "High"]

# A short curated list to prime the country dropdown. The Universities API
# accepts any country name as free text, so the combobox stays editable.
COMMON_COUNTRIES = [
    "Pakistan", "United States", "United Kingdom", "Canada", "Germany",
    "Australia", "China", "Turkey", "Malaysia", "South Korea",
    "United Arab Emirates", "Netherlands", "Sweden", "Japan", "France",
]

# Config file lives in the user's home directory so the API key survives
# across app restarts without being bundled into the source tree.
CONFIG_DIR = Path.home() / ".ai_college_finder"
CONFIG_FILE = CONFIG_DIR / "config.json"
PROFILE_FILE = CONFIG_DIR / "profile.json"


# ---------------------------------------------------------------------------
# Color / style palette (used by gui.py to keep visuals consistent)
# ---------------------------------------------------------------------------

class Theme:
    BG_DARK = "#1a1d24"
    BG_SIDEBAR = "#15171d"
    BG_CARD = "#232733"
    BG_CARD_HOVER = "#2a2f3d"
    ACCENT = "#3ba3ff"
    ACCENT_HOVER = "#2f8ce0"
    ACCENT_SOFT = "#25314a"
    SUCCESS = "#3ed598"
    WARNING = "#f5a623"
    DANGER = "#ef5350"
    TEXT_PRIMARY = "#e8eaf0"
    TEXT_SECONDARY = "#8b93a7"
    BORDER = "#2d3140"

    FONT_FAMILY = "Segoe UI"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class StudentProfile:
    full_name: str = ""
    gpa: str = ""
    major: str = ""
    country: str = ""
    degree_level: str = DEGREE_LEVELS[0]
    budget: str = BUDGET_LEVELS[1]
    interests: str = ""

    def is_complete(self) -> bool:
        return bool(self.full_name and self.gpa and self.major and self.country)

    def as_dict(self) -> dict:
        return {
            "Full Name": self.full_name,
            "GPA": self.gpa,
            "Intended Major": self.major,
            "Preferred Country": self.country,
            "Degree Level": self.degree_level,
            "Budget": self.budget,
            "Interests": self.interests or "Not specified",
        }


@dataclass
class University:
    name: str
    country: str
    website: str = ""
    state_province: str = ""

    @property
    def display_name(self) -> str:
        return f"{self.name} ({self.country})"


@dataclass
class AppState:
    """Central in-memory state shared across GUI pages."""
    profile: StudentProfile = field(default_factory=StudentProfile)
    search_results: List[University] = field(default_factory=list)
    favorites: List[University] = field(default_factory=list)
    last_recommendation: str = ""
    last_comparison: str = ""


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_profile(profile: StudentProfile) -> tuple[bool, str]:
    """Validate the student profile fields. Returns (is_valid, message)."""
    if not profile.full_name.strip():
        return False, "Please enter your full name."

    if not profile.gpa.strip():
        return False, "Please enter your GPA."
    try:
        gpa_value = float(profile.gpa)
        if not (0.0 <= gpa_value <= 4.0):
            return False, "GPA must be a number between 0.0 and 4.0."
    except ValueError:
        return False, "GPA must be a valid number (e.g. 3.5)."

    if not profile.major.strip():
        return False, "Please enter your intended major."

    if not profile.country.strip():
        return False, "Please enter your preferred country."

    return True, "Profile looks good."


def validate_search_query(country: str, name: str) -> tuple[bool, str]:
    if not country.strip() and not name.strip():
        return False, "Enter a country and/or a university name to search."
    return True, ""


# ---------------------------------------------------------------------------
# Local config store (Gemini API key)
# ---------------------------------------------------------------------------

def load_api_key() -> str:
    """Load the saved Gemini API key, falling back to the environment
    variable GEMINI_API_KEY if no local config exists."""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                key = data.get("gemini_api_key", "")
                if key:
                    return key
    except (json.JSONDecodeError, OSError):
        pass
    return os.environ.get("GEMINI_API_KEY", "")


def save_api_key(api_key: str) -> None:
    """Persist the Gemini API key locally so the user only enters it once."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"gemini_api_key": api_key.strip()}, f, indent=2)
def save_profile(profile: "StudentProfile") -> None:
    """Persist the student profile to a local JSON file so it survives
    app restarts / browser refreshes."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "full_name": profile.full_name,
            "gpa": profile.gpa,
            "major": profile.major,
            "country": profile.country,
            "degree_level": profile.degree_level,
            "budget": profile.budget,
            "interests": profile.interests,
        }, f, indent=2)


def load_profile() -> "StudentProfile":
    """Load the previously saved student profile, if one exists.
    Returns a blank StudentProfile if no saved file is found."""
    try:
        if PROFILE_FILE.exists():
            with open(PROFILE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return StudentProfile(
                    full_name=data.get("full_name", ""),
                    gpa=data.get("gpa", ""),
                    major=data.get("major", ""),
                    country=data.get("country", ""),
                    degree_level=data.get("degree_level", DEGREE_LEVELS[0]),
                    budget=data.get("budget", BUDGET_LEVELS[1]),
                    interests=data.get("interests", ""),
                )
    except (json.JSONDecodeError, OSError):
        pass
    return StudentProfile()        


def truncate(text: str, max_len: int = 60) -> str:
    text = text or ""
    return text if len(text) <= max_len else text[: max_len - 1] + "…"
