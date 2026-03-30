import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from journal_matcher.parser import parse_dgrsdt_pdf, parse_csv_fallback
from journal_matcher.enricher import load_scimago, batch_fetch_openalex, enrich_journals
from journal_matcher.storage import init_db, insert_journals, get_stats
from journal_matcher.keywords import extract_title_keywords


DATA_DIR = Path(__file__).parent / 'data'
DEFAULT_CSV = DATA_DIR / 'journals_parsed.csv'
DEFAULT_SCIMAGO = DATA_DIR / 'scimago.csv'
DEFAULT_DB = DATA_DIR / 'journals.db'


def main():
    parser = argparse.ArgumentParser(description='Build journal matcher database')
    parser.add_argument('--pdf', type=str, help='Path to DGRSDT PDF (uses CSV fallback if omitted)')
    parser.add_argument('--csv', type=str, default=str(DEFAULT_CSV), help='Path to parsed journals CSV')
    parser.add_argument('--scimago', type=str, default=str(DEFAULT_SCIMAGO), help='Path to Scimago CSV')
    parser.add_argument('--db', type=str, default=str(DEFAULT_DB), help='Output database path')
    parser.add_argument('--skip-openalex', action='store_true', help='Skip OpenAlex API enrichment')
    parser.add_argument('--api-key', type=str, default='', help='OpenAlex API key (free at https://openalex.org/settings/api)')
    args = parser.parse_args()

    start = time.time()

    print("Step 1: Parsing journals...")
    if args.pdf:
        journals = parse_dgrsdt_pdf(args.pdf)
        print(f"  Parsed {len(journals)} journals from PDF")
    else:
        journals = parse_csv_fallback(args.csv)
        print(f"  Loaded {len(journals)} journals from CSV")

    print("\nStep 2: Loading Scimago data...")
    scimago = load_scimago(args.scimago)
    print(f"  Loaded {len(scimago)} ISSN entries from Scimago")

    openalex = {}
    if not args.skip_openalex:
        print("\nStep 3: Fetching OpenAlex topics...")
        # Collect all unique ISSNs from parsed journals
        issns = set()
        for j in journals:
            if j.issn:
                issns.add(j.issn)
            if j.eissn:
                issns.add(j.eissn)
        print(f"  {len(issns)} unique ISSNs to look up (20 parallel workers)")
        openalex = batch_fetch_openalex(list(issns), api_key=args.api_key)
    else:
        print("\nStep 3: Skipping OpenAlex (--skip-openalex)")

    print("\nStep 4: Enriching journals...")
    enriched = enrich_journals(journals, scimago, openalex)

    # Add title keywords to each record
    for record in enriched:
        record['title_keywords'] = ' '.join(extract_title_keywords(record['title']))

    scimago_count = sum(1 for r in enriched if r.get('quartile'))
    openalex_count = sum(1 for r in enriched if r.get('openalex_topics'))
    print(f"  {len(enriched)} journals enriched")
    print(f"  Scimago matches: {scimago_count}")
    print(f"  OpenAlex matches: {openalex_count}")

    print("\nStep 5: Building database...")
    if os.path.exists(args.db):
        os.remove(args.db)

    conn = init_db(args.db)
    insert_journals(conn, enriched)

    # Print final stats
    stats = get_stats(conn)
    conn.close()

    elapsed = time.time() - start
    print(f"\nDone in {elapsed:.1f}s")
    print(f"  Total journals: {stats['total']}")
    print(f"  Enriched: {stats['enriched']} ({stats['enrichment_rate']}%)")
    print(f"  Quartile distribution: {stats['quartile_distribution']}")
    print(f"  Database saved to: {args.db}")


if __name__ == '__main__':
    main()
