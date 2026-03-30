from dataclasses import asdict

from flask import Blueprint, current_app, jsonify, request

from api import get_index, limiter
from journal_matcher.matcher import match_abstract
from journal_matcher.storage import get_stats, query_filtered_journals, search_by_title

bp = Blueprint("api", __name__, url_prefix="/api")

MAX_ABSTRACT_LENGTH = 10_000  # ~2000 words
MAX_TOP_N = 200
MAX_PER_PAGE = 100


@bp.route("/match", methods=["POST"])
@limiter.limit("20 per minute")
def match():
    """Match an abstract to relevant journals.

    POST /api/match
    Body: {"abstract": "...", "top_n": 15, "quartiles": ["Q1","Q2"], "min_sjr": 0.5}
    """
    data = request.get_json()
    if not data or not data.get("abstract", "").strip():
        return jsonify({"error": "abstract is required"}), 400

    abstract = data["abstract"]
    if len(abstract) > MAX_ABSTRACT_LENGTH:
        return jsonify({"error": f"abstract too long (max {MAX_ABSTRACT_LENGTH} characters)"}), 400

    top_n = min(data.get("top_n", 15), MAX_TOP_N)
    quartiles = data.get("quartiles")
    min_sjr = data.get("min_sjr")

    index = get_index()
    results = match_abstract(abstract, index, top_n=top_n)

    # Apply post-match filters if provided
    if quartiles:
        results = [r for r in results if r.quartile in quartiles]
    if min_sjr is not None:
        results = [r for r in results if r.sjr >= min_sjr]

    # Re-rank after filtering
    for i, r in enumerate(results):
        r.rank = i + 1

    return jsonify([asdict(r) for r in results])


@bp.route("/search")
def search():
    """Search journals by title.

    GET /api/search?q=blockchain&limit=20
    """
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "q parameter is required"}), 400

    limit = min(request.args.get("limit", 20, type=int), MAX_PER_PAGE)
    conn = current_app.config["DB_CONN"]
    journals = search_by_title(conn, query, limit=limit)

    return jsonify(journals)


@bp.route("/stats")
def stats():
    """Get database statistics.

    GET /api/stats
    """
    conn = current_app.config["DB_CONN"]
    return jsonify(get_stats(conn))


@bp.route("/journals")
def journals():
    """List journals with optional filters.

    GET /api/journals?quartile=Q1&min_sjr=1.0&page=1&per_page=50
    """
    conn = current_app.config["DB_CONN"]

    quartile = request.args.get("quartile")
    quartiles = quartile.split(",") if quartile else None
    min_sjr = request.args.get("min_sjr", type=float)
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(request.args.get("per_page", 50, type=int), MAX_PER_PAGE)

    all_journals = query_filtered_journals(conn, quartiles=quartiles, min_sjr=min_sjr)

    # Pagination
    start = (page - 1) * per_page
    end = start + per_page
    paginated = all_journals[start:end]

    return jsonify(
        {
            "journals": paginated,
            "total": len(all_journals),
            "page": page,
            "per_page": per_page,
        }
    )
