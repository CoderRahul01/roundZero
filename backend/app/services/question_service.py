print("  QuestionService: importing os...", flush=True)
import os
print("  QuestionService: importing logging...", flush=True)
import logging
print("  QuestionService: importing typing...", flush=True)
from typing import List, Dict, Any
print("  QuestionService: importing google.genai...", flush=True)
from google import genai
print("  QuestionService: importing pinecone...", flush=True)
from pinecone import Pinecone
print("  QuestionService: importing app.core.settings...", flush=True)
from app.core.settings import get_settings
print("  QuestionService: imports done.", flush=True)

logger = logging.getLogger(__name__)

class QuestionService:
    _pc_index = None
    _genai_client = None

    @classmethod
    def _get_pinecone_index(cls):
        if cls._pc_index is None:
            settings = get_settings()
            if not settings.google_api_key or not os.getenv("PINECONE_API_KEY"):
                return None
            
            try:
                pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
                cls._pc_index = pc.Index(os.getenv("PINECONE_INDEX", "interview-questions"))
            except Exception as e:
                logger.error(f"Failed to initialize Pinecone: {e}")
                return None
        return cls._pc_index

    @classmethod
    def _get_genai_client(cls):
        if cls._genai_client is None:
            settings = get_settings()
            if not settings.google_api_key:
                return None
            cls._genai_client = genai.Client(api_key=settings.google_api_key)
        return cls._genai_client

    @classmethod
    async def fetch_questions(cls, role: str, topics: List[str], difficulty: str, limit: int = 5) -> List[Dict[str, str]]:
        """
        Fetch relevant interview questions using Pinecone RAG and Gemini Embeddings.
        """
        index = cls._get_pinecone_index()
        client = cls._get_genai_client()
        
        if not index or not client:
            logger.warning("Pinecone or Gemini Client not configured. Falling back to static questions.")
            return cls._get_static_questions(role, difficulty)

        try:
            # Create a query string
            query_text = f"Interview questions for a {role} focusing on {', '.join(topics)}. Difficulty: {difficulty}"
            
            # gemini-embedding-001: upgraded from text-embedding-004.
            # output_dimensionality=768 keeps compatibility with existing Pinecone index.
            model_name = "gemini-embedding-001"
            print(f"DEBUG: Attempting embedding with model '{model_name}'", flush=True)

            try:
                res = client.models.embed_content(
                    model=model_name,
                    contents=[query_text],
                    config={"task_type": "RETRIEVAL_QUERY", "output_dimensionality": 768},
                )
            except Exception as e:
                err_msg = str(e).lower()
                if "404" in err_msg or "not found" in err_msg:
                    print(f"DEBUG: Model '{model_name}' not found, falling back to 'text-embedding-004'", flush=True)
                    res = client.models.embed_content(
                        model="text-embedding-004",
                        contents=[query_text],
                        config={"task_type": "RETRIEVAL_QUERY"},
                    )
                else:
                    raise e

            embedding = res.embeddings[0].values
            
            # Search Pinecone
            search_res = index.query(
                vector=embedding,
                top_k=limit,
                include_metadata=True,
                filter={"difficulty": {"$eq": difficulty}} if difficulty else None
            )
            
            questions = []
            for match in search_res.matches:
                meta = match.metadata
                questions.append({
                    "question": meta.get("question", ""),
                    "ideal_answer": meta.get("ideal_answer", ""),
                    "category": meta.get("category", ""),
                    "difficulty": meta.get("difficulty", "")
                })
            
            if not questions:
                return cls._get_static_questions(role, difficulty)
                
            return questions

        except Exception as e:
            logger.error(f"Error fetching questions from Pinecone: {e}")
            return cls._get_static_questions(role, difficulty)

    @staticmethod
    def _get_static_questions(role: str, difficulty: str) -> List[Dict[str, str]]:
        """Fallback static questions."""
        return [
            {"question": f"Tell me about your most challenging {role} project.", "ideal_answer": "STAR method response."},
            {"question": "How do you keep your technical skills up to date?", "ideal_answer": "Continuous learning and project work."}
        ]
