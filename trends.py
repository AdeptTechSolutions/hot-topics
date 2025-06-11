import asyncio
import json
from typing import Dict, List, Optional

import google.generativeai as genai
import requests

from config import Config

PROMPT_TEMPLATE = """
You are a senior marketing strategist specializing in identifying high-potential advertising opportunities from market trends.

Your task is to analyze the following list of categorized trending search queries from Google Trends and select the single best topic for a new, broad-based advertising campaign.

**Trending Search Queries:**
{trends_summary}

**Your Goal:**
Identify one single topic from the queries that has the highest potential for a successful advertising campaign. Consider factors like:
- Commercial intent (Is it something people buy or research before buying?).
- Broad appeal (Can it target a large audience?).
- Timeliness and trendiness.
- Competitiveness (A very high-level news event might be too crowded).

**Instructions:**
1. Review all the trends provided.
2. Choose the single most promising topic for an ad campaign.
3. Your response MUST be only the chosen topic string. Do not add any explanation, preamble, or any other text. Just the topic.

Example: If you choose 'electric car chargers', your entire response should be:
electric car chargers
"""


class TrendsAnalyzer:
    """Fetches and analyzes trending topics to suggest a campaign idea."""

    def __init__(self, config: Config):
        self.config = config
        self.searchapi_key = config.SEARCHAPI_KEY
        self.gemini_key = config.GEMINI_API_KEY
        self.gemini_model = config.GEMINI_MODEL
        self.categories_to_track = [
            "autos_and_vehicles",
            "beauty_and_fashion",
            "entertainment",
            # "games",
            "health",
            "shopping",
            "technology",
            "travel_and_transportation",
            "pets_and_animals",
        ]
        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)

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
        """Categorizes trends and limits them to 10 per category."""
        categorized = {cat: [] for cat in self.categories_to_track}

        if not trends_data or "trends" not in trends_data:
            return categorized

        for trend in trends_data["trends"]:
            trend_categories = trend.get("categories", [])
            for cat in trend_categories:
                if cat in self.categories_to_track and len(categorized[cat]) < 10:
                    categorized[cat].append(
                        {"query": trend.get("query"), "position": trend.get("position")}
                    )
        return categorized

    def _prepare_gemini_prompt(self, categorized_trends: Dict) -> str:
        """Formats the categorized trends into a string for the Gemini prompt."""
        summary_parts = []
        for category, trends in categorized_trends.items():
            summary_parts.append(f"Category: {category}")
            if trends:
                for trend in trends:
                    summary_parts.append(
                        f"- {trend['query']} (Overall Position: {trend['position']})"
                    )
            else:
                summary_parts.append("NULL")
            summary_parts.append("")

        trends_summary = "\n".join(summary_parts)
        return PROMPT_TEMPLATE.format(trends_summary=trends_summary)

    async def get_most_promising_topic(self) -> Optional[str]:
        """Orchestrates fetching, categorizing, and analyzing trends to get a topic."""
        if not self.gemini_key:
            print("Gemini API key is not configured.")
            return None

        trends_data = self._fetch_trending_searches()
        if not trends_data:
            return None

        categorized_trends = self._categorize_trends(trends_data)

        prompt = self._prepare_gemini_prompt(categorized_trends)

        try:
            model = genai.GenerativeModel(self.gemini_model)
            response = await model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Gemini API call failed: {e}")
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

    print("\n🤖 Asking Gemini for the most promising topic...")
    topic = await analyzer.get_most_promising_topic()

    if topic:
        print(f"\nGemini suggested topic: '{topic}'")
    else:
        print("Gemini failed to suggest a topic.")


if __name__ == "__main__":
    asyncio.run(main())
