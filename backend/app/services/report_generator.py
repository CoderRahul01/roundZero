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

        session_data = await SessionService.get_session(session_id)
        if not session_data:
            raise ValueError(f"Session {session_id} not found")

        results = await SessionService.get_session_results(session_id)
        logger.info(f"Loaded {len(results)} results for session {session_id}")

        user_id = session_data.get("user_id")

        if not results:
            return {
                "overallScore": 0,
                "confidenceAvg": 0,
                "totalFillers": 0,
                "questionsAnswered": 0,
                "breakdown": [],
                "strengths": ["Complete at least one question to receive a strength analysis."],
                "weaknesses": ["Complete at least one question to receive improvement suggestions."],
                "summary": (
                    "The session ended before any questions were fully evaluated. "
                    "Start a new interview and answer at least one question to generate a performance report."
                ),
            }

        # Deduplicate by question_number — keep the last entry per question
        # (record_score may write after the provisional evaluate_answer entry)
        deduped: dict = {}
        for r in results:
            qnum = r.get("question_number") or 0
            deduped[qnum] = r
        results = [deduped[k] for k in sorted(deduped.keys())]

        total_score = sum(r.get("score", 0) for r in results)
        avg_score = round(total_score / len(results))
        total_fillers = sum(r.get("filler_word_count", 0) for r in results)
        overall_score_pct = min(100, avg_score * 10)

        # Build a readable breakdown for the prompt
        q_lines = []
        for r in results:
            qnum = r.get("question_number", "?")
            score = r.get("score", 0)
            q_text = (r.get("question_text") or "")[:120]
            feedback = (r.get("feedback") or r.get("user_answer") or "No feedback recorded.")[:200]
            q_lines.append(
                f"Q{qnum} ({score}/10): \"{q_text}\"\n  Feedback: {feedback}"
            )
        breakdown_text = "\n".join(q_lines)

        partial_note = (
            f"NOTE: Only {len(results)} of 5 questions were answered — "
            "tailor your summary to what actually happened, not the full session."
            if len(results) < 5 else ""
        )

        prompt = f"""You are an expert technical interview coach writing a performance report for a candidate.
Be specific, direct, and professional. Reference actual questions and answers where possible.

CANDIDATE PROFILE:
- Target Role: {session_data.get('role', 'Software Engineer')}
- Difficulty Level: {session_data.get('difficulty', 'Medium')}
- Interview Mode: {session_data.get('mode', 'buddy')}
- Questions Answered: {len(results)} of {session_data.get('total_questions', 5)}
- Overall Score: {overall_score_pct}/100
- Filler Words Used: {total_fillers}
{partial_note}

QUESTION-BY-QUESTION RESULTS:
{breakdown_text}

Write a JSON object with exactly these fields:
{{
  "summary": "<2-3 sentences that are honest and specific — name the candidate's strongest moment and their biggest gap. Avoid generic praise.>",
  "strengths": ["<strength 1 — cite a specific question or answer pattern>", "<strength 2 — specific and actionable praise>"],
  "weaknesses": ["<weakness 1 — specific gap with a clear action: e.g. 'Practice X by doing Y'>", "<weakness 2 — specific and actionable>"]
}}

Rules:
- summary must be 2-3 sentences, no bullet points
- Each strength/weakness must be one clear sentence, maximum 20 words
- Strengths and weaknesses must be grounded in the actual answers above, not generic
- If only 1-2 questions were answered, acknowledge it naturally in the summary
"""

        summary_text = (
            f"You answered {len(results)} question(s) in this session. "
            "The AI coach evaluated your responses — see the breakdown below for detailed feedback."
        )
        strengths = ["Engagement with the interview process"]
        weaknesses = ["Complete more questions for a fuller strength/weakness analysis"]

        try:
            settings = get_settings()
            client = genai.Client(api_key=settings.google_api_key)

            class ReportOutput(types.BaseModel):
                summary: str
                strengths: List[str]
                weaknesses: List[str]

            response = client.models.generate_content(
                model="gemini-2.0-flash-001",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ReportOutput,
                ),
            )
            report_ai = response.parsed
            if report_ai and report_ai.summary:
                summary_text = report_ai.summary
                strengths = report_ai.strengths or strengths
                weaknesses = report_ai.weaknesses or weaknesses
        except Exception as e:
            logger.error(f"Failed to generate structured AI report: {e}")

        # Save to Supermemory for cross-session learning
        if user_id:
            try:
                await SupermemoryService.save_session_summary(user_id, summary_text)
                logger.info(f"Summary saved to Supermemory for {user_id}")
            except Exception as e:
                logger.warning(f"Failed to save to Supermemory: {e}")

        max_score_per_q = results[0].get("max_score", 10) if results else 10
        confidence_avg = round((avg_score / max_score_per_q) * 100) if max_score_per_q else overall_score_pct

        return {
            "overallScore": overall_score_pct,
            "confidenceAvg": confidence_avg,
            "totalFillers": total_fillers,
            "questionsAnswered": len(results),
            "summary": summary_text,
            "breakdown": [
                {
                    "q": r.get("question_text") or "Question not recorded",
                    "score": min(100, int(r.get("score") or 0) * 10),
                    "feedback": r.get("feedback") or r.get("user_answer") or "No feedback available.",
                    "fillers": r.get("filler_word_count", 0),
                }
                for r in results
            ],
            "strengths": strengths,
            "weaknesses": weaknesses,
        }
