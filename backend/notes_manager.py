"""
Manager for author notes data persistence and retrieval
"""
import json
import time
import sys
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
NOTES_FILE = None


def initialize(notes_file_path: Path):
    """Initialize the notes manager with the file path"""
    global NOTES_FILE
    NOTES_FILE = notes_file_path

    # Create file if it doesn't exist
    if not NOTES_FILE.exists():
        NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
        initial_data = {
            "notes": [],
            "metadata": {
                "version": "1.0",
                "last_updated": datetime.utcnow().isoformat() + "Z"
            }
        }
        with open(NOTES_FILE, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, indent=2, ensure_ascii=False)


def load_notes() -> Dict:
    """
    Load all notes from the JSON file with file locking (Unix only)

    Returns:
        Dictionary with notes array and metadata
    """
    if not NOTES_FILE or not NOTES_FILE.exists():
        return {
            "notes": [],
            "metadata": {
                "version": "1.0",
                "last_updated": datetime.utcnow().isoformat() + "Z"
            }
        }

    with open(NOTES_FILE, 'r', encoding='utf-8') as f:
        if HAS_FCNTL:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock for reading
        try:
            data = json.load(f)
        finally:
            if HAS_FCNTL:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    return data


def save_notes(notes_data: Dict) -> bool:
    """
    Save notes to the JSON file with file locking (Unix only)

    Args:
        notes_data: Dictionary containing notes array and metadata

    Returns:
        True if save was successful, False otherwise
    """
    if not NOTES_FILE:
        return False

    # Update metadata timestamp
    notes_data["metadata"]["last_updated"] = datetime.utcnow().isoformat() + "Z"

    try:
        with open(NOTES_FILE, 'r+', encoding='utf-8') as f:
            if HAS_FCNTL:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock for writing
            try:
                f.seek(0)
                json.dump(notes_data, f, indent=2, ensure_ascii=False)
                f.truncate()
            finally:
                if HAS_FCNTL:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        return True
    except Exception as e:
        print(f"Error saving notes: {e}")
        return False


def add_note(author_name: str, content: str, created_by_username: Optional[str] = None) -> Dict:
    """
    Add a new note for an author

    Args:
        author_name: Name of the author
        content: Note content
        created_by_username: Username who created the note (None for anonymous/legacy notes)

    Returns:
        The newly created note object
    """
    notes_data = load_notes()

    # Generate unique note ID using timestamp
    note_id = f"note_{int(time.time() * 1000)}"

    # Create note object
    new_note = {
        "id": note_id,
        "author_name": author_name,
        "content": content.strip(),
        "created_at": datetime.utcnow().isoformat() + "Z",
        "created_by": None,  # Legacy field, kept for compatibility
        "created_by_username": created_by_username,
        "status": "active"
    }

    # Add to notes array
    notes_data["notes"].append(new_note)

    # Save to file
    save_notes(notes_data)

    return new_note


def get_notes_for_author(author_name: str) -> List[Dict]:
    """
    Get all active notes for a specific author

    Args:
        author_name: Name of the author

    Returns:
        List of note objects, sorted by creation date (newest first)
    """
    notes_data = load_notes()

    # Filter notes for this author (active only)
    author_notes = [
        note for note in notes_data["notes"]
        if note.get("author_name") == author_name and note.get("status") == "active"
    ]

    # Sort by creation date (newest first)
    author_notes.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return author_notes


def get_all_notes() -> List[Dict]:
    """
    Get all active notes (for debugging/admin purposes)

    Returns:
        List of all active note objects
    """
    notes_data = load_notes()
    return [note for note in notes_data["notes"] if note.get("status") == "active"]


def get_note_by_id(note_id: str) -> Optional[Dict]:
    """
    Get a specific note by its ID

    Args:
        note_id: The note ID to look up

    Returns:
        The note object if found, None otherwise
    """
    notes_data = load_notes()

    for note in notes_data["notes"]:
        if note.get("id") == note_id and note.get("status") == "active":
            return note

    return None


def update_note(note_id: str, content: str) -> bool:
    """
    Update the content of an existing note

    Args:
        note_id: The note ID to update
        content: New content for the note

    Returns:
        True if successful, False if note not found
    """
    notes_data = load_notes()

    for note in notes_data["notes"]:
        if note.get("id") == note_id and note.get("status") == "active":
            note["content"] = content.strip()
            note["updated_at"] = datetime.utcnow().isoformat() + "Z"
            save_notes(notes_data)
            return True

    return False


def delete_note(note_id: str) -> bool:
    """
    Delete a note (soft delete - sets status to 'deleted')

    Args:
        note_id: The note ID to delete

    Returns:
        True if successful, False if note not found
    """
    notes_data = load_notes()

    for note in notes_data["notes"]:
        if note.get("id") == note_id and note.get("status") == "active":
            note["status"] = "deleted"
            note["deleted_at"] = datetime.utcnow().isoformat() + "Z"
            save_notes(notes_data)
            return True

    return False


def build_author_index() -> Dict[str, List[Dict]]:
    """
    Build an in-memory index of notes by author name
    Useful for performance if we need to look up notes for multiple authors

    Returns:
        Dictionary mapping author names to their notes
    """
    notes_data = load_notes()
    index = {}

    for note in notes_data["notes"]:
        if note.get("status") != "active":
            continue

        author = note.get("author_name")
        if author not in index:
            index[author] = []
        index[author].append(note)

    # Sort each author's notes by date (newest first)
    for author in index:
        index[author].sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return index
