import base64
import json
from typing import Dict, List, Optional

import requests


class DataForSEOLabs:
    """DataForSEO Labs API integration for keyword research"""

    def __init__(self, login: str, password: str):
        self.login = login
        self.password = password
        self.base_url = "https://api.dataforseo.com/v3/dataforseo_labs/google"
        self.headers = {
            "Authorization": f'Basic {base64.b64encode(f"{login}:{password}".encode()).decode()}',
            "Content-Type": "application/json",
        }

    def get_related_keywords(
        self,
        seed_keyword: str,
        location_code: int = 2840,
        language_code: str = "en",
        depth: int = 3,
        limit: int = 10,
    ) -> Optional[Dict]:
        """
        Fetch related keywords for a given seed keyword

        Args:
            seed_keyword: The main keyword to find related keywords for
            location_code: Location code (2840 for US)
            language_code: Language code (en for English)
            depth: Depth of keyword research
            limit: Maximum number of keywords to return

        Returns:
            Dictionary containing keyword data or None if error
        """
        url = f"{self.base_url}/related_keywords/live"

        payload = [
            {
                "keyword": seed_keyword,
                "location_code": location_code,
                "language_code": language_code,
                "depth": depth,
                "include_seed_keyword": False,
                "include_serp_info": True,
                "ignore_synonyms": False,
                "include_clickstream_data": False,
                "replace_with_core_keyword": False,
                "limit": limit,
            }
        ]

        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            print(f"Failed to parse API response: {str(e)}")
            return None

    def extract_keyword_data(self, api_response: Dict) -> List[Dict]:
        """
        Extract and structure keyword data from API response.
        This version is corrected to handle the 'tasks' array structure.

        Args:
            api_response: Raw API response from DataForSEO

        Returns:
            List of dictionaries containing structured keyword data
        """
        keywords_data = []
        if not api_response or not isinstance(api_response, dict):
            return []

        tasks = api_response.get("tasks")
        if not tasks or not isinstance(tasks, list):
            return []

        for task in tasks:
            if not task or task.get("status_code") != 20000:
                continue

            result_list = task.get("result")
            if not result_list or not isinstance(result_list, list):
                continue

            for result_item in result_list:
                if not result_item or not isinstance(result_item, dict):
                    continue

                items = result_item.get("items")
                if not items or not isinstance(items, list):
                    continue

                for item in items:
                    if not item or not isinstance(item, dict):
                        continue

                    keyword_data = item.get("keyword_data") or {}
                    keyword_info = keyword_data.get("keyword_info") or {}
                    keyword_properties = keyword_data.get("keyword_properties") or {}

                    structured_data = {
                        "keyword": keyword_data.get("keyword", ""),
                        "competition": keyword_info.get("competition", 0.0),
                        "competition_level": keyword_info.get(
                            "competition_level", "UNKNOWN"
                        ),
                        "cpc": keyword_info.get("cpc", 0.0),
                        "search_volume": keyword_info.get("search_volume", 0),
                        "low_top_of_page_bid": keyword_info.get(
                            "low_top_of_page_bid", 0.0
                        ),
                        "high_top_of_page_bid": keyword_info.get(
                            "high_top_of_page_bid", 0.0
                        ),
                        "keyword_difficulty": keyword_properties.get(
                            "keyword_difficulty", 0
                        ),
                        "related_keywords": item.get("related_keywords") or [],
                        "depth": item.get("depth", 0),
                        "monthly_searches": keyword_info.get("monthly_searches") or [],
                    }

                    if structured_data["keyword"]:
                        keywords_data.append(structured_data)

        return keywords_data

    def get_competition_color(self, competition_level: str) -> str:
        """
        Get color based on competition level

        Args:
            competition_level: Competition level string (LOW, MEDIUM, HIGH)

        Returns:
            Color string for Streamlit styling
        """
        color_map = {
            "LOW": "#28a745",
            "MEDIUM": "#ffc107",
            "HIGH": "#dc3545",
            "UNKNOWN": "#6c757d",
        }
        return color_map.get(competition_level.upper(), "#6c757d")

    def format_currency(self, value: float) -> str:
        """Format currency values"""
        return f"${value:.2f}" if value is not None else "$0.00"

    def format_number(self, value: int) -> str:
        """Format large numbers with commas"""
        if not value:
            return "0"
        if value >= 1000000:
            return f"{value/1000000:.1f}M"
        elif value >= 1000:
            return f"{value/1000:.1f}K"
        else:
            return str(value)

    def get_keyword_analysis_data(self, keywords_data: List[Dict]) -> Dict:
        """
        Prepare data for analysis charts and graphs

        Args:
            keywords_data: List of keyword data dictionaries

        Returns:
            Dictionary containing data for various visualizations
        """
        if not keywords_data:
            return {}

        search_volumes = [
            kw["search_volume"] for kw in keywords_data if kw.get("search_volume")
        ]
        cpc_values = [kw["cpc"] for kw in keywords_data if kw.get("cpc") is not None]
        competition_levels = [
            kw["competition_level"]
            for kw in keywords_data
            if kw.get("competition_level")
        ]
        keyword_difficulties = [
            kw["keyword_difficulty"]
            for kw in keywords_data
            if kw.get("keyword_difficulty") is not None
        ]
        keywords = [kw["keyword"] for kw in keywords_data]

        competition_counts = {}
        for level in competition_levels:
            competition_counts[level] = competition_counts.get(level, 0) + 1

        analysis_data = {
            "keywords": keywords,
            "search_volumes": search_volumes,
            "cpc_values": cpc_values,
            "competition_levels": competition_levels,
            "competition_counts": competition_counts,
            "keyword_difficulties": keyword_difficulties,
            "avg_search_volume": (
                sum(search_volumes) / len(search_volumes) if search_volumes else 0
            ),
            "avg_cpc": sum(cpc_values) / len(cpc_values) if cpc_values else 0,
            "avg_difficulty": (
                sum(keyword_difficulties) / len(keyword_difficulties)
                if keyword_difficulties
                else 0
            ),
            "total_keywords": len(keywords_data),
        }

        return analysis_data


def main():
    """Test function to verify DataForSEO Labs API integration"""
    from dotenv import load_dotenv

    load_dotenv()
    import os

    login = os.getenv("DATAFORSEO_LOGIN")
    password = os.getenv("DATAFORSEO_PASSWORD")

    if not login or not password:
        print("❌ DataForSEO credentials not found in .env file.")
        return

    print("🔍 Testing DataForSEO Labs API Integration")
    print("=" * 50)

    api = DataForSEOLabs(login, password)

    test_keyword = "tyre dealer"
    print(f"📊 Testing with keyword: '{test_keyword}'")
    print("-" * 30)

    print("🌐 Making API request...")
    raw_response = api.get_related_keywords(test_keyword, limit=10)

    if not raw_response:
        print("❌ API request failed!")
        return

    print("✅ API request successful!")
    print(f"📄 Raw response status: {raw_response.get('status_message', 'Unknown')}")
    print(f"💰 API cost: {raw_response.get('cost', 0)}")
    print(f"⏱️  Time taken: {raw_response.get('time', 'Unknown')}")

    print("\n🔧 Extracting keyword data...")
    keywords_data = api.extract_keyword_data(raw_response)

    if not keywords_data:
        print(
            "❌ No keywords extracted! The API may have returned no items for this keyword."
        )
        print("\nRaw Response for debugging:")
        print(json.dumps(raw_response, indent=2))
        return

    print(f"✅ Extracted {len(keywords_data)} keywords")

    print("\n📋 Sample Keywords:")
    print("-" * 50)

    for i, keyword in enumerate(keywords_data[:5]):
        print(f"\n{i+1}. Keyword: {keyword['keyword']}")
        print(f"   📊 Search Volume: {api.format_number(keyword['search_volume'])}")
        print(f"   💰 CPC: {api.format_currency(keyword['cpc'])}")
        print(
            f"   🎯 Competition: {keyword['competition_level']} ({keyword.get('competition', 0):.2f})"
        )
        print(f"   📈 Difficulty: {keyword['keyword_difficulty']}/100")
        print(
            f"   💵 Bid Range: {api.format_currency(keyword['low_top_of_page_bid'])} - {api.format_currency(keyword['high_top_of_page_bid'])}"
        )

        if keyword["related_keywords"]:
            print(f"   🔗 Related: {', '.join(keyword['related_keywords'][:3])}...")

    print("\n📈 Analysis Summary:")
    print("-" * 30)
    analysis = api.get_keyword_analysis_data(keywords_data)

    print(f"Total Keywords: {analysis['total_keywords']}")
    print(
        f"Avg Search Volume: {api.format_number(int(analysis.get('avg_search_volume', 0)))}"
    )
    print(f"Avg CPC: {api.format_currency(analysis.get('avg_cpc', 0))}")
    print(f"Avg Difficulty: {analysis.get('avg_difficulty', 0):.1f}/100")

    if analysis["competition_counts"]:
        print("\nCompetition Distribution:")
        for level, count in analysis["competition_counts"].items():
            print(f"  {level}: {count} keywords")


if __name__ == "__main__":
    main()
