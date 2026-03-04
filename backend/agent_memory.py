"""
Manager for per-user AI agent memory and preferences
Follows the notes_manager.py pattern: module-level file path, initialize(), Load-Modify-Save
"""
import json
import time
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Import fcntl for Unix systems (file locking)
# On Windows, file locking is not used
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

# Will be set by importing module
MEMORY_FILE = None

MAX_CONVERSATION_HISTORY = 20
MAX_CUSTOM_INSTRUCTIONS = 1000


def _default_prefs(user_id: str) -> Dict:
    """Return default preferences for a new user."""
    now = datetime.utcnow().isoformat() + "Z"
    return {
        "user_id": user_id,
        "exclusions": {
            "authors": [],
            "countries": [],
            "affiliations": []
        },
        "defaults": {
            "conferences": [],
            "year_min": None,
            "year_max": None,
            "model": "llama-3.3-70b-versatile"
        },
        "custom_instructions": "",
        "conversation_history": [],
        "created_at": now,
        "updated_at": now
    }


def initialize(memory_file_path: Path):
    """Initialize the agent memory manager with the file path."""
    global MEMORY_FILE
    MEMORY_FILE = memory_file_path

    # Create file if it doesn't exist
    if not MEMORY_FILE.exists():
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        initial_data = {
            "user_preferences": [],
            "metadata": {
                "version": "1.0",
                "last_updated": datetime.utcnow().isoformat() + "Z"
            }
        }
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, indent=2, ensure_ascii=False)


def _load() -> Dict:
    """Load all agent memory data from JSON file."""
    if not MEMORY_FILE or not MEMORY_FILE.exists():
        return {
            "user_preferences": [],
            "metadata": {
                "version": "1.0",
                "last_updated": datetime.utcnow().isoformat() + "Z"
            }
        }

    with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
        if HAS_FCNTL:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
        try:
            data = json.load(f)
        finally:
            if HAS_FCNTL:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    return data


def _save(data: Dict) -> bool:
    """Save agent memory data to JSON file."""
    if not MEMORY_FILE:
        return False

    data["metadata"]["last_updated"] = datetime.utcnow().isoformat() + "Z"

    try:
        with open(MEMORY_FILE, 'r+', encoding='utf-8') as f:
            if HAS_FCNTL:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.seek(0)
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.truncate()
            finally:
                if HAS_FCNTL:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        return True
    except Exception as e:
        print(f"Error saving agent memory: {e}")
        return False


def _find_user_index(data: Dict, user_id: str) -> int:
    """Find the index of a user's preferences in the array. Returns -1 if not found."""
    for i, prefs in enumerate(data["user_preferences"]):
        if prefs.get("user_id") == user_id:
            return i
    return -1


def get_user_prefs(user_id: str) -> Dict:
    """
    Get preferences for a user. Creates defaults if user is new.

    Args:
        user_id: The user's unique identifier

    Returns:
        User preferences dictionary
    """
    data = _load()
    idx = _find_user_index(data, user_id)

    if idx >= 0:
        return data["user_preferences"][idx]

    # New user - create default prefs
    prefs = _default_prefs(user_id)
    data["user_preferences"].append(prefs)
    _save(data)
    return prefs


def update_user_prefs(user_id: str, updates: Dict) -> Dict:
    """
    Merge updates into a user's preferences.

    Args:
        user_id: The user's unique identifier
        updates: Dictionary of fields to update (shallow merge for top-level,
                 deep merge for 'exclusions' and 'defaults')

    Returns:
        Updated user preferences dictionary
    """
    data = _load()
    idx = _find_user_index(data, user_id)

    if idx < 0:
        prefs = _default_prefs(user_id)
        data["user_preferences"].append(prefs)
        idx = len(data["user_preferences"]) - 1

    prefs = data["user_preferences"][idx]

    # Deep merge for nested dicts
    for key, value in updates.items():
        if key in ("user_id", "created_at", "conversation_history"):
            continue  # Protected fields
        if key in ("exclusions", "defaults") and isinstance(value, dict):
            if key not in prefs:
                prefs[key] = {}
            prefs[key].update(value)
        elif key == "custom_instructions" and isinstance(value, str):
            prefs[key] = value[:MAX_CUSTOM_INSTRUCTIONS]
        else:
            prefs[key] = value

    prefs["updated_at"] = datetime.utcnow().isoformat() + "Z"
    data["user_preferences"][idx] = prefs
    _save(data)
    return prefs


def add_exclusion(user_id: str, category: str, value: str) -> bool:
    """
    Add a value to an exclusion list.

    Args:
        user_id: The user's unique identifier
        category: One of 'authors', 'countries', 'affiliations'
        value: The value to exclude

    Returns:
        True if added, False if invalid category or already exists
    """
    valid_categories = ("authors", "countries", "affiliations")
    if category not in valid_categories:
        return False

    data = _load()
    idx = _find_user_index(data, user_id)

    if idx < 0:
        prefs = _default_prefs(user_id)
        data["user_preferences"].append(prefs)
        idx = len(data["user_preferences"]) - 1

    prefs = data["user_preferences"][idx]
    exclusions = prefs.setdefault("exclusions", {})
    category_list = exclusions.setdefault(category, [])

    if value in category_list:
        return False  # Already excluded

    category_list.append(value)
    prefs["updated_at"] = datetime.utcnow().isoformat() + "Z"
    _save(data)
    return True


def remove_exclusion(user_id: str, category: str, value: str) -> bool:
    """
    Remove a value from an exclusion list.

    Args:
        user_id: The user's unique identifier
        category: One of 'authors', 'countries', 'affiliations'
        value: The value to un-exclude

    Returns:
        True if removed, False if not found
    """
    valid_categories = ("authors", "countries", "affiliations")
    if category not in valid_categories:
        return False

    data = _load()
    idx = _find_user_index(data, user_id)

    if idx < 0:
        return False

    prefs = data["user_preferences"][idx]
    category_list = prefs.get("exclusions", {}).get(category, [])

    if value not in category_list:
        return False

    category_list.remove(value)
    prefs["updated_at"] = datetime.utcnow().isoformat() + "Z"
    _save(data)
    return True


def add_conversation_entry(user_id: str, role: str, content: str) -> Dict:
    """
    Append a message to conversation history, capping at MAX_CONVERSATION_HISTORY.

    Args:
        user_id: The user's unique identifier
        role: 'user' or 'assistant'
        content: The message content

    Returns:
        The new conversation entry
    """
    data = _load()
    idx = _find_user_index(data, user_id)

    if idx < 0:
        prefs = _default_prefs(user_id)
        data["user_preferences"].append(prefs)
        idx = len(data["user_preferences"]) - 1

    prefs = data["user_preferences"][idx]
    history = prefs.setdefault("conversation_history", [])

    entry = {
        "id": f"msg_{int(time.time() * 1000)}",
        "role": role,
        "content": content[:2000],  # Cap content length
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    history.append(entry)

    # Cap at max history
    if len(history) > MAX_CONVERSATION_HISTORY:
        prefs["conversation_history"] = history[-MAX_CONVERSATION_HISTORY:]

    prefs["updated_at"] = datetime.utcnow().isoformat() + "Z"
    _save(data)
    return entry


def clear_conversation_history(user_id: str) -> bool:
    """
    Clear all conversation history for a user.

    Args:
        user_id: The user's unique identifier

    Returns:
        True if cleared, False if user not found
    """
    data = _load()
    idx = _find_user_index(data, user_id)

    if idx < 0:
        return False

    data["user_preferences"][idx]["conversation_history"] = []
    data["user_preferences"][idx]["updated_at"] = datetime.utcnow().isoformat() + "Z"
    _save(data)
    return True


def get_conversation_history(user_id: str) -> List[Dict]:
    """
    Get conversation history for context injection.

    Args:
        user_id: The user's unique identifier

    Returns:
        List of conversation entries
    """
    prefs = get_user_prefs(user_id)
    return prefs.get("conversation_history", [])
