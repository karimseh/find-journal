import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine

from .keywords import TITLE_STOPWORDS


@dataclass
class MatchResult:
    rank: int
    title: str
    issn: str
    eissn: str
    publisher: str
    quartile: str
    sjr: float
    h_index: int
    categories: str
    areas: str
    open_access: bool
    open_access_diamond: bool
    similarity_score: float


MODEL_NAME = "all-MiniLM-L6-v2"
TFIDF_WEIGHT = 0.6
EMBEDDING_WEIGHT = 0.4

CACHE_DIR = Path(__file__).parent.parent / "data"

_model = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _build_tfidf_document(journal: dict) -> str:
    """Build a keyword-rich document for TF-IDF matching."""
    parts = []

    title = journal.get("title", "")
    title_words = re.findall(r"[a-z]+", title.lower())
    keywords = [w for w in title_words if w not in TITLE_STOPWORDS and len(w) >= 3]
    if keywords:
        keyword_text = " ".join(keywords)
        parts.append(keyword_text)
        parts.append(keyword_text)  # repeat for weight

    categories = journal.get("categories", "") or ""
    categories_clean = re.sub(r"\(Q[1-4]\)", "", categories).strip()
    if categories_clean:
        parts.append(categories_clean)

    areas = journal.get("areas", "") or ""
    if areas:
        parts.append(areas)

    openalex_raw = journal.get("openalex_topics")
    if openalex_raw:
        try:
            topics = json.loads(openalex_raw)
            for topic in topics:
                name = topic.get("name", "")
                subfield = topic.get("subfield", "")
                field = topic.get("field", "")
                parts.append(name)
                if subfield:
                    parts.append(subfield)
                if field:
                    parts.append(field)
        except (json.JSONDecodeError, TypeError):
            pass

    return " ".join(parts)


def _build_embedding_document(journal: dict) -> str:
    """Build a natural-language document for semantic embedding."""
    parts = []

    title = journal.get("title", "")
    if title:
        parts.append(title)

    categories = journal.get("categories", "") or ""
    categories_clean = re.sub(r"\(Q[1-4]\)", "", categories).strip()
    if categories_clean:
        parts.append(categories_clean)

    areas = journal.get("areas", "") or ""
    if areas:
        parts.append(areas)

    openalex_raw = journal.get("openalex_topics")
    if openalex_raw:
        try:
            topics = json.loads(openalex_raw)
            for topic in topics:
                name = topic.get("name", "")
                subfield = topic.get("subfield", "")
                field = topic.get("field", "")
                if name:
                    parts.append(name)
                if subfield:
                    parts.append(subfield)
                if field:
                    parts.append(field)
        except (json.JSONDecodeError, TypeError):
            pass

    return ". ".join(parts)


def _cache_key(documents: list[str]) -> str:
    """Hash all documents + model name to detect when cache is stale."""
    content = MODEL_NAME + "\n".join(documents)
    return hashlib.md5(content.encode()).hexdigest()


@dataclass
class HybridIndex:
    """Holds both TF-IDF and embedding indices."""

    vectorizer: TfidfVectorizer
    tfidf_matrix: object
    embeddings: np.ndarray
    journals: list[dict]


def build_index(journals: list[dict]) -> HybridIndex:
    tfidf_docs = []
    embedding_docs = []
    valid_journals = []

    for journal in journals:
        tfidf_doc = _build_tfidf_document(journal)
        emb_doc = _build_embedding_document(journal)
        if tfidf_doc.strip() or emb_doc.strip():
            tfidf_docs.append(tfidf_doc)
            embedding_docs.append(emb_doc)
            valid_journals.append(journal)

    if not valid_journals:
        raise ValueError("No valid journal documents to index")

    # Build TF-IDF index
    print(f"  Building TF-IDF index for {len(valid_journals)} journals...")
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_df=0.3,
        min_df=1,
        sublinear_tf=True,
    )
    tfidf_matrix = vectorizer.fit_transform(tfidf_docs)

    # Build embedding index (with file cache)
    key = _cache_key(embedding_docs)
    cache_file = CACHE_DIR / f"embeddings_{key}.npy"

    if cache_file.exists():
        print(f"  Loading cached embeddings from {cache_file.name}")
        embeddings = np.load(cache_file)
    else:
        for old in CACHE_DIR.glob("embeddings_*.npy"):
            old.unlink()

        model = _get_model()
        print(f"  Encoding {len(embedding_docs)} journal documents (first time, will cache)...")
        embeddings = model.encode(
            embedding_docs, show_progress_bar=True, batch_size=64, normalize_embeddings=True
        )
        np.save(cache_file, embeddings)
        print(f"  Cached embeddings to {cache_file.name}")

    return HybridIndex(
        vectorizer=vectorizer,
        tfidf_matrix=tfidf_matrix,
        embeddings=embeddings,
        journals=valid_journals,
    )


def match_abstract(
    abstract: str,
    index: HybridIndex,
    top_n: int = 15,
) -> list[MatchResult]:

    # --- TF-IDF scores (keyword matching) ---
    tfidf_vector = index.vectorizer.transform([abstract])
    tfidf_scores = sklearn_cosine(tfidf_vector, index.tfidf_matrix).flatten()
    # Normalize to 0-1
    tfidf_max = tfidf_scores.max()
    if tfidf_max > 0:
        tfidf_scores = tfidf_scores / tfidf_max

    # --- Embedding scores (semantic matching) ---
    model = _get_model()
    abstract_embedding = model.encode([abstract], normalize_embeddings=True)
    emb_scores = (index.embeddings @ abstract_embedding.T).flatten()
    # Normalize to 0-1
    emb_max = emb_scores.max()
    if emb_max > 0:
        emb_scores = emb_scores / emb_max

    # --- Hybrid score ---
    scores = TFIDF_WEIGHT * tfidf_scores + EMBEDDING_WEIGHT * emb_scores

    ranked_indices = scores.argsort()[::-1]

    results = []
    for idx in ranked_indices:
        score = scores[idx]
        if score <= 0:
            break
        if len(results) >= top_n:
            break

        j = index.journals[idx]
        results.append(
            MatchResult(
                rank=len(results) + 1,
                title=j.get("title", ""),
                issn=j.get("issn", "") or "",
                eissn=j.get("eissn", "") or "",
                publisher=j.get("publisher", "") or "",
                quartile=j.get("quartile", "") or "N/A",
                sjr=j.get("sjr") or 0.0,
                h_index=j.get("h_index") or 0,
                categories=j.get("categories", "") or "N/A",
                areas=j.get("areas", "") or "N/A",
                open_access=bool(j.get("open_access", False)),
                open_access_diamond=bool(j.get("open_access_diamond", False)),
                similarity_score=round(float(score), 4),
            )
        )

    return results
