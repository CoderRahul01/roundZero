import asyncio
import logging
from typing import Any, Dict, List

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
                "scoreTrend": "stable",
                "scoreTrendNote": "",
                "topicsCovered": [],
                "scoresByQuestion": [],
                "breakdown": [],
                "strengths": ["Complete at least one question to receive a strength analysis."],
                "weaknesses": ["Complete at least one question to receive improvement suggestions."],
                "summary": (
                    "The session ended before any questions were fully evaluated. "
                    "Start a new interview and answer at least one question to generate a performance report."
                ),
            }

        # Deduplicate by question_number — keep the last entry per question
        deduped: dict = {}
        for r in results:
            qnum = r.get("question_number") or 0
            deduped[qnum] = r
        results = [deduped[k] for k in sorted(deduped.keys())]

        total_score = sum(r.get("score", 0) for r in results)
        avg_score = round(total_score / len(results))
        total_fillers = sum(r.get("filler_word_count", 0) for r in results)
        overall_score_pct = min(100, avg_score * 10)

        # Compute score trend across questions
        scores_by_q = [int(r.get("score") or 0) for r in results]
        score_trend = "stable"
        if len(scores_by_q) >= 3:
            half = len(scores_by_q) // 2
            first_half_avg = sum(scores_by_q[:half]) / half
            second_half_avg = sum(scores_by_q[half:]) / (len(scores_by_q) - half)
            if second_half_avg > first_half_avg + 0.5:
                score_trend = "improving"
            elif second_half_avg < first_half_avg - 0.5:
                score_trend = "declining"

        # Unique topics in order of appearance
        topics_covered = list(dict.fromkeys(
            r.get("topic") or "General" for r in results
        ))

        # Build a readable breakdown for the prompt
        q_lines = []
        for r in results:
            qnum = r.get("question_number", "?")
            score = r.get("score", 0)
            topic = r.get("topic") or "General"
            q_text = (r.get("question_text") or "")[:120]
            feedback = (r.get("feedback") or r.get("user_answer") or "No feedback recorded.")[:200]
            what_right = (r.get("what_was_right") or "")[:100]
            what_wrong = (r.get("what_was_wrong") or "")[:100]
            correctness = r.get("correctness_percent", 0)
            q_lines.append(
                f"Q{qnum} ({score}/10) [{topic}] {correctness}% correct: \"{q_text}\"\n"
                f"  Right: {what_right or 'N/A'} | Wrong: {what_wrong or 'N/A'}\n"
                f"  Feedback: {feedback}"
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
- Score Trend: {score_trend} (Q1 → Q{len(results)})
- Topics Covered: {', '.join(topics_covered)}
{partial_note}

QUESTION-BY-QUESTION RESULTS:
{breakdown_text}

Write a JSON object with exactly these fields:
{{
  "summary": "<2-3 sentences that are honest and specific — name the candidate's strongest moment and their biggest gap. Avoid generic praise.>",
  "strengths": ["<strength 1 — cite a specific question or answer pattern>", "<strength 2 — specific and actionable praise>"],
  "weaknesses": ["<weakness 1 — specific gap with a clear action: e.g. 'Practice X by doing Y'>", "<weakness 2 — specific and actionable>"],
  "score_trend_note": "<one sentence about the performance trajectory, e.g. 'Performance improved steadily across the interview' or 'Started strong but declined on later technical questions'>"
}}

Rules:
- summary must be 2-3 sentences, no bullet points
- Each strength/weakness must be one clear sentence, maximum 20 words
- Strengths and weaknesses must be grounded in the actual answers above, not generic
- score_trend_note must be exactly one sentence
- If only 1-2 questions were answered, acknowledge it naturally in the summary
"""

        summary_text = (
            f"You answered {len(results)} question(s) in this session. "
            "The AI coach evaluated your responses — see the breakdown below for detailed feedback."
        )
        strengths = ["Engagement with the interview process"]
        weaknesses = ["Complete more questions for a fuller strength/weakness analysis"]
        score_trend_note = ""

        try:
            settings = get_settings()
            client = genai.Client(api_key=settings.google_api_key)

            class ReportOutput(types.BaseModel):
                summary: str
                strengths: List[str]
                weaknesses: List[str]
                score_trend_note: str = ""

            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.generate_content,
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ReportOutput,
                    ),
                ),
                timeout=30.0,
            )
            report_ai = response.parsed
            if report_ai and report_ai.summary:
                summary_text = report_ai.summary
                strengths = report_ai.strengths or strengths
                weaknesses = report_ai.weaknesses or weaknesses
                score_trend_note = report_ai.score_trend_note or ""
            elif response.text:
                import json as _json
                raw = response.text.strip()
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                parsed = _json.loads(raw)
                if parsed.get("summary"):
                    summary_text = parsed["summary"]
                    strengths = parsed.get("strengths") or strengths
                    weaknesses = parsed.get("weaknesses") or weaknesses
                    score_trend_note = parsed.get("score_trend_note") or ""
        except Exception as e:
            logger.error(f"Failed to generate AI report: {type(e).__name__}: {e}", exc_info=True)

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
            "scoreTrend": score_trend,
            "scoreTrendNote": score_trend_note,
            "topicsCovered": topics_covered,
            "scoresByQuestion": scores_by_q,
            "breakdown": [
                {
                    "q": r.get("question_text") or "Question not recorded",
                    "score": min(100, int(r.get("score") or 0) * 10),
                    "feedback": r.get("feedback") or r.get("user_answer") or "No feedback available.",
                    "fillers": r.get("filler_word_count", 0),
                    "whatWasRight": r.get("what_was_right") or "",
                    "whatWasWrong": r.get("what_was_wrong") or "",
                    "correctnessPercent": int(r.get("correctness_percent") or 0),
                    "topic": r.get("topic") or "General",
                }
                for r in results
            ],
            "strengths": strengths,
            "weaknesses": weaknesses,
        }
