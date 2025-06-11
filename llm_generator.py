import asyncio
import json
import os
import time
from typing import Any, Dict, List, Optional

import google.generativeai as genai

from config import Config

PROMPT = """
You are an expert PPC campaign strategist. A user has provided the topic "{topic}", but no specific keyword data is available.

**Your Task:**
Brainstorm and create 2-3 distinct, hypothetical starter campaign strategies for this topic. Since there's no data, base your strategies on common sense, industry knowledge, and likely user intents (e.g., informational, commercial, local).

**For each campaign, provide:**
1. A compelling title.
2. A primary objective.
3. A list of 5-8 *example* keywords you would expect to be relevant for this campaign.
4. A clear description of the strategy.
5. General expectations for performance.
6. Example ad copy (headlines and descriptions).
7. General targeting suggestions.

**Output Format:**
Return your response as a single, valid JSON array of campaign objects. Do NOT include any text or markdown outside of the JSON array.

The JSON structure for each campaign object must be:
{{
    "title": "string",
    "objective": "string",
    "keywords": ["string", "string", ...],
    "description": "string",
    "expected_performance": "string",
    "ad_copies": ["string", "string", "string"],
    "targeting_suggestions": "string"
}}
"""


class LLMGenerator:
    """AI-powered campaign generator using Gemini for DataForSEO keyword data"""

    def __init__(self, config: Config):
        self.api_key = config.GEMINI_API_KEY
        self.model_name = config.GEMINI_MODEL
        self.client = None
        self.last_request_time = 0
        self.request_delay = 2.0

        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.client = True
            except Exception as e:
                print(f"Error initializing Gemini client: {e}")

    def is_available(self) -> bool:
        """Check if Gemini API is available"""
        return self.client is not None and self.api_key is not None

    async def _wait_for_rate_limit(self):
        """Implement rate limiting for Gemini API"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.request_delay:
            await asyncio.sleep(self.request_delay - elapsed)
        self.last_request_time = time.time()

    async def generate_campaigns_from_keywords(
        self, keywords_data: List[Dict[str, Any]], topic: str
    ) -> List[Dict[str, Any]]:
        """Generate campaign ideas based on DataForSEO keyword data"""
        if not self.is_available():
            return []

        await self._wait_for_rate_limit()

        top_keywords = sorted(
            keywords_data, key=lambda x: x.get("search_volume", 0), reverse=True
        )[:20]

        keyword_context = self._prepare_dataforseo_keyword_context(top_keywords)

        prompt = f"""
        You are an expert PPC campaign strategist. Your task is to create comprehensive advertising campaigns based on the provided DataForSEO keyword research for the topic: "{topic}".

        **Keyword Data from DataForSEO:**
        {keyword_context}

        **Instructions:**
        1. Analyze the keyword data, paying close attention to search volume, CPC, competition, and keyword intent.
        2. Create 3-4 distinct campaign strategies based on patterns you identify (e.g., high-volume informational keywords, low-competition commercial keywords).
        3. For each campaign, provide all the requested details in the specified JSON structure.

        **Output Format:**
        Return your response as a single, valid JSON array of campaign objects. Do NOT include any explanatory text, markdown formatting (like ```json), or anything outside of the JSON array itself.

        The JSON structure for each campaign object must be:
        {{
            "title": "string (A compelling and specific campaign name)",
            "objective": "string (The primary goal, e.g., 'Lead Generation', 'Brand Awareness')",
            "keywords": ["string", "string", ...],
            "description": "string (A detailed description of the campaign strategy and rationale)",
            "expected_performance": "string (Performance expectations based on the data, e.g., 'High click volume with moderate CPC')",
            "ad_copies": ["string (Headline 1)", "string (Headline 2)", "string (Description 1)"],
            "targeting_suggestions": "string (Recommendations for targeting, bidding, and budget)"
        }}
        """

        model = genai.GenerativeModel(self.model_name)
        response = await model.generate_content_async(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.7,
                max_output_tokens=4096,
            ),
        )
        return self._parse_campaign_response(response.text)

    async def generate_hypothetical_campaigns(self, topic: str) -> List[Dict[str, Any]]:
        """Generate hypothetical campaign ideas when no keyword data is available."""
        if not self.is_available():
            return []

        await self._wait_for_rate_limit()

        prompt = PROMPT.format(topic=topic)
        model = genai.GenerativeModel(self.model_name)
        response = await model.generate_content_async(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.8,
                max_output_tokens=4096,
            ),
        )
        return self._parse_campaign_response(response.text)

    def _prepare_dataforseo_keyword_context(
        self, keywords: List[Dict[str, Any]]
    ) -> str:
        """Prepare DataForSEO keyword data context for prompts"""
        context_lines = []
        for kw in keywords:
            line = (
                f"Keyword: {kw.get('keyword', '')} | "
                f"Volume: {kw.get('search_volume', 0):,} | "
                f"CPC: ${kw.get('cpc', 0):.2f} | "
                f"Competition: {kw.get('competition_level', 'N/A')} | "
                f"Difficulty: {kw.get('keyword_difficulty', 0)}/100"
            )
            context_lines.append(line)
        return "\n".join(context_lines)

    def _parse_campaign_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse campaign response from Gemini, expecting a JSON string."""
        try:

            data = json.loads(response_text)
            if isinstance(data, list):
                return data
            return []
        except json.JSONDecodeError:

            try:
                text = response_text.strip()

                if text.startswith("```json"):
                    text = text[7:].strip()
                elif text.startswith("```"):
                    text = text[3:].strip()

                if text.endswith("```"):
                    text = text[:-3].strip()

                campaigns = json.loads(text)
                if isinstance(campaigns, list):
                    return campaigns
                return []
            except Exception as parse_error:
                print(f"Fallback JSON parsing failed: {parse_error}")
                return []
