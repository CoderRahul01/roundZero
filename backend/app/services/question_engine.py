import json
import logging
from typing import List, Dict, Any
from google import genai
from google.genai import types
from app.core.settings import get_settings

logger = logging.getLogger(__name__)

class QuestionEngine:
    """
    Hybrid Question Engine that uses an LLM (Claude or Gemini) to generate
    tailored interview questions based on session configuration.
    """
    
    @classmethod
    async def generate_questions(
        cls, 
        role: str, 
        topics: List[str], 
        difficulty: str,
        user_memory: str = "",
        company: str = "a top tech company",
        total_questions: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generates a tailored question bank for an interview session.
        """
        settings = get_settings()
        client = genai.Client(api_key=settings.google_api_key)
        
        # Build the generation prompt
        prompt = f"""
You are an expert technical interviewer at {company}. 
Your goal is to generate a tailored interview question bank for a candidate applying for a {role} position.

INTERVIEW PARAMETERS:
- Role: {role}
- Topics: {', '.join(topics)}
- Difficulty: {difficulty}
- Number of Main Questions: {total_questions}
"""

        if user_memory:
            prompt += f"""
CANDIDATE HISTORY / PERSISTENT MEMORY:
{user_memory}

USE THIS CONTEXT to:
1. Avoid repeating questions or topics they have already mastered.
2. Probe deeper into their documented weaknesses or inconsistent areas.
3. Tailor the tone if the memory indicates they struggle with high pressure.
"""

        prompt += f"""
REQUIRMENTS:
1. Generate exactly {total_questions} main questions.
2. For each question, provide:
   - "question": The actual question text to be spoken by the AI.
   - "topic": The specific sub-topic (e.g., "arrays", "system design").
   - "difficulty": The specific difficulty of this question.
   - "expected_signals": A list of 3-5 keywords or concepts the candidate should mention in a good answer.
   - "follow_ups": A list of 2 potential follow-up questions to ask if the candidate misses key signals or gives a basic answer. Each follow-up should have a "trigger" and a "question".

OUTPUT FORMAT:
Return ONLY a valid JSON array of objects. Do not include any preamble or markdown formatting like ```json.

Example:
[
  {{
    "question": "Can you explain how you would design a rate limiter?",
    "topic": "system design",
    "difficulty": "medium",
    "expected_signals": ["token bucket", "fixed window", "distributed locking"],
    "follow_ups": [
        {{"trigger": "if they miss scalability", "question": "How would this handle 10 million requests per second?"}},
        {{"trigger": "if they miss storage", "question": "Where would you store the counters?"}}
    ]
  }}
]
"""
        
        try:
            # Use Gemini for generation (default)
            # We use gemini-2.5-flash as it's fast and has better free-tier availability for unary
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            if not response.text:
                raise ValueError("Empty response from LLM")
                
            questions = json.loads(response.text)
            
            # Basic validation
            if not isinstance(questions, list) or len(questions) == 0:
                raise ValueError("Invalid question bank format returned")
                
            logger.info(f"Generated {len(questions)} questions for {role} interview")
            return questions
            
        except Exception as e:
            logger.error(f"Failed to generate questions: {e}")
            # Fallback to a single generic question if everything fails
            return [{
                "question": f"Tell me about your most significant project as a {role}.",
                "topic": "behavioral",
                "difficulty": difficulty,
                "expected_signals": ["STAR method", "impact", "technical depth"],
                "follow_ups": []
            }]
