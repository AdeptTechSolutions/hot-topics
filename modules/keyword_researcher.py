import asyncio
import base64
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp
import requests


@dataclass
class KeywordData:
    """Data structure for keyword information"""

    keyword: str
    search_volume: int
    cpc: float
    competition: str
    difficulty: int
    intent: str
    trend_data: List[int]
    related_keywords: List[str]
    source: str


class KeywordResearcher:
    """Multi-API keyword research system"""

    def __init__(self):
        self.dataforseo_login = os.getenv("DATAFORSEO_LOGIN")
        self.dataforseo_password = os.getenv("DATAFORSEO_PASSWORD")
        self.semrush_key = os.getenv("SEMRUSH_API_KEY")
        self.serpapi_key = os.getenv("SERPAPI_KEY")

        self.last_request_time = {}
        self.request_delays = {
            "dataforseo": 1.0,
            "semrush": 1.0,
            "serpapi": 1.0,
        }

    async def rate_limit(self, service: str):
        """Implement rate limiting for API calls"""
        if service in self.last_request_time:
            elapsed = time.time() - self.last_request_time[service]
            delay = self.request_delays.get(service, 1.0)
            if elapsed < delay:
                await asyncio.sleep(delay - elapsed)

        self.last_request_time[service] = time.time()

    async def get_dataforseo_keywords(self, keywords: List[str]) -> List[KeywordData]:
        """Get keyword data from DataForSEO API"""
        if not self.dataforseo_login or not self.dataforseo_password:
            print("DataForSEO credentials not available")
            return []

        results = []

        try:
            await self.rate_limit("dataforseo")

            auth_string = f"{self.dataforseo_login}:{self.dataforseo_password}"
            auth_bytes = auth_string.encode("ascii")
            auth_b64 = base64.b64encode(auth_bytes).decode("ascii")

            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/json",
            }

            post_data = [
                {
                    "keywords": keywords[:50],
                    "language_name": "English",
                    "location_code": 2840,
                    "include_serp_info": True,
                }
            ]

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.dataforseo.com/v3/dataforseo_labs/google/keyword_suggestions/live",
                    headers=headers,
                    json=post_data,
                ) as response:

                    if response.status == 200:
                        data = await response.json()

                        if data.get("status_code") == 20000:
                            tasks = data.get("tasks", [])
                            for task in tasks:
                                if task.get("status_code") == 20000:
                                    result_items = task.get("result", [])
                                    for result in result_items:
                                        items = result.get("items", [])
                                        for item in items:
                                            keyword_data = KeywordData(
                                                keyword=item.get("keyword", ""),
                                                search_volume=item.get(
                                                    "keyword_info", {}
                                                ).get("search_volume", 0),
                                                cpc=item.get("keyword_info", {}).get(
                                                    "cpc", 0.0
                                                ),
                                                competition=self.get_competition_level(
                                                    item.get("keyword_info", {}).get(
                                                        "competition", 0
                                                    )
                                                ),
                                                difficulty=int(
                                                    item.get("keyword_info", {}).get(
                                                        "competition", 0
                                                    )
                                                    * 100
                                                ),
                                                intent=self.determine_intent(
                                                    item.get("keyword", "")
                                                ),
                                                trend_data=item.get(
                                                    "keyword_info", {}
                                                ).get("search_volume_trend", []),
                                                related_keywords=[],
                                                source="DataForSEO",
                                            )
                                            results.append(keyword_data)
                    else:
                        print(f"DataForSEO API error: {response.status}")

        except Exception as e:
            print(f"Error with DataForSEO API: {e}")

        return results[:100]

    async def get_serpapi_data(self, keywords: List[str]) -> List[KeywordData]:
        """Get keyword data from SerpApi"""
        if not self.serpapi_key:
            print("SerpApi API key not available")
            return []

        results = []

        try:
            await self.rate_limit("serpapi")

            for keyword in keywords[:20]:
                params = {
                    "q": keyword,
                    "engine": "google",
                    "api_key": self.serpapi_key,
                    "location": "United States",
                    "gl": "us",
                    "hl": "en",
                }

                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://serpapi.com/search", params=params
                    ) as response:
                        if response.status == 200:
                            data = await response.json()

                            search_results = data.get("organic_results", [])
                            search_volume = self.estimate_volume_from_results(
                                len(search_results)
                            )

                            cpc = self.estimate_cpc(keyword)
                            difficulty = self.estimate_difficulty_from_keyword(keyword)

                            keyword_data = KeywordData(
                                keyword=keyword,
                                search_volume=search_volume,
                                cpc=cpc,
                                competition=self.estimate_competition(keyword),
                                difficulty=difficulty,
                                intent=self.determine_intent(keyword),
                                trend_data=[],
                                related_keywords=self.extract_related_keywords(data),
                                source="SerpApi",
                            )
                            results.append(keyword_data)
                        else:
                            print(f"SerpApi error: {response.status}")

                await asyncio.sleep(0.1)

        except Exception as e:
            print(f"Error with SerpApi: {e}")

        return results

    def estimate_volume_from_results(self, num_results: int) -> int:
        """Estimate search volume based on number of search results"""
        if num_results >= 8:
            return 5000
        elif num_results >= 5:
            return 2000
        elif num_results >= 3:
            return 1000
        else:
            return 500

    def extract_related_keywords(self, serpapi_data: dict) -> List[str]:
        """Extract related keywords from SerpApi response"""
        related = []

        people_also_ask = serpapi_data.get("people_also_ask", [])
        for item in people_also_ask[:5]:
            if "question" in item:
                related.append(item["question"])

        related_searches = serpapi_data.get("related_searches", [])
        for item in related_searches[:5]:
            if "query" in item:
                related.append(item["query"])

        return related[:10]

    async def get_semrush_data(self, keywords: List[str]) -> List[KeywordData]:
        """Get keyword data from SEMrush API"""
        if not self.semrush_key:
            print("SEMrush API key not available")
            return []

        results = []

        try:
            await self.rate_limit("semrush")

            for keyword in keywords[:20]:
                url = f"https://api.semrush.com/"
                params = {
                    "type": "phrase_these",
                    "key": self.semrush_key,
                    "phrase": keyword,
                    "database": "us",
                    "export_columns": "Ph,Nq,Cp,Co,Nr,Td",
                }

                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            text = await response.text()
                            lines = text.strip().split("\n")

                            for line in lines[1:]:
                                if line:
                                    parts = line.split(";")
                                    if len(parts) >= 6:
                                        keyword_data = KeywordData(
                                            keyword=parts[0],
                                            search_volume=(
                                                int(parts[1])
                                                if parts[1].isdigit()
                                                else 0
                                            ),
                                            cpc=(
                                                float(parts[2])
                                                if parts[2].replace(".", "").isdigit()
                                                else 0.0
                                            ),
                                            competition=self.get_competition_level(
                                                float(parts[3])
                                                if parts[3].replace(".", "").isdigit()
                                                else 0
                                            ),
                                            difficulty=(
                                                int(float(parts[3]) * 100)
                                                if parts[3].replace(".", "").isdigit()
                                                else 0
                                            ),
                                            intent=self.determine_intent(parts[0]),
                                            trend_data=[],
                                            related_keywords=[],
                                            source="SEMrush",
                                        )
                                        results.append(keyword_data)

                await asyncio.sleep(0.1)

        except Exception as e:
            print(f"Error with SEMrush API: {e}")

        return results

    def get_free_keyword_suggestions(
        self, seed_keywords: List[str]
    ) -> List[KeywordData]:
        """Generate keyword suggestions using free methods (Google Suggest, etc.)"""
        suggestions = []

        modifiers = [
            "best",
            "top",
            "cheap",
            "affordable",
            "near me",
            "reviews",
            "how to",
            "what is",
            "guide",
            "tips",
            "cost",
            "price",
            "vs",
            "comparison",
            "list",
            "services",
            "company",
            "local",
        ]

        for seed in seed_keywords[:10]:
            for modifier in modifiers:

                variations = [
                    f"{modifier} {seed}",
                    f"{seed} {modifier}",
                    f"best {seed}",
                    f"{seed} near me",
                    f"how to choose {seed}",
                    f"{seed} reviews",
                ]

                for variation in variations:

                    keyword_data = KeywordData(
                        keyword=variation,
                        search_volume=self.estimate_search_volume(variation),
                        cpc=self.estimate_cpc(variation),
                        competition=self.estimate_competition(variation),
                        difficulty=self.estimate_difficulty_from_keyword(variation),
                        intent=self.determine_intent(variation),
                        trend_data=[],
                        related_keywords=[],
                        source="Generated",
                    )
                    suggestions.append(keyword_data)

        return suggestions[:50]

    def estimate_search_volume(self, keyword: str) -> int:
        """Estimate search volume based on keyword characteristics"""
        base_volume = 1000

        if len(keyword.split()) == 1:
            base_volume *= 5
        elif len(keyword.split()) > 4:
            base_volume //= 3

        if any(word in keyword.lower() for word in ["near me", "local"]):
            base_volume //= 2
        elif any(word in keyword.lower() for word in ["best", "top", "review"]):
            base_volume *= 2
        elif any(word in keyword.lower() for word in ["how to", "what is", "guide"]):
            base_volume *= 1.5

        return max(100, base_volume)

    def estimate_cpc(self, keyword: str) -> float:
        """Estimate CPC based on keyword characteristics"""
        base_cpc = 1.50

        if any(
            word in keyword.lower()
            for word in ["buy", "price", "cost", "cheap", "best"]
        ):
            base_cpc *= 2
        elif any(
            word in keyword.lower() for word in ["how to", "what is", "guide", "tips"]
        ):
            base_cpc *= 0.5

        return round(base_cpc, 2)

    def estimate_competition(self, keyword: str) -> str:
        """Estimate competition level"""
        if len(keyword.split()) == 1:
            return "High"
        elif len(keyword.split()) <= 3:
            return "Medium"
        else:
            return "Low"

    def estimate_difficulty_from_keyword(self, keyword: str) -> int:
        """Estimate keyword difficulty score"""
        if len(keyword.split()) == 1:
            return 80
        elif len(keyword.split()) <= 3:
            return 50
        else:
            return 30

    def estimate_difficulty(self, volume: int, cpc: float) -> int:
        """Estimate difficulty based on volume and CPC"""
        if volume > 10000 and cpc > 2.0:
            return 80
        elif volume > 5000 and cpc > 1.0:
            return 60
        elif volume > 1000:
            return 40
        else:
            return 20

    def get_competition_level(self, competition_score: float) -> str:
        """Convert competition score to level"""
        if competition_score >= 0.7:
            return "High"
        elif competition_score >= 0.4:
            return "Medium"
        else:
            return "Low"

    def determine_intent(self, keyword: str) -> str:
        """Determine search intent from keyword"""
        keyword_lower = keyword.lower()

        if any(
            word in keyword_lower
            for word in [
                "buy",
                "purchase",
                "price",
                "cost",
                "cheap",
                "deal",
                "discount",
            ]
        ):
            return "Commercial"

        elif any(
            word in keyword_lower
            for word in ["how to", "what is", "guide", "tips", "tutorial", "learn"]
        ):
            return "Informational"

        elif any(
            word in keyword_lower
            for word in ["login", "website", "official", "contact"]
        ):
            return "Navigational"

        elif any(
            word in keyword_lower for word in ["near me", "local", "store", "shop"]
        ):
            return "Local"

        elif any(
            word in keyword_lower
            for word in ["review", "comparison", "vs", "best", "top"]
        ):
            return "Investigation"

        else:
            return "Mixed"

    async def research_keywords(
        self, initial_keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """Main method to research keywords using multiple sources"""
        all_keyword_data = []

        try:

            tasks = []

            if self.dataforseo_login and self.dataforseo_password:
                tasks.append(self.get_dataforseo_keywords(initial_keywords))

            if self.serpapi_key:
                tasks.append(self.get_serpapi_data(initial_keywords))

            if self.semrush_key:
                tasks.append(self.get_semrush_data(initial_keywords))

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, list):
                        all_keyword_data.extend(result)
                    elif isinstance(result, Exception):
                        print(f"API call failed: {result}")

            free_suggestions = self.get_free_keyword_suggestions(initial_keywords)
            all_keyword_data.extend(free_suggestions)

            processed_keywords = self.process_keyword_data(all_keyword_data)

        except Exception as e:
            print(f"Error in research_keywords: {e}")

            free_suggestions = self.get_free_keyword_suggestions(initial_keywords)
            processed_keywords = self.process_keyword_data(free_suggestions)

        return processed_keywords

    def process_keyword_data(
        self, keyword_data_list: List[KeywordData]
    ) -> List[Dict[str, Any]]:
        """Process and deduplicate keyword data"""

        keyword_groups = {}

        for kw_data in keyword_data_list:
            keyword = kw_data.keyword.lower().strip()
            if keyword not in keyword_groups:
                keyword_groups[keyword] = []
            keyword_groups[keyword].append(kw_data)

        processed_keywords = []

        for keyword, data_list in keyword_groups.items():

            if len(data_list) > 1:
                avg_volume = sum(d.search_volume for d in data_list) // len(data_list)
                avg_cpc = sum(d.cpc for d in data_list) / len(data_list)
                avg_difficulty = sum(d.difficulty for d in data_list) // len(data_list)

                best_data = data_list[0]
                sources = list(set(d.source for d in data_list))
            else:
                best_data = data_list[0]
                avg_volume = best_data.search_volume
                avg_cpc = best_data.cpc
                avg_difficulty = best_data.difficulty
                sources = [best_data.source]

            opportunity_score = self.calculate_opportunity_score(
                avg_volume, avg_cpc, avg_difficulty, best_data.intent
            )

            processed_keyword = {
                "keyword": best_data.keyword,
                "search_volume": avg_volume,
                "cpc": round(avg_cpc, 2),
                "competition": best_data.competition,
                "difficulty": avg_difficulty,
                "intent": best_data.intent,
                "opportunity_score": opportunity_score,
                "sources": sources,
                "trend_data": best_data.trend_data,
            }

            processed_keywords.append(processed_keyword)

        processed_keywords.sort(key=lambda x: x["opportunity_score"], reverse=True)

        return processed_keywords[:100]

    def calculate_opportunity_score(
        self, volume: int, cpc: float, difficulty: int, intent: str
    ) -> float:
        """Calculate opportunity score for a keyword (0-10 scale)"""
        score = 0

        if volume >= 10000:
            score += 3
        elif volume >= 5000:
            score += 2.5
        elif volume >= 1000:
            score += 2
        elif volume >= 500:
            score += 1.5
        elif volume >= 100:
            score += 1

        if cpc >= 5.0:
            score += 2
        elif cpc >= 2.0:
            score += 1.5
        elif cpc >= 1.0:
            score += 1
        elif cpc >= 0.5:
            score += 0.5

        if difficulty <= 30:
            score += 3
        elif difficulty <= 50:
            score += 2
        elif difficulty <= 70:
            score += 1

        intent_scores = {
            "Commercial": 2,
            "Investigation": 1.5,
            "Local": 1.5,
            "Informational": 1,
            "Navigational": 0.5,
            "Mixed": 1,
        }
        score += intent_scores.get(intent, 1)

        return round(min(score, 10), 1)


if __name__ == "__main__":

    async def test_researcher():
        researcher = KeywordResearcher()
        keywords = ["tire dealers", "best tire shop", "tire installation"]
        results = await researcher.research_keywords(keywords)

        for result in results[:5]:
            print(f"Keyword: {result['keyword']}")
            print(f"Volume: {result['search_volume']}")
            print(f"CPC: ${result['cpc']}")
            print(f"Difficulty: {result['difficulty']}")
            print(f"Score: {result['opportunity_score']}")
            print("---")
