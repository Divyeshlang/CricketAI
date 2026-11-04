import os
import psycopg2
from supabase import create_client, Client

_supabase_client: Client | None = None

def get_supabase_client() -> Client | None:
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    url = os.getenv("SUPABASE_URL")
    secret_key = os.getenv("SUPABASE_SECRET_KEY")
    if url and secret_key and "your-project" not in url:
        try:
            _supabase_client = create_client(url, secret_key)
        except Exception as e:
            print(f"[Supabase] Client initialization error: {e}")
    return _supabase_client

def get_pg_connection():
    db_url = os.getenv("DATABASE_URL")
    if not db_url or "your-project" in db_url:
        return None
    try:
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        print(f"[Supabase] PostgreSQL connection error: {e}")
        return None

def init_supabase_tables():
    conn = get_pg_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS assistant_interactions (
                    id SERIAL PRIMARY KEY,
                    assistant_type VARCHAR(50) NOT NULL,
                    question TEXT NOT NULL,
                    response TEXT NOT NULL,
                    provider VARCHAR(50) DEFAULT 'gemini',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.commit()
        conn.close()
        print("[Supabase] Tables initialized successfully via Session Pooler.")
        return True
    except Exception as e:
        print(f"[Supabase] Table initialization error: {e}")
        return False

def log_interaction(assistant_type: str, question: str, response: str, provider: str = 'gemini'):
    conn = get_pg_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO assistant_interactions (assistant_type, question, response, provider)
                    VALUES (%s, %s, %s, %s);
                """, (assistant_type, question, response, provider))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[Supabase] Failed to log interaction: {e}")
    return False

def check_supabase_health():
    status = {"supabase_client": False, "postgres_session_pooler": False, "interaction_count": 0}
    try:
        sb = get_supabase_client()
        if sb:
            status["supabase_client"] = True
    except Exception:
        pass

    try:
        conn = get_pg_connection()
        if conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM assistant_interactions;")
                cnt = cur.fetchone()[0]
                status["postgres_session_pooler"] = True
                status["interaction_count"] = cnt
            conn.close()
    except Exception:
        pass
    return status
