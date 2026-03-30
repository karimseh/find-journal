import http.client
import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from threading import Lock

import pandas as pd

from . import utils


@dataclass
class ScimagoData:
    sjr: float | None
    quartile: str | None
    h_index: int | None
    categories: str | None
    areas: str | None
    citations_per_doc: float | None
    scimago_title: str | None
    open_access: bool
    open_access_diamond: bool


@dataclass
class OpenAlexData:
    openalex_id: str | None
    display_name: str | None
    topics: list[dict] = field(default_factory=list)


def load_scimago(csv_path: str) -> dict[str, ScimagoData]:
    df = pd.read_csv(csv_path, sep=";")
    scimago_dict = {}

    for _, row in df.iterrows():
        data = ScimagoData(
            sjr=utils.safe_float(row.get("SJR")),
            quartile=utils.clean_text(row.get("SJR Best Quartile")),
            h_index=utils.safe_int(row.get("H index")),
            categories=utils.clean_text(row.get("Categories")),
            areas=utils.clean_text(row.get("Areas")),
            citations_per_doc=utils.safe_float(row.get("Citations / Doc. (2years)")),
            scimago_title=utils.clean_text(row.get("Title")),
            open_access=str(row.get("Open Access", "")).strip().lower() == "yes",
            open_access_diamond=str(row.get("Open Access Diamond", "")).strip().lower() == "yes",
        )

        raw_issns = str(row.get("Issn", "")).split(",")
        for raw_issn in raw_issns:
            normalized = utils.normalize_issn(raw_issn.strip())
            if normalized:
                scimago_dict[normalized] = data

    return scimago_dict


OPENALEX_BASE = "https://api.openalex.org/sources/issn:"


def fetch_openalex(issn: str, api_key: str = "", retries: int = 2) -> OpenAlexData | None:
    hyphenated = utils.issn_with_hyphen(issn)
    if not hyphenated:
        return None

    url = f"{OPENALEX_BASE}{hyphenated}"
    if api_key:
        url += f"?api_key={api_key}"

    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "JournalMatcher/1.0 (academic research tool)")

            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = json.loads(resp.read().decode())
            break  # success
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            return None
        except (
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
            http.client.IncompleteRead,
            ConnectionError,
            OSError,
        ):
            if attempt < retries:
                time.sleep(1)
                continue
            return None

    topics = []
    for t in raw.get("topics", []):
        topics.append(
            {
                "name": t.get("display_name", ""),
                "count": t.get("count", 0),
                "subfield": t.get("subfield", {}).get("display_name", ""),
                "field": t.get("field", {}).get("display_name", ""),
                "domain": t.get("domain", {}).get("display_name", ""),
            }
        )

    return OpenAlexData(
        openalex_id=raw.get("id"),
        display_name=raw.get("display_name"),
        topics=topics,
    )


def batch_fetch_openalex(
    issns: list[str],
    api_key: str = "",
    workers: int = 20,
) -> dict[str, OpenAlexData]:
    """Fetch OpenAlex data for many ISSNs in parallel.

    Uses ThreadPoolExecutor for concurrent HTTP requests.
    With api_key set, OpenAlex gives higher rate limits.
    Get a free key at https://openalex.org/settings/api
    """
    results = {}
    total = len(issns)
    counter = {"done": 0}
    lock = Lock()

    def _fetch_one(issn):
        return issn, fetch_openalex(issn, api_key=api_key)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_fetch_one, issn): issn for issn in issns}

        for future in as_completed(futures):
            issn, data = future.result()
            with lock:
                counter["done"] += 1
                if data:
                    results[issn] = data
                if counter["done"] % 500 == 0:
                    print(f"  OpenAlex: {counter['done']}/{total} fetched, {len(results)} matched")

    print(f"  OpenAlex: {total}/{total} done, {len(results)} matched")
    return results


def enrich_journals(
    journals: list,
    scimago: dict[str, ScimagoData],
    openalex: dict[str, OpenAlexData] | None = None,
) -> list[dict]:

    if openalex is None:
        openalex = {}

    enriched = []

    for journal in journals:
        # Try ISSN first, fall back to eISSN for Scimago match
        sci = None
        if journal.issn:
            sci = scimago.get(journal.issn)
        if not sci and journal.eissn:
            sci = scimago.get(journal.eissn)

        # Same lookup strategy for OpenAlex
        oal = None
        if journal.issn:
            oal = openalex.get(journal.issn)
        if not oal and journal.eissn:
            oal = openalex.get(journal.eissn)

        record = {
            "number": journal.number,
            "title": journal.title,
            "issn": journal.issn,
            "eissn": journal.eissn,
            "publisher": journal.publisher,
            # Scimago fields (None if no match)
            "sjr": sci.sjr if sci else None,
            "quartile": sci.quartile if sci else None,
            "h_index": sci.h_index if sci else None,
            "categories": sci.categories if sci else None,
            "areas": sci.areas if sci else None,
            "citations_per_doc": sci.citations_per_doc if sci else None,
            "open_access": sci.open_access if sci else False,
            "open_access_diamond": sci.open_access_diamond if sci else False,
            # OpenAlex fields (None/empty if no match)
            "openalex_id": oal.openalex_id if oal else None,
            "openalex_topics": json.dumps(oal.topics) if oal else None,
        }

        enriched.append(record)

    return enriched
