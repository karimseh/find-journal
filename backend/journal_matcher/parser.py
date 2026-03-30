"""PDF table extraction for DGRSDT Category A journal list."""

from dataclasses import dataclass

import pandas as pd
import pdfplumber

from . import utils


@dataclass
class RawJournal:
    number: int
    title: str
    issn: str | None
    eissn: str | None
    publisher: str


def parse_dgrsdt_pdf(pdf_path: str) -> list[RawJournal]:
    """Extract all journals from the DGRSDT Category A PDF.

    The DGRSDT PDF is a large table spanning hundreds of pages.
    Each row has 5 columns: [number, title, issn, eissn, publisher].

    Tricky part: pdfplumber sometimes splits a single journal entry
    across two rows at page boundaries:
      Row A: ['', 'JOURNAL TITLE', '', '', '']         (title but no number)
      Row B: ['35', None, '0951-3574', '1758-4205', 'Pub']  (number but no title)
    This function detects and merges such split rows.
    """
    all_rows = []

    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            table = page.extract_table()
            if table:
                # Keep only rows with at least 5 columns
                all_rows.extend(row for row in table if row and len(row) >= 5)
            # Free memory after each page
            page.flush_cache()

            if (i + 1) % 50 == 0:
                print(f"  Parsed {i + 1}/{total} pages...")

    print(f"  Parsed {total}/{total} pages, merging rows...")
    return _merge_rows(all_rows)


def _merge_rows(all_rows: list[list]) -> list[RawJournal]:
    """Process raw table rows, merging entries split across page boundaries.

    Handles two cases:
    1. Normal row: has number + title + ISSNs + publisher → create journal directly
    2. Split row: first row has title only, next row has number + ISSNs → merge them
    """
    journals = []
    pending_title = None

    for row in all_rows:
        cell0 = (row[0] or "").strip()  # number
        cell1 = utils.clean_text(row[1]) if row[1] else ""  # title
        cell2 = row[2] or ""  # issn
        cell3 = row[3] or ""  # eissn
        cell4 = utils.clean_text(row[4]) if row[4] else ""  # publisher

        # Skip header rows (contain "N°" or similar)
        if "N" in cell0 and "°" in cell0:
            continue

        has_number = cell0.replace(".", "").isdigit()

        if not has_number and cell1:
            # Title-only row — save it, expect a number-only row next
            pending_title = cell1
            continue

        if has_number:
            try:
                number = int(cell0.replace(".", ""))
            except ValueError:
                continue

            # Use this row's title, or the pending one from a split row
            if cell1:
                title = cell1
                pending_title = None
            elif pending_title:
                title = pending_title
                pending_title = None
            else:
                continue  # No title available — skip

            journals.append(
                RawJournal(
                    number=number,
                    title=title,
                    issn=utils.normalize_issn(cell2) if cell2.strip() else None,
                    eissn=utils.normalize_issn(cell3) if cell3.strip() else None,
                    publisher=cell4,
                )
            )

    return journals


def parse_csv_fallback(csv_path: str) -> list[RawJournal]:
    """Load journals from CSV as alternative to PDF parsing.
    Useful if you've already parsed the PDF once and exported to CSV.
    Expected columns: number, title, issn, eissn, publisher
    """
    df = pd.read_csv(csv_path)
    journals = []

    for _, row in df.iterrows():
        journals.append(
            RawJournal(
                number=int(row.get("number", 0)),
                title=str(row.get("title", "")),
                issn=(
                    utils.normalize_issn(str(row.get("issn", "")))
                    if pd.notna(row.get("issn"))
                    else None
                ),
                eissn=(
                    utils.normalize_issn(str(row.get("eissn", "")))
                    if pd.notna(row.get("eissn"))
                    else None
                ),
                publisher=str(row.get("publisher", "")),
            )
        )

    return journals
