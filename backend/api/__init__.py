from flask import Flask
from flask_cors import CORS

from config import Config
from journal_matcher.storage import init_db, query_all_journals
from journal_matcher.matcher import build_index


# Module-level cache for the TF-IDF index (built once, reused per request)
_index_cache = {
    'vectorizer': None,
    'tfidf_matrix': None,
    'journals': None,
}


def get_index():
    """Return the cached TF-IDF index components."""
    return _index_cache['vectorizer'], _index_cache['tfidf_matrix'], _index_cache['journals']


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Allow React dev server (localhost:5173) to call the API
    CORS(app)

    # Open DB connection (shared across requests)
    conn = init_db(app.config['DATABASE_PATH'])
    app.config['DB_CONN'] = conn

    # Build TF-IDF index at startup (~2-5 seconds)
    print("Building TF-IDF index...")
    journals = query_all_journals(conn)
    vectorizer, tfidf_matrix, valid_journals = build_index(journals)
    _index_cache['vectorizer'] = vectorizer
    _index_cache['tfidf_matrix'] = tfidf_matrix
    _index_cache['journals'] = valid_journals
    print(f"Index ready: {len(valid_journals)} journals indexed")

    # Register routes
    from api.routes import bp
    app.register_blueprint(bp)

    return app
