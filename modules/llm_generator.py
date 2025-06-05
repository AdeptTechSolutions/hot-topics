import asyncio
import json
import os
import time
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from google.generativeai import types


class LLMGenerator:
    """AI-powered keyword and campaign generator using Gemini 2.5 Flash Exp"""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        self.model_name = "gemini-2.5-flash-preview-05-20"

        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.client = True
            except Exception as e:
                print(f"Error initializing Gemini client: {e}")

    def is_available(self) -> bool:
        """Check if Gemini API is available"""
        return self.client is not None and self.api_key is not None

    async def generate_initial_keywords(
        self, topic: str, scraped_data: Dict[str, Any], target_audience: str
    ) -> List[str]:
        """Generate initial keyword ideas using Gemini AI"""
        if not self.is_available():
            return self._fallback_keyword_generation(topic)

        try:

            context = self._prepare_context(scraped_data)

            prompt = f"""
            As an expert digital marketing strategist, analyze the following topic and generate comprehensive keyword ideas for PPC campaigns.

            TOPIC: {topic}
            TARGET AUDIENCE: {target_audience}

            CONTEXT FROM WEB RESEARCH:
            {context}

            TASK: Generate 50 diverse keywords that follow this strategy:

            1. BROAD SOLUTION-BASED TOPICS (10 keywords):
            - Focus on general topics where users look for solutions but aren't in buying phase
            - Examples: "how to find the best {topic}", "choosing the right {topic}"

            2. LONG-TAIL, LOW-COMPETITION KEYWORDS (15 keywords):
            - 3-5 word phrases with clear user intent
            - Examples: "affordable {topic} near me", "best {topic} providers"

            3. INFORMATIONAL KEYWORDS (10 keywords):
            - "How to" queries and educational content
            - Examples: "how to choose {topic}", "what to look for in {topic}"

            4. COMMERCIAL INTENT KEYWORDS (10 keywords):
            - Keywords indicating readiness to purchase
            - Examples: "best {topic} deals", "{topic} pricing", "buy {topic}"

            5. LOCAL/GEOGRAPHIC KEYWORDS (5 keywords):
            - Location-based searches
            - Examples: "{topic} near me", "local {topic} services"

            REQUIREMENTS:
            - Avoid overly competitive or high-cost terms
            - Focus on solution-oriented keywords
            - Ensure keywords can be naturally included in content
            - Prioritize terms that encourage user interaction
            - Consider the target audience's search behavior

            Return ONLY a JSON array of keyword strings, no other text or formatting:
            ["keyword1", "keyword2", ...]
            """

            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7, max_output_tokens=2000
                ),
            )

            if not response.candidates or not response.candidates[0].content.parts:
                print(f"Gemini response blocked or empty. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'No candidates'}")
                return self._fallback_keyword_generation(topic)

            try:
                response_text = response.text
            except ValueError as e:
                print(f"Error accessing response text: {e}")
                return self._fallback_keyword_generation(topic)

            keywords = self._parse_keyword_response(response_text)

            if keywords:
                return keywords
            else:
                return self._fallback_keyword_generation(topic)

        except Exception as e:
            print(f"Error generating keywords with Gemini: {e}")
            return self._fallback_keyword_generation(topic)

    async def generate_campaigns(
        self,
        keywords: List[Dict[str, Any]],
        target_audience: str,
        budget_range: str,
        campaign_goals: List[str],
        scraped_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate comprehensive campaign strategies using Gemini AI"""
        if not self.is_available():
            return self._fallback_campaign_generation(
                keywords, target_audience, budget_range
            )

        try:

            top_keywords = sorted(
                keywords, key=lambda x: x.get("opportunity_score", 0), reverse=True
            )[:20]
            keyword_list = [kw["keyword"] for kw in top_keywords]

            context = self._prepare_context(scraped_data)
            keyword_data = self._prepare_keyword_context(top_keywords)

            prompt = f"""
            As an expert PPC campaign strategist, create comprehensive advertising campaigns based on the following data:

            TARGET AUDIENCE: {target_audience}
            BUDGET RANGE: {budget_range}
            CAMPAIGN GOALS: {', '.join(campaign_goals)}

            TOP PERFORMING KEYWORDS WITH METRICS:
            {keyword_data}

            MARKET RESEARCH CONTEXT:
            {context}

            TASK: Create 4-5 distinct campaign strategies that maximize ROI and align with the goals.

            For each campaign, provide:

            1. CAMPAIGN OVERVIEW:
            - Title (compelling and descriptive)
            - Primary objective
            - Target keyword group (5-8 keywords from the list)
            - Budget allocation recommendation

            2. STRATEGY DETAILS:
            - Campaign description and approach
            - Why this strategy works for the target audience
            - Expected performance metrics
            - Competitive advantages

            3. AD COPY SUGGESTIONS:
            - 3 different headline variations
            - 2 description variations
            - Call-to-action recommendations

            4. LANDING PAGE RECOMMENDATIONS:
            - Key elements to include
            - Content strategy
            - Conversion optimization tips

            5. TARGETING & SETTINGS:
            - Geographic targeting suggestions
            - Demographic targeting
            - Device targeting recommendations
            - Bidding strategy

            6. SUCCESS METRICS:
            - KPIs to track
            - Expected CTR range
            - Conversion rate expectations
            - ROI projections

            Return response as a JSON array of campaign objects with the structure:
            [
                {{
                    "title": "Campaign Name",
                    "objective": "Primary goal",
                    "keywords": ["keyword1", "keyword2", ...],
                    "description": "Campaign strategy description",
                    "budget_recommendation": "Budget allocation and reasoning",
                    "expected_performance": "Performance expectations",
                    "ad_copies": ["headline1", "headline2", "headline3"],
                    "descriptions": ["desc1", "desc2"],
                    "call_to_action": "CTA recommendation",
                    "landing_page_tips": "Landing page strategy",
                    "targeting_suggestions": "Targeting recommendations",
                    "success_metrics": "KPIs and expectations"
                }},
                ...
            ]
            """

            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.8, max_output_tokens=4000
                ),
            )

            campaigns = self._parse_campaign_response(response.text)

            if campaigns:
                return campaigns
            else:
                return self._fallback_campaign_generation(
                    keywords, target_audience, budget_range
                )

        except Exception as e:
            print(f"Error generating campaigns with Gemini: {e}")
            return self._fallback_campaign_generation(
                keywords, target_audience, budget_range
            )

    def _prepare_context(self, scraped_data: Dict[str, Any]) -> str:
        """Prepare context from scraped data for prompts"""
        context = ""

        if scraped_data.get("content"):
            content = scraped_data["content"]

            if content.get("combined_text"):
                text = content["combined_text"][:2000]
                context += f"Market Research Summary:\n{text}\n\n"

            if content.get("headings"):
                headings = content["headings"][:10]
                context += f"Trending Topics: {', '.join(headings)}\n\n"

            if scraped_data.get("keywords"):
                keywords = scraped_data["keywords"][:15]
                context += f"Market Keywords: {', '.join(keywords)}\n\n"

        if scraped_data.get("insights"):
            insights = scraped_data["insights"]
            context += f"Market Insights:\n" + "\n".join(
                f"- {insight}" for insight in insights
            )

        return context[:3000]

    def _prepare_keyword_context(self, keywords: List[Dict[str, Any]]) -> str:
        """Prepare keyword data context for prompts"""
        context = ""

        for kw in keywords:
            context += f"""
            Keyword: {kw.get('keyword', '')}
            - Search Volume: {kw.get('search_volume', 0):,}
            - CPC: ${kw.get('cpc', 0):.2f}
            - Difficulty: {kw.get('difficulty', 0)}/100
            - Intent: {kw.get('intent', 'Unknown')}
            - Opportunity Score: {kw.get('opportunity_score', 0)}/10
            """

        return context

    def _parse_keyword_response(self, response_text: str) -> List[str]:
        """Parse keyword response from Gemini"""
        try:

            text = response_text.strip()

            start_idx = text.find("[")
            end_idx = text.rfind("]") + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_text = text[start_idx:end_idx]
                keywords = json.loads(json_text)

                if isinstance(keywords, list):
                    return [
                        kw.strip()
                        for kw in keywords
                        if isinstance(kw, str) and kw.strip()
                    ]

            lines = text.split("\n")
            keywords = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith(("#", "//", "```", "*", "-")):

                    clean_line = line.strip("\"'").strip()
                    if clean_line and len(clean_line.split()) <= 6:
                        keywords.append(clean_line)

            return keywords[:50]

        except Exception as e:
            print(f"Error parsing keyword response: {e}")
            return []

    def _parse_campaign_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse campaign response from Gemini"""
        try:
            text = response_text.strip()

            start_idx = text.find("[")
            end_idx = text.rfind("]") + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_text = text[start_idx:end_idx]

                import re

                json_text = json_text.replace("\n", " ")
                json_text = json_text.replace("\t", " ")

                json_text = re.sub(r",\s*}", "}", json_text)
                json_text = re.sub(r",\s*]", "]", json_text)

                json_text = re.sub(r'(?<!\\)"([^"]*)"([^,}\]]*)"', r'"\1\2"', json_text)

                json_text = re.sub(r"}\s*{", "},{", json_text)

                json_text = json_text[: json_text.rfind("]") + 1]

                try:
                    campaigns = json.loads(json_text)
                    if isinstance(campaigns, list):
                        return campaigns
                except json.JSONDecodeError as json_error:
                    print(f"JSON parsing failed: {json_error}")
                    print(f"Problematic JSON text (first 500 chars): {json_text[:500]}")

                    try:

                        fixed_json = self._fix_malformed_json(json_text)
                        if fixed_json:
                            campaigns = json.loads(fixed_json)
                            if isinstance(campaigns, list):
                                return campaigns
                    except Exception as fix_error:
                        print(f"JSON fix attempt failed: {fix_error}")

            return self._extract_campaigns_from_text(text)

        except Exception as e:
            print(f"Error parsing campaign response: {e}")
            print(f"Response text (first 1000 chars): {response_text[:1000]}")
            return self._fallback_campaign_generation([], "", "")

    def _fix_malformed_json(self, json_text: str) -> Optional[str]:
        """Attempt to fix common JSON malformation issues"""
        import re

        try:

            fixed_text = json_text

            pattern = r'"([^"]+)":\s*"([^"]*"[^"]*"[^"]*)"'

            def fix_quotes(match):
                key = match.group(1)
                value = match.group(2)

                fixed_value = value.replace('"', '\\"')
                return f'"{key}": "{fixed_value}"'

            fixed_text = re.sub(pattern, fix_quotes, fixed_text)

            json.loads(fixed_text)
            return fixed_text

        except Exception:
            return None

    def _extract_campaigns_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract campaign information from unstructured text"""
        campaigns = []

        sections = text.split("\n\n")
        current_campaign = {}

        for section in sections:
            if "campaign" in section.lower() or "title" in section.lower():
                if current_campaign:
                    campaigns.append(current_campaign)
                    current_campaign = {}

                current_campaign["title"] = section.strip()[:100]
                current_campaign["objective"] = "Lead Generation"
                current_campaign["description"] = section.strip()[:500]
                current_campaign["keywords"] = []
                current_campaign["budget_recommendation"] = (
                    "Allocate based on keyword performance"
                )
                current_campaign["expected_performance"] = (
                    "Monitor and optimize based on data"
                )
                current_campaign["ad_copies"] = ["Compelling headline here"]
                current_campaign["descriptions"] = ["Engaging description here"]
                current_campaign["call_to_action"] = "Learn More"
                current_campaign["landing_page_tips"] = (
                    "Focus on clear value proposition"
                )
                current_campaign["targeting_suggestions"] = (
                    "Target relevant demographics"
                )
                current_campaign["success_metrics"] = (
                    "Track CTR, conversion rate, and ROI"
                )

        if current_campaign:
            campaigns.append(current_campaign)

        return campaigns[:5]

    def _fallback_keyword_generation(self, topic: str) -> List[str]:
        """Fallback keyword generation when Gemini is not available"""
        base_keywords = [
            f"{topic}",
            f"best {topic}",
            f"{topic} near me",
            f"top {topic}",
            f"affordable {topic}",
            f"{topic} reviews",
            f"how to choose {topic}",
            f"{topic} guide",
            f"{topic} tips",
            f"local {topic}",
            f"{topic} services",
            f"{topic} cost",
            f"{topic} pricing",
            f"cheap {topic}",
            f"{topic} comparison",
            f"find {topic}",
            f"{topic} recommendations",
            f"quality {topic}",
            f"reliable {topic}",
            f"{topic} experts",
        ]

        variations = []
        modifiers = ["professional", "trusted", "experienced", "certified", "licensed"]

        for keyword in base_keywords:
            variations.append(keyword)
            for modifier in modifiers[:2]:
                variations.append(f"{modifier} {keyword}")

        return variations[:50]

    def _fallback_campaign_generation(
        self, keywords: List[Dict[str, Any]], target_audience: str, budget_range: str
    ) -> List[Dict[str, Any]]:
        """Fallback campaign generation when Gemini is not available"""

        commercial_kws = [kw for kw in keywords if kw.get("intent") == "Commercial"][:5]
        informational_kws = [
            kw for kw in keywords if kw.get("intent") == "Informational"
        ][:5]
        local_kws = [kw for kw in keywords if kw.get("intent") == "Local"][:5]

        campaigns = [
            {
                "title": "High-Intent Commercial Campaign",
                "objective": "Drive immediate conversions",
                "keywords": [kw["keyword"] for kw in commercial_kws],
                "description": "Target users ready to purchase with commercial intent keywords",
                "budget_recommendation": "Allocate 40% of budget to this high-converting campaign",
                "expected_performance": "Higher CPC but better conversion rates",
                "ad_copies": [
                    "Premium Solutions Available Now",
                    "Get Quote Today - Fast Service",
                    "Trusted by Thousands - Start Now",
                ],
                "descriptions": [
                    "Professional service with guaranteed results",
                    "Fast, reliable, and affordable solutions",
                ],
                "call_to_action": "Get Quote Now",
                "landing_page_tips": "Include pricing, testimonials, and clear contact forms",
                "targeting_suggestions": "Target users in decision-making phase",
                "success_metrics": "Focus on conversion rate and cost per acquisition",
            },
            {
                "title": "Educational Content Campaign",
                "objective": "Build awareness and capture early-stage prospects",
                "keywords": [kw["keyword"] for kw in informational_kws],
                "description": "Target users in research phase with helpful, educational content",
                "budget_recommendation": "Allocate 30% of budget for long-term lead nurturing",
                "expected_performance": "Lower CPC, higher volume, longer conversion cycle",
                "ad_copies": [
                    "Free Guide: How to Choose the Best Option",
                    "Expert Tips and Advice",
                    "Learn Before You Buy",
                ],
                "descriptions": [
                    "Get expert insights and make informed decisions",
                    "Comprehensive guides from industry professionals",
                ],
                "call_to_action": "Learn More",
                "landing_page_tips": "Offer valuable content in exchange for contact information",
                "targeting_suggestions": "Target broader audience in research phase",
                "success_metrics": "Track engagement, email signups, and lead quality",
            },
            {
                "title": "Local Service Campaign",
                "objective": "Capture local market share",
                "keywords": [kw["keyword"] for kw in local_kws],
                "description": "Target local customers looking for nearby services",
                "budget_recommendation": "Allocate 20% of budget for geo-targeted campaigns",
                "expected_performance": "Moderate CPC with good local conversion rates",
                "ad_copies": [
                    "Local Service in Your Area",
                    "Serving [City] Since [Year]",
                    "Your Neighborhood Experts",
                ],
                "descriptions": [
                    "Local, trusted service with fast response times",
                    "Proud to serve the local community",
                ],
                "call_to_action": "Call Now",
                "landing_page_tips": "Include local phone number, address, and service areas",
                "targeting_suggestions": "Use radius targeting around service areas",
                "success_metrics": "Track phone calls, local conversions, and foot traffic",
            },
        ]

        return campaigns


if __name__ == "__main__":

    async def test_generator():
        generator = LLMGenerator()

        if generator.is_available():

            keywords = await generator.generate_initial_keywords(
                "tire dealers",
                {"content": {"combined_text": "tire installation and repair services"}},
                "car owners",
            )
            print(f"Generated {len(keywords)} keywords")

            keyword_data = [
                {
                    "keyword": "best tire shop",
                    "search_volume": 1000,
                    "cpc": 2.5,
                    "opportunity_score": 8.5,
                },
                {
                    "keyword": "tire installation",
                    "search_volume": 800,
                    "cpc": 3.0,
                    "opportunity_score": 7.5,
                },
            ]

            campaigns = await generator.generate_campaigns(
                keyword_data,
                "car owners",
                "Medium ($500-$2000/month)",
                ["Lead Generation"],
            )
            print(f"Generated {len(campaigns)} campaigns")
        else:
            print("Gemini API not available - using fallback methods")
