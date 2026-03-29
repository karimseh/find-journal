from dataclasses import asdict

from flask import Blueprint, current_app, jsonify, request

from api import get_index
from journal_matcher.matcher import match_abstract
from journal_matcher.storage import query_filtered_journals, search_by_title, get_stats

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/match', methods=['POST'])
def match():
    """Match an abstract to relevant journals.

    POST /api/match
    Body: {"abstract": "...", "top_n": 15, "quartiles": ["Q1","Q2"], "min_sjr": 0.5}
    """
    data = request.get_json()
    if not data or not data.get('abstract', '').strip():
        return jsonify({'error': 'abstract is required'}), 400

    abstract = data['abstract']
    top_n = data.get('top_n', 15)
    quartiles = data.get('quartiles')
    min_sjr = data.get('min_sjr')

    vectorizer, tfidf_matrix, journals = get_index()
    results = match_abstract(abstract, vectorizer, tfidf_matrix, journals, top_n=top_n)

    # Apply post-match filters if provided
    if quartiles:
        results = [r for r in results if r.quartile in quartiles]
    if min_sjr is not None:
        results = [r for r in results if r.sjr >= min_sjr]

    # Re-rank after filtering
    for i, r in enumerate(results):
        r.rank = i + 1

    return jsonify([asdict(r) for r in results])


@bp.route('/search')
def search():
    """Search journals by title.

    GET /api/search?q=blockchain&limit=20
    """
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'q parameter is required'}), 400

    limit = request.args.get('limit', 20, type=int)
    conn = current_app.config['DB_CONN']
    journals = search_by_title(conn, query, limit=limit)

    return jsonify(journals)


@bp.route('/stats')
def stats():
    """Get database statistics.

    GET /api/stats
    """
    conn = current_app.config['DB_CONN']
    return jsonify(get_stats(conn))


@bp.route('/journals')
def journals():
    """List journals with optional filters.

    GET /api/journals?quartile=Q1&min_sjr=1.0&page=1&per_page=50
    """
    conn = current_app.config['DB_CONN']

    quartile = request.args.get('quartile')
    quartiles = quartile.split(',') if quartile else None
    min_sjr = request.args.get('min_sjr', type=float)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    all_journals = query_filtered_journals(conn, quartiles=quartiles, min_sjr=min_sjr)

    # Pagination
    start = (page - 1) * per_page
    end = start + per_page
    paginated = all_journals[start:end]

    return jsonify({
        'journals': paginated,
        'total': len(all_journals),
        'page': page,
        'per_page': per_page,
    })
