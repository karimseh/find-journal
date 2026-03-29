import json
import re
from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

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
    similarity_score: float



def _build_journal_document(journal: dict) -> str:
    parts = []

    title = journal.get('title', '')
    title_words = re.findall(r'[a-z]+', title.lower())
    keywords = [w for w in title_words if w not in TITLE_STOPWORDS and len(w) >= 3]
    if keywords:
        keyword_text = ' '.join(keywords)
        parts.append(keyword_text)
        parts.append(keyword_text)  # repeat for weight

    categories = journal.get('categories', '') or ''
    categories_clean = re.sub(r'\(Q[1-4]\)', '', categories).strip()
    if categories_clean:
        parts.append(categories_clean)

    areas = journal.get('areas', '') or ''
    if areas:
        parts.append(areas)

  
    openalex_raw = journal.get('openalex_topics')
    if openalex_raw:
        try:
            topics = json.loads(openalex_raw)
            for topic in topics:
                name = topic.get('name', '')
                subfield = topic.get('subfield', '')
                field = topic.get('field', '')
                parts.append(name)
                if subfield:
                    parts.append(subfield)
                if field:
                    parts.append(field)
        except (json.JSONDecodeError, TypeError):
            pass

    return ' '.join(parts)



def build_index(journals: list[dict]) -> tuple[TfidfVectorizer, object, list[dict]]:
   
    documents = []
    valid_journals = []

    for journal in journals:
        doc = _build_journal_document(journal)
        if doc.strip():
            documents.append(doc)
            valid_journals.append(journal)

    if not documents:
        raise ValueError("No valid journal documents to index")

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),    # unigrams + bigrams (captures "computer science", "health informatics")
        max_df=0.3,            # ignore terms appearing in >30% of docs (too common)
        min_df=1,              # keep all terms (even rare ones matter)
        sublinear_tf=True,     # log-normalize term frequency (dampens repeated terms)
    )

    tfidf_matrix = vectorizer.fit_transform(documents)

    return vectorizer, tfidf_matrix, valid_journals


# ── Abstract matching ────────────────────────────────────────────

def match_abstract(
    abstract: str,
    vectorizer: TfidfVectorizer,
    tfidf_matrix,
    journals: list[dict],
    top_n: int = 15,
) -> list[MatchResult]:
   
    abstract_vector = vectorizer.transform([abstract])

    scores = cosine_similarity(abstract_vector, tfidf_matrix).flatten()

    ranked_indices = scores.argsort()[::-1]

    results = []
    for idx in ranked_indices:
        score = scores[idx]
        if score <= 0:
            break
        if len(results) >= top_n:
            break

        j = journals[idx]
        results.append(MatchResult(
            rank=len(results) + 1,
            title=j.get('title', ''),
            issn=j.get('issn', '') or '',
            eissn=j.get('eissn', '') or '',
            publisher=j.get('publisher', '') or '',
            quartile=j.get('quartile', '') or 'N/A',
            sjr=j.get('sjr') or 0.0,
            h_index=j.get('h_index') or 0,
            categories=j.get('categories', '') or 'N/A',
            areas=j.get('areas', '') or 'N/A',
            similarity_score=round(float(score), 4),
        ))

    return results
