"""
Authentication and user management module for Papers4AI.
Handles user accounts, sessions, and password management.
"""

import json
import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from werkzeug.security import generate_password_hash, check_password_hash


class AuthManager:
    """Manages user authentication and sessions."""

    def __init__(self, users_file: Path, sessions_file: Path, session_lifetime_days: int = 7):
        """
        Initialize the authentication manager.

        Args:
            users_file: Path to users.json
            sessions_file: Path to sessions.json
            session_lifetime_days: Number of days before sessions expire
        """
        self.users_file = users_file
        self.sessions_file = sessions_file
        self.session_lifetime_days = session_lifetime_days

        # Ensure files exist
        self._initialize_files()

    def _initialize_files(self):
        """Create data files if they don't exist and create default admin."""
        # Create users file
        if not self.users_file.exists():
            users_data = {
                "users": [],
                "metadata": {
                    "version": "1.0",
                    "last_updated": datetime.utcnow().isoformat() + "Z"
                }
            }
            self.users_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(users_data, f, indent=2, ensure_ascii=False)

        # Create sessions file
        if not self.sessions_file.exists():
            sessions_data = {
                "sessions": [],
                "metadata": {
                    "version": "1.0",
                    "last_updated": datetime.utcnow().isoformat() + "Z"
                }
            }
            self.sessions_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(sessions_data, f, indent=2, ensure_ascii=False)

        # Create default admin if no users exist
        users_data = self._load_users()
        if not users_data["users"]:
            admin_user = {
                "id": f"user_{int(time.time() * 1000)}",
                "username": "admin",
                "email": "admin@localhost",
                "password_hash": generate_password_hash("admin123", method='pbkdf2:sha256'),
                "role": "admin",
                "status": "approved",
                "created_at": datetime.utcnow().isoformat() + "Z",
                "approved_at": datetime.utcnow().isoformat() + "Z",
                "approved_by": "system"
            }
            users_data["users"].append(admin_user)
            users_data["metadata"]["last_updated"] = datetime.utcnow().isoformat() + "Z"
            self._save_users(users_data)
            print("==> Default admin created: username='admin', password='admin123'")
            print("    Please change the password after first login!")

    def _load_users(self) -> Dict:
        """Load users from JSON file."""
        with open(self.users_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_users(self, users_data: Dict):
        """Save users to JSON file."""
        users_data["metadata"]["last_updated"] = datetime.utcnow().isoformat() + "Z"
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, indent=2, ensure_ascii=False)

    def _load_sessions(self) -> Dict:
        """Load sessions from JSON file."""
        with open(self.sessions_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_sessions(self, sessions_data: Dict):
        """Save sessions to JSON file."""
        sessions_data["metadata"]["last_updated"] = datetime.utcnow().isoformat() + "Z"
        with open(self.sessions_file, 'w', encoding='utf-8') as f:
            json.dump(sessions_data, f, indent=2, ensure_ascii=False)

    def create_user(self, username: str, email: str, password: str, role: str = "user") -> Dict:
        """
        Create a new user account with pending status.

        Args:
            username: Unique username
            email: User email address
            password: Plain text password (will be hashed)
            role: User role (default: "user")

        Returns:
            Created user object (without password hash)

        Raises:
            ValueError: If username or email already exists
        """
        users_data = self._load_users()

        # Check if username already exists
        if any(u["username"].lower() == username.lower() for u in users_data["users"]):
            raise ValueError("Username already exists")

        # Check if email already exists
        if any(u["email"].lower() == email.lower() for u in users_data["users"]):
            raise ValueError("Email already exists")

        # Create new user
        new_user = {
            "id": f"user_{int(time.time() * 1000)}",
            "username": username,
            "email": email,
            "password_hash": generate_password_hash(password, method='pbkdf2:sha256'),
            "role": role,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat() + "Z"
        }

        users_data["users"].append(new_user)
        self._save_users(users_data)

        # Return user without password hash
        user_copy = new_user.copy()
        del user_copy["password_hash"]
        return user_copy

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username (case-insensitive)."""
        users_data = self._load_users()
        for user in users_data["users"]:
            if user["username"].lower() == username.lower():
                return user
        return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID."""
        users_data = self._load_users()
        for user in users_data["users"]:
            if user["id"] == user_id:
                # Return copy without password hash
                user_copy = user.copy()
                if "password_hash" in user_copy:
                    del user_copy["password_hash"]
                return user_copy
        return None

    def verify_password(self, username: str, password: str) -> Optional[Dict]:
        """
        Verify username and password.

        Returns:
            User object (without password hash) if valid, None otherwise
        """
        user = self.get_user_by_username(username)
        if not user:
            return None

        if not check_password_hash(user["password_hash"], password):
            return None

        # Return user without password hash
        user_copy = user.copy()
        del user_copy["password_hash"]
        return user_copy

    def update_user_status(self, user_id: str, status: str, approved_by: str = None) -> bool:
        """
        Update user status (approve or reject).

        Args:
            user_id: User ID to update
            status: New status ("approved" or "rejected")
            approved_by: Username of admin who approved/rejected

        Returns:
            True if successful, False otherwise
        """
        if status not in ["approved", "rejected"]:
            return False

        users_data = self._load_users()

        for user in users_data["users"]:
            if user["id"] == user_id:
                user["status"] = status
                if status == "approved":
                    user["approved_at"] = datetime.utcnow().isoformat() + "Z"
                    if approved_by:
                        user["approved_by"] = approved_by
                elif status == "rejected":
                    user["rejected_at"] = datetime.utcnow().isoformat() + "Z"
                    if approved_by:
                        user["rejected_by"] = approved_by

                self._save_users(users_data)
                return True

        return False

    def list_users(self, status: Optional[str] = None, role: Optional[str] = None) -> List[Dict]:
        """
        List all users, optionally filtered by status or role.

        Args:
            status: Filter by status (pending, approved, rejected)
            role: Filter by role (user, admin)

        Returns:
            List of user objects (without password hashes)
        """
        users_data = self._load_users()
        users = users_data["users"]

        # Apply filters
        if status:
            users = [u for u in users if u.get("status") == status]
        if role:
            users = [u for u in users if u.get("role") == role]

        # Remove password hashes
        result = []
        for user in users:
            user_copy = user.copy()
            if "password_hash" in user_copy:
                del user_copy["password_hash"]
            result.append(user_copy)

        return result

    def create_session(self, user_id: str) -> str:
        """
        Create a new session for a user.

        Args:
            user_id: User ID

        Returns:
            Session token
        """
        # Generate secure random token
        token = secrets.token_urlsafe(32)

        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(days=self.session_lifetime_days)

        # Create session
        session = {
            "token": token,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "expires_at": expires_at.isoformat() + "Z"
        }

        sessions_data = self._load_sessions()
        sessions_data["sessions"].append(session)
        self._save_sessions(sessions_data)

        return token

    def get_session(self, token: str) -> Optional[Dict]:
        """
        Get session by token and validate expiration.

        Returns:
            Session object if valid, None if expired or not found
        """
        sessions_data = self._load_sessions()

        for session in sessions_data["sessions"]:
            if session["token"] == token:
                # Check if expired
                expires_at = datetime.fromisoformat(session["expires_at"].replace("Z", ""))
                if datetime.utcnow() > expires_at:
                    # Session expired
                    return None

                return session

        return None

    def delete_session(self, token: str) -> bool:
        """
        Delete a session (logout).

        Returns:
            True if session was found and deleted, False otherwise
        """
        sessions_data = self._load_sessions()

        initial_count = len(sessions_data["sessions"])
        sessions_data["sessions"] = [s for s in sessions_data["sessions"] if s["token"] != token]

        if len(sessions_data["sessions"]) < initial_count:
            self._save_sessions(sessions_data)
            return True

        return False

    def cleanup_expired_sessions(self):
        """Remove expired sessions from storage."""
        sessions_data = self._load_sessions()
        now = datetime.utcnow()

        active_sessions = []
        for session in sessions_data["sessions"]:
            expires_at = datetime.fromisoformat(session["expires_at"].replace("Z", ""))
            if now <= expires_at:
                active_sessions.append(session)

        sessions_data["sessions"] = active_sessions
        self._save_sessions(sessions_data)

        return len(sessions_data["sessions"]) - len(active_sessions)
