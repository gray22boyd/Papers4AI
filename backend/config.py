"""
Configuration for the Paper Search Engine
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Data paths
DATA_DIR = BASE_DIR / "data"
PAPERS_JSON = DATA_DIR / "papers.json"
PAPERS_CSV = DATA_DIR / "papers.csv"
AUTHOR_NOTES_FILE = DATA_DIR / "author_notes.json"
USERS_FILE = DATA_DIR / "users.json"
SESSIONS_FILE = DATA_DIR / "sessions.json"
AGENT_MEMORY_FILE = DATA_DIR / "agent_memory.json"
CAMPAIGNS_FILE = DATA_DIR / "campaigns.json"

# Server configuration
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", 5000))
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# Search configuration
DEFAULT_LIMIT = 20
MAX_LIMIT = 100
TITLE_WEIGHT = 3  # Weight for title matches
ABSTRACT_WEIGHT = 1  # Weight for abstract matches
PHRASE_MULTIPLIER = 2  # Multiplier for phrase matches

# Author notes configuration
NOTE_MIN_LENGTH = 1
NOTE_MAX_LENGTH = 500

# Authentication configuration
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 30
PASSWORD_MIN_LENGTH = 6
SESSION_LIFETIME_DAYS = 7
