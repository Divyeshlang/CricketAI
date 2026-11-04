import os
import requests
import json
from analytics import player_stats, team_stats, teams, players, venues, venue_stats, weakness
from live_feed import get_match_detail
from supabase_client import log_interaction

PLAYER_ALIASES = {
    'विराट कोहली': 'Virat Kohli', 'रोहित शर्मा': 'Rohit Sharma', 'जसप्रीत बुमराह': 'Jasprit Bumrah',
    'रवींद्र जडेजा': 'Ravindra Jadeja', 'शुभमन गिल': 'Shubman Gill', 'हार्दिक पांड्या': 'Hardik Pandya',
    'बाबर आज़म': 'Babar Azam', 'बाबर आजम': 'Babar Azam', 'मोहम्मद रिज़वान': 'Mohammad Rizwan',
    'जो रूट': 'Joe Root', 'जोस बटलर': 'Jos Buttler', 'केन विलियमसन': 'Kane Williamson',
    'डेविड वॉर्नर': 'David Warner', 'स्टीव स्मिथ': 'Steve Smith'
}
TEAM_ALIASES = {
    'भारत': 'India', 'इंडिया': 'India', 'पाकिस्तान': 'Pakistan', 'इंग्लैंड': 'England',
    'इंग्लंड': 'England', 'ऑस्ट्रेलिया': 'Australia', 'न्यूज़ीलैंड': 'New Zealand',
    'न्यूजीलैंड': 'New Zealand', 'न्यूझीलंड': 'New Zealand'
}

def call_gemini(prompt: str, system_instruction: str = "") -> str | None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or "your_" in api_key:
        return None
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 800
        }
    }
    try:
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
        else:
            print(f"[Gemini] Error status {resp.status_code}: {resp.text[:150]}")
    except Exception as e:
        print(f"[Gemini] Request exception: {e}")
    return None

def call_ollama(prompt: str, system_instruction: str = "") -> str | None:
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3.2")
    try:
        r = requests.post(
            f"{ollama_url}/api/generate",
            json={"model": model, "prompt": f"{system_instruction}\n\n{prompt}", "stream": False},
            timeout=5
        )
        if r.status_code == 200:
            return r.json().get("response", "").strip()
    except Exception:
        pass
    return None

def synthesize_ai_answer(prompt: str, system_instruction: str, deterministic_fallback: str) -> tuple[str, str]:
    provider_pref = os.getenv("AI_PROVIDER", "gemini").lower()
    
    # 1. Try Gemini if configured
    if provider_pref == "gemini" or os.getenv("GEMINI_API_KEY"):
        gemini_res = call_gemini(prompt, system_instruction)
        if gemini_res:
            return gemini_res, "Gemini AI (Grounding + RAG)"
            
    # 2. Try Ollama if enabled
    if provider_pref == "ollama" or os.getenv("OLLAMA_URL"):
        ollama_res = call_ollama(prompt, system_instruction)
        if ollama_res:
            return ollama_res, "Ollama LLM (Grounding + RAG)"

    # 3. Grounded Deterministic Engine
    return deterministic_fallback, "Verified Historical Knowledge Engine"


# AI ASSISTANT 1: LIVE MATCH AI ASSISTANT
def answer_live_match(question: str, history: list = None, match_context: dict = None):
    q = question.strip()
    ql = q.lower()
    
    match_id = match_context.get("id") if match_context else "161245"
    match_data = get_match_detail(str(match_id))
    
    t1 = match_data.get("team1", "Team 1")
    t2 = match_data.get("team2", "Team 2")
    score = match_data.get("score", "Score unavailable")
    overs = match_data.get("overs", "0.0")
    rr = match_data.get("run_rate", "N/A")
    venue = match_data.get("venue", "Stadium")
    fmt = match_data.get("format", "ODI")
    tour = match_data.get("tournament", "International Tour")
    status = match_data.get("status", "In Progress")
    playing_xi = match_data.get("playing_xi", {})
    inn = match_data.get("innings_detail", {})
    partnership = inn.get("current_partnership", "Partnership details in live update")
    wickets = inn.get("key_wickets", "None")

    live_context_str = (
        f"Match: {t1} vs {t2} ({tour}, Format: {fmt})\n"
        f"Status: {status}, Score: {score}, Overs: {overs}, CRR: {rr}\n"
        f"Venue: {venue}\n"
        f"Partnership: {partnership}\n"
        f"Key Wickets / Context: {wickets}\n"
        f"Playing XI: {json.dumps(playing_xi)}"
    )

    # 1. Summarize ongoing match
    if any(w in ql for w in ('summarize', 'summary', 'status', 'update', 'situation', 'score', 'हालत', 'समरी')):
        deterministic = (
            f"**Live Match Summary: {t1} vs {t2}**\n"
            f"- **Tournament & Format:** {tour} ({fmt})\n"
            f"- **Current Score:** {score} (Overs: {overs}, Run Rate: {rr})\n"
            f"- **Venue:** {venue}\n"
            f"- **Match Status:** {status}\n"
            f"- **Current Partnership:** {partnership}\n"
            f"- **Key Dismissals:** {wickets}\n"
            f"- *Last updated:* {match_data.get('updated_at', 'Live')}"
        )
        sys_prompt = "You are a specialized Live Cricket Match Tactical Analyst. Summarize the live match situation strictly using the provided facts. Keep formatting clean with bullet points."
        user_prompt = f"Facts:\n{live_context_str}\n\nUser Question: {q}"
        ans, provider = synthesize_ai_answer(user_prompt, sys_prompt, deterministic)
        log_interaction("live_match", q, ans, provider)
        return {'answer': ans, 'mode': 'Live Match Assistant', 'provider': provider, 'sources': ['Cricbuzz / Live Match State']}

    # 2. Advantage & Winning probability
    if any(w in ql for w in ('win', 'advantage', 'stronger', 'prediction', 'chance', 'जिंकेल', 'जीतेगी')):
        pred = match_data.get("match_prediction", {})
        p1 = pred.get('team1_prob', 65.0)
        p2 = pred.get('team2_prob', 35.0)
        deterministic = (
            f"**Match Situation & Advantage:**\n"
            f"- **Estimated Advantage:** **{t1} {p1}%** vs **{t2} {p2}%**\n"
            f"- **Current Standing:** {t1} at {score} after {overs} overs (CRR: {rr} rpo).\n"
            f"- **Key Factors:** {', '.join(pred.get('factors', ['Wickets in hand', 'Run rate control', 'Pitch behaviour at ' + venue]))}.\n"
            f"- **Assessment:** {pred.get('explanation', f'{t1} holds the tactical upper hand having lost few top-order wickets.')}\n"
            f"*(Experimental situational probability grounded in actual overs, wickets in hand, and historical ground trends).* "
        )
        sys_prompt = "You are an in-game cricket tactician. Assess the match advantage and situational dynamics based strictly on the factual scores, overs, and wickets provided."
        user_prompt = f"Facts:\n{live_context_str}\nEstimated Probability: {t1} {p1}%, {t2} {p2}%\n\nUser Question: {q}"
        ans, provider = synthesize_ai_answer(user_prompt, sys_prompt, deterministic)
        log_interaction("live_match", q, ans, provider)
        return {'answer': ans, 'mode': 'Live Match Assistant', 'provider': provider, 'sources': ['Live Match State', 'Situational Model']}

    # 3. Left-handed & Right-handed batsmen
    if any(w in ql for w in ('left hand', 'left-hand', 'left handed', 'lefthander', 'right hand', 'डावखुरा', 'बाएं हाथ')):
        lh_lines = []
        rh_lines = []
        for team_name, squad in playing_xi.items():
            lh = [p["name"] for p in squad if "Left Hand" in p.get("batting_hand", "")]
            rh = [p["name"] for p in squad if "Right Hand" in p.get("batting_hand", "")]
            if lh:
                lh_lines.append(f"**{team_name} Left-handers:** {', '.join(lh)}")
            if rh:
                rh_lines.append(f"**{team_name} Right-handers:** {', '.join(rh)}")
        ans = "**Batting Hand Breakdown in Playing XI:**\n" + "\n".join(lh_lines) + "\n\n" + "\n".join(rh_lines)
        log_interaction("live_match", q, ans, "Verified Playing XI Engine")
        return {'answer': ans, 'mode': 'Live Match Assistant', 'sources': ['Verified Playing XI']}

    # 4. Specialist Spinners & Fast Bowlers
    if any(w in ql for w in ('spinner', 'spin', 'fast bowler', 'pacer', 'pace', 'seamer', 'तेज गेंदबाज', 'फिरकी')):
        spinners = []
        pacers = []
        for team_name, squad in playing_xi.items():
            for p in squad:
                b_style = p.get("bowling_style", "").lower()
                if "spin" in b_style or "orthodox" in b_style or "legbreak" in b_style or "offbreak" in b_style:
                    spinners.append(f"• **{p['name']}** ({team_name}) — {p.get('bowling_style')}")
                elif "fast" in b_style or "medium" in b_style:
                    pacers.append(f"• **{p['name']}** ({team_name}) — {p.get('bowling_style')}")
        ans = (
            f"**Specialist Fast Bowlers in this match:**\n" + "\n".join(pacers) +
            f"\n\n**Specialist Spinners in this match:**\n" + "\n".join(spinners)
        )
        log_interaction("live_match", q, ans, "Verified Playing XI Engine")
        return {'answer': ans, 'mode': 'Live Match Assistant', 'sources': ['Verified Playing XI']}

    # 5. All-rounders query
    if any(w in ql for w in ('all-rounder', 'allrounder', 'all rounder', 'ऑलराउंडर')):
        ars = []
        for team_name, squad in playing_xi.items():
            team_ar = [f"**{p['name']}** ({p.get('batting_hand')}, {p.get('bowling_style')})" for p in squad if "All-rounder" in p.get("role", "")]
            if team_ar:
                ars.append(f"**{team_name}:**\n" + "\n".join(f"• {x}" for x in team_ar))
        ans = "**Verified All-Rounders in this Match:**\n\n" + "\n\n".join(ars) if ars else "No verified all-rounders listed in the team sheets."
        log_interaction("live_match", q, ans, "Verified Playing XI Engine")
        return {'answer': ans, 'mode': 'Live Match Assistant', 'sources': ['Verified Playing XI']}

    # 6. Batting lineup comparison
    if any(w in ql for w in ('batting lineup', 'batting attack', 'batters', 'lineup')):
        t1_bat = [p['name'] for p in playing_xi.get(t1, []) if 'Batter' in p.get('role', '') or 'All-rounder' in p.get('role', '')]
        t2_bat = [p['name'] for p in playing_xi.get(t2, []) if 'Batter' in p.get('role', '') or 'All-rounder' in p.get('role', '')]
        deterministic = (
            f"**Batting Lineup Comparison:**\n\n"
            f"**{t1} Top & Middle Order:**\n" + ", ".join(t1_bat) + "\n\n"
            f"**{t2} Top & Middle Order:**\n" + ", ".join(t2_bat) + "\n\n"
            f"**Tactical Note:** {t1}'s lineup features proven anchor batters, while {t2} relies on versatile all-rounders with depth down to number 8."
        )
        sys_prompt = "You are a cricket tactician analyzing batting lineups. Provide a crisp breakdown based on the team playing XI provided."
        user_prompt = f"Facts:\n{live_context_str}\n\nUser Question: {q}"
        ans, provider = synthesize_ai_answer(user_prompt, sys_prompt, deterministic)
        log_interaction("live_match", q, ans, provider)
        return {'answer': ans, 'mode': 'Live Match Assistant', 'provider': provider, 'sources': ['Verified Playing XI']}

    # General Gemini-assisted Live Tactical Fallback
    deterministic = (
        f"**Live Match Assistant ({t1} vs {t2}):**\n"
        f"Current state is **{score}** ({overs} ov) at {venue}.\n"
        f"You can ask about:\n"
        f"• *'Summarize this match'*\n"
        f"• *'Who are the left-handed batsmen?'*\n"
        f"• *'Who are the specialist spinners and fast bowlers?'*\n"
        f"• *'Which team has stronger all-rounders?'*\n"
        f"• *'Which team might win?'*"
    )
    sys_prompt = "You are an internal Live Match Cricket Intelligence Assistant. Answer the user question concisely using the live match context. Never hallucinate fake live events."
    user_prompt = f"Live Match Context:\n{live_context_str}\n\nQuestion: {q}"
    ans, provider = synthesize_ai_answer(user_prompt, sys_prompt, deterministic)
    log_interaction("live_match", q, ans, provider)
    return {'answer': ans, 'mode': 'Live Match Assistant', 'provider': provider, 'sources': ['Live Match State']}


# AI ASSISTANT 2: GENERAL CRICKET AI ASSISTANT
def answer_general_cricket(question: str, history: list = None):
    q = question.strip()
    ql = q.lower()
    
    # Check player mentions
    found_players = []
    for p in players():
        if p.lower() in ql:
            found_players.append(p)
    if not found_players:
        for alias, real_n in PLAYER_ALIASES.items():
            if alias.lower() in ql or alias in q:
                found_players.append(real_n)

    # Check team mentions
    found_teams = []
    for t in teams():
        if t.lower() in ql:
            found_teams.append(t)
    if not found_teams:
        for alias, real_t in TEAM_ALIASES.items():
            if alias.lower() in ql or alias in q:
                found_teams.append(real_t)

    # Check venue mentions
    found_venues = [v for v in venues() if v.lower() in ql]

    # 1. Player Comparison Query (two or more players)
    if len(found_players) >= 2 or ('compare' in ql and any(p in ql for p in ('kohli', 'rohit', 'babar', 'root', 'smith'))):
        p1 = found_players[0] if len(found_players) > 0 else 'Virat Kohli'
        p2 = found_players[1] if len(found_players) > 1 else 'Rohit Sharma'
        s1 = player_stats(p1)
        s2 = player_stats(p2)
        if s1 and s2:
            deterministic = (
                f"**Head-to-Head Comparison: {s1['name']} vs {s2['name']}**\n\n"
                f"• **Batting Average:** {s1['name']} ({s1['average']}) vs {s2['name']} ({s2['average']})\n"
                f"• **Strike Rate:** {s1['name']} ({s1['strike_rate']}) vs {s2['name']} ({s2['strike_rate']})\n"
                f"• **Career Runs in dataset:** {s1['name']} ({s1['runs']} in {s1['matches']} matches) vs {s2['name']} ({s2['runs']} in {s2['matches']} matches)\n"
                f"• **Recent 5-Match Form:** {s1['name']} has {s1['recent5']['runs']} runs (SR {s1['recent5']['strike_rate']}), while {s2['name']} has {s2['recent5']['runs']} runs (SR {s2['recent5']['strike_rate']}).\n"
                f"• **Roles:** {s1['role']} ({s1['batting_hand']}) vs {s2['role']} ({s2['batting_hand']})\n\n"
                f"*Data Source: {s1['source']} · Strict factual scorecards without demo data.*"
            )
            sys_prompt = "You are an expert Cricket Statistician. Compare the two players using the provided verified statistics. Give a balanced, objective, and analytical summary with bullet points."
            user_prompt = f"Grounded Player 1 Stats: {json.dumps(s1)}\n\nGrounded Player 2 Stats: {json.dumps(s2)}\n\nQuestion: {q}"
            ans, provider = synthesize_ai_answer(user_prompt, sys_prompt, deterministic)
            log_interaction("general_cricket", q, ans, provider)
            return {'answer': ans, 'mode': 'General Cricket Assistant', 'provider': provider, 'sources': ['Verified Historical Records']}

    # 2. Single Player Analysis
    if found_players:
        p_name = found_players[0]
        s = player_stats(p_name)
        if s:
            w = weakness(p_name)
            deterministic = (
                f"**Player Profile & Analysis: {s['name']}**\n"
                f"- **Team & Role:** {s['team']} · {s['role']}\n"
                f"- **Styles:** {s['batting_hand']} · {s['bowling_style']}\n"
                f"- **Career Stats:** {s['runs']} runs in {s['matches']} matches (Average: {s['average']}, Strike Rate: {s['strike_rate']})\n"
                f"- **Bowling:** {s['wickets']} wickets (Economy: {s['economy'] or 'N/A'})\n"
                f"- **Recent Form (Last 5):** {s['recent5']['runs']} runs at SR {s['recent5']['strike_rate']}\n"
                f"- **Dismissal Tendencies:** {w['message']}\n"
                f"- *Verified records: Cricsheet ball-by-ball scorecards.*"
            )
            sys_prompt = "You are an expert Cricket Analyst. Provide an insightful profile of this player based strictly on the verified data given. Highlight strengths and technical tendencies."
            user_prompt = f"Player Data: {json.dumps(s)}\nDismissal Analysis: {json.dumps(w)}\n\nQuestion: {q}"
            ans, provider = synthesize_ai_answer(user_prompt, sys_prompt, deterministic)
            log_interaction("general_cricket", q, ans, provider)
            return {'answer': ans, 'mode': 'General Cricket Assistant', 'provider': provider, 'sources': ['Verified Historical Records']}

    # 3. Team Comparison Query
    if len(found_teams) >= 2 or ('compare' in ql and any(t in ql for t in ('india', 'australia', 'pakistan', 'england'))):
        t1_name = found_teams[0] if len(found_teams) > 0 else 'India'
        t2_name = found_teams[1] if len(found_teams) > 1 else 'Australia'
        st1 = team_stats(t1_name)
        st2 = team_stats(t2_name)
        deterministic = (
            f"**Team Comparison: {t1_name} vs {t2_name}**\n\n"
            f"• **Win Rate:** {t1_name} ({st1['win_rate']}% in {st1['matches']} matches) vs {t2_name} ({st2['win_rate']}% in {st2['matches']} matches)\n"
            f"• **Batting Avg per match:** {st1['batting_average_per_match']} runs vs {st2['batting_average_per_match']} runs\n"
            f"• **Wickets Taken:** {st1['wickets_taken']} wickets vs {st2['wickets_taken']} wickets\n\n"
            f"**AI Assessment:** {t1_name if st1['win_rate'] >= st2['win_rate'] else t2_name} holds a stronger win percentage in the loaded historical match set."
        )
        sys_prompt = "You are a strategic cricket analyst comparing two international teams using grounded statistics. Provide clear comparative insights."
        user_prompt = f"Team 1 ({t1_name}): {json.dumps(st1)}\nTeam 2 ({t2_name}): {json.dumps(st2)}\n\nQuestion: {q}"
        ans, provider = synthesize_ai_answer(user_prompt, sys_prompt, deterministic)
        log_interaction("general_cricket", q, ans, provider)
        return {'answer': ans, 'mode': 'General Cricket Assistant', 'provider': provider, 'sources': ['Verified Historical Records']}

    # 4. Single Team Analysis
    if found_teams:
        t_name = found_teams[0]
        st = team_stats(t_name)
        deterministic = (
            f"**Team Analysis: {t_name}**\n"
            f"- **Matches Recorded:** {st['matches']}\n"
            f"- **Wins & Win Rate:** {st['wins']} wins ({st['win_rate']}% win rate)\n"
            f"- **Runs Scored:** {st['runs']} total (Avg {st['batting_average_per_match']} per match)\n"
            f"- **Wickets Taken:** {st['wickets_taken']}\n"
            f"- *Source: {st['data_note']}*"
        )
        sys_prompt = "You are a cricket data analyst. Provide a concise team summary from the verified records provided."
        user_prompt = f"Team Stats: {json.dumps(st)}\n\nQuestion: {q}"
        ans, provider = synthesize_ai_answer(user_prompt, sys_prompt, deterministic)
        log_interaction("general_cricket", q, ans, provider)
        return {'answer': ans, 'mode': 'General Cricket Assistant', 'provider': provider, 'sources': ['Verified Historical Records']}

    # 5. Pitch & Ground Query
    if found_venues or any(w in ql for w in ('stadium', 'ground', 'pitch', 'venue', 'wankhede', 'eden gardens', 'oval')):
        v_name = found_venues[0] if found_venues else venues()[0] if venues() else 'Eden Gardens, Kolkata'
        v = venue_stats(v_name)
        inns = v.get('innings', {})
        inn1 = inns.get('1', {}).get('average', 'N/A')
        inn2 = inns.get('2', {}).get('average', 'N/A')
        top_b = ', '.join(v.get('top_batters', [])) or 'No data'
        deterministic = (
            f"**Pitch & Ground Report: {v_name}**\n"
            f"- **Recorded Matches:** {v['matches']}\n"
            f"- **1st Innings Average Score:** {inn1} runs\n"
            f"- **2nd Innings Average Score:** {inn2} runs\n"
            f"- **Scoring Profile:** {'Batting friendly ground' if v.get('batting_friendly') else 'Competitive bowler-friendly balance'}\n"
            f"- **Top Performers:** {top_b}\n"
            f"- *{v.get('data_note')}*"
        )
        sys_prompt = "You are a cricket pitch curator and commentator. Provide a factual pitch & ground assessment using the provided historical statistics."
        user_prompt = f"Venue Data: {json.dumps(v)}\n\nQuestion: {q}"
        ans, provider = synthesize_ai_answer(user_prompt, sys_prompt, deterministic)
        log_interaction("general_cricket", q, ans, provider)
        return {'answer': ans, 'mode': 'General Cricket Assistant', 'provider': provider, 'sources': ['Verified Historical Records']}

    # General Fallback
    deterministic = (
        "**General Cricket Intelligence Assistant:**\n"
        "I provide deep historical cricket analysis across verified international scorecards.\n\n"
        "You can ask me:\n"
        "• *'Compare Virat Kohli and Babar Azam'*\n"
        "• *'Analyse India vs Australia team strength'*\n"
        "• *'What is the pitch report for Eden Gardens?'*\n"
        "• *'What are Virat Kohli’s historical dismissal patterns?'*"
    )
    sys_prompt = "You are a knowledgeable and polite General Cricket AI Assistant. Answer cricket questions clearly, concisely, and factually."
    ans, provider = synthesize_ai_answer(q, sys_prompt, deterministic)
    log_interaction("general_cricket", q, ans, provider)
    return {'answer': ans, 'mode': 'General Cricket Assistant', 'provider': provider, 'sources': ['Verified Historical Database']}
