from flask import Flask
from flask_cors import CORS

from config import Config
from journal_matcher.storage import init_db, query_all_journals
from journal_matcher.matcher import build_index, HybridIndex


_index_cache: HybridIndex | None = None


def get_index() -> HybridIndex:
    """Return the cached hybrid index."""
    return _index_cache


def create_app():
    global _index_cache

    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app)

    conn = init_db(app.config['DATABASE_PATH'])
    app.config['DB_CONN'] = conn

    print("Building hybrid index (TF-IDF + embeddings)...")
    journals = query_all_journals(conn)
    _index_cache = build_index(journals)
    print(f"Index ready: {len(_index_cache.journals)} journals indexed")

    from api.routes import bp
    app.register_blueprint(bp)

    return app
