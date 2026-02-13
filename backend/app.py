"""
Paper Search Engine - Flask REST API
====================================
Backend API for searching academic papers.
Serves both API and frontend in production.
"""

import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import DEFAULT_LIMIT, MAX_LIMIT, BASE_DIR, DATA_DIR
from search_engine import search_engine

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


@app.before_request
def ensure_data_loaded():
    """Ensure paper data is loaded before handling requests."""
    if not search_engine._loaded:
        search_engine.load_data()


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
        limit = min(int(data.get("limit", DEFAULT_LIMIT)), MAX_LIMIT)
        offset = max(int(data.get("offset", 0)), 0)

        if conferences and not isinstance(conferences, list):
            conferences = [conferences]

        results = search_engine.search(
            query=query,
            conferences=conferences,
            year_min=year_min,
            year_max=year_max,
            author=author if author else None,
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


@app.route("/api/author/<path:author_name>", methods=["GET"])
def get_author_profile(author_name: str):
    """Get full profile for an author."""
    profile = search_engine.get_author_profile(author_name)
    if profile:
        return jsonify(profile)
    return jsonify({"error": "Author not found"}), 404


@app.route("/api/author/<path:author_name>/export", methods=["GET"])
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
        
        # Add new suggestion
        suggestion = {
            "author_name": author_name,
            "link_type": link_type,
            "link_url": link_url,
            "submitted_at": datetime.utcnow().isoformat(),
            "ip": get_remote_address(),
            "status": "pending"
        }
        suggestions.append(suggestion)
        
        # Save suggestions
        with open(SUGGESTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(suggestions, f, indent=2)
        
        return jsonify({"success": True, "message": "Thank you! Your suggestion has been submitted for review."})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("Paper Search Engine API")
    print("=" * 50)
    print(f"Starting server on port {PORT}")
    print("Press Ctrl+C to stop\n")

    search_engine.load_data()
    app.run(host="0.0.0.0", port=PORT, debug=False)
