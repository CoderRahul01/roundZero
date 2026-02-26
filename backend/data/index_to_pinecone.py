# backend/data/index_to_pinecone.py
import json, os, time
from pinecone import Pinecone, ServerlessSpec
from google import genai
from dotenv import load_dotenv

load_dotenv()

# We use Gemini for embeddings as Anthropic doesn't have a native embedding API
genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# Create index if not exists (Delete first if wrong dimension)
index_name = "interview-questions"
if index_name in [idx.name for idx in pc.list_indexes()]:
    idx_info = pc.describe_index(index_name)
    if idx_info.dimension != 3072:
        print(f"🗑️ Deleting index '{index_name}' due to dimension mismatch...")
        pc.delete_index(index_name)
        # Wait for deletion
        time.sleep(10)

if index_name not in [idx.name for idx in pc.list_indexes()]:
    print(f"🚀 Creating index '{index_name}' with dimension 3072...")
    pc.create_index(
        name=index_name,
        dimension=3072, # Gemini gemini-embedding-001 is 3072
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
    # Wait for creation
    time.sleep(10)

index = pc.Index(index_name)

with open("questions_normalized.json") as f:
    questions = json.load(f)

print(f"Embedding {len(questions)} questions using Gemini...")

BATCH = 50
for i in range(0, len(questions), BATCH):
    batch = questions[i:i+BATCH]
    texts = [f"{q['question']} {q['category']} {q['difficulty']}" for q in batch]
    
    # Batch embed with Gemini for speed
    res = genai_client.models.embed_content(
        model="models/gemini-embedding-001",
        contents=texts
    )
    
    vectors = []
    for q, emb_obj in zip(batch, res.embeddings):
        vectors.append((
            q["id"],
            emb_obj.values,
            {
                "question": q["question"],
                "ideal_answer": q["ideal_answer"],
                "category": q["category"],
                "difficulty": q["difficulty"],
                "source": q["source"]
            }
        ))
    
    index.upsert(vectors=vectors)
    print(f"Indexed {min(i+BATCH, len(questions))}/{len(questions)}")

print("✅ Pinecone index complete (Gemini Embeddings)")