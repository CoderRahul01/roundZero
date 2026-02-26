# backend/data/prepare_datasets.py
import pandas as pd, json
import os
from pathlib import Path

# Paths relative to repository root
ROOT = Path(__file__).resolve().parents[2]
swe_path = ROOT / "Software Questions.csv"
lc_path = ROOT / "leetcode_dataset - lc.csv"

questions = []

# 1. Process Software Questions
if os.path.exists(swe_path):
    try:
        df = pd.read_csv(swe_path, encoding="latin1")
        for idx, row in df.iterrows():
            questions.append({
                "id": f"swe_{row.get('Question Number', idx)}",
                "question": str(row.get('Question')),
                "ideal_answer": str(row.get('Answer', '')),
                "category": str(row.get('Category', 'General')),
                "difficulty": str(row.get('Difficulty', 'medium')).lower(),
                "source": "Software Questions"
            })
        print(f"Loaded {len(df)} software questions")
    except Exception as e:
        print(f"Error loading {swe_path}: {e}")

# 2. Process LeetCode Dataset
if os.path.exists(lc_path):
    try:
        df = pd.read_csv(lc_path, encoding="latin1")
        for _, row in df.iterrows():
            questions.append({
                "id": f"lc_{row.get('id')}",
                "question": f"{row.get('title')}: {row.get('description')}",
                "ideal_answer": f"Solution link: {row.get('solution_link', 'Internal')}",
                "category": str(row.get('related_topics', 'Algorithms')),
                "difficulty": str(row.get('difficulty', 'medium')).lower(),
                "source": "LeetCode"
            })
        print(f"Loaded {len(df)} leetcode questions")
    except Exception as e:
        print(f"Error loading {lc_path}: {e}")

# Add some hardcoded HR questions
hr_samples = [
    {"id": "hr_1", "question": "Tell me about a time you handled conflict in a team.", "ideal_answer": "STAR format: Situation, Task, Action, Result.", "category": "Behavioral", "difficulty": "medium", "source": "Manual"},
    {"id": "hr_2", "question": "What is your greatest technical weakness?", "ideal_answer": "Identify a real weakness and explain how you are working on it.", "category": "Behavioral", "difficulty": "medium", "source": "Manual"},
    {"id": "hr_3", "question": "Why do you want to work at this company?", "ideal_answer": "Align your values with the company mission.", "category": "Behavioral", "difficulty": "easy", "source": "Manual"},
]
questions.extend(hr_samples)

with open("questions_normalized.json", "w") as f:
    json.dump(questions, f)

print(f"Total questions: {len(questions)}")
