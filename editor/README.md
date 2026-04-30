# Cavallin Lexicon — web editor & public viewer

Web presence for the 1873 Christian Cavallin *Latinskt lexicon* at `alatius.com/cavallinlatin/`.

## Dev setup

```bash
cd editor

# Backend
python3.12 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env

# First-time: regenerate column PNGs, import XML, seed admin
python -m app.scripts.convert_tiff_to_png        # ../columns/*.tiff -> data/columns/*.png (gitignored; ~2-3 min)
python -m app.scripts.import_xml                 # cavallinlatin.xml -> SQLite
python -m app.scripts.create_admin               # prompts for admin password

# Run backend
(cd backend && uvicorn app.main:app --reload --port 8001)

# Frontend (in another terminal)
cd frontend
npm install
npm run dev    # http://localhost:5173/cavallinlatin/
```

## Layout

- `backend/app/` — FastAPI app (routers, scripts, security)
- `frontend/src/` — React + Vite + CodeMirror
- `data/` — SQLite database (gitignored), master XML (committed), column images (gitignored, regenerated from `../columns/*.tiff`)
- `deploy/` — systemd unit, Apache vhost snippet, runbook

## Production deploy

See `deploy/README.md`.
