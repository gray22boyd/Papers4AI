"""
Paper Search Engine - Flask REST API
====================================
Backend API for searching academic papers.
Serves both API and frontend in production.
"""

import os
import json
import re
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from config import (
    DEFAULT_LIMIT, MAX_LIMIT, BASE_DIR, DATA_DIR, AUTHOR_NOTES_FILE,
    NOTE_MIN_LENGTH, NOTE_MAX_LENGTH, USERS_FILE, SESSIONS_FILE,
    USERNAME_MIN_LENGTH, USERNAME_MAX_LENGTH, PASSWORD_MIN_LENGTH, SESSION_LIFETIME_DAYS,
    AGENT_MEMORY_FILE, CAMPAIGNS_FILE
)
from search_engine import search_engine
import notes_manager
import agent_memory
from auth_manager import AuthManager
from ai_agent_groq_v2 import GroqAIAgentV2 as GroqAIAgent
import semantic_search
import author_expertise
import intelligent_agent
import candidate_enrichment_v2 as candidate_enrichment
import campaign_manager

# File to store link suggestions
SUGGESTIONS_FILE = DATA_DIR / "link_suggestions.json"

# Initialize Flask app
app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# Enable gzip compression
Compress(app)

# Rate limiting (prevent abuse)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# Get port from environment (Railway sets this)
PORT = int(os.environ.get("PORT", 5000))

# Initialize auth manager
auth_manager = AuthManager(USERS_FILE, SESSIONS_FILE, SESSION_LIFETIME_DAYS)

# Initialize AI agent with Groq
# API key is loaded from GROQ_API_KEY environment variable (.env file)
try:
    groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    ai_agent = GroqAIAgent(model_name=groq_model)
    print(f"[OK] AI Agent initialized with Groq ({groq_model})")
except Exception as e:
    print(f"[WARNING] AI Agent failed to initialize: {e}")
    print("  AI features will be disabled. Check your GROQ_API_KEY in .env file")
    ai_agent = None


def auth_required(f):
    """Decorator to require authentication for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({"error": "Missing or invalid authorization header"}), 401

        token = auth_header.replace('Bearer ', '')

        # Validate session
        session = auth_manager.get_session(token)
        if not session:
            return jsonify({"error": "Invalid or expired session"}), 401

        # Get user data
        user = auth_manager.get_user_by_id(session['user_id'])
        if not user:
            return jsonify({"error": "User not found"}), 401

        if user.get('status') != 'approved':
            return jsonify({"error": "User account not approved"}), 403

        # Pass user data to the route function
        return f(user, *args, **kwargs)

    return decorated_function


@app.before_request
def ensure_data_loaded():
    """Ensure paper data is loaded before handling requests."""
    if not search_engine._loaded:
        search_engine.load_data()

    # Always initialize notes manager if not already initialized
    if notes_manager.NOTES_FILE is None:
        notes_manager.initialize(AUTHOR_NOTES_FILE)

    # Initialize agent memory manager if not already initialized
    if agent_memory.MEMORY_FILE is None:
        agent_memory.initialize(AGENT_MEMORY_FILE)

    # Initialize intelligent search modules if not already initialized
    if semantic_search.semantic_engine is None:
        semantic_search.initialize(DATA_DIR)

    if candidate_enrichment.candidate_enricher is None:
        candidate_enrichment.initialize()

    if intelligent_agent.intelligent_agent is None:
        intelligent_agent.initialize(
            search_engine,
            semantic_search.semantic_engine,
            author_expertise.expertise_analyzer
        )

    # Initialize campaign manager if not already initialized
    if campaign_manager.campaign_manager is None:
        campaign_manager.initialize(CAMPAIGNS_FILE)


# Authentication decorators
def require_auth(f):
    """Decorator to require authentication for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({"error": "Unauthorized - No token provided"}), 401

        session = auth_manager.get_session(token)
        if not session:
            return jsonify({"error": "Unauthorized - Invalid or expired token"}), 401

        # Get user and attach to request
        user = auth_manager.get_user_by_id(session['user_id'])
        if not user:
            return jsonify({"error": "Unauthorized - User not found"}), 401

        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function


def require_admin(f):
    """Decorator to require admin role for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({"error": "Unauthorized - No token provided"}), 401

        session = auth_manager.get_session(token)
        if not session:
            return jsonify({"error": "Unauthorized - Invalid or expired token"}), 401

        user = auth_manager.get_user_by_id(session['user_id'])
        if not user:
            return jsonify({"error": "Unauthorized - User not found"}), 401

        if user.get('role') != 'admin':
            return jsonify({"error": "Forbidden - Admin access required"}), 403

        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function


# Authentication endpoints
@app.route("/api/auth/register", methods=["POST"])
@limiter.limit("3 per hour")
def register():
    """Register a new user account (requires admin approval)."""
    try:
        data = request.get_json() or {}

        username = data.get("username", "").strip()
        email = data.get("email", "").strip()
        password = data.get("password", "")

        # Validate username
        if not username:
            return jsonify({"error": "Username is required"}), 400
        if len(username) < USERNAME_MIN_LENGTH or len(username) > USERNAME_MAX_LENGTH:
            return jsonify({"error": f"Username must be {USERNAME_MIN_LENGTH}-{USERNAME_MAX_LENGTH} characters"}), 400
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return jsonify({"error": "Username can only contain letters, numbers, and underscores"}), 400

        # Validate email
        if not email:
            return jsonify({"error": "Email is required"}), 400
        if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email):
            return jsonify({"error": "Invalid email format"}), 400

        # Validate password
        if not password:
            return jsonify({"error": "Password is required"}), 400
        if len(password) < PASSWORD_MIN_LENGTH:
            return jsonify({"error": f"Password must be at least {PASSWORD_MIN_LENGTH} characters"}), 400

        # Create user
        try:
            user = auth_manager.create_user(username, email, password)
            return jsonify({
                "success": True,
                "message": "Account created! Awaiting admin approval.",
                "user": user
            }), 201
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/auth/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    """Login with username and password."""
    try:
        data = request.get_json() or {}

        username = data.get("username", "").strip()
        password = data.get("password", "")

        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400

        # Verify credentials
        user = auth_manager.verify_password(username, password)
        if not user:
            return jsonify({"error": "Invalid username or password"}), 401

        # Check if account is approved
        if user.get("status") != "approved":
            if user.get("status") == "pending":
                return jsonify({"error": "Account pending admin approval"}), 403
            elif user.get("status") == "rejected":
                return jsonify({"error": "Account has been rejected"}), 403
            else:
                return jsonify({"error": "Account not active"}), 403

        # Create session
        token = auth_manager.create_session(user["id"])

        return jsonify({
            "success": True,
            "token": token,
            "user": user
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/auth/logout", methods=["POST"])
@require_auth
def logout():
    """Logout (invalidate session token)."""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        auth_manager.delete_session(token)
        return jsonify({"success": True, "message": "Logged out successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/auth/me", methods=["GET"])
@require_auth
def get_current_user():
    """Get current logged-in user information."""
    return jsonify(request.current_user)


# Admin endpoints
@app.route("/api/admin/users", methods=["GET"])
@require_admin
def list_users():
    """List all users, optionally filtered by status."""
    try:
        status = request.args.get("status")
        users = auth_manager.list_users(status=status)
        return jsonify(users)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/admin/users/<string:user_id>/approve", methods=["POST"])
@require_admin
def approve_user(user_id: str):
    """Approve a pending user account."""
    try:
        approved_by = request.current_user.get("username")
        success = auth_manager.update_user_status(user_id, "approved", approved_by)

        if success:
            return jsonify({"success": True, "message": "User approved successfully"})
        else:
            return jsonify({"error": "User not found or could not be approved"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/admin/users/<string:user_id>/reject", methods=["POST"])
@require_admin
def reject_user(user_id: str):
    """Reject a pending user account."""
    try:
        rejected_by = request.current_user.get("username")
        success = auth_manager.update_user_status(user_id, "rejected", rejected_by)

        if success:
            return jsonify({"success": True, "message": "User rejected successfully"})
        else:
            return jsonify({"error": "User not found or could not be rejected"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Serve frontend
@app.route("/")
def serve_frontend():
    """Serve the frontend HTML."""
    return send_from_directory(app.static_folder, 'index.html')


@app.route("/api/search", methods=["POST"])
@limiter.limit("100 per minute")  # Allow 100 searches per minute per IP
def search():
    """Search papers by query with Boolean operators."""
    try:
        data = request.get_json() or {}

        query = data.get("query", "").strip()
        conferences = data.get("conferences")
        year_min = data.get("year_min")
        year_max = data.get("year_max")
        author = data.get("author", "").strip()
        countries_param = data.get("countries")
        limit = min(int(data.get("limit", DEFAULT_LIMIT)), MAX_LIMIT)
        offset = max(int(data.get("offset", 0)), 0)

        if conferences and not isinstance(conferences, list):
            conferences = [conferences]
        
        if countries_param and not isinstance(countries_param, list):
            countries_param = [countries_param]

        results = search_engine.search(
            query=query,
            conferences=conferences,
            year_min=year_min,
            year_max=year_max,
            author=author if author else None,
            countries=countries_param,
            limit=limit,
            offset=offset,
        )

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/stats", methods=["GET"])
def stats():
    """Get database statistics."""
    return jsonify(search_engine.get_stats())


@app.route("/api/conferences", methods=["GET"])
def conferences():
    """Get list of all conferences with paper counts."""
    return jsonify(search_engine.get_conferences())


@app.route("/api/countries", methods=["GET"])
def countries():
    """Get list of all countries with paper counts."""
    return jsonify(search_engine.get_countries())


@app.route("/api/paper/<int:paper_id>", methods=["GET"])
def get_paper(paper_id: int):
    """Get a single paper by ID."""
    paper = search_engine.get_paper(paper_id)
    if paper:
        return jsonify(paper)
    return jsonify({"error": "Paper not found"}), 404


@app.route("/api/authors", methods=["GET"])
def search_authors():
    """Search for authors by name."""
    query = request.args.get("q", "").strip()
    limit = min(int(request.args.get("limit", 20)), 100)
    offset = max(int(request.args.get("offset", 0)), 0)
    
    if not query:
        return jsonify({"error": "Query parameter 'q' is required"}), 400
    
    results = search_engine.search_authors(query, limit=limit, offset=offset)
    return jsonify(results)


# Notes endpoints - use string converter (not path) to avoid matching slashes
@app.route("/api/author/<string:author_name>/notes", methods=["GET"])
def get_author_notes(author_name: str):
    """
    Get all notes for a specific author.

    Returns a list of notes with their content, timestamps, and metadata.
    """
    try:
        # Verify author exists in database
        profile = search_engine.get_author_profile(author_name)
        if not profile:
            return jsonify({"error": "Author not found"}), 404

        # Get notes for this author
        notes = notes_manager.get_notes_for_author(author_name)

        # Return note objects with username
        simplified_notes = [
            {
                "id": note["id"],
                "content": note["content"],
                "created_at": note["created_at"],
                "created_by_username": note.get("created_by_username")
            }
            for note in notes
        ]

        return jsonify({
            "author_name": author_name,
            "notes": simplified_notes,
            "total": len(simplified_notes)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/author/<string:author_name>/notes", methods=["POST"])
@require_auth
@limiter.limit("5 per minute")  # Stricter limit for note creation
def add_author_note(author_name: str):
    """
    Add a new note for an author.

    Accepts JSON with 'content' field containing the note text.
    Notes are visible to all users and persist across sessions.
    Requires authentication.
    """
    try:
        data = request.get_json() or {}

        content = data.get("content", "").strip()

        # Validate input
        if not content:
            return jsonify({"error": "Note content is required"}), 400

        if len(content) < NOTE_MIN_LENGTH:
            return jsonify({"error": f"Note content must be at least {NOTE_MIN_LENGTH} characters"}), 400

        if len(content) > NOTE_MAX_LENGTH:
            return jsonify({"error": f"Note content must be no more than {NOTE_MAX_LENGTH} characters"}), 400

        # Verify author exists in database
        profile = search_engine.get_author_profile(author_name)
        if not profile:
            return jsonify({"error": "Author not found"}), 404

        # Add the note with username
        username = request.current_user.get("username")
        new_note = notes_manager.add_note(author_name, content, username)

        # Return note object
        return jsonify({
            "success": True,
            "note": {
                "id": new_note["id"],
                "content": new_note["content"],
                "created_at": new_note["created_at"],
                "created_by_username": new_note.get("created_by_username")
            },
            "message": "Note added successfully"
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/notes/<string:note_id>", methods=["PUT"])
@require_auth
@limiter.limit("10 per minute")
def edit_note(note_id: str):
    """
    Edit an existing note.

    Users can only edit their own notes.
    """
    try:
        data = request.get_json() or {}
        content = data.get("content", "").strip()

        # Validate input
        if not content:
            return jsonify({"error": "Note content is required"}), 400

        if len(content) < NOTE_MIN_LENGTH:
            return jsonify({"error": f"Note content must be at least {NOTE_MIN_LENGTH} characters"}), 400

        if len(content) > NOTE_MAX_LENGTH:
            return jsonify({"error": f"Note content must be no more than {NOTE_MAX_LENGTH} characters"}), 400

        # Get the note to verify ownership
        note = notes_manager.get_note_by_id(note_id)
        if not note:
            return jsonify({"error": "Note not found"}), 404

        # Verify ownership
        username = request.current_user.get("username")
        if note.get("created_by_username") != username:
            return jsonify({"error": "You can only edit your own notes"}), 403

        # Update the note
        success = notes_manager.update_note(note_id, content)
        if success:
            return jsonify({
                "success": True,
                "message": "Note updated successfully"
            })
        else:
            return jsonify({"error": "Failed to update note"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/notes/<string:note_id>", methods=["DELETE"])
@require_auth
@limiter.limit("10 per minute")
def delete_note(note_id: str):
    """
    Delete a note.

    Users can only delete their own notes.
    """
    try:
        # Get the note to verify ownership
        note = notes_manager.get_note_by_id(note_id)
        if not note:
            return jsonify({"error": "Note not found"}), 404

        # Verify ownership
        username = request.current_user.get("username")
        if note.get("created_by_username") != username:
            return jsonify({"error": "You can only delete your own notes"}), 403

        # Delete the note
        success = notes_manager.delete_note(note_id)
        if success:
            return jsonify({
                "success": True,
                "message": "Note deleted successfully"
            })
        else:
            return jsonify({"error": "Failed to delete note"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/author/<string:author_name>/export", methods=["GET"])
def export_author_papers(author_name: str):
    """Export author's papers as CSV."""
    profile = search_engine.get_author_profile(author_name)
    if not profile:
        return jsonify({"error": "Author not found"}), 404

    # Build CSV
    import io
    import csv

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Title", "Year", "Conference", "First Author", "All Authors", "URL"])

    for paper in profile["papers"]:
        writer.writerow([
            paper["title"],
            paper["year"],
            paper["conference"],
            "Yes" if paper["is_first_author"] else "No",
            paper["authors"],
            paper["url"],
        ])

    csv_content = output.getvalue()

    # Return as downloadable CSV
    from flask import Response
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={author_name.replace(' ', '_')}_papers.csv"}
    )


@app.route("/api/author/<string:author_name>", methods=["GET"])
def get_author_profile(author_name: str):
    """Get full profile for an author."""
    profile = search_engine.get_author_profile(author_name)
    if profile:
        return jsonify(profile)
    return jsonify({"error": "Author not found"}), 404


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "loaded": search_engine._loaded,
        "papers": len(search_engine.papers) if search_engine._loaded else 0,
    })


@app.route("/api/suggest-link", methods=["POST"])
@limiter.limit("10 per minute")  # Limit suggestions to prevent spam
def suggest_link():
    """
    Submit a suggested link for an author.
    
    Users can suggest profile links (homepage, scholar, etc.) for authors
    who don't have them in the database. These are stored for review.
    """
    try:
        data = request.get_json() or {}
        
        author_name = data.get("author_name", "").strip()
        link_type = data.get("link_type", "").strip()  # homepage, google_scholar, linkedin, etc.
        link_url = data.get("link_url", "").strip()
        
        # Validate input
        if not author_name:
            return jsonify({"error": "Author name is required"}), 400
        if not link_type:
            return jsonify({"error": "Link type is required"}), 400
        if not link_url:
            return jsonify({"error": "Link URL is required"}), 400
        
        valid_types = ["homepage", "google_scholar", "dblp", "linkedin", "orcid"]
        if link_type not in valid_types:
            return jsonify({"error": f"Link type must be one of: {', '.join(valid_types)}"}), 400
        
        # Basic URL validation
        if not link_url.startswith(("http://", "https://")):
            return jsonify({"error": "URL must start with http:// or https://"}), 400
        
        # Load existing suggestions
        suggestions = []
        if SUGGESTIONS_FILE.exists():
            with open(SUGGESTIONS_FILE, "r", encoding="utf-8") as f:
                suggestions = json.load(f)
        
        # Add new suggestion (no IP stored for privacy)
        suggestion = {
            "author_name": author_name,
            "link_type": link_type,
            "link_url": link_url,
            "submitted_at": datetime.utcnow().isoformat(),
            "status": "pending"
        }
        suggestions.append(suggestion)
        
        # Save suggestions
        with open(SUGGESTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(suggestions, f, indent=2)
        
        return jsonify({"success": True, "message": "Thank you! Your suggestion has been submitted for review."})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# =====================
# Agent Preferences & Memory Endpoints
# =====================

def get_optional_user():
    """Extract user from auth token without requiring auth (returns None if not logged in)."""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return None
    session = auth_manager.get_session(token)
    if not session:
        return None
    return auth_manager.get_user_by_id(session['user_id'])


def build_enriched_query(query: str, prefs: dict, history: list) -> str:
    """Prepend user context (recent messages, custom instructions, preferred conferences) to query."""
    context_parts = []

    # Add custom instructions
    custom = prefs.get("custom_instructions", "").strip()
    if custom:
        context_parts.append(f"User instructions: {custom}")

    # Add preferred conferences
    default_confs = prefs.get("defaults", {}).get("conferences", [])
    if default_confs:
        context_parts.append(f"Preferred conferences: {', '.join(default_confs)}")

    # Add last 4 messages for conversational context
    if history:
        recent = history[-4:]
        conv_lines = []
        for msg in recent:
            role = msg.get("role", "user")
            content = msg.get("content", "")[:200]
            conv_lines.append(f"{role}: {content}")
        if conv_lines:
            context_parts.append("Recent conversation:\n" + "\n".join(conv_lines))

    if not context_parts:
        return query

    context_block = "\n\n".join(context_parts)
    return f"[User Context]\n{context_block}\n\n[Current Query]\n{query}"


def get_agent_for_user(prefs: dict):
    """Return an agent instance for the user's preferred model."""
    user_model = prefs.get("defaults", {}).get("model", "")
    if not user_model:
        return ai_agent  # Use default

    # If model matches current agent, reuse it
    if ai_agent and ai_agent.model_name == user_model:
        return ai_agent

    # Create a new agent with the user's preferred model
    try:
        return GroqAIAgent(model_name=user_model)
    except Exception as e:
        print(f"[AGENT MEMORY] Failed to create agent for model {user_model}: {e}")
        return ai_agent  # Fallback to default


@app.route("/api/agent/preferences", methods=["GET"])
@require_auth
def get_agent_preferences():
    """Get the current user's agent preferences."""
    try:
        user_id = request.current_user.get("id")
        prefs = agent_memory.get_user_prefs(user_id)
        return jsonify({"success": True, "preferences": prefs})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/agent/preferences", methods=["PUT"])
@require_auth
def update_agent_preferences():
    """Update (merge) the current user's agent preferences."""
    try:
        user_id = request.current_user.get("id")
        updates = request.get_json() or {}
        prefs = agent_memory.update_user_prefs(user_id, updates)
        return jsonify({"success": True, "preferences": prefs})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/agent/exclusions", methods=["POST"])
@require_auth
def add_agent_exclusion():
    """Add an exclusion (author, country, or affiliation)."""
    try:
        data = request.get_json() or {}
        category = data.get("category", "").strip()
        value = data.get("value", "").strip()

        if not category or not value:
            return jsonify({"error": "Category and value are required"}), 400

        user_id = request.current_user.get("id")
        added = agent_memory.add_exclusion(user_id, category, value)

        if added:
            return jsonify({"success": True, "message": f"Excluded {category}: {value}"})
        else:
            return jsonify({"error": "Invalid category or value already excluded"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/agent/exclusions", methods=["DELETE"])
@require_auth
def remove_agent_exclusion():
    """Remove an exclusion."""
    try:
        data = request.get_json() or {}
        category = data.get("category", "").strip()
        value = data.get("value", "").strip()

        if not category or not value:
            return jsonify({"error": "Category and value are required"}), 400

        user_id = request.current_user.get("id")
        removed = agent_memory.remove_exclusion(user_id, category, value)

        if removed:
            return jsonify({"success": True, "message": f"Removed exclusion: {value}"})
        else:
            return jsonify({"error": "Exclusion not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/agent/history", methods=["GET"])
@require_auth
def get_agent_history():
    """Get the current user's conversation history."""
    try:
        user_id = request.current_user.get("id")
        history = agent_memory.get_conversation_history(user_id)
        return jsonify({"success": True, "history": history})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/agent/history", methods=["DELETE"])
@require_auth
def clear_agent_history():
    """Clear the current user's conversation history."""
    try:
        user_id = request.current_user.get("id")
        agent_memory.clear_conversation_history(user_id)
        return jsonify({"success": True, "message": "Conversation history cleared"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# =====================
# AI Agent Endpoints
# =====================

@app.route("/api/ai/query", methods=["POST"])
@limiter.limit("20 per minute")  # Limit AI queries to prevent abuse
def ai_query():
    """
    Process natural language query using AI agent
    Request body: {query: string, context?: object}
    """
    # Check if AI agent is available
    if ai_agent is None:
        return jsonify({
            "error": "AI features are not configured. Please set GROQ_API_KEY in .env file."
        }), 503

    try:
        data = request.json
        user_query = data.get("query", "").strip()

        if not user_query:
            return jsonify({"error": "Query is required"}), 400

        if len(user_query) > 500:
            return jsonify({"error": "Query too long (max 500 characters)"}), 400

        # Load user preferences if authenticated (optional - no 401 if missing)
        user = get_optional_user()
        user_prefs = None
        user_id = None
        active_agent = ai_agent

        if user:
            user_id = user.get("id")
            user_prefs = agent_memory.get_user_prefs(user_id)

            # Record user message in conversation history
            agent_memory.add_conversation_entry(user_id, "user", user_query)

            # Use user's preferred model if set
            active_agent = get_agent_for_user(user_prefs) or ai_agent

        # Build enriched query with user context
        enriched_query = user_query
        if user_prefs:
            history = user_prefs.get("conversation_history", [])
            enriched_query = build_enriched_query(user_query, user_prefs, history)

        # Parse the natural language query into search parameters
        parse_result = active_agent.parse_search_query(enriched_query)

        if not parse_result.get("success"):
            # Fallback: answer as a general question
            answer = active_agent.answer_question(enriched_query, context=data.get("context"))

            # Record assistant response
            if user_id:
                agent_memory.add_conversation_entry(user_id, "assistant", answer or "")

            return jsonify({
                "type": "answer",
                "answer": answer,
                "error": parse_result.get("error")
            })

        # Extract search parameters and function type
        search_params = parse_result["parameters"]
        function_type = parse_result.get("function", "search_papers")

        # Apply default conferences/year filters from preferences
        if user_prefs:
            defaults = user_prefs.get("defaults", {})

            # Apply default conferences if none specified in query
            if not search_params.get("conferences") and defaults.get("conferences"):
                search_params["conferences"] = defaults["conferences"]

            # Apply default year range if not specified in query
            if not search_params.get("year_min") and defaults.get("year_min"):
                search_params["year_min"] = defaults["year_min"]
            if not search_params.get("year_max") and defaults.get("year_max"):
                search_params["year_max"] = defaults["year_max"]

        print(f"[AI AGENT V2] Function: {function_type}")
        print(f"[AI AGENT V2] Params: {json.dumps(search_params, indent=2)}")

        # Get exclusion lists for post-filtering
        excluded_authors = set()
        excluded_countries = set()
        excluded_affiliations = set()
        if user_prefs:
            exclusions = user_prefs.get("exclusions", {})
            excluded_authors = set(exclusions.get("authors", []))
            excluded_countries = set(exclusions.get("countries", []))
            excluded_affiliations = set(exclusions.get("affiliations", []))

        # Handle author search
        if function_type == "search_authors":
            topic_query = search_params.get("topic", "")

            # Search for papers on the topic
            search_results = search_engine.search(
                query=topic_query,
                conferences=search_params.get("conferences", []) or [],
                year_min=search_params.get("year_min"),
                year_max=search_params.get("year_max"),
                countries=search_params.get("countries", []) or [],
                limit=500,  # Get more papers to aggregate authors
                offset=0
            )

            print(f"[AI AGENT V2] Found {search_results.get('total', 0)} papers")

            # Aggregate authors from results with intelligent scoring
            author_counts = {}
            author_details = {}
            author_scores = {}

            for paper in search_results.get("results", []):
                paper_year = paper.get("year", 2020)
                for author_data in paper.get("authors_data", []):
                    name = author_data.get("name", "")
                    if not name:
                        continue

                    # Post-filter: skip excluded authors
                    if name in excluded_authors:
                        continue

                    # Post-filter: skip excluded countries
                    author_country = author_data.get("country", "")
                    if author_country and author_country in excluded_countries:
                        continue

                    # Post-filter: skip excluded affiliations
                    author_affiliation = author_data.get("affiliation", "")
                    if author_affiliation and author_affiliation in excluded_affiliations:
                        continue

                    if name not in author_counts:
                        author_counts[name] = 0
                        author_scores[name] = 0.0
                        author_details[name] = {
                            "name": name,
                            "affiliation": author_affiliation,
                            "country": author_country,
                            "conferences": set(),
                            "years": set()
                        }

                    author_counts[name] += 1

                    # Intelligent relevance scoring (not just paper count)
                    # 1. Base score: 1 point per paper
                    score = 1.0

                    # 2. Recency bonus: Recent work weighted higher (max +1.5x)
                    years_ago = 2026 - paper_year
                    if years_ago <= 1:
                        score *= 2.0      # 2024-2026: double weight
                    elif years_ago <= 3:
                        score *= 1.5      # 2021-2023: 1.5x weight
                    elif years_ago <= 5:
                        score *= 1.2      # 2019-2020: 1.2x weight

                    # 3. Top conference bonus (+0.3)
                    top_conferences = {"CVPR", "NeurIPS", "ICLR", "ICML", "ICCV", "ECCV", "ACL", "EMNLP"}
                    if paper.get("conference") in top_conferences:
                        score += 0.3

                    author_scores[name] += score

                    if paper.get("conference"):
                        author_details[name]["conferences"].add(paper["conference"])
                    if paper.get("year"):
                        author_details[name]["years"].add(paper["year"])

            # Sort authors by intelligent relevance score (not just count)
            sorted_authors = sorted(author_scores.items(), key=lambda x: x[1], reverse=True)
            limit = min(search_params.get("limit", 10), 50)

            top_authors = []
            for name, relevance_score in sorted_authors[:limit]:
                author = author_details[name]

                # Fetch notes for this author
                author_notes = notes_manager.get_notes_for_author(name)

                top_authors.append({
                    "name": name,
                    "paper_count": author_counts[name],  # Actual paper count
                    "relevance_score": round(relevance_score, 2),  # Intelligent relevance score
                    "affiliation": author["affiliation"],
                    "country": author["country"],
                    "conferences": sorted(list(author["conferences"])),
                    "years": sorted(list(author["years"]), reverse=True),
                    "notes": author_notes  # Include notes
                })

            # Generate AI summary of author results
            summary = active_agent.generate_author_summary(
                user_query,
                top_authors,
                search_params
            )

            # Record assistant response
            if user_id:
                agent_memory.add_conversation_entry(user_id, "assistant", summary or "")

            return jsonify({
                "type": "authors",
                "query": user_query,
                "search_params": search_params,
                "authors": top_authors,
                "total": len(sorted_authors),
                "summary": summary,
                "success": True
            })

        # Handle paper search (default)
        else:
            search_results = search_engine.search(
                query=search_params.get("query", ""),
                conferences=search_params.get("conferences", []) or [],
                year_min=search_params.get("year_min"),
                year_max=search_params.get("year_max"),
                author=search_params.get("author"),
                countries=search_params.get("countries", []) or [],
                limit=min(search_params.get("limit", 20), 50),  # Max 50 for AI
                offset=search_params.get("offset", 0)
            )

            print(f"[AI AGENT V2] Found {search_results.get('total', 0)} papers")

            # Post-filter: remove excluded authors/countries/affiliations from paper results
            if excluded_authors or excluded_countries or excluded_affiliations:
                filtered_results = []
                for paper in search_results.get("results", []):
                    # Check if any author in the paper is excluded
                    dominated_by_excluded = False
                    for author_data in paper.get("authors_data", []):
                        name = author_data.get("name", "")
                        country = author_data.get("country", "")
                        affiliation = author_data.get("affiliation", "")

                        if name in excluded_authors:
                            dominated_by_excluded = True
                            break
                        if country and country in excluded_countries:
                            dominated_by_excluded = True
                            break
                        if affiliation and affiliation in excluded_affiliations:
                            dominated_by_excluded = True
                            break

                    if not dominated_by_excluded:
                        filtered_results.append(paper)

                search_results["results"] = filtered_results
                search_results["total"] = len(filtered_results)

            # Generate AI summary of results
            summary = active_agent.generate_search_summary(
                user_query,
                search_results,
                search_params
            )

            # Record assistant response
            if user_id:
                agent_memory.add_conversation_entry(user_id, "assistant", summary or "")

            return jsonify({
                "type": "search",
                "query": user_query,
                "search_params": search_params,
                "results": search_results,
                "summary": summary,
                "success": True
            })

    except Exception as e:
        print(f"AI query error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/ai/status", methods=["GET"])
def ai_status():
    """Check AI agent status and available models"""
    if ai_agent is None:
        return jsonify({
            "status": "error",
            "configured": False,
            "error": "AI agent not initialized. Set GROQ_API_KEY in .env file."
        })

    try:
        status = ai_agent.check_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


# =====================
# Intelligent Search Endpoints
# =====================

@app.route("/api/intelligent/search", methods=["POST"])
@limiter.limit("10 per minute")
def intelligent_search():
    """
    Intelligent candidate search with multi-stage reasoning
    Request: {query: string, use_llm: bool, max_results: int, use_enrichment: bool}
    """
    try:
        data = request.get_json() or {}
        query = data.get("query", "").strip()
        use_llm = data.get("use_llm", True)
        use_enrichment = data.get("use_enrichment", False)  # New parameter
        max_results = min(int(data.get("max_results", 20)), 50)

        if not query:
            return jsonify({"error": "Query is required"}), 400

        # Run intelligent search
        candidates = intelligent_agent.intelligent_agent.intelligent_search(
            query,
            use_llm_ranking=use_llm,
            max_results=max_results,
            use_enrichment=use_enrichment  # Pass enrichment flag
        )

        return jsonify({
            "success": True,
            "query": query,
            "candidates": candidates,
            "total": len(candidates),
            "used_llm": use_llm,
            "used_enrichment": use_enrichment
        })

    except Exception as e:
        print(f"[INTELLIGENT SEARCH] Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/intelligent/analyze-author", methods=["POST"])
def analyze_author_intelligence():
    """
    Deep intelligence analysis of a specific author
    Request: {author_name: string, query: string}
    """
    try:
        data = request.get_json() or {}
        author_name = data.get("author_name", "").strip()
        query = data.get("query", "").strip()

        if not author_name:
            return jsonify({"error": "Author name is required"}), 400

        # Get author profile
        profile = search_engine.get_author_profile(author_name)
        if not profile:
            return jsonify({"error": "Author not found"}), 404

        papers = profile.get("papers", [])

        # Compute expertise
        expertise = semantic_search.semantic_engine.compute_author_expertise(papers)

        # Analyze trajectory
        trajectory = semantic_search.semantic_engine.analyze_research_trajectory(papers)

        # Estimate seniority
        seniority = author_expertise.expertise_analyzer.estimate_seniority(papers)

        # Analyze venues
        venues = author_expertise.expertise_analyzer.analyze_venues(papers)

        # Compute impact
        impact = author_expertise.expertise_analyzer.compute_impact_score(papers)

        # LLM evaluation if query provided
        llm_eval = None
        if query and intelligent_agent.intelligent_agent.claude:
            llm_eval = intelligent_agent.intelligent_agent.evaluate_candidate_with_llm(
                author_name, papers, query
            )

        return jsonify({
            "success": True,
            "author_name": author_name,
            "expertise": expertise,
            "trajectory": trajectory,
            "seniority": seniority,
            "venues": venues,
            "impact": impact,
            "llm_evaluation": llm_eval,
            "paper_count": len(papers)
        })

    except Exception as e:
        print(f"[AUTHOR ANALYSIS] Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/intelligent/compare-authors", methods=["POST"])
def compare_authors():
    """
    Compare multiple authors across expertise dimensions
    Request: {authors: [string], query?: string}
    """
    try:
        data = request.get_json() or {}
        author_names = data.get("authors", [])
        query = data.get("query", "").strip()

        if not author_names or len(author_names) < 2:
            return jsonify({"error": "At least 2 authors required"}), 400

        if len(author_names) > 5:
            return jsonify({"error": "Maximum 5 authors for comparison"}), 400

        comparisons = []

        for author_name in author_names:
            profile = search_engine.get_author_profile(author_name)
            if not profile:
                continue

            papers = profile.get("papers", [])

            comparison = {
                "name": author_name,
                "expertise": semantic_search.semantic_engine.compute_author_expertise(papers),
                "seniority": author_expertise.expertise_analyzer.estimate_seniority(papers),
                "impact": author_expertise.expertise_analyzer.compute_impact_score(papers),
                "paper_count": len(papers),
                "venues": author_expertise.expertise_analyzer.analyze_venues(papers)
            }

            # LLM evaluation if query provided
            if query and intelligent_agent.intelligent_agent.claude:
                comparison["llm_evaluation"] = intelligent_agent.intelligent_agent.evaluate_candidate_with_llm(
                    author_name, papers, query
                )

            comparisons.append(comparison)

        return jsonify({
            "success": True,
            "query": query if query else None,
            "comparisons": comparisons
        })

    except Exception as e:
        print(f"[COMPARE AUTHORS] Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# SOURCING CAMPAIGN ROUTES
# ============================================================================

@app.route("/api/campaigns", methods=["GET"])
@auth_required
def get_campaigns(user_data):
    """Get all campaigns for the logged-in user"""
    try:
        user_id = user_data["id"]
        include_archived = request.args.get("include_archived", "false").lower() == "true"

        campaigns = campaign_manager.campaign_manager.get_user_campaigns(
            user_id,
            include_archived=include_archived
        )

        return jsonify({
            "success": True,
            "campaigns": campaigns
        })

    except Exception as e:
        print(f"[GET CAMPAIGNS] Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/campaigns", methods=["POST"])
@auth_required
def create_campaign(user_data):
    """Create a new campaign"""
    try:
        user_id = user_data["id"]
        data = request.json

        name = data.get("name", "").strip()
        if not name:
            return jsonify({"error": "Campaign name is required"}), 400

        description = data.get("description", "").strip()
        stages = data.get("stages")  # Optional custom stages

        campaign = campaign_manager.campaign_manager.create_campaign(
            user_id=user_id,
            name=name,
            description=description,
            stages=stages
        )

        return jsonify({
            "success": True,
            "campaign": campaign
        })

    except Exception as e:
        print(f"[CREATE CAMPAIGN] Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/campaigns/<string:campaign_id>", methods=["GET"])
@auth_required
def get_campaign(user_data, campaign_id):
    """Get a specific campaign with all candidates"""
    try:
        user_id = user_data["id"]

        campaign = campaign_manager.campaign_manager.get_campaign(user_id, campaign_id)
        if not campaign:
            return jsonify({"error": "Campaign not found"}), 404

        # Also return stats
        stats = campaign_manager.campaign_manager.get_campaign_stats(user_id, campaign_id)

        return jsonify({
            "success": True,
            "campaign": campaign,
            "stats": stats
        })

    except Exception as e:
        print(f"[GET CAMPAIGN] Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/campaigns/<string:campaign_id>", methods=["PUT"])
@auth_required
def update_campaign(user_data, campaign_id):
    """Update campaign metadata"""
    try:
        user_id = user_data["id"]
        data = request.json

        campaign = campaign_manager.campaign_manager.update_campaign(
            user_id=user_id,
            campaign_id=campaign_id,
            name=data.get("name"),
            description=data.get("description"),
            stages=data.get("stages"),
            archived=data.get("archived")
        )

        if not campaign:
            return jsonify({"error": "Campaign not found"}), 404

        return jsonify({
            "success": True,
            "campaign": campaign
        })

    except Exception as e:
        print(f"[UPDATE CAMPAIGN] Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/campaigns/<string:campaign_id>", methods=["DELETE"])
@auth_required
def delete_campaign(user_data, campaign_id):
    """Delete a campaign"""
    try:
        user_id = user_data["id"]

        success = campaign_manager.campaign_manager.delete_campaign(user_id, campaign_id)
        if not success:
            return jsonify({"error": "Campaign not found"}), 404

        return jsonify({"success": True})

    except Exception as e:
        print(f"[DELETE CAMPAIGN] Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/campaigns/<string:campaign_id>/candidates", methods=["POST"])
@auth_required
def add_candidate_to_campaign(user_data, campaign_id):
    """Add a candidate to a campaign"""
    try:
        user_id = user_data["id"]
        data = request.json

        candidate_data = data.get("candidate")
        if not candidate_data:
            return jsonify({"error": "Candidate data is required"}), 400

        stage_id = data.get("stage_id", "new")

        campaign = campaign_manager.campaign_manager.add_candidate(
            user_id=user_id,
            campaign_id=campaign_id,
            candidate_data=candidate_data,
            stage_id=stage_id
        )

        if not campaign:
            return jsonify({"error": "Campaign not found"}), 404

        return jsonify({
            "success": True,
            "campaign": campaign
        })

    except Exception as e:
        print(f"[ADD CANDIDATE] Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/campaigns/<string:campaign_id>/candidates/<string:candidate_id>/move", methods=["POST"])
@auth_required
def move_candidate(user_data, campaign_id, candidate_id):
    """Move candidate to a different stage (drag-and-drop)"""
    try:
        user_id = user_data["id"]
        data = request.json

        new_stage_id = data.get("stage_id")
        if not new_stage_id:
            return jsonify({"error": "stage_id is required"}), 400

        campaign = campaign_manager.campaign_manager.move_candidate(
            user_id=user_id,
            campaign_id=campaign_id,
            candidate_id=candidate_id,
            new_stage_id=new_stage_id
        )

        if not campaign:
            return jsonify({"error": "Campaign or candidate not found"}), 404

        return jsonify({
            "success": True,
            "campaign": campaign
        })

    except Exception as e:
        print(f"[MOVE CANDIDATE] Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/campaigns/<string:campaign_id>/candidates/<string:candidate_id>", methods=["DELETE"])
@auth_required
def remove_candidate_from_campaign(user_data, campaign_id, candidate_id):
    """Remove a candidate from a campaign"""
    try:
        user_id = user_data["id"]

        campaign = campaign_manager.campaign_manager.remove_candidate(
            user_id=user_id,
            campaign_id=campaign_id,
            candidate_id=candidate_id
        )

        if not campaign:
            return jsonify({"error": "Campaign not found"}), 404

        return jsonify({
            "success": True,
            "campaign": campaign
        })

    except Exception as e:
        print(f"[REMOVE CANDIDATE] Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/campaigns/<string:campaign_id>/candidates/<string:candidate_id>/tasks", methods=["POST"])
@auth_required
def add_task(user_data, campaign_id, candidate_id):
    """Add a task for a candidate"""
    try:
        user_id = user_data["id"]
        data = request.json

        task_type = data.get("type", "note")
        description = data.get("description", "").strip()
        if not description:
            return jsonify({"error": "Task description is required"}), 400

        due_date = data.get("due_date")
        completed = data.get("completed", False)

        campaign = campaign_manager.campaign_manager.add_task(
            user_id=user_id,
            campaign_id=campaign_id,
            candidate_id=candidate_id,
            task_type=task_type,
            description=description,
            due_date=due_date,
            completed=completed
        )

        if not campaign:
            return jsonify({"error": "Campaign or candidate not found"}), 404

        return jsonify({
            "success": True,
            "campaign": campaign
        })

    except Exception as e:
        print(f"[ADD TASK] Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/campaigns/<string:campaign_id>/candidates/<string:candidate_id>/tasks/<string:task_id>", methods=["PUT"])
@auth_required
def update_task(user_data, campaign_id, candidate_id, task_id):
    """Update a task"""
    try:
        user_id = user_data["id"]
        data = request.json

        campaign = campaign_manager.campaign_manager.update_task(
            user_id=user_id,
            campaign_id=campaign_id,
            candidate_id=candidate_id,
            task_id=task_id,
            completed=data.get("completed"),
            description=data.get("description"),
            due_date=data.get("due_date")
        )

        if not campaign:
            return jsonify({"error": "Campaign, candidate, or task not found"}), 404

        return jsonify({
            "success": True,
            "campaign": campaign
        })

    except Exception as e:
        print(f"[UPDATE TASK] Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/campaigns/<string:campaign_id>/candidates/<string:candidate_id>/notes", methods=["POST"])
@auth_required
def add_candidate_note(user_data, campaign_id, candidate_id):
    """Add a note to a candidate"""
    try:
        user_id = user_data["id"]
        data = request.json

        note = data.get("note", "").strip()
        if not note:
            return jsonify({"error": "Note is required"}), 400

        campaign = campaign_manager.campaign_manager.add_note(
            user_id=user_id,
            campaign_id=campaign_id,
            candidate_id=candidate_id,
            note=note
        )

        if not campaign:
            return jsonify({"error": "Campaign or candidate not found"}), 404

        return jsonify({
            "success": True,
            "campaign": campaign
        })

    except Exception as e:
        print(f"[ADD NOTE] Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("Paper Search Engine API")
    print("=" * 50)
    print(f"Starting server on port {PORT}")
    print("Press Ctrl+C to stop\n")

    search_engine.load_data()
    app.run(host="0.0.0.0", port=PORT, debug=False)
