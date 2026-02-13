"""
Paper Search Engine - Flask REST API
====================================
Backend API for searching academic papers.

Endpoints:
    POST /api/search     - Search papers
    GET  /api/stats      - Get database statistics
    GET  /api/conferences - Get list of conferences
    GET  /api/paper/<id> - Get single paper details
"""

from flask import Flask, request, jsonify
from flask_cors import CORS

from config import HOST, PORT, DEBUG, DEFAULT_LIMIT, MAX_LIMIT
from search_engine import search_engine

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration


@app.before_request
def ensure_data_loaded():
    """Ensure paper data is loaded before handling requests."""
    if not search_engine._loaded:
        search_engine.load_data()


@app.route("/api/search", methods=["POST"])
def search():
    """
    Search papers by query.

    Request body:
    {
        "query": "transformer attention",
        "conferences": ["CVPR", "ICLR"],  // optional
        "year_min": 2020,                  // optional
        "year_max": 2024,                  // optional
        "limit": 20,                       // optional, default 20
        "offset": 0                        // optional, for pagination
    }
    """
    try:
        data = request.get_json() or {}

        query = data.get("query", "").strip()
        conferences = data.get("conferences")
        year_min = data.get("year_min")
        year_max = data.get("year_max")
        limit = min(int(data.get("limit", DEFAULT_LIMIT)), MAX_LIMIT)
        offset = max(int(data.get("offset", 0)), 0)

        # Validate conferences list
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


@app.route("/", methods=["GET"])
def index():
    """Root endpoint with API info."""
    return jsonify({
        "name": "Paper Search Engine API",
        "version": "1.0.0",
        "endpoints": {
            "POST /api/search": "Search papers by query",
            "GET /api/stats": "Get database statistics",
            "GET /api/conferences": "List all conferences",
            "GET /api/paper/<id>": "Get paper details",
            "GET /api/health": "Health check",
        }
    })


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("Paper Search Engine API")
    print("=" * 50)
    print(f"Starting server at http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop\n")

    # Pre-load data
    search_engine.load_data()

    # Run the server
    app.run(host=HOST, port=PORT, debug=DEBUG)
