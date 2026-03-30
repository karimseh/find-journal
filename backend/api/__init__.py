from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
from journal_matcher.matcher import HybridIndex, build_index
from journal_matcher.storage import init_db, query_all_journals

_index_cache: HybridIndex | None = None

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60 per minute"],
    storage_uri="memory://",
)


def get_index() -> HybridIndex:
    """Return the cached hybrid index."""
    return _index_cache


def create_app():
    global _index_cache

    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, origins=app.config["ALLOWED_ORIGINS"])
    limiter.init_app(app)

    conn = init_db(app.config["DATABASE_PATH"])
    app.config["DB_CONN"] = conn

    print("Building hybrid index (TF-IDF + embeddings)...")
    journals = query_all_journals(conn)
    _index_cache = build_index(journals)
    print(f"Index ready: {len(_index_cache.journals)} journals indexed")

    from api.routes import bp

    app.register_blueprint(bp)

    return app
