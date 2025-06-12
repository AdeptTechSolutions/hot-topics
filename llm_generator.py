import asyncio
import json
import os
import time
from typing import Any, Dict, List, Optional

import google.generativeai as genai

from config import Config
from image_gen import ImageGenerator

PROMPT = """
You are an expert PPC campaign strategist. Your task is to create comprehensive advertising campaigns based on the provided keyword research for the topic: "{topic}".

**Keyword Data:**
{keyword_context}

**Instructions:**
1. Analyze the keyword data, paying close attention to search volume, CPC, competition, and keyword intent.
2. Create 3-4 distinct campaign strategies based on patterns you identify (e.g., high-volume informational keywords, low-competition commercial keywords).
3. For each campaign, provide all the requested details in the specified JSON structure.
4. For the `ad_copies`, create one complete, detailed ad copy structured as a JSON object. It should follow modern digital advertising standards.
5. For the `image_prompt`, create a detailed, descriptive prompt for a text-to-image model to generate a relevant ad creative. Follow prompt writing best practices: include a clear subject, context/background, and style (e.g., 'photorealistic', 'vibrant illustration', 'minimalist'). For example: "A photorealistic, close-up shot of a high-quality, durable car tyre on a wet asphalt road, with water splashing dynamically. The lighting should be dramatic to highlight the tread pattern and grip."
6. **Crucially, ensure the entire output is a single, valid JSON array. All string values within the JSON must be properly escaped, especially for multi-line content like descriptions.**

**Output Format:**
Return your response as a single, valid JSON array of campaign objects. Do NOT include any explanatory text, markdown formatting (like ```json), or anything outside of the JSON array itself.

The JSON structure for each campaign object must be:
{{
    "title": "string (A compelling and specific campaign name)",
    "objective": "string (The primary goal, e.g., 'Lead Generation', 'Brand Awareness')",
    "keywords": ["string", "string", ...],
    "description": "string (A detailed description of the campaign strategy and rationale)",
    "expected_performance": "string (Performance expectations based on the data, e.g., 'High click volume with moderate CPC')",
    "ad_copies": [
        {{
            "headlines": [
                "string (Headline 1, max 30 chars)",
                "string (Headline 2, max 30 chars)",
                "string (Headline 3, max 30 chars)"
            ],
            "descriptions": [
                "string (Description 1, max 90 chars)",
                "string (Description 2, max 90 chars)"
            ],
            "display_path": "string (e.g., /tyre-deals)"
        }}
    ],
    "targeting_suggestions": "string (Recommendations for targeting, bidding, and budget)",
    "image_prompt": "string (A detailed prompt for an image generation model.)"
}}
"""


class LLMGenerator:
    """AI-powered campaign generator using Gemini for keyword data"""

    def __init__(self, config: Config):
        self.api_key = config.GEMINI_API_KEY
        self.model_name = config.GEMINI_MODEL
        self.client = None
        self.last_request_time = 0
        self.request_delay = 2.0
        self.image_generator = ImageGenerator(config)

        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.client = True
            except Exception as e:
                print(f"Error initializing Gemini client: {e}")

    def is_available(self) -> bool:
        """Check if Gemini API is available for text generation"""
        return self.client is not None and self.api_key is not None

    async def _wait_for_rate_limit(self):
        """Implement rate limiting for Gemini API"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.request_delay:
            await asyncio.sleep(self.request_delay - elapsed)
        self.last_request_time = time.time()

    async def _generate_and_attach_images(
        self, campaigns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Takes a list of campaigns, generates an image for each, and attaches the path.
        """
        if not self.image_generator.is_available():
            print("Image generator not available, skipping image generation.")
            return campaigns

        async def process_campaign(campaign: Dict[str, Any]) -> Dict[str, Any]:
            image_prompt = campaign.get("image_prompt")
            title = campaign.get("title", "untitled-campaign")
            if image_prompt:
                await asyncio.sleep(1)
                image_path = await self.image_generator.generate_image(
                    image_prompt, title
                )
                campaign["image_path"] = image_path
            return campaign

        tasks = [process_campaign(c) for c in campaigns]
        processed_campaigns = await asyncio.gather(*tasks)
        return processed_campaigns

    async def generate_campaigns_from_keywords(
        self, keywords_data: List[Dict[str, Any]], topic: str
    ) -> List[Dict[str, Any]]:
        """Generate campaign ideas based on keyword data"""
        if not self.is_available():
            return []

        await self._wait_for_rate_limit()

        top_keywords = sorted(
            keywords_data, key=lambda x: x.get("search_volume", 0), reverse=True
        )[:20]

        keyword_context = self._prepare_keyword_context(top_keywords)

        prompt = PROMPT.format(topic=topic, keyword_context=keyword_context)

        model = genai.GenerativeModel(self.model_name)
        response = await model.generate_content_async(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.2,
                max_output_tokens=8192,
            ),
        )
        campaigns = self._parse_campaign_response(response.text)
        if not campaigns:
            return []

        return await self._generate_and_attach_images(campaigns)

    def _prepare_keyword_context(self, keywords: List[Dict[str, Any]]) -> str:
        """Prepare keyword data context for prompts"""
        context_lines = []
        for kw in keywords:
            search_volume = kw.get("search_volume") or 0
            cpc = kw.get("cpc") or 0.0
            difficulty = kw.get("keyword_difficulty") or 0

            line = (
                f"Keyword: {kw.get('keyword', '')} | "
                f"Volume: {search_volume:,} | "
                f"CPC: ${cpc:.2f} | "
                f"Competition: {kw.get('competition_level', 'N/A')} | "
                f"Difficulty: {difficulty}/100"
            )
            context_lines.append(line)
        return "\n".join(context_lines)

    def _parse_campaign_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse campaign response from Gemini, cleaning and correcting common LLM-induced JSON errors.
        """
        text = response_text.strip()

        if text.startswith("```json"):
            text = text[7:].strip()
        elif text.startswith("```"):
            text = text[3:].strip()

        if text.endswith("```"):
            text = text[:-3].strip()

        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
            return []
        except json.JSONDecodeError as e:
            print(
                f"Initial JSON parsing failed: {e}. Attempting to slice and re-parse..."
            )
            start = text.find("[")
            end = text.rfind("]")

            if start != -1 and end != -1:
                json_str = text[start : end + 1]
                try:
                    data = json.loads(json_str)
                    if isinstance(data, list):
                        print("✅ Fallback JSON parsing successful after slicing.")
                        return data
                except json.JSONDecodeError as final_e:
                    print(f"Fallback JSON parsing failed even after slicing: {final_e}")
                    print(f">>> Offending Text\n{response_text}")
                    return []

            return []
