import hashlib
import json
import logging
import time
from typing import Any, Dict, List

from google import genai
from google.genai import types

from app.core.settings import get_settings

logger = logging.getLogger(__name__)


class QuestionEngine:
    """
    Hybrid Question Engine that uses Gemini to generate tailored interview
    questions with ideal answers for accurate semantic scoring.
    """

    @classmethod
    async def generate_questions(
        cls,
        role: str,
        topics: List[str],
        difficulty: str,
        user_memory: str = "",
        company: str = "a top tech company",
        total_questions: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Generates a tailored question bank for an interview session.
        Each question includes an ideal_answer used for semantic scoring.
        """
        settings = get_settings()
        client = genai.Client(api_key=settings.google_api_key)

        # Session-unique seed so identical inputs still produce fresh questions
        session_seed = hashlib.md5(
            f"{role}{topics}{difficulty}{time.time()}".encode()
        ).hexdigest()[:10]

        topics_str = ", ".join(topics) if topics else "General Software Engineering"

        prompt = f"""You are a senior technical interviewer at {company} with 15+ years of experience.
Generate a high-quality interview question bank for a {role} candidate.

INTERVIEW PARAMETERS:
- Role: {role}
- Topics: {topics_str}
- Difficulty: {difficulty}
- Total Questions: {total_questions}
- Session seed (ensures variety): {session_seed}
"""

        if user_memory:
            prompt += f"""
CANDIDATE HISTORY:
{user_memory}

USE THIS CONTEXT to:
1. Avoid repeating topics they have already been tested on.
2. Probe deeper into documented weaknesses or inconsistent areas.
3. Tailor difficulty based on their past performance.
"""

        prompt += f"""
VARIETY REQUIREMENTS — MANDATORY:
Generate {total_questions} questions that collectively cover ALL of these dimensions.
Do NOT ask more than one question from the same dimension:

  1. PRACTICAL/HANDS-ON — "How would you implement...", "Walk me through coding..."
     Tests: ability to DO, not just know. Requires explaining concrete steps or code.

  2. THEORETICAL/CONCEPTUAL — "Explain the difference between...", "Why does X work this way?"
     Tests: depth of understanding. Requires explaining WHY, not just WHAT.

  3. SYSTEM DESIGN / ARCHITECTURE — "How would you design a system that...", "How would you scale..."
     Tests: big-picture thinking, trade-offs, real-world constraints.

  4. BEHAVIORAL (STAR format) — "Tell me about a time when...", "Describe a situation where..."
     Tests: real experience, judgment, teamwork, and impact. Requires a specific story.

  5. SITUATIONAL / DEBUGGING — "What would you do if...", "How would you debug...", "Your system is..."
     Tests: problem-solving under pressure, edge cases, and decision-making.

QUALITY RULES:
- Every question must be open-ended (no yes/no answers possible).
- Questions must require elaboration — a one-sentence answer should feel incomplete.
- Each question must feel like it came from a real interview at a top company.
- Use varied opening words — never start two questions the same way.
- Ask about real-world trade-offs, failure modes, and practical consequences.
- Do NOT ask trivia or definition-only questions.
- Tailor to the specific role: a {role} would actually face these challenges.

OUTPUT FORMAT:
Return ONLY a valid JSON array. No markdown, no preamble.

Each object must have exactly these fields:
  "question"        : The question exactly as Aria should speak it (conversational, clear)
  "topic"           : Specific sub-topic (e.g., "database indexing", "async/await", "conflict resolution")
  "difficulty"      : One of: Easy, Medium, Hard (match the overall difficulty: {difficulty})
  "ideal_answer"    : A comprehensive 120-180 word model answer covering all key points.
                      Write as a spoken explanation (not bullet points). Be specific and technical.
                      This is used for semantic scoring — be thorough and accurate.
  "expected_signals": List of 4-6 specific keywords/concepts a strong answer must mention.
  "follow_ups"      : List of exactly 2 follow-up objects, each with:
                        "trigger"  : When to ask (e.g., "if they miss error handling")
                        "question" : The follow-up question text

Example of ONE question object (do not copy this verbatim):
{{
  "question": "Walk me through how you'd design a URL shortening service that handles 100 million URLs.",
  "topic": "system design",
  "difficulty": "Hard",
  "ideal_answer": "I'd start with the core requirements: generating a short unique key for each URL and resolving it back quickly. For key generation I'd use base62 encoding of an auto-incrementing ID from a distributed counter — this avoids hash collisions without needing a lookup. The read path is the hot path, so I'd use a distributed cache like Redis with the short code as key and the long URL as value, with a cache hit rate target above 99%. For storage I'd use a relational DB with a compound index on short_code. To scale writes I'd shard by the first character of the short code. Analytics can be handled asynchronously via a Kafka queue so they don't block redirects. Custom URLs need a separate uniqueness check. CDN-level edge caching handles geographic latency.",
  "expected_signals": ["base62 encoding", "Redis caching", "sharding", "CDN", "async analytics"],
  "follow_ups": [
    {{"trigger": "if they miss expiry/TTL", "question": "How would you handle URL expiration and cleanup of stale entries?"}},
    {{"trigger": "if they miss abuse prevention", "question": "What mechanisms would you add to prevent malicious URL shortening?"}}
  ]
}}
"""

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=1.0,
                ),
            )

            if not response.text:
                raise ValueError("Empty response from LLM")

            questions = json.loads(response.text)

            if not isinstance(questions, list) or len(questions) == 0:
                raise ValueError("Invalid question bank format returned")

            # Validate each question has required fields; fill missing ones
            required = {"question", "topic", "difficulty", "ideal_answer", "expected_signals", "follow_ups"}
            validated = []
            for q in questions:
                if not isinstance(q, dict):
                    continue
                # Ensure all required keys exist
                if "question" not in q or not q["question"]:
                    continue
                q.setdefault("ideal_answer", "")
                q.setdefault("expected_signals", [])
                q.setdefault("follow_ups", [])
                q.setdefault("topic", "General")
                q.setdefault("difficulty", difficulty)
                validated.append(q)

            if not validated:
                raise ValueError("No valid questions after validation")

            logger.info(f"Generated {len(validated)} questions for {role} interview")
            return validated

        except Exception as e:
            logger.error(f"Failed to generate questions: {e}")
            # Fallback to a single generic question if everything fails
            return [
                {
                    "question": f"Tell me about the most technically challenging project you've worked on as a {role}. Walk me through the problem, your approach, and the trade-offs you made.",
                    "topic": "behavioral",
                    "difficulty": difficulty,
                    "ideal_answer": f"A strong answer would follow the STAR format: describe the specific technical challenge clearly, explain the constraints (time, scale, team size), walk through the solution architecture with concrete technical decisions, discuss the trade-offs considered (e.g., consistency vs. availability, build vs. buy), describe the outcome with measurable impact, and reflect on what they learned or would do differently. For a {role}, the answer should demonstrate both technical depth and ownership.",
                    "expected_signals": ["STAR method", "technical depth", "trade-offs", "measurable impact", "ownership"],
                    "follow_ups": [
                        {"trigger": "if they stay vague", "question": "Can you give me a specific technical decision you made and why you chose that approach over alternatives?"},
                        {"trigger": "if they skip the outcome", "question": "What was the measurable impact of your solution, and how did you validate it?"},
                    ],
                }
            ]
