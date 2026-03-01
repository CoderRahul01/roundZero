import os
import ijson
import pandas as pd
from pymongo import MongoClient, UpdateOne
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = "roundZero"
COLLECTION_NAME = "questions"

# Paths relative to repository root
ROOT = Path(__file__).resolve().parents[2]
SWE_PATH = ROOT / "Software Questions.csv"
LC_PATH = ROOT / "leetcode_dataset - lc.csv"
HR_PATH = ROOT / "backend/data/hr_interview_questions_dataset.json"

def migrate_data():
    if not MONGODB_URI:
        print("Error: MONGODB_URI not found in .env or environment variables.")
        return

    client = MongoClient(MONGODB_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    # Create indexes for performance
    print("Creating indexes...")
    collection.create_index("category")
    collection.create_index("difficulty")
    collection.create_index("source")
    collection.create_index("id", unique=True)

    ops = []

    # 1. Process Software Questions
    if SWE_PATH.exists():
        print(f"Processing {SWE_PATH}...")
        try:
            df = pd.read_csv(SWE_PATH, encoding="latin1")
            for idx, row in df.iterrows():
                q_id = f"swe_{row.get('Question Number', idx)}"
                doc = {
                    "id": q_id,
                    "question": str(row.get('Question')),
                    "ideal_answer": str(row.get('Answer', '')),
                    "category": str(row.get('Category', 'General')),
                    "difficulty": str(row.get('Difficulty', 'medium')).lower(),
                    "source": "Software Questions"
                }
                ops.append(UpdateOne({"id": q_id}, {"$set": doc}, upsert=True))
            print(f"Prepared {len(df)} software questions")
        except Exception as e:
            print(f"Error loading {SWE_PATH}: {e}")

    # 2. Process LeetCode Dataset
    if LC_PATH.exists():
        print(f"Processing {LC_PATH}...")
        try:
            df = pd.read_csv(LC_PATH, encoding="latin1")
            for _, row in df.iterrows():
                q_id = f"lc_{row.get('id')}"
                doc = {
                    "id": q_id,
                    "question": f"{row.get('title', '')}: {row.get('description', '')}",
                    "ideal_answer": f"Solution link: {row.get('solution_link', 'Internal')}",
                    "category": str(row.get('related_topics', 'Algorithms')),
                    "difficulty": str(row.get('difficulty', 'medium')).lower(),
                    "source": "LeetCode"
                }
                ops.append(UpdateOne({"id": q_id}, {"$set": doc}, upsert=True))
            print(f"Prepared {len(df)} leetcode questions")
        except Exception as e:
            print(f"Error loading {LC_PATH}: {e}")

    # 3. Process HR Dataset (Streaming with ijson)
    if HR_PATH.exists():
        print(f"Processing {HR_PATH} with ijson...")
        try:
            count = 0
            with open(HR_PATH, 'r') as f:
                items = ijson.items(f, 'item')
                for idx, item in enumerate(items):
                    q_id = f"hr_{idx}"
                    doc = {
                        "id": q_id,
                        "question": item.get("question"),
                        "ideal_answer": item.get("ideal_answer", ""),
                        "category": item.get("category", "Behavioral"),
                        "difficulty": str(item.get("difficulty", "medium")).lower(),
                        "source": "HR Dataset"
                    }
                    ops.append(UpdateOne({"id": q_id}, {"$set": doc}, upsert=True))
                    count += 1
                    
                    # Batch upsert every 1000 items to avoid memory pressure
                    if len(ops) >= 1000:
                        collection.bulk_write(ops)
                        print(f"Upserted {count} questions...")
                        ops = []
            print(f"Prepared {count} HR questions")
        except Exception as e:
            print(f"Error loading {HR_PATH}: {e}")

    # Final batch upsert
    if ops:
        collection.bulk_write(ops)
        print("Final batch upserted.")

    print("Migration complete!")

if __name__ == "__main__":
    migrate_data()
