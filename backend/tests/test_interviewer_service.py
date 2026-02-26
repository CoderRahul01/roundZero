import unittest

from agent.interviewer import InterviewerService, SessionConfig


class InterviewerServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.service = InterviewerService()

    async def test_start_session_returns_first_question(self) -> None:
        config = SessionConfig(
            user_id="tester",
            role="Backend Engineer",
            topics=["System Design"],
            difficulty="medium",
            mode="buddy",
        )

        response = await self.service.start_session(config)

        self.assertIn("session_id", response)
        self.assertTrue(response["first_question"])
        self.assertGreaterEqual(response["total_questions"], 1)

    async def test_submit_answer_advances_on_detailed_response(self) -> None:
        config = SessionConfig(
            user_id="tester2",
            role="Backend Engineer",
            topics=["System Design"],
            difficulty="medium",
            mode="buddy",
        )
        started = await self.service.start_session(config)

        transcript = (
            "I would start by defining requirements and traffic assumptions, then split the design into API, "
            "queue, worker, persistence, caching and observability layers. The tradeoff is consistency versus "
            "latency, and I would use retries with idempotency keys, rate limits, and failure isolation for scale."
        )
        response = await self.service.submit_answer(started["session_id"], transcript)

        self.assertEqual(response["action"], "NEXT")
        self.assertFalse(response["is_finished"])
        self.assertGreaterEqual(response["question_index"], 2)

    async def test_end_session_generates_report(self) -> None:
        config = SessionConfig(
            user_id="tester3",
            role="Frontend Engineer",
            topics=["JavaScript"],
            difficulty="easy",
            mode="buddy",
        )
        started = await self.service.start_session(config)
        session_id = started["session_id"]

        await self.service.submit_answer(
            session_id,
            "I would explain with a clear approach, include edge cases, and provide tradeoffs with examples.",
        )
        await self.service.end_session(session_id)
        report = await self.service.get_report(session_id)

        self.assertIn("overall_score", report)
        self.assertIn("breakdown", report)
        self.assertGreaterEqual(report["questions_answered"], 1)


if __name__ == "__main__":
    unittest.main()
