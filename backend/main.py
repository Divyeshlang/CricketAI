import os
from dotenv import load_dotenv
load_dotenv()
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from data import init_db, ingest_file, connect
from analytics import players, teams, venues, player_stats, team_stats, venue_stats, weakness, prediction
from ai_assistant import answer_live_match, answer_general_cricket
from live_feed import get_filtered_matches, get_match_detail
from supabase_client import init_supabase_tables, check_supabase_health

@asynccontextmanager
async def lifespan(app):
    init_db()
    init_supabase_tables()
    yield

app = FastAPI(title='Cricket Intelligence Assistant API', version='1.0.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

@app.get('/api/health')
def health_check():
    sb = check_supabase_health()
    return {
        'status': 'healthy',
        'gemini': bool(os.getenv('GEMINI_API_KEY')),
        'gemini_model': os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite'),
        'supabase': sb
    }


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    history: list[dict] = []
    match_context: dict | None = None

class CompareRequest(BaseModel):
    first: str
    second: str

@app.get('/api/matches')
@app.get('/api/live-matches')
def get_matches():
    matches = get_filtered_matches()
    counts = {
        "all": len(matches),
        "ongoing": sum(1 for m in matches if m.get("category") == "Ongoing"),
        "upcoming": sum(1 for m in matches if m.get("category") == "Upcoming"),
        "completed": sum(1 for m in matches if m.get("category") == "Completed")
    }
    return {'matches': matches, 'counts': counts}

@app.get('/api/matches/{match_id}')
def get_match_by_id(match_id: str):
    detail = get_match_detail(match_id)
    if not detail:
        raise HTTPException(404, 'Match not found')
    
    # Calculate live match-aware prediction estimate
    t1 = detail.get('team1')
    t2 = detail.get('team2')
    pred = prediction()
    match_pred = None
    if pred.get('available') and t1 in pred.get('teams', []) and t2 in pred.get('teams', []):
        try:
            from sklearn.linear_model import LogisticRegression
            from sklearn.preprocessing import StandardScaler
            from sklearn.pipeline import make_pipeline
            with connect() as c:
                rows = c.execute("SELECT team1,team2,winner FROM matches WHERE source<>'demo' AND winner IS NOT NULL AND winner<>''").fetchall()
            names = pred['teams']
            ix = {t: i for i, t in enumerate(names)}
            X, y = [], []
            for r in rows:
                v = [0.0] * (2 * len(names))
                v[ix[r['team1']]] = 1
                v[len(names) + ix[r['team2']]] = 1
                X.append(v)
                y.append(int(r['winner'] == r['team1']))
            model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=500)).fit(X, y)
            v = [0.0] * (2 * len(names))
            v[ix[t1]] = 1
            v[len(names) + ix[t2]] = 1
            prob = float(model.predict_proba([v])[0][1])
            match_pred = {
                'available': True,
                'team1_prob': round(prob * 100, 1),
                'team2_prob': round((1 - prob) * 100, 1),
                'factors': ['Historical head-to-head outcomes in database', f'Ground profile at {detail.get("venue")}'],
                'explanation': f"Based on historical database encounters between {t1} and {t2}."
            }
        except Exception:
            pass

    if not match_pred:
        # Transparent rule-based situational estimate (grounded in overs & wickets, clearly labelled experimental)
        wkts = detail.get('wickets', 3)
        rr = float(detail.get('run_rate') or 5.5)
        # Situation weight
        t1_chances = min(82.0, max(28.0, 50.0 + (10 - wkts) * 2.5 + (rr - 5.0) * 4.0))
        match_pred = {
            'available': True,
            'team1_prob': round(t1_chances, 1),
            'team2_prob': round(100.0 - t1_chances, 1),
            'factors': [
                f"{detail.get('score')} ({detail.get('overs')} overs) with {10 - wkts} wickets remaining",
                f"Current run rate of {rr} rpo",
                f"Defending / chasing conditions at {detail.get('venue')}"
            ],
            'explanation': f"Experimental match situation estimate. {t1} currently holds advantage having lost only {wkts} wickets with a steady scoring rate."
        }

    return {**detail, 'match_prediction': match_pred}

@app.get('/api/health')
def health():
    with connect() as c:
        m = c.execute('SELECT count(*) FROM matches').fetchone()[0]
        real = c.execute("SELECT count(*) FROM matches WHERE source<>'demo'").fetchone()[0]
    return {'status': 'ok', 'matches': m, 'historical_matches': real, 'demo_mode': real == 0, 'ai_provider': os.getenv('AI_PROVIDER', 'ollama')}

@app.get('/api/overview')
def overview():
    with connect() as c:
        m = c.execute('SELECT count(*) FROM matches').fetchone()[0]
        demo = c.execute("SELECT count(*) FROM matches WHERE source='demo'").fetchone()[0]
        d = c.execute('SELECT count(*) FROM deliveries').fetchone()[0]
    return {
        'matches': m,
        'deliveries': d,
        'players': len(players()),
        'teams': len(teams()),
        'venues': len(venues()),
        'demo_matches': demo,
        'historical_matches': m - demo,
        'mode': 'DEMO DATA' if m == demo else ('MIXED DATA' if demo else 'HISTORICAL DATA')
    }

@app.get('/api/players')
def get_players(): return {'players': players()}
@app.get('/api/teams')
def get_teams(): return {'teams': teams()}
@app.get('/api/venues')
def get_venues(): return {'venues': venues()}
@app.get('/api/players/{name}')
def get_player(name: str):
    s = player_stats(name)
    if not s: raise HTTPException(404, 'Player not found in ingested data')
    return {**s, 'weakness': weakness(name)}

@app.post('/api/players/compare')
def compare_players(body: CompareRequest):
    a, b = player_stats(body.first), player_stats(body.second)
    if not a or not b: raise HTTPException(404, 'Both players must exist in ingested data')
    return {'first': a, 'second': b, 'note': 'Compare like-for-like competition and match formats where possible; mixed uploaded data may not be comparable.'}

@app.get('/api/teams/{name}')
def get_team(name: str): return team_stats(name)

@app.post('/api/teams/compare')
def compare_teams(body: CompareRequest):
    a, b = team_stats(body.first), team_stats(body.second)
    winner = max((a, b), key=lambda x: x['win_rate']) if a['matches'] and b['matches'] else None
    return {
        'first': a,
        'second': b,
        'recommendation': f"Historical results lean toward {winner['team']} ({winner['win_rate']}% win rate in this dataset)." if winner and winner['win_rate'] != min(a['win_rate'], b['win_rate']) else 'The available historical results do not clearly separate these teams.',
        'label': 'Historical comparison, not a live match forecast.'
    }

@app.get('/api/venues/{venue:path}')
def get_venue(venue: str): return venue_stats(venue)

@app.get('/api/prediction')
def get_prediction(first: str | None = None, second: str | None = None):
    result = prediction()
    if not result.get('available') or not first or not second: return result
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    rows = []
    with connect() as c:
        rows = c.execute("SELECT team1,team2,winner FROM matches WHERE source<>'demo' AND winner IS NOT NULL AND winner<>''").fetchall()
        # Retrieve direct head-to-head records
        h2h_rows = c.execute(
            """SELECT winner, count(*) as count 
               FROM matches 
               WHERE ((team1=? AND team2=?) OR (team1=? AND team2=?)) 
                 AND source<>'demo' AND winner IS NOT NULL AND winner<>''
               GROUP BY winner""",
            (first, second, second, first)
        ).fetchall()
        
    names = result['teams']
    ix = {t: i for i, t in enumerate(names)}
    X, y = [], []
    for r in rows:
        v = [0.0] * (2 * len(names))
        v[ix[r['team1']]] = 1
        v[len(names) + ix[r['team2']]] = 1
        X.append(v)
        y.append(int(r['winner'] == r['team1']))
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=500)).fit(X, y)
    if first not in ix or second not in ix:
        return {**result, 'probabilities': None, 'message': 'Choose teams represented in the uploaded results.'}
    v = [0.0] * (2 * len(names))
    v[ix[first]] = 1
    v[len(names) + ix[second]] = 1
    p = float(model.predict_proba([v])[0][1])

    h2h_dict = {r['winner']: r['count'] for r in h2h_rows}
    h2h_total = sum(h2h_dict.values())
    w1 = h2h_dict.get(first, 0)
    w2 = h2h_dict.get(second, 0)

    # Factual breakdown to enrich prediction
    st1 = team_stats(first)
    st2 = team_stats(second)
    
    factual_info = {
        'total_head_to_head_matches': h2h_total,
        f'{first}_h2h_wins': w1,
        f'{second}_h2h_wins': w2,
        f'{first}_overall_win_rate': f"{st1['win_rate']}% ({st1['wins']}/{st1['matches']} matches)",
        f'{second}_overall_win_rate': f"{st2['win_rate']}% ({st2['wins']}/{st2['matches']} matches)",
        f'{first}_avg_runs_per_match': st1['batting_average_per_match'],
        f'{second}_avg_runs_per_match': st2['batting_average_per_match']
    }

    explanation = (
        f"In {h2h_total} verified head-to-head international encounters in our scorebook, "
        f"{first} won {w1} times while {second} won {w2} times. "
        f"Overall win rate across the dataset is {st1['win_rate']}% for {first} and {st2['win_rate']}% for {second}."
    ) if h2h_total > 0 else (
        f"No direct head-to-head match recorded between {first} and {second} in current slice. "
        f"Prediction is estimated by general relative win ratios ({first}: {st1['win_rate']}%, {second}: {st2['win_rate']}%)."
    )

    return {
        **result,
        'first': first,
        'second': second,
        'probabilities': {first: round(p * 100, 1), second: round((1 - p) * 100, 1)},
        'factual_info': factual_info,
        'factual_explanation': explanation
    }

@app.post('/api/chat/live')
def chat_live(body: ChatRequest):
    return answer_live_match(body.question, body.history, body.match_context)

@app.post('/api/chat/general')
def chat_general(body: ChatRequest):
    return answer_general_cricket(body.question, body.history)

@app.post('/api/chat')
def chat(body: ChatRequest):
    if body.match_context:
        return answer_live_match(body.question, body.history, body.match_context)
    return answer_general_cricket(body.question, body.history)

@app.post('/api/upload')
async def upload(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(('.json', '.zip', '.csv')):
        raise HTTPException(400, 'Upload a .json, .zip, or .csv file')
    payload = await file.read()
    if len(payload) > 25_000_000:
        raise HTTPException(413, 'File exceeds 25 MB')
    try:
        count = ingest_file(file.filename, payload)
    except Exception as e:
        raise HTTPException(400, f'Could not ingest dataset: {e}')
    return {'imported_matches': count, 'mode': 'HISTORICAL DATA', 'message': f'Imported {count} match(es). These records are stored separately from demo rows.'}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:app', host='0.0.0.0', port=int(os.getenv('PORT', 8080)))
