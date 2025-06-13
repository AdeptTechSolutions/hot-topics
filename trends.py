import asyncio
import json
from typing import Dict, List, Optional

import requests
from google import genai

from config import Config

PROMPT_TEMPLATE = """
You are a senior marketing strategist specializing in identifying high-potential advertising opportunities from market trends.

Your task is to analyze the following list of categorized trending search queries from Google Trends and select the 50 most promising and distinct topics for new, broad-based advertising campaigns.

**Trending Search Queries:**
{trends_summary}

**Your Goal:**
Identify 50 distinct topics from the queries that have high potential for a successful advertising campaign. Prioritize topics with commercial intent. Consider factors like:
- Commercial intent (Is it something people buy or research before buying?).
- Broad appeal (Can it target a large audience?).
- Timeliness and trendiness.
- Competitiveness (A very high-level news event might be too crowded).
- Variety (Choose topics from different categories if possible).

**Distribution Strategy:**
Try to distribute the 50 topics across available categories in a relatively even fashion. Aim for roughly 5-6 topics per category when data is available, but prioritize quality over perfect distribution. If a category has no trending data (marked as NULL), skip it entirely and focus on categories with actual trends. You may filter out topics from a category that you find irrelevant, for example, the topic "all" in "travel_and_transportation" category or "age" in "games" category.

**Instructions:**
1. Review the trends provided.
2. Choose the 50 most promising topics for ad campaigns.
3. Your response MUST be a single, valid JSON object with categories as keys and arrays of topic strings as values. Each category should contain relevant topics. Do not add any explanation, preamble, markdown, or any other text. Just the JSON object.

**Example of a valid response:**
{{
  "technology": ["electric car chargers", "new smartphone release", "smart home devices"],
  "travel_and_transportation": ["summer travel deals", "airline ticket prices"],
  "entertainment": ["local concert tickets", "streaming service deals"],
  "health": ["skincare trends", "fitness equipment"],
  "pets_and_animals": ["pet adoption near me", "dog training classes"]
  ...
}}
"""


class TrendsAnalyzer:
    """Fetches and analyzes trending topics to suggest a campaign idea."""

    def __init__(self, config: Config):
        self.config = config
        self.searchapi_key = config.SEARCHAPI_KEY
        self.gemini_key = config.GEMINI_API_KEY
        self.gemini_model = config.GEMINI_MODEL
        self.client = None
        self.categories_to_track = [
            "autos_and_vehicles",
            "beauty_and_fashion",
            "entertainment",
            "games",
            "health",
            "shopping",
            "technology",
            "travel_and_transportation",
            "pets_and_animals",
        ]
        if self.gemini_key:
            self.client = genai.Client(api_key=self.gemini_key)

    def _fetch_trending_searches(self, geo: str = "US") -> Optional[Dict]:
        """Fetches trending searches from SearchAPI."""
        if not self.searchapi_key:
            print("SearchAPI key is not configured.")
            return None

        url = "https://www.searchapi.io/api/v1/search"
        params = {
            "engine": "google_trends_trending_now",
            "geo": geo,
            "api_key": self.searchapi_key,
        }
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"SearchAPI request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Failed to parse SearchAPI response: {e}")
            return None

    def _categorize_trends(self, trends_data: Dict) -> Dict[str, List[Dict]]:
        """Categorizes trends and limits them to 50 per category."""
        categorized = {cat: [] for cat in self.categories_to_track}

        if not trends_data or "trends" not in trends_data:
            return categorized

        for trend in trends_data["trends"]:
            trend_categories = trend.get("categories", [])
            for cat in trend_categories:
                if cat in self.categories_to_track and len(categorized[cat]) < 50:
                    query = trend.get("query") or "Unknown Query"
                    position = trend.get("position") or "N/A"
                    categorized[cat].append({"query": query, "position": position})
        return categorized

    def _prepare_gemini_prompt(self, categorized_trends: Dict) -> str:
        """Formats the categorized trends into a string for the Gemini prompt."""
        summary_parts = []
        categories_with_data = []

        for category, trends in categorized_trends.items():
            summary_parts.append(f"Category: {category}")
            if trends:
                categories_with_data.append(category)
                for trend in trends:
                    query = trend.get("query", "N/A")
                    position = trend.get("position", "N/A")
                    summary_parts.append(f"- {query} (Overall Position: {position})")
            else:
                summary_parts.append("NULL")
            summary_parts.append("")

        if categories_with_data:
            target_per_category = max(1, 50 // len(categories_with_data))
            summary_parts.append(
                f"DISTRIBUTION GUIDANCE: You have {len(categories_with_data)} categories with data. Try to select approximately {target_per_category} topics from each category with data to achieve even distribution."
            )
            summary_parts.append("")

        trends_summary = "\n".join(summary_parts)

        if PROMPT_TEMPLATE is None:
            print("Error: PROMPT_TEMPLATE is None")
            return ""

        return PROMPT_TEMPLATE.format(
            trends_summary=trends_summary or "No trends data available"
        )

    async def get_promising_topics(self) -> Optional[List[str]]:
        """Orchestrates fetching, categorizing, and analyzing trends to get a list of topics."""
        if not self.client:
            print("Gemini client is not configured.")
            return None

        trends_data = self._fetch_trending_searches()
        if not trends_data:
            return None

        categorized_trends = self._categorize_trends(trends_data)
        prompt = self._prepare_gemini_prompt(categorized_trends)
        response_text = ""

        try:
            response = await self.client.aio.models.generate_content(
                model=self.gemini_model,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.5,
                ),
            )
            response_text = response.text

            text = response_text.strip()
            if text.startswith("```json"):
                text = text[7:].strip()
            if text.endswith("```"):
                text = text[:-3].strip()

            data = json.loads(text)
            if isinstance(data, dict):
                topics_with_categories = []
                for category, topics in data.items():
                    if isinstance(topics, list):
                        for topic in topics:
                            if isinstance(topic, str):
                                topics_with_categories.append(
                                    {"topic": topic.lower(), "category": category}
                                )
                return topics_with_categories[:50]
            else:
                print(f"Gemini returned data in an unexpected format: {data}")
                return None

        except (json.JSONDecodeError, Exception) as e:
            print(f"Gemini API call or JSON parsing failed: {e}")
            print(f"Raw response from Gemini: {response_text}")
            return None


async def main():
    """Test function to verify TrendsAnalyzer functionality."""
    from dotenv import load_dotenv

    load_dotenv()
    config = Config()

    if not config.SEARCHAPI_KEY or not config.GEMINI_API_KEY:
        print("Missing SEARCHAPI_KEY or GEMINI_API_KEY in .env file.")
        return

    print("Testing Trends Analyzer")
    analyzer = TrendsAnalyzer(config)

    print("Fetching trends...")
    trends_data = analyzer._fetch_trending_searches()
    if not trends_data:
        print("Failed to fetch trends.")
        return
    print(f"Fetched {len(trends_data.get('trends', []))} trends.")

    print("\nCategorizing trends...")
    categorized = analyzer._categorize_trends(trends_data)
    print("Categorization complete.")
    for cat, trends in categorized.items():
        print(f"  - {cat}: {len(trends)} trends found.")

    print("\nAsking Gemini for the most promising topics...")
    topics = await analyzer.get_promising_topics()

    if topics:
        print(f"\nGemini suggested {len(topics)} topics:")
        for i, topic in enumerate(topics):
            print(f"  {i+1}. {topic}")
    else:
        print("Gemini failed to suggest any topics.")


if __name__ == "__main__":
    asyncio.run(main())
