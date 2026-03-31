# Korzennik

Automated genealogy tree builder with Polish source specialization. Searches 8 genealogical databases, cross-validates records, and recursively discovers ancestors.

## Features

- **8 data sources**: FamilySearch, Geneteka, Find A Grave, BillionGraves, szukajwarchiwach.gov.pl, Ellis Island, MyHeritage, Ancestry
- **Polish name matching engine**: handles gender declension (Kowalski/Kowalska), Latin church forms (Joannes/Jan), historical spellings, patronymics, diacritics
- **Confidence scoring**: weighted 0-100% score across 7 factors with full breakdown transparency
- **Cross-validation**: matches confirmed by 2+ sources get lower auto-confirm threshold
- **Recursive auto-discovery**: click "Szukaj przodkow" and the system searches all nodes, discovers parents, and recursively builds the tree up to 10 generations
- **GEDCOM import/export**: compatible with all genealogy software
- **Interactive tree visualization**: React + ReactFlow with dagre layout
- **Emigration tracking**: Ellis Island manifests, ship records, immigration data

## Quick Start

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### Configuration

Copy `.env.example` to `backend/.env` and fill in:

```
KORZENNIK_FAMILYSEARCH_APP_KEY=your_key_here
```

FamilySearch API key is optional - the other 7 sources work without it. Register at https://developers.familysearch.org/ to get a free key.

## Architecture

```
Frontend (React + TypeScript + ReactFlow)
        |
   Backend API (Python/FastAPI)
        |
   +--------+----------+-----------+
   |        |          |           |
FamilySearch Geneteka  FindAGrave  ... (8 sources)
   |
   Matching Engine (Polish rules + phonetic + fuzzy)
   |
   Confidence Scoring (7-factor weighted)
   |
   Auto-Discovery (recursive, cross-validated)
   |
   SQLite + GEDCOM export
```

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy (async), httpx, jellyfish, selectolax
- **Frontend**: React 19, TypeScript, Vite, ReactFlow, TanStack Query, Tailwind CSS
- **Database**: SQLite with WAL mode

## License

MIT
