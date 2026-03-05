# backend/data/init_db.py
import os
import asyncio
import asyncpg
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

async def init():
    print("🚀 Initializing RoundZero Database & Index...")
    
    # 1. Check Pinecone
    try:
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index_name = os.getenv("PINECONE_INDEX", "interview-questions")
        
        if index_name not in [idx.name for idx in pc.list_indexes()]:
            print(f"❌ Pinecone Index '{index_name}' missing!")
        else:
            stats = pc.Index(index_name).describe_index_stats()
            print(f"✅ Pinecone Index '{index_name}' READY ({stats['total_vector_count']} vectors)")
    except Exception as e:
        print(f"❌ Pinecone Error: {e}")

    # 2. Check Neon
    try:
        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            raise ValueError("DATABASE_URL missing")
            
        conn = await asyncpg.connect(dsn)
        try:
            # Verify tables exist
            await conn.execute("SELECT id FROM user_profiles LIMIT 1")
            await conn.execute("SELECT id FROM sessions LIMIT 1")
            await conn.execute("SELECT id FROM question_results LIMIT 1")
            print("✅ Neon Tables READY")
        finally:
            await conn.close()
    except Exception as e:
        print(f"❌ Neon Error: {e}")
        print("\nMake sure you have run the following SQL in Neon console:")
        print("""
        CREATE TABLE user_profiles (
            id TEXT PRIMARY KEY,
            full_name TEXT,
            bio TEXT,
            resume_url TEXT,
            skills TEXT[],
            experience_level TEXT,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        );

        CREATE TABLE sessions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id text NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
            role text,
            topics text[],
            difficulty text,
            mode text DEFAULT 'buddy',
            overall_score int,
            confidence_avg int,
            created_at timestamptz DEFAULT now(),
            ended_at timestamptz
        );

        CREATE TABLE question_results (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id uuid REFERENCES sessions(id) ON DELETE CASCADE,
            question_text text,
            user_answer text,
            ideal_answer text,
            score int,
            filler_word_count int,
            emotion_log jsonb,
            created_at timestamptz DEFAULT now()
        );
        """)

if __name__ == "__main__":
    asyncio.run(init())
