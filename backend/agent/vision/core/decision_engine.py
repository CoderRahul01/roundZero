"""
DecisionEngine for intelligent interview decision-making using Claude Sonnet 4.

This module interfaces with Claude to make context-aware decisions during
live interviews based on multimodal input (emotion, speech, content).
"""

import json
import logging
from typing import Dict, Any
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)


class DecisionEngine:
    """
    Makes intelligent interview decisions using Claude Sonnet 4.
    Analyzes multimodal context and returns structured actions.
    
    Actions:
    - CONTINUE: Let candidate keep talking
    - INTERRUPT: Redirect if off-topic or rambling
    - ENCOURAGE: Provide encouragement if nervous/struggling
    - NEXT: Move to next question (answer is complete)
    - HINT: Provide subtle hint if stuck
    """
    
    def __init__(self, claude_api_key: str, error_handler=None):
        """
        Initialize DecisionEngine with Claude API.
        
        Args:
            claude_api_key: Anthropic API key
            error_handler: Optional ErrorHandler instance for centralized error handling
        """
        self.client = AsyncAnthropic(api_key=claude_api_key)
        self.model = "claude-3-5-sonnet-20241022"
        self.error_handler = error_handler
        
        logger.info("Initialized DecisionEngine with Claude Sonnet 4")
    
    async def make_decision(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make decision based on multimodal context.
        
        Args:
            context: Dictionary with question_text, transcript_so_far, emotion,
                    confidence_score, engagement_level, filler_word_count,
                    speech_pace, long_pause_count
        
        Returns:
            Dictionary with action, message (optional), reasoning
        """
        prompt = self._build_decision_prompt(context)
        
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse structured response
            decision = self._parse_decision_response(response.content[0].text)
            
            logger.info(
                f"Decision made: {decision['action']} "
                f"(reasoning: {decision.get('reasoning', 'N/A')})"
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            
            # Use error handler if available
            if self.error_handler:
                context_with_error = {**context, "error": str(e)}
                fallback = await self.error_handler.handle_claude_error(e, context_with_error)
                return fallback
            
            # Fallback to rule-based decision
            return self._fallback_decision(context)
    
    def _build_decision_prompt(self, context: Dict[str, Any]) -> str:
        """
        Build prompt for Claude with multimodal context.
        
        Args:
            context: Multimodal context dictionary
        
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are an AI interview coach. Analyze the candidate's response and decide the next action.

QUESTION: {context.get('question_text', 'N/A')}

CANDIDATE'S ANSWER SO FAR: {context.get('transcript_so_far', '')}

MULTIMODAL CONTEXT:
- Emotion: {context.get('emotion', 'neutral')}
- Confidence Score: {context.get('confidence_score', 50)}/100
- Engagement Level: {context.get('engagement_level', 'medium')}
- Filler Words: {context.get('filler_word_count', 0)}
- Speech Pace: {context.get('speech_pace', 0):.1f} words/minute
- Long Pauses: {context.get('long_pause_count', 0)}

ACTIONS:
- CONTINUE: Let them keep talking (answer is on track)
- INTERRUPT: Redirect if off-topic or rambling
- ENCOURAGE: Provide encouragement if nervous/struggling
- NEXT: Move to next question (answer is complete)
- HINT: Provide subtle hint if stuck

Return JSON:
{{
    "action": "ACTION_NAME",
    "message": "Message to speak (if needed)",
    "reasoning": "Brief explanation"
}}"""
        return prompt
    
    def _parse_decision_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Claude's JSON response.
        
        Args:
            response_text: Raw response from Claude
        
        Returns:
            Parsed decision dictionary
        """
        try:
            decision = json.loads(response_text)
            
            # Validate action
            valid_actions = ["CONTINUE", "INTERRUPT", "ENCOURAGE", "NEXT", "HINT"]
            if decision.get("action") not in valid_actions:
                logger.warning(f"Invalid action: {decision.get('action')}, defaulting to CONTINUE")
                decision["action"] = "CONTINUE"
            
            return decision
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response: {e}")
            return {
                "action": "CONTINUE",
                "message": "",
                "reasoning": "Failed to parse response"
            }
    
    def _fallback_decision(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rule-based fallback when Claude API fails.
        
        Args:
            context: Multimodal context dictionary
        
        Returns:
            Decision dictionary based on simple rules
        """
        logger.info("Using fallback decision logic")
        
        # High filler count - encourage
        if context.get('filler_word_count', 0) > 10:
            return {
                "action": "ENCOURAGE",
                "message": "Take your time. You're doing great.",
                "reasoning": "High filler word count"
            }
        
        # Low confidence - encourage
        if context.get('confidence_score', 50) < 30:
            return {
                "action": "ENCOURAGE",
                "message": "You've got this. Take a deep breath.",
                "reasoning": "Low confidence"
            }
        
        # Multiple long pauses - hint
        if context.get('long_pause_count', 0) > 3:
            return {
                "action": "HINT",
                "message": "Think about the key concepts we discussed.",
                "reasoning": "Multiple long pauses"
            }
        
        # Default: continue listening
        return {
            "action": "CONTINUE",
            "message": "",
            "reasoning": "No intervention needed"
        }
    
    async def evaluate_answer(
        self,
        question: str,
        answer: str
    ) -> Dict[str, Any]:
        """
        Evaluate final answer quality.
        
        Args:
            question: Question text
            answer: Candidate's answer
        
        Returns:
            Dictionary with relevance_score, completeness_score,
            correctness_score, feedback
        """
        prompt = f"""Evaluate this interview answer:

QUESTION: {question}

ANSWER: {answer}

Provide:
1. Relevance Score (0-100): How well does it address the question?
2. Completeness Score (0-100): Is the answer thorough?
3. Correctness Score (0-100): Is the information accurate?
4. Feedback: 2-3 sentences of constructive feedback

Return as JSON:
{{
    "relevance_score": 85,
    "completeness_score": 75,
    "correctness_score": 90,
    "feedback": "Your feedback here"
}}"""
        
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )
            
            evaluation = json.loads(response.content[0].text)
            logger.info(f"Answer evaluated: relevance={evaluation.get('relevance_score', 0)}")
            return evaluation
            
        except Exception as e:
            logger.error(f"Evaluation error: {e}")
            return {
                "relevance_score": 50,
                "completeness_score": 50,
                "correctness_score": 50,
                "feedback": "Unable to evaluate at this time."
            }
    
    async def generate_summary(self, prompt: str) -> str:
        """
        Generate session summary.
        
        Args:
            prompt: Summary generation prompt with session context
        
        Returns:
            Generated summary text
        """
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            
            summary = response.content[0].text
            logger.info("Session summary generated successfully")
            return summary
            
        except Exception as e:
            logger.error(f"Summary generation error: {e}")
            return "Session completed successfully. Detailed feedback will be available shortly."
