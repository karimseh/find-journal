from dataclasses import asdict

from flask import Blueprint, current_app, jsonify, request

from api import get_index, limiter
from journal_matcher.matcher import match_abstract
from journal_matcher.storage import get_stats, query_filtered_journals, search_by_title

bp = Blueprint("api", __name__, url_prefix="/api")

MAX_ABSTRACT_LENGTH = 10_000  # ~2000 words
MAX_TOP_N = 200
MAX_PER_PAGE = 100
VALID_QUARTILES = {"Q1", "Q2", "Q3", "Q4"}


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

    top_n = data.get("top_n", 15)
    if not isinstance(top_n, int) or top_n < 1:
        return jsonify({"error": "top_n must be a positive integer"}), 400
    top_n = min(top_n, MAX_TOP_N)

    quartiles = data.get("quartiles")
    if quartiles is not None:
        if not isinstance(quartiles, list) or not all(q in VALID_QUARTILES for q in quartiles):
            return jsonify({"error": f"quartiles must be a list of {sorted(VALID_QUARTILES)}"}), 400

    min_sjr = data.get("min_sjr")
    if min_sjr is not None:
        if not isinstance(min_sjr, (int, float)) or min_sjr < 0:
            return jsonify({"error": "min_sjr must be a non-negative number"}), 400

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
    if quartile:
        quartiles = quartile.split(",")
        if not all(q in VALID_QUARTILES for q in quartiles):
            return jsonify({"error": f"quartile must be from {sorted(VALID_QUARTILES)}"}), 400
    else:
        quartiles = None

    min_sjr = request.args.get("min_sjr", type=float)
    if min_sjr is not None and min_sjr < 0:
        return jsonify({"error": "min_sjr must be a non-negative number"}), 400

    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 50, type=int), 1), MAX_PER_PAGE)

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
