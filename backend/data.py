"""SQLite persistence, transparent demo seed data, and Cricsheet ingestion."""
import json, os, sqlite3, zipfile, io, csv, hashlib
from pathlib import Path

DB_PATH = os.getenv("CRICKET_DB", str(Path(__file__).with_name("cricket.db")))

def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db

def init_db():
    with connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS matches(id TEXT PRIMARY KEY, date TEXT, venue TEXT, city TEXT, team1 TEXT, team2 TEXT, winner TEXT, result TEXT, source TEXT NOT NULL DEFAULT 'cricsheet');
        CREATE TABLE IF NOT EXISTS deliveries(id INTEGER PRIMARY KEY AUTOINCREMENT, match_id TEXT REFERENCES matches(id) ON DELETE CASCADE, innings INTEGER, batting_team TEXT, over_no INTEGER, batter TEXT, bowler TEXT, batter_runs INTEGER, total_runs INTEGER, extras INTEGER, legal_ball INTEGER NOT NULL DEFAULT 1, wicket INTEGER, dismissal TEXT, source TEXT NOT NULL DEFAULT 'cricsheet');
        CREATE INDEX IF NOT EXISTS idx_del_player ON deliveries(batter); CREATE INDEX IF NOT EXISTS idx_del_match ON deliveries(match_id);
        ''')
        if 'legal_ball' not in [r[1] for r in c.execute('PRAGMA table_info(deliveries)')]: c.execute('ALTER TABLE deliveries ADD COLUMN legal_ball INTEGER NOT NULL DEFAULT 1')
        if c.execute("SELECT count(*) FROM matches WHERE source='demo'").fetchone()[0] == 0: seed_demo(c)

def seed_demo(c):
    """Illustrative records only. Never include these rows in model training."""
    players = ["Virat Kohli","Rohit Sharma","Jasprit Bumrah","Ravindra Jadeja","Shubman Gill","Hardik Pandya","Babar Azam","Shaheen Shah Afridi","Mohammad Rizwan","Shadab Khan","Jos Buttler","Ben Stokes","Jofra Archer","Joe Root","Kane Williamson","Trent Boult","Glenn Maxwell","David Warner","Pat Cummins","Steve Smith"]
    teams=["India","Pakistan","England","New Zealand","Australia"]
    venues=["Wankhede Stadium","M. Chinnaswamy Stadium","Narendra Modi Stadium","Eden Gardens","Dubai International Cricket Stadium"]
    c.executemany("INSERT OR IGNORE INTO matches VALUES(?,?,?,?,?,?,?,?,?)", [(f'DEMO-{i+1:03}',f'2024-{(i%12)+1:02}-{(i%27)+1:02}',venues[i%len(venues)], ["Mumbai","Bengaluru","Ahmedabad","Kolkata","Dubai"][i%5],teams[i%5],teams[(i+1)%5],teams[i%5] if i%4!=0 else teams[(i+1)%5],"runs" if i%2 else "wickets","demo") for i in range(30)])
    import random
    rng=random.Random(42); rows=[]
    for match_idx in range(30):
        t1,t2=teams[match_idx%5],teams[(match_idx+1)%5]
        for inn,team,opp in [(1,t1,t2),(2,t2,t1)]:
            batters=[p for j,p in enumerate(players) if j%5==teams.index(team)]
            bowlers=[p for j,p in enumerate(players) if j%5==teams.index(opp)]
            over=0
            for ball in range(120):
                batter=batters[(ball//12)%len(batters)]; bowler=bowlers[(ball//12)%len(bowlers)]
                br=rng.choices([0,1,2,3,4,6],[.42,.32,.08,.01,.13,.04])[0]
                wicket=1 if rng.random()<.028 else 0
                rows.append((f'DEMO-{match_idx+1:03}',inn,team,over,batter,bowler,br,br,0,1,wicket,"caught" if wicket else None,"demo"))
                over=(over+1)%20
    c.executemany("INSERT INTO deliveries(match_id,innings,batting_team,over_no,batter,bowler,batter_runs,total_runs,extras,legal_ball,wicket,dismissal,source) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",rows)

def parse_cricsheet(doc, source, match_key=None):
    info=doc.get('info',{}); teams=info.get('teams',[]); outcome=info.get('outcome',{}) or {}
    mid=Path(match_key).stem[:100] if match_key else hashlib.sha256(json.dumps(info,sort_keys=True).encode()).hexdigest()[:16]
    match=(mid,str((info.get('dates') or [''])[0]),info.get('venue','Unknown venue'),info.get('city',''),teams[0] if teams else '',teams[1] if len(teams)>1 else '',outcome.get('winner'),outcome.get('by',{}).get('runs') and 'runs' or outcome.get('by',{}).get('wickets') and 'wickets' or outcome.get('result',''),source)
    rows=[]
    for inn_no,inn in enumerate(doc.get('innings',[]),1):
        team=inn.get('team','')
        for ov in inn.get('overs',[]):
            for d in ov.get('deliveries',[]):
                extras=d.get('extras',{}); bat=d.get('runs',{}).get('batter',0); total=d.get('runs',{}).get('total',bat); wickets=d.get('wickets',[]); w=wickets[0] if wickets else None
                legal=int('wides' not in extras and 'noballs' not in extras)
                rows.append((mid,inn_no,team,int(ov.get('over',0)),d.get('batter',''),d.get('bowler',''),bat,total,total-bat,legal,int(bool(w)),w.get('kind') if w else None,source))
    return match, rows

def ingest_file(name, payload):
    source='cricsheet'; files=[]
    if name.lower().endswith('.zip'):
        z=zipfile.ZipFile(io.BytesIO(payload)); files=[(n,z.read(n)) for n in z.namelist() if n.lower().endswith('.json')]
    elif name.lower().endswith('.json'): files=[(name,payload)]
    elif name.lower().endswith('.csv'):
        # CSV columns: match_id,date,venue,team1,team2,winner,innings,batting_team,over,batter,bowler,batter_runs,total_runs,wicket
        data=list(csv.DictReader(io.StringIO(payload.decode('utf-8-sig')))); grouped={}
        for r in data:
            mid=r['match_id']; grouped.setdefault(mid,[]).append(r)
        with connect() as c:
            count=0
            for mid,rs in grouped.items():
                f=rs[0]; c.execute('INSERT OR REPLACE INTO matches VALUES(?,?,?,?,?,?,?,?,?)',(mid,f.get('date',''),f.get('venue','Unknown venue'),f.get('city',''),f.get('team1',''),f.get('team2',''),f.get('winner') or None,'',source)); c.execute('DELETE FROM deliveries WHERE match_id=?',(mid,))
                c.executemany('INSERT INTO deliveries(match_id,innings,batting_team,over_no,batter,bowler,batter_runs,total_runs,extras,legal_ball,wicket,dismissal,source) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',[(mid,int(r.get('innings',1)),r.get('batting_team',''),int(float(r.get('over',0))),r.get('batter',''),r.get('bowler',''),int(r.get('batter_runs',0)),int(r.get('total_runs',0)),int(r.get('total_runs',0))-int(r.get('batter_runs',0)),int(r.get('total_runs',0))==int(r.get('batter_runs',0)),int(r.get('wicket',0)),r.get('dismissal') or None,source) for r in rs]); count+=1
        return count
    else: raise ValueError('Upload a Cricsheet JSON, ZIP of JSON files, or CSV in the documented format.')
    count=0
    with connect() as c:
        for _,raw in files:
            match,rows=parse_cricsheet(json.loads(raw),source,_); c.execute('INSERT OR REPLACE INTO matches VALUES(?,?,?,?,?,?,?,?,?)',match); c.execute('DELETE FROM deliveries WHERE match_id=?',(match[0],)); c.executemany('INSERT INTO deliveries(match_id,innings,batting_team,over_no,batter,bowler,batter_runs,total_runs,extras,legal_ball,wicket,dismissal,source) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',rows); count+=1
    return count
