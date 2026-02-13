"""
Paper Search Engine - Flask REST API
====================================
Backend API for searching academic papers.
Serves both API and frontend in production.
"""

import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from config import DEFAULT_LIMIT, MAX_LIMIT, BASE_DIR
from search_engine import search_engine

# Initialize Flask app
app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

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
def search():
    """Search papers by query with Boolean operators."""
    try:
        data = request.get_json() or {}

        query = data.get("query", "").strip()
        conferences = data.get("conferences")
        year_min = data.get("year_min")
        year_max = data.get("year_max")
        limit = min(int(data.get("limit", DEFAULT_LIMIT)), MAX_LIMIT)
        offset = max(int(data.get("offset", 0)), 0)

        if conferences and not isinstance(conferences, list):
            conferences = [conferences]

        results = search_engine.search(
            query=query,
            conferences=conferences,
            year_min=year_min,
            year_max=year_max,
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


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "loaded": search_engine._loaded,
        "papers": len(search_engine.papers) if search_engine._loaded else 0,
    })


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("Paper Search Engine API")
    print("=" * 50)
    print(f"Starting server on port {PORT}")
    print("Press Ctrl+C to stop\n")

    search_engine.load_data()
    app.run(host="0.0.0.0", port=PORT, debug=False)
