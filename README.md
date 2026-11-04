# Boundary — Cricket Intelligence Assistant

A local-first cricket analytics MVP. The React dashboard talks to a FastAPI service backed by SQLite. It can start with no API keys and no network connection to a paid service.

## Features

- Natural-language cricket assistant using Ollama when available, with a deterministic rule-based fallback.
- SQLite-backed player and team scorecards, head-to-head comparisons, and venue innings summaries.
- Cricsheet JSON / ZIP and documented CSV ingestion through the UI.
- Experimental scikit-learn outcome model, trained only from imported historical match results. Demo rows are excluded. It becomes available after at least 8 eligible matches with both outcome classes.
- Demo mode with visibly labelled illustrative records so the UI works before importing data.
- Responsive dark/light dashboard.

Delivery-style weaknesses (pace, spin, yorker, bouncer, bowling arm) are reported as unavailable unless source data provides reliable labels. No live score API is connected; the app does not display simulated scores as live scores.

## Run locally

Requirements: Python 3.10+ and Node.js 18+.

### 1. Start the backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python main.py
```

The API runs at `http://localhost:8000`; interactive API documentation is at `http://localhost:8000/docs`. SQLite is created at `backend/cricket.db` on first start. Set `CRICKET_DB` to choose another path.

### 2. Start the frontend

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The frontend uses `http://localhost:8000/api` by default. Set `VITE_API_URL` before starting Vite if the API uses another address, for example `https://your-api.example/api`.

## Ollama (optional)

The app works without Ollama. To enable local LLM explanations, install Ollama, pull a model such as `llama3.2`, start Ollama, and set these values in `backend/.env`:

```dotenv
AI_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

If Ollama is missing, slow, or returns an error, chat requests use the rule-based fallback. Both modes use statistics retrieved from SQLite; the language model is instructed not to supply unsupported numbers.

## Import historical data

Choose **Import dataset** in the left navigation.

- `.json`: one Cricsheet match JSON.
- `.zip`: a ZIP containing Cricsheet JSON match files.
- `.csv`: one row per delivery with these columns:

```text
match_id,date,venue,team1,team2,winner,innings,batting_team,over,batter,bowler,batter_runs,total_runs,wicket,dismissal
```

Dates should sort lexically (`YYYY-MM-DD`). `over` is the zero-based over number as used in Cricsheet. `wicket` is `1` or `0`; optional `dismissal` should use standard dismissal names. CSV imports treat an entry with equal `total_runs` and `batter_runs` as a legal ball; for precise extras and legal-ball counts, prefer Cricsheet JSON. Uploads are limited to 25 MB.

Imported scorecards are labeled historical. Illustrative demo scorecards are stored with a separate source marker. The model only selects matches with imported historical outcomes; it never uses demo rows. If your SQLite database needs a clean reset, stop the backend and remove `backend/cricket.db`; the next start creates a fresh demo database.

## API summary

- `GET /api/health`, `/api/overview`
- `GET /api/players`, `/api/players/{name}`
- `POST /api/players/compare` with `{ "first": "...", "second": "..." }`
- `GET /api/teams`, `/api/teams/{name}`, `POST /api/teams/compare`
- `GET /api/venues`, `/api/venues/{venue}`
- `GET /api/prediction?first=...&second=...`
- `POST /api/chat` with `{ "question": "...", "history": [] }`
- `POST /api/upload` multipart form field `file`

## Limits

- The included records are synthetic UI demo data and are not real match/player statistics.
- Recent form is the latest five match IDs found for that player in the selected source. Tournament and format are not inferred, so comparisons across mixed formats may be misleading.
- Bowling economy and wickets are derived from delivery rows; CSV quality affects accuracy.
- The predictor is intentionally small and experimental. It uses team identity and historical winners only, with no toss, venue, squad, current-match, or calibration features. Eight records are a low operating threshold, not a claim of statistical reliability.
- Cricsheet does not consistently provide the delivery taxonomy needed for weakness analysis. Live score integrations are not included.

## Deployment notes

The frontend can be built with `npm run build` and served by static hosting. Run the FastAPI service with `uvicorn main:app --host 0.0.0.0 --port 8000` from `backend`. For persistent hosting, mount a durable volume for SQLite and set `CRICKET_DB` to that mounted path; ephemeral server filesystems will lose the database when recycled. Configure `CORS_ORIGINS` with the frontend origin. No paid service or credential is required for core features.
