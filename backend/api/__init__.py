from flask import Flask
from flask import request as flask_request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_talisman import Talisman

from config import Config
from journal_matcher.matcher import HybridIndex, build_index
from journal_matcher.storage import init_db, query_all_journals

_index_cache: HybridIndex | None = None


def get_client_ip():
    return (
        flask_request.headers.get("X-Forwarded-For", flask_request.remote_addr)
        .split(",")[0]
        .strip()
    )


limiter = Limiter(
    key_func=get_client_ip,
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
    Talisman(
        app,
        force_https=False,  # handled by Azure / reverse proxy
        content_security_policy=None,  # API-only, no HTML to protect
    )

    conn = init_db(app.config["DATABASE_PATH"])
    app.config["DB_CONN"] = conn

    print("Building hybrid index (TF-IDF + embeddings)...")
    journals = query_all_journals(conn)
    _index_cache = build_index(journals)
    print(f"Index ready: {len(_index_cache.journals)} journals indexed")

    from api.routes import bp

    app.register_blueprint(bp)

    return app
