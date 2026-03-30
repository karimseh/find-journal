# FindJournal

FindJournal helps Algerian researchers identify suitable journals for their work from the DGRSDT Category A list (~13,600 journals). 

## Features

- **Abstract matching** — paste your abstract, get ranked journal suggestions with similarity scores
- **Browse & search** — explore the full catalog by title, quartile, or minimum SJR
- **Rich metadata** — SJR, quartile (Q1-Q4), H-index, subject categories, areas
- **Open access status** — Diamond OA, Gold OA, or subscription-based



## Quick start

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Build the database (first time only)
python build_db.py --api-key YOUR_OPENALEX_KEY

# Start the API server
python -m flask --app api run
```

The server runs on `http://localhost:5000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The dev server runs on `http://localhost:5173`.

## Building the database

The `build_db.py` script parses journal data, enriches it with Scimago and OpenAlex metadata, and builds the SQLite database.

```
python build_db.py [options]

Options:
  --pdf PATH           Path to DGRSDT PDF (uses CSV fallback if omitted)
  --csv PATH           Path to parsed journals CSV (default: data/journals_parsed.csv)
  --scimago PATH       Path to Scimago CSV (default: data/scimago.csv)
  --db PATH            Output database path (default: data/journals.db)
  --skip-openalex      Skip OpenAlex API enrichment
  --api-key KEY        OpenAlex API key (free at https://openalex.org/settings/api)
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/match` | Match an abstract to journals. Body: `{"abstract": "...", "top_n": 15}` |
| GET | `/api/search?q=blockchain&limit=20` | Search journals by title |
| GET | `/api/journals?quartile=Q1,Q2&min_sjr=1.0&page=1&per_page=50` | Browse journals with filters |
| GET | `/api/stats` | Database statistics |

## How matching works

FindJournal uses a hybrid scoring algorithm that combines two approaches:

**TF-IDF (60% weight)** — matches exact keywords from your abstract against journal metadata (title, Scimago categories, OpenAlex topics). Catches direct term overlap like "blockchain", "cryptography", "privacy".

**Sentence embeddings (40% weight)** — encodes both the abstract and journal documents into dense vectors using `all-MiniLM-L6-v2`, then measures cosine similarity. Catches semantic relationships where different words express the same concept.

The combined score ensures journals that match on both dimensions rank highest. Embeddings are cached to disk (`.npy` file) and only recomputed when journal data changes.



## Author

Created by [Karim Sehimi](https://karimdev.me)
