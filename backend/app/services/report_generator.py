import logging
from typing import Dict, Any, List
from app.services.session_service import SessionService
from app.services.supermemory_service import SupermemoryService
from app.core.settings import get_settings
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Service to compile session results into a polished candidate report."""

    @staticmethod
    async def generate_report(session_id: str) -> Dict[str, Any]:
        logger.info(f"Generating report for session {session_id}")
        
        # 1. Fetch all raw results — use get_session_results which checks:
        #    Redis list (session_results:{id}) → config blob → Neon, in order.
        session_data = await SessionService.get_session(session_id)
        if not session_data:
            raise ValueError(f"Session {session_id} not found")

        results = await SessionService.get_session_results(session_id)
        logger.info(f"Loaded {len(results)} results for session {session_id}")

        user_id = session_data.get("user_id")
        
        if not results:
            # Fallback for empty/aborted sessions
            return {
                "overallScore": 0,
                "confidenceAvg": 0,
                "duration": "0:00",
                "questionsAnswered": 0,
                "breakdown": [],
                "strengths": ["Session was too short for evaluation."],
                "weaknesses": [],
                "summary": "No data available."
            }

        # 2. Compile Aggregates
        total_score = sum(r.get("score", 0) for r in results)
        avg_score = round(total_score / len(results))
        total_fillers = sum(r.get("filler_word_count", 0) for r in results)
        
        # 3. AI-Powered Summary (The "Coach's Note")
        settings = get_settings()
        client = genai.Client(api_key=settings.google_api_key)
        
        # Define response schema for structured output
        class ReportOutput(types.BaseModel):
            summary: str
            strengths: List[str]
            weaknesses: List[str]

        prompt = f"""
        You are an expert Interview Coach. Review these candidate performance results and provide a structured report.
        
        SESSION DATA:
        - Role: {session_data.get('role')}
        - Difficulty: {session_data.get('difficulty')}
        - Average Score: {avg_score}/100
        - Total Filler Words: {total_fillers}
        
        QUESTION BREAKDOWN:
        {[{'q': r.get('question_text'), 'score': r.get('score'), 'feedback': r.get('feedback')} for r in results]}
        
        Include:
        1. A 3-sentence professional summary of overall performance.
        2. Top 2 specific Strengths based on the answers.
        3. Top 2 actionable Areas for Improvement.
        """
        
        summary_text = "Analysis pending..."
        strengths = ["Technical depth"]
        weaknesses = ["Verbal clarity"]
        
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash-001",  # text model — native-audio model doesn't support structured output
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ReportOutput
                )
            )
            report_ai = response.parsed
            summary_text = report_ai.summary
            strengths = report_ai.strengths
            weaknesses = report_ai.weaknesses
        except Exception as e:
            logger.error(f"Failed to generate structured AI report: {e}")

        # 4. Save to Supermemory (Phase 6 loop closure)
        if user_id:
            try:
                await SupermemoryService.save_session_summary(user_id, summary_text)
                logger.info(f"Summary saved to Supermemory for {user_id}")
            except Exception as e:
                logger.warning(f"Failed to save to Supermemory: {e}")

        # 5. Build Final Report Object
        # Confidence: derive from avg score (score is 0-10, map to 0-100%)
        max_score_per_q = results[0].get("max_score", 10) if results else 10
        confidence_avg = round((avg_score / max_score_per_q) * 100) if max_score_per_q else avg_score

        return {
            "overallScore": min(100, avg_score * 10),  # scores are 0-10; convert to 0-100
            "confidenceAvg": confidence_avg,
            "totalFillers": total_fillers,
            "questionsAnswered": len(results),
            "summary": summary_text,
            "breakdown": [
                {
                    "q": r.get("question_text"),
                    "score": r.get("score"),
                    "feedback": r.get("feedback") or r.get("user_answer", ""),
                    "fillers": r.get("filler_word_count", 0)
                } for r in results
            ],
            "strengths": strengths,
            "weaknesses": weaknesses
        }
