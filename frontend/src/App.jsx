import {lazy,Suspense,useEffect,useState} from 'react';
import {Activity,ArrowDownRight,ArrowRight,ArrowUpRight,BarChart3,ChevronDown,ChevronLeft,ChevronRight,Clock3,Database,ExternalLink,Eye,HelpCircle,Home,Info,MapPin,Menu,MessageCircle, Moon,Radio,RefreshCw,Send,Settings2,Shield, Sparkles, Sun, Trophy, Upload, UserRound, Users, X, Zap, BookOpen} from 'lucide-react';
import {api,post} from './services/api';
const RunChart=lazy(()=>import('./components/RunChart.jsx'));

// Main Navigation: General Cricket AI in menu, Live Match AI embedded directly inside Match Tracking
const nav=[
  ['Overview', Home],
  ['Live Match Tracking', Radio],
  ['General Cricket AI Assistant', MessageCircle],
  ['Player Analysis', UserRound],
  ['Player Comparison', Users],
  ['Team Comparison', Trophy],
  ['Pitch & Ground Analysis', MapPin],
  ['Match Prediction', Activity]
];

function App(){
 const [page,setPage]=useState('Overview'),
       [dark,setDark]=useState(true),
       [mobile,setMobile]=useState(false),
       [overview,setOverview]=useState(null),
       [players,setPlayers]=useState([]),
       [teams,setTeams]=useState([]),
       [venues,setVenues]=useState([]),
       [error,setError]=useState(''),
       [selectedMatchId,setSelectedMatchId]=useState('161245'),
       [selectedMatchDetail,setSelectedMatchDetail]=useState(null);

 const refreshData = ()=>{
   Promise.all([api('/overview'),api('/players'),api('/teams'),api('/venues')])
     .then(([o,p,t,v])=>{setOverview(o);setPlayers(p.players);setTeams(t.teams);setVenues(v.venues)})
     .catch(e=>setError(e.message));
 };

 useEffect(()=>{ refreshData(); },[]);

 useEffect(()=>{
   if(!selectedMatchId)return;
   api('/matches/'+encodeURIComponent(selectedMatchId))
     .then(setSelectedMatchDetail)
     .catch(()=>setSelectedMatchDetail(null));
 },[selectedMatchId]);

 function handleSelectMatch(mId){
   setSelectedMatchId(mId);
   setPage('Live Match Tracking');
 }

 return <div className={dark?'app dark':'app light'}>
  <aside className={'sidebar '+(mobile?'show':'')}>
    <div className="brand"><div className="brand-mark"><Activity size={20}/></div><span>boundary<span className="brand-dot">.</span></span><button className="icon-btn close-mobile" onClick={()=>setMobile(false)}><X size={17}/></button></div>
    <div className="side-caption">WORKSPACE</div>
    <nav>{nav.map(([label,Icon])=><button key={label} onClick={()=>{setPage(label);setMobile(false)}} className={'nav-item '+(page===label?'active':'')}><Icon size={17}/><span>{label}</span>{label==='Live Match Tracking'&&selectedMatchDetail&&<span className="live-dot" title="Active match tracking"/>}</button>)}</nav>
    <div className="side-bottom"><button className="nav-item muted" onClick={()=>setPage('Dataset Import')}><Upload size={17}/><span>Import dataset</span></button></div>
  </aside>
  <main className="main">
    <header className="topbar">
      <button className="icon-btn mobile-menu" onClick={()=>setMobile(true)}><Menu size={19}/></button>
      <div className="crumb">Workspace <ChevronRight size={14}/><b>{page}</b>{selectedMatchDetail&&<span className="match-pill-top">Selected: {selectedMatchDetail.team1} vs {selectedMatchDetail.team2}</span>}</div>
      <div className="top-actions"><span className="data-chip"><i/> {overview?.mode||'VERIFIED DATA'}</span><button className="icon-btn" title="Toggle color theme" onClick={()=>setDark(!dark)}>{dark?<Sun size={17}/>:<Moon size={17}/>}</button><div className="top-avatar">C</div></div>
    </header>
    <div className="content">
      {error&&<div className="alert"><HelpCircle size={16}/>{error}.</div>}
      {page==='Overview'&&<Overview setPage={setPage} onSelectMatch={handleSelectMatch} selectedMatchId={selectedMatchId}/>}
      {page==='Live Match Tracking'&&<MatchTrackingPage matchId={selectedMatchId} onSelectMatch={setSelectedMatchId} setPage={setPage}/>}
      {page==='General Cricket AI Assistant'&&<GeneralCricketAIAssistant players={players} teams={teams}/>}
      {page==='Player Analysis'&&<PlayerPage players={players}/>}
      {page==='Player Comparison'&&<PlayerCompare players={players}/>}
      {page==='Team Comparison'&&<TeamCompare teams={teams}/>}
      {page==='Pitch & Ground Analysis'&&<VenuePage venues={venues}/>}
      {page==='Match Prediction'&&<Prediction teams={teams}/>}
      {page==='Dataset Import'&&<ImportPage onDone={refreshData}/>}
    </div>
    <footer><span>Boundary <b>·</b> Cricket Intelligence Assistant</span><span>ICC Full Members & IPL verified coverage · Dual Specialized AI Assistants</span></footer>
  </main>
 </div>;
}

function PageHeading({eyebrow,title,subtitle,action}){
  return <div className="page-head"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{subtitle}</p></div>{action}</div>;
}

// ----------------- OVERVIEW PAGE -----------------
function Overview({setPage, onSelectMatch, selectedMatchId}){
  const [matches,setMatches]=useState([]),
        [counts,setCounts]=useState({all:0,ongoing:0,upcoming:0,completed:0}),
        [tab,setTab]=useState('All'),
        [formatFilter,setFormatFilter]=useState('ALL'),
        [busy,setBusy]=useState(true),
        [err,setErr]=useState('');

  function load(){
    setBusy(true);setErr('');
    api('/matches')
      .then(r=>{
        const list = r.matches||[];
        setMatches(list);
        if(r.counts) {
          setCounts(r.counts);
          // If no ongoing matches right now, default gracefully to Upcoming or All so user sees fixtures
          if (r.counts.ongoing === 0 && r.counts.upcoming > 0) {
            setTab('Upcoming');
          }
        }
      })
      .catch(e=>setErr(e.message))
      .finally(()=>setBusy(false));
  }
  useEffect(()=>{load()},[]);

  const filtered = matches.filter(m=>{
    const matchCat = tab==='All' || m.category===tab;
    const matchFmt = formatFilter==='ALL' || m.format===formatFilter;
    return matchCat && matchFmt;
  });

  return <>
    <div className="overview-header-box">
      <div>
        <span className="eyebrow">CRICKET INTELLIGENCE DASHBOARD</span>
        <h2>Match Discovery & Overview</h2>
        <p>Verified ICC Full Member nations (Test, ODI, T20I) & Indian Premier League matches.</p>
      </div>
      <button className="primary-btn" onClick={load} disabled={busy}>
        <RefreshCw size={15}/> {busy?'Updating…':'Refresh'}
      </button>
    </div>

    {err&&<div className="inline-error">{err}</div>}

    {/* Match Counts & Categories + Format Filters */}
    <div style={{display:'flex', flexDirection:'column', gap:10, marginBottom:16}}>
      <div className="category-tabs-bar" style={{margin:0}}>
        {[['Ongoing', counts.ongoing], ['Upcoming', counts.upcoming], ['Completed', counts.completed], ['All', counts.all]].map(([cat, count])=>(
          <button key={cat} onClick={()=>setTab(cat)} className={'cat-pill '+(tab===cat?'active':'')}>
            {cat==='Ongoing'&&<i className="live-dot-mini"/>}
            <span>{cat} Matches</span>
            <b>{count}</b>
          </button>
        ))}
      </div>

      <div style={{display:'flex', gap:8, alignItems:'center', flexWrap:'wrap'}}>
        <span style={{fontSize:11, textTransform:'uppercase', letterSpacing:'0.06em', color:'var(--muted)', fontWeight:600}}>Format:</span>
        {['ALL', 'TEST', 'ODI', 'T20I', 'IPL'].map(fmt=>(
          <button 
            key={fmt} 
            onClick={()=>setFormatFilter(fmt)}
            style={{
              padding:'4px 10px',
              borderRadius:6,
              fontSize:12,
              fontWeight:600,
              background: formatFilter===fmt?'rgba(204,255,0,0.15)':'var(--surface)',
              color: formatFilter===fmt?'#ccff00':'var(--muted)',
              border: formatFilter===fmt?'1px solid #ccff00':'1px solid var(--border)',
              cursor:'pointer'
            }}
          >
            {fmt}
          </button>
        ))}
      </div>
    </div>

    {busy&&!matches.length?<div className="loading">Checking verified match schedules…</div>:null}

    {/* Match Grid */}
    <div className="match-discovery-grid">
      {filtered.map(m=>(
        <div className={'match-box-card '+(selectedMatchId===m.id?'selected-border':'')} key={m.id}>
          <div className="match-box-top">
            <span className="format-chip">{m.format}</span>
            <span className="tour-name">{m.tournament}</span>
            {m.category==='Ongoing'?<span className="live-badge"><i className="live-dot"/> LIVE</span>:<span className="data-chip">{m.status}</span>}
          </div>
          <div className="match-box-teams">
            <div className="m-team"><b>{m.team1}</b></div>
            <span className="m-vs">vs</span>
            <div className="m-team"><b>{m.team2}</b></div>
          </div>
          <div className="match-box-score">
            <span>{m.score}</span>
            {m.run_rate&&<small>CRR: {m.run_rate}</small>}
          </div>
          <div className="match-box-meta">
            <span><MapPin size={13}/> {m.venue}</span>
            <span><Clock3 size={13}/> {m.date_time}</span>
          </div>
          <div className="match-box-actions">
            <button className="track-btn" onClick={()=>onSelectMatch(m.id)}>
              <Eye size={14}/> Track Match Internally
            </button>
          </div>
        </div>
      ))}
    </div>

    {/* Quick access cards for AI, Player Comparison & Grounds */}
    <div className="section-title"><div><h2>Cricket Intelligence Tools</h2><p>Explore players, head-to-head comparisons, and pitch reports.</p></div></div>
    <div className="quick-grid">
      {[['General Cricket AI','Ask plain-language questions across verified scorecards.',MessageCircle,'General Cricket AI Assistant','01'],
        ['Player Comparison','Compare career runs, averages, and strike rates side by side.',Users,'Player Comparison','02'],
        ['Pitch & Ground Analysis','Explore 1st vs 2nd innings totals and top performers.',MapPin,'Pitch & Ground Analysis','03']].map(([t,d,I,p,n])=>(
        <button className="quick-card" key={t} onClick={()=>setPage(p)}>
          <span className="quick-no">{n}</span><div className="quick-icon"><I size={18}/></div>
          <h3>{t}</h3><p>{d}</p><ArrowRight className="quick-arrow" size={16}/>
        </button>
      ))}
    </div>
  </>;
}

// ----------------- MATCH TRACKING PAGE -----------------
function MatchTrackingPage({matchId, onSelectMatch, setPage}){
  const [data,setData]=useState(null),
        [matches,setMatches]=useState([]),
        [busy,setBusy]=useState(true),
        [err,setErr]=useState(''),
        [tab,setTab]=useState('live');

  function fetchDetail(){
    if(!matchId)return;
    setBusy(true);
    api('/matches/'+encodeURIComponent(matchId))
      .then(setData)
      .catch(e=>setErr(e.message))
      .finally(()=>setBusy(false));
  }

  useEffect(()=>{
    fetchDetail();
    api('/matches').then(r=>setMatches(r.matches||[])).catch(()=>{});
    const timer = setInterval(fetchDetail, 25000);
    return ()=>clearInterval(timer);
  },[matchId]);

  return <>
    <PageHeading
      eyebrow="INTERNAL MATCH TRACKING"
      title={data?`${data.team1} vs ${data.team2}`:'Match Tracking'}
      subtitle="Real-time match tracking inside Boundary. Strictly no external redirects."
      action={
        <div className="action-row">
          <button className={'primary-btn '+(tab==='ai'?'active-track-ai':'zap-btn')} onClick={()=>setTab('ai')}>
            <Zap size={15}/> Live Match AI Assistant
          </button>
          <button className="primary-btn" onClick={fetchDetail} disabled={busy}>
            <RefreshCw size={15}/> {busy?'Updating…':'Refresh'}
          </button>
        </div>
      }
    />

    {/* Match Switcher */}
    <div className="match-switcher-bar">
      <span>Switch Match:</span>
      {matches.map(m=>(
        <button
          key={m.id}
          className={'switch-pill '+(String(m.id)===String(matchId)?'active':'')}
          onClick={()=>onSelectMatch(m.id)}
        >
          {m.category==='Ongoing'&&<i className="live-dot-mini"/>}
          {m.team1} vs {m.team2} ({m.format})
        </button>
      ))}
    </div>

    {err&&<div className="inline-error">{err}</div>}
    {busy&&!data?<div className="loading">Loading match scorebook…</div>:null}

    {data&&<div className="tracking-container">
      <div className="tracking-score-hero">
        <div className="score-hero-left">
          <div className="score-hero-status">
            {data.category==='Ongoing'?<span className="live-badge"><i className="live-dot"/> LIVE</span>:<span className="data-chip">{data.category}</span>}
            <span className="format-tag">{data.format} · {data.tournament}</span>
          </div>
          <h2>{data.score}</h2>
          <div className="score-details-line">
            <span>Overs: <b>{data.overs}</b></span>
            {data.run_rate&&<span>CRR: <b>{data.run_rate}</b></span>}
            {data.target&&<span>Target: <b>{data.target}</b></span>}
            <span>Venue: <b>{data.venue}</b></span>
          </div>
          {data.toss&&<p className="toss-note"><Shield size={13}/> {data.toss}</p>}
        </div>

        {data.match_prediction&&<div className="win-prob-card">
          <span className="eyebrow">ESTIMATED ADVANTAGE (EXPERIMENTAL)</span>
          <div className="prob-numbers">
            <div><span>{data.team1}</span><b>{data.match_prediction.team1_prob}%</b></div>
            <div><span>{data.team2}</span><b>{data.match_prediction.team2_prob}%</b></div>
          </div>
          <div className="prob-track">
            <i style={{width:data.match_prediction.team1_prob+'%'}}/>
          </div>
          <small>{data.match_prediction.explanation}</small>
        </div>}
      </div>

      <div className="track-tabs">
        <button className={tab==='live'?'active':''} onClick={()=>setTab('live')}>Live Situation</button>
        <button className={tab==='squads'?'active':''} onClick={()=>setTab('squads')}>Playing XI & Squads</button>
        <button className={tab==='comms'?'active':''} onClick={()=>setTab('comms')}>Recent Deliveries</button>
        <button className={'tab-ai-pill '+(tab==='ai'?'active':'')} onClick={()=>setTab('ai')}><Zap size={13}/> Live Match AI Assistant</button>
      </div>

      {tab==='live'&&<div className="situation-grid">
        <div className="panel">
          <span className="eyebrow">CURRENT PARTNERSHIP</span>
          <h3>{data.innings_detail?.current_partnership||'Data not available'}</h3>
          <p className="source-note">Verified from live match state.</p>
        </div>
        <div className="panel">
          <span className="eyebrow">KEY DISMISSALS</span>
          <p className="wickets-text">{data.innings_detail?.key_wickets||'No wickets fallen yet in this innings.'}</p>
        </div>
      </div>}

      {tab==='squads'&&<div className="squads-grid">
        {data.playing_xi&&Object.entries(data.playing_xi).map(([teamName, squad])=>(
          <div className="panel squad-panel" key={teamName}>
            <h3>{teamName} Playing XI</h3>
            <div className="squad-list">
              {squad.map((p,idx)=>(
                <div className="player-row-item" key={p.name}>
                  <span className="p-num">{idx+1}</span>
                  <div className="p-info">
                    <b>{p.name}</b>
                    <small>{p.role}</small>
                  </div>
                  <div className="p-tags">
                    <span className="style-tag">{p.batting_hand}</span>
                    <span className="style-tag">{p.bowling_style}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>}

      {tab==='comms'&&<div className="panel">
        <span className="eyebrow">RECENT DELIVERIES</span>
        <div className="ball-list">
          {(data.recent_balls||[]).map((b,i)=>(
            <div className="ball-row" key={i}>
              <div className="ball-badge">{b.ball}</div>
              <div className="ball-text">
                <b>{b.bowler} to {b.batter} ({b.runs} run{b.runs!==1?'s':''})</b>
                <p>{b.text}</p>
              </div>
            </div>
          ))}
        </div>
      </div>}

      {/* Embedded Live Match AI Assistant directly inside Match Tracking */}
      {tab==='ai'&&<div className="embedded-ai-wrapper">
        <LiveMatchAIAssistant selectedMatch={data} embedded={true}/>
      </div>}
    </div>}
  </>;
}

// ----------------- EMBEDDED LIVE MATCH AI ASSISTANT -----------------
function LiveMatchAIAssistant({selectedMatch, embedded=false}){
  const [messages,setMessages]=useState([]),
        [input,setInput]=useState(''),
        [busy,setBusy]=useState(false),
        [err,setErr]=useState('');

  const liveSuggestions=[
    'Summarize this match',
    'Which team currently has the advantage?',
    'Who are the left-handed batsmen in this match?',
    'Who are the specialist fast bowlers and spinners?',
    'Which team has stronger all-rounders?'
  ];

  async function send(text=input){
    if(!text.trim()||busy)return;
    const next=[...messages,{role:'user',content:text}];
    setMessages(next);
    setInput('');
    setBusy(true);
    setErr('');
    try{
      const r=await post('/chat/live',{
        question:text,
        history:messages,
        match_context:selectedMatch?{id:selectedMatch.id,team1:selectedMatch.team1,team2:selectedMatch.team2}:null
      });
      setMessages([...next,{role:'assistant',content:r.answer,mode:r.mode,sources:r.sources}]);
    }catch(e){
      setErr(e.message);
    }finally{
      setBusy(false);
    }
  }

  return <>
    {!embedded&&<PageHeading
      eyebrow="IN-GAME TACTICAL AI"
      title="Live Match AI Assistant"
      subtitle={selectedMatch?`Automatically synchronized with ${selectedMatch.team1} vs ${selectedMatch.team2} (${selectedMatch.format})`:'Tracking live match context.'}
    />}
    <div className="assistant-layout">
      <div className="chat-shell live-shell-theme">
        <div className="chat-head live-head">
          <div className="bot-mark live-mark"><Zap size={18}/></div>
          <div>
            <b>Live Match Assistant</b>
            {selectedMatch?<span className="match-active-pill">● Context: {selectedMatch.team1} vs {selectedMatch.team2}</span>:<span>● Active</span>}
          </div>
          <span className="provider-label live-pill">IN-GAME TACTICS</span>
        </div>
        <div className="chat-scroll">
          {!messages.length?(
            <div className="chat-empty">
              <div className="empty-orbit live-orbit"><Zap size={25}/></div>
              <h2>Ask about {selectedMatch?`${selectedMatch.team1} vs ${selectedMatch.team2}`:'the ongoing match'}</h2>
              <p>In-game analysis on current score, batting lineups, bowling styles, left-handers, and win probability.</p>
              <div className="suggestions">
                {liveSuggestions.map(s=><button key={s} onClick={()=>send(s)}>{s}<ArrowUpRight size={13}/></button>)}
              </div>
            </div>
          ):(
            <div className="messages">
              {messages.map((m,i)=>(
                <div className={'message '+m.role} key={i}>
                  <div className="message-icon">{m.role==='assistant'?<Zap size={14}/>:<span>YOU</span>}</div>
                  <div className="message-content">
                    <div className="message-who">{m.role==='assistant'?'LIVE MATCH AI':'YOU'}{m.mode&&<span>{m.mode}</span>}</div>
                    <p style={{whiteSpace:'pre-line'}}>{m.content}</p>
                    {m.sources&&<div className="evidence-tags">{m.sources.map(src=><span key={src}><Shield size={11}/> {src}</span>)}</div>}
                  </div>
                </div>
              ))}
              {busy&&<div className="typing"><i/><i/><i/> Computing live in-game tactics…</div>}
            </div>
          )}
          {err&&<div className="inline-error">{err}</div>}
        </div>
        <div className="composer">
          <textarea
            rows="1"
            value={input}
            onChange={e=>setInput(e.target.value)}
            onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}}}
            placeholder={`Ask about ${selectedMatch?.team1||'team'} vs ${selectedMatch?.team2||'team'}...`}
          />
          <button className="send-btn zap-bg" disabled={!input.trim()||busy} onClick={()=>send()}><Send size={16}/></button>
          <small>Grounded in live Playing XI and real-time state · Enter to send</small>
        </div>
      </div>

      <aside className="assistant-aside">
        <div className="aside-card">
          <div className="aside-kicker">SUGGESTED QUESTIONS</div>
          {liveSuggestions.map((s,i)=>(
            <button className="prompt-row" key={s} onClick={()=>send(s)}>
              <span>0{i+1}</span>{s}<ArrowUpRight size={13}/></button>
          ))}
        </div>
        {selectedMatch&&<div className="aside-card">
          <div className="aside-kicker">ACTIVE MATCH SCORE</div>
          <div className="mini-match-state">
            <b>{selectedMatch.team1} vs {selectedMatch.team2}</b>
            <span className="live-score-val">{selectedMatch.score}</span>
            <small><MapPin size={11}/> {selectedMatch.venue}</small>
          </div>
        </div>}
      </aside>
    </div>
  </>;
}

// ----------------- AI ASSISTANT 2: GENERAL CRICKET AI -----------------
function GeneralCricketAIAssistant({players,teams}){
  const [messages,setMessages]=useState([]),
        [input,setInput]=useState(''),
        [busy,setBusy]=useState(false),
        [err,setErr]=useState('');

  const generalSuggestions=[
    'Compare Virat Kohli and Babar Azam',
    'Analyse India’s team batting and bowling strength',
    'Compare India and Australia historical records',
    'What are Virat Kohli’s historical dismissal patterns?',
    'What is the average score at Eden Gardens?'
  ];

  async function send(text=input){
    if(!text.trim()||busy)return;
    const next=[...messages,{role:'user',content:text}];
    setMessages(next);
    setInput('');
    setBusy(true);
    setErr('');
    try{
      const r=await post('/chat/general',{
        question:text,
        history:messages
      });
      setMessages([...next,{role:'assistant',content:r.answer,mode:r.mode,sources:r.sources}]);
    }catch(e){
      setErr(e.message);
    }finally{
      setBusy(false);
    }
  }

  return <>
    <PageHeading
      eyebrow="AI ASSISTANT 2 · GENERAL CRICKET INTELLIGENCE"
      title="General Cricket AI Assistant"
      subtitle="Independent assistant for historical player analysis, team comparisons, and ground reports."
    />
    <div className="assistant-layout">
      <div className="chat-shell general-shell-theme">
        <div className="chat-head general-head">
          <div className="bot-mark general-mark"><BookOpen size={18}/></div>
          <div>
            <b>General Cricket Assistant</b>
            <span>● Historical Knowledge Base (No live match dependencies)</span>
          </div>
          <span className="provider-label general-pill">FACTUAL DATABASE</span>
        </div>
        <div className="chat-scroll">
          {!messages.length?(
            <div className="chat-empty">
              <div className="empty-orbit general-orbit"><BookOpen size={25}/></div>
              <h2>Cricket Encyclopedia & Statistics</h2>
              <p>Ask about career records, player comparisons, weaknesses, and ground averages across verified international matches.</p>
              <div className="suggestions">
                {generalSuggestions.map(s=><button key={s} onClick={()=>send(s)}>{s}<ArrowUpRight size={13}/></button>)}
              </div>
            </div>
          ):(
            <div className="messages">
              {messages.map((m,i)=>(
                <div className={'message '+m.role} key={i}>
                  <div className="message-icon">{m.role==='assistant'?<BookOpen size={14}/>:<span>YOU</span>}</div>
                  <div className="message-content">
                    <div className="message-who">{m.role==='assistant'?'CRICKET AI':'YOU'}{m.mode&&<span>{m.mode}</span>}</div>
                    <p style={{whiteSpace:'pre-line'}}>{m.content}</p>
                    {m.sources&&<div className="evidence-tags">{m.sources.map(src=><span key={src}><Shield size={11}/> {src}</span>)}</div>}
                  </div>
                </div>
              ))}
              {busy&&<div className="typing"><i/><i/><i/> Searching verified cricket records…</div>}
            </div>
          )}
          {err&&<div className="inline-error">{err}</div>}
        </div>
        <div className="composer">
          <textarea
            rows="1"
            value={input}
            onChange={e=>setInput(e.target.value)}
            onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}}}
            placeholder="Ask about players, records, head-to-heads, grounds..."
          />
          <button className="send-btn" disabled={!input.trim()||busy} onClick={()=>send()}><Send size={16}/></button>
          <small>Verified Cricsheet ball-by-ball scorecards · Zero demo statistics</small>
        </div>
      </div>

      <aside className="assistant-aside">
        <div className="aside-card">
          <div className="aside-kicker">EXPLORE IDEAS</div>
          {generalSuggestions.map((s,i)=>(
            <button className="prompt-row" key={s} onClick={()=>send(s)}>
              <span>0{i+1}</span>{s}<ArrowUpRight size={13}/></button>
          ))}
        </div>
        <div className="aside-card">
          <div className="aside-kicker">AVAILABLE DATASET</div>
          <p className="aside-help">Includes verified international scorecards between ICC Full Member teams.</p>
        </div>
      </aside>
    </div>
  </>;
}

function Select({label,value,onChange,options,placeholder='Choose…'}){
  return <label className="field"><span>{label}</span><div className="select-wrap"><select value={value} onChange={e=>onChange(e.target.value)}><option value="">{placeholder}</option>{options.map(x=><option key={x} value={x}>{x}</option>)}</select><ChevronDown size={15}/></div></label>;
}

function Stat({label,value,unit}){
  return <div className="stat-cell"><span>{label}</span><b>{value??'—'}{unit&&<small>{unit}</small>}</b></div>;
}

// ----------------- PLAYER ANALYSIS (REAL DATA) -----------------
function PlayerPage({players}){
  const [name,setName]=useState(players[0]||'Virat Kohli'),[data,setData]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  useEffect(()=>{
    if(!name){setData(null);return;}
    setBusy(true);
    api('/players/'+encodeURIComponent(name)).then(setData).catch(e=>setError(e.message)).finally(()=>setBusy(false));
  },[name]);

  return <>
    <PageHeading eyebrow="VERIFIED CRICKET RECORDS" title="Player Analysis" subtitle="Career totals, form, batting hand, bowling style, and verified dismissal trends."/>
    <div className="selector-card single">
      <Select label="Choose an international player" value={name} onChange={x=>{setName(x);setError('')}} options={players}/>
      {busy&&<span className="loading">Loading verified scorecard…</span>}
    </div>
    {error&&<div className="inline-error">{error}</div>}
    {data&&<>
      <div className="profile-banner">
        <div className="player-avatar">{data.name.split(' ').map(x=>x[0]).join('').slice(0,2)}</div>
        <div>
          <span className="eyebrow">{data.role.toUpperCase()} · {data.team}</span>
          <h2>{data.name}</h2>
          <span className="data-label historical">{data.source}</span>
        </div>
        <span className="match-count"><b>{data.matches}</b> matches in record</span>
      </div>
      <div className="stats-grid profile-stats">
        <Stat label="CAREER RUNS" value={data.runs}/>
        <Stat label="BATTING AVERAGE" value={data.average}/>
        <Stat label="STRIKE RATE" value={data.strike_rate}/>
        <Stat label="WICKETS" value={data.wickets}/>
        <Stat label="ECONOMY" value={data.economy}/>
      </div>
      <div className="two-col">
        <div className="panel">
          <div className="panel-title"><div><span className="eyebrow">RECENT FORM</span><h3>Last five matches</h3></div><Clock3 size={17}/></div>
          <div className="form-big">{data.recent5.runs}<small> runs</small></div>
          <div className="chart-wrap"><Suspense fallback={<div className="loading">Loading chart…</div>}><RunChart data={data.recent5.chart}/></Suspense></div>
          <div className="form-foot"><span>{data.recent5.balls} balls faced in sample</span><b>SR {data.recent5.strike_rate}</b></div>
          <div className="source-note">{data.data_note} · Updated: {data.updated_at}</div>
        </div>
        <div className="panel">
          <div className="panel-title"><div><span className="eyebrow">PLAYER PROFILE & WEAKNESS</span><h3>Bowling matchups & styles</h3></div><Shield size={17}/></div>
          <div className="style-grid">
            <div><span>Batting Hand:</span> <b>{data.batting_hand}</b></div>
            <div><span>Bowling Style:</span> <b>{data.bowling_style}</b></div>
            <div><span>Playing Role:</span> <b>{data.role}</b></div>
          </div>
          <div className="caution"><Shield size={16}/><p>{data.weakness?.message}</p></div>
          <div className="source-note">Derived strictly from verified delivery dismissals. No demo data.</div>
        </div>
      </div>
    </>}
  </>;
}

// ----------------- PLAYER COMPARISON (REAL DATA) -----------------
function PlayerCompare({players}){
  const [a,setA]=useState(players[0]||'Virat Kohli'),[b,setB]=useState(players[1]||'Rohit Sharma'),[result,setResult]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  async function run(){
    if(!a||!b||a===b)return;
    setBusy(true);setError('');
    try{setResult(await post('/players/compare',{first:a,second:b}))}catch(e){setError(e.message)}finally{setBusy(false)}
  }
  useEffect(()=>{if(a&&b&&a!==b)run();},[a,b]);

  return <>
    <PageHeading eyebrow="HEAD TO HEAD COMPARISON" title="Player Comparison" subtitle="Side-by-side comparison using verified international cricket records."/>
    <div className="selector-card compare-select">
      <Select label="PLAYER ONE" value={a} onChange={setA} options={players}/>
      <div className="versus">VS</div>
      <Select label="PLAYER TWO" value={b} onChange={setB} options={players}/>
      <button className="primary-btn" disabled={!a||!b||a===b||busy} onClick={run}>{busy?'Comparing…':'Compare players'} <ArrowRight size={15}/></button>
    </div>
    {error&&<div className="inline-error">{error}</div>}
    {result&&<CompareCards first={result.first} second={result.second} labels={['CAREER RUNS','AVERAGE','STRIKE RATE','WICKETS','MATCHES']} keys={['runs','average','strike_rate','wickets','matches']} note={result.note}/>}
  </>;
}

function CompareCards({first,second,labels,keys,note}){
  return <div className="compare-wrap">
    <div className="compare-head">
      <div/>
      <div className="compare-person">
        <div className="player-avatar">{first.name?first.name.slice(0,1):first.team.slice(0,1)}</div>
        <h3>{first.name||first.team}</h3>
        <span>{first.source}</span>
      </div>
      <div className="compare-person">
        <div className="player-avatar alt">{second.name?second.name.slice(0,1):second.team.slice(0,1)}</div>
        <h3>{second.name||second.team}</h3>
        <span>{second.source}</span>
      </div>
    </div>
    {keys.map((k,i)=>(
      <div className="compare-row" key={k}>
        <span>{labels[i]}</span>
        <b>{first[k]??'—'}</b>
        <div className="compare-meter">
          <i style={{width:Math.max(8,100*(Number(first[k]||0)/(Number(first[k]||0)+Number(second[k]||0)||1)))+'%'}}/>
          <i style={{width:Math.max(8,100*(Number(second[k]||0)/(Number(first[k]||0)+Number(second[k]||0)||1)))+'%'}}/>
        </div>
        <b>{second[k]??'—'}</b>
      </div>
    ))}
    <p className="source-note">{note}</p>
  </div>;
}

// ----------------- TEAM COMPARISON (REAL DATA) -----------------
function TeamCompare({teams}){
  const [a,setA]=useState(teams[0]||'India'),[b,setB]=useState(teams[1]||'Australia'),[result,setResult]=useState(null),[error,setError]=useState('');
  async function run(){
    try{setResult(await post('/teams/compare',{first:a,second:b}));setError('')}catch(e){setError(e.message)}
  }
  useEffect(()=>{if(a&&b&&a!==b)run();},[a,b]);

  return <>
    <PageHeading eyebrow="INTERNATIONAL RIVALRY ROOM" title="Team Comparison" subtitle="Compare verified international team records and win ratios."/>
    <div className="selector-card compare-select">
      <Select label="TEAM ONE" value={a} onChange={setA} options={teams}/>
      <div className="versus">VS</div>
      <Select label="TEAM TWO" value={b} onChange={setB} options={teams}/>
      <button className="primary-btn" disabled={!a||!b||a===b} onClick={run}>Compare teams <ArrowRight size={15}/></button>
    </div>
    {error&&<div className="inline-error">{error}</div>}
    {result&&<>
      <CompareCards first={result.first} second={result.second} labels={['WIN RATE','WINS','RUNS / MATCH','WICKETS TAKEN','MATCHES']} keys={['win_rate','wins','batting_average_per_match','wickets_taken','matches']} note={result.label}/>
      <div className="recommendation"><Sparkles size={17}/><div><b>AI Analysis from Scorebook</b><span>{result.recommendation}</span></div></div>
    </>}
  </>;
}

// ----------------- PITCH & GROUND (REAL DATA) -----------------
function VenuePage({venues}){
  const [v,setV]=useState(venues[0]||''),[data,setData]=useState(null),[err,setErr]=useState('');
  useEffect(()=>{
    if(v)api('/venues/'+encodeURIComponent(v)).then(setData).catch(e=>setErr(e.message));
    else setData(null);
  },[v]);

  return <>
    <PageHeading eyebrow="STADIUM RECORD REPORT" title="Pitch & Ground Analysis" subtitle="Ground scoring profiles and top performers from verified international scorecards."/>
    <div className="selector-card single">
      <Select label="Select an international stadium" value={v} onChange={x=>{setV(x);setErr('')}} options={venues}/>
    </div>
    {err&&<div className="inline-error">{err}</div>}
    {data&&<>
      <div className="profile-banner venue-banner">
        <div className="quick-icon"><MapPin size={20}/></div>
        <div>
          <span className="eyebrow">STADIUM REPORT · {data.source}</span>
          <h2>{data.venue}</h2>
          <span className="muted-copy">{data.matches} international matches recorded</span>
        </div>
      </div>
      <div className="venue-grid">
        <div className="panel">
          <span className="eyebrow">FIRST INNINGS AVERAGE</span>
          <div className="form-big">{data.innings['1']?.average??'—'}<small> runs</small></div>
          <span className="muted-copy">{data.innings['1']?.innings??0} innings in sample</span>
        </div>
        <div className="panel">
          <span className="eyebrow">SECOND INNINGS AVERAGE</span>
          <div className="form-big">{data.innings['2']?.average??'—'}<small> runs</small></div>
          <span className="muted-copy">{data.innings['2']?.innings??0} innings in sample</span>
        </div>
        <div className="panel pitch-insight">
          <div className="quick-icon"><Activity size={18}/></div>
          <span className="eyebrow">SCORING TENDENCY</span>
          <h3>{data.batting_friendly?'Higher-scoring venue':'Balanced pitch for bowling'}</h3>
          <p>Top Batters: {data.top_batters?.join(', ') || 'N/A'}</p>
          <p>Top Bowlers: {data.top_bowlers?.join(', ') || 'N/A'}</p>
        </div>
      </div>
      <div className="notice"><HelpCircle size={16}/> {data.data_note}</div>
    </>}
  </>;
}

function Prediction({teams}){
  const [a,setA]=useState(teams[0]||'India'),[b,setB]=useState(teams[1]||'Australia'),[data,setData]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  async function run(){
    setBusy(true);
    try{setData(await api(`/prediction?first=${encodeURIComponent(a)}&second=${encodeURIComponent(b)}`));setError('')}catch(e){setError(e.message)}finally{setBusy(false)}
  }
  return <>
    <PageHeading eyebrow="EXPERIMENTAL MACHINE LEARNING" title="Match Prediction" subtitle="Trained strictly on verified historical international outcomes (Scikit-Learn)."/>
    <div className="prediction-banner">
      <div className="prediction-symbol"><Activity size={22}/></div>
      <div><b>Statistical Probability Model</b><span>Calculated using logistic regression across real match outcomes.</span></div>
      <span className="experiment-pill">SCIKIT-LEARN</span>
    </div>
    <div className="selector-card compare-select">
      <Select label="TEAM ONE" value={a} onChange={setA} options={teams}/>
      <div className="versus">VS</div>
      <Select label="TEAM TWO" value={b} onChange={setB} options={teams}/>
      <button className="primary-btn" disabled={!a||!b||a===b||busy} onClick={run}>{busy?'Running model…':'Estimate outcome'} <ArrowRight size={15}/></button>
    </div>
    {error&&<div className="inline-error">{error}</div>}
    {data&&<div className="panel prediction-result">
      <div className="result-label"><span className="eyebrow">MODEL STATUS</span><span className="data-label">{data.available?'TRAINED':'NEEDS DATA'}</span></div>
      {data.probabilities?<>
        <h2>{data.first} <em>vs</em> {data.second}</h2>
        <div className="prob-row">
          <div><span>{data.first}</span><b>{data.probabilities[data.first]}%</b></div>
          <div><span>{data.second}</span><b>{data.probabilities[data.second]}%</b></div>
        </div>
        <div className="prob-track"><i style={{width:data.probabilities[data.first]+'%'}}/></div>

        {data.factual_explanation&&<div className="pred-factual-box">
          <div className="factual-head"><Shield size={14}/> <b>Historical Data Backing</b></div>
          <p>{data.factual_explanation}</p>
          {data.factual_info&&<div className="factual-tags">
            {Object.entries(data.factual_info).map(([k,v])=>(
              <span key={k}><b>{k.replace(/_/g,' ')}:</b> {v}</span>
            ))}
          </div>}
        </div>}
      </>:<>
        <h3>{data.message}</h3>
      </>}
      <div className="source-note">{data.model} {data.caveat}</div>
    </div>}
  </>;
}

function ImportPage({onDone}){
  const [file,setFile]=useState(null),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState('');
  async function upload(){
    if(!file)return;
    setBusy(true);setMessage('');setError('');
    const body=new FormData();
    body.append('file',file);
    try{
      const r=await api('/upload',{method:'POST',body});
      setMessage(r.message);
      onDone();
    }catch(e){
      setError(e.message);
    }finally{
      setBusy(false);
    }
  }
  return <>
    <PageHeading eyebrow="EXTEND YOUR SCOREBOOK" title="Import Additional Datasets" subtitle="Upload Cricsheet JSON files, ZIP archives, or standard CSVs."/>
    <div className="upload-card">
      <div className="upload-icon"><Upload size={22}/></div>
      <h2>Add more historical matches</h2>
      <p>Uploaded records will immediately update the Player Analysis, Comparisons, and Ground analytics.</p>
      <label className="file-drop">
        <input type="file" accept=".json,.zip,.csv" onChange={e=>setFile(e.target.files?.[0]||null)}/>
        <div className="drop-icon"><Upload size={19}/></div>
        <b>{file?.name||'Choose a Cricsheet JSON or ZIP'}</b>
        <span>{file?`${(file.size/1024/1024).toFixed(2)} MB · Ready to upload`:'Standard Cricsheet JSON format'}</span>
      </label>
      <button className="primary-btn upload-submit" disabled={!file||busy} onClick={upload}>{busy?'Importing…':'Import dataset'} <ArrowRight size={15}/></button>
      {message&&<div className="success">{message}</div>}
      {error&&<div className="inline-error">{error}</div>}
    </div>
  </>;
}

export default App;
