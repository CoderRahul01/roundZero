print("  Importing typing...", flush=True)
from typing import List, Dict, Any, Optional
print("  Importing uuid...", flush=True)
import uuid
print("  Importing app.core.logger...", flush=True)
from app.core.logger import logger
print("  Importing app.core.settings...", flush=True)
from app.core.settings import get_settings
print("  Importing google.genai...", flush=True)
from google import genai
print("  Importing google.genai.types...", flush=True)
from google.genai import types
print("  Importing app.services.question_service...", flush=True)
from app.services.question_service import QuestionService
print("  tools.py reached imports end.", flush=True)

async def fetch_interview_questions(role: str, topics: List[str], difficulty: str) -> List[Dict[str, str]]:
    """
    Tool to fetch relevant interview questions.
    Uses Pinecone RAG and Gemini Embeddings.
    """
    logger.info(f"Fetching {difficulty} questions for {role} in {topics}")
    return await QuestionService.fetch_questions(role, topics, difficulty)

async def save_session_results(session_id: str, results: List[Dict[str, Any]]) -> str:
    """
    Tool to save the results of an interview session to Neon.
    """
    from app.services.session_service import SessionService
    
    success_count = 0
    for result in results:
        if await SessionService.save_question_result(session_id, result):
            success_count += 1
            
    logger.info(f"Saved {success_count}/{len(results)} question results for session {session_id}")
    return f"Saved {success_count} results successfully."

def update_interview_metrics(emotion: str, confidence: int) -> str:
    """
    Tool to update the candidate's real-time metrics (emotion and confidence).
    Use this when you notice a change in the candidate's non-verbal cues.
    Confidence should be an integer between 0 and 100.
    """
    logger.info(f"Metric update: Emotion={emotion}, Confidence={confidence}")
    return f"Metrics updated to {emotion} ({confidence}%)"

def generate_interview_certificate(name: str, performance_summary: str) -> str:
    """
    Generates a personalized interview completion certificate using Imagen 3.
    Call this at the very end of the interview session.
    It returns a URL or confirmation of the generated image.
    """
    settings = get_settings()
    if not settings.google_api_key:
        return "Error: Missing GOOGLE_API_KEY for image generation."
        
    try:
        client = genai.Client(api_key=settings.google_api_key)
        prompt = (
            f"A professional, elegant, and modern certificate of completion for an AI Interview. "
            f"The name '{name}' is clearly inscribed in a beautiful serif font. "
            f"Text: 'Certificate of Excellence'. "
            f"Theme: Minimalist dark blue and gold borders. "
            f"Context: {performance_summary}. "
            f"High quality, 4k resolution, symmetrical layout."
        )
        
        # Note: In a real-world scenario, we'd save this to a public URL or Cloud Storage.
        # For the hackathon demo, we'll log it and simulate.
        logger.info(f"Generating certificate for {name} with prompt: {prompt}")
        
        # Uncomment for actual generation if credits available
        # response = client.models.generate_images(
        #     model="imagen-3.0-generate-002",
        #     prompt=prompt,
        #     config=types.GenerateImagesConfig(number_of_images=1)
        # )
        # return f"Certificate generated successfully for {name}."
        
        return f"SIMULATED: Certificate generated for {name}. (Imagen 3 API call logged)"
        
    except Exception as e:
        logger.error(f"Imagen Error: {e}")
        return f"Error generating certificate: {str(e)}"

def get_interviewer_tools() -> List[Any]:
    """Wraps tools for ADK consumption."""
    return [
        fetch_interview_questions, 
        save_session_results, 
        update_interview_metrics,
        generate_interview_certificate
    ]
