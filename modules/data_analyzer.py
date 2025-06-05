import re
import statistics
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


class DataAnalyzer:
    """Advanced data analysis for keyword research and campaign optimization"""

    def __init__(self):
        self.intent_priorities = {
            "Commercial": 5,
            "Investigation": 4,
            "Local": 4,
            "Informational": 3,
            "Navigational": 2,
            "Mixed": 3,
        }

        self.competition_scores = {"Low": 1, "Medium": 2, "High": 3}

    def analyze_keywords(
        self,
        keywords: List[Dict[str, Any]],
        budget_range: str,
        campaign_goals: List[str],
    ) -> List[Dict[str, Any]]:
        """Analyze keywords and enhance with additional metrics"""
        if not keywords:
            return []

        df = pd.DataFrame(keywords)

        enhanced_keywords = []

        for _, row in df.iterrows():
            keyword_dict = row.to_dict()

            keyword_dict["efficiency_score"] = self.calculate_efficiency_score(
                row.get("search_volume", 0), row.get("cpc", 0), row.get("difficulty", 0)
            )

            keyword_dict["budget_fit_score"] = self.calculate_budget_fit(
                row.get("cpc", 0), budget_range
            )

            keyword_dict["goal_alignment_score"] = self.calculate_goal_alignment(
                row.get("intent", "Mixed"), campaign_goals
            )

            keyword_dict["competition_analysis"] = self.analyze_competition_level(
                row.get("competition", "Medium"),
                row.get("difficulty", 50),
                row.get("cpc", 0),
            )

            keyword_dict["recommendation"] = self.generate_keyword_recommendation(
                keyword_dict
            )

            keyword_dict["enhanced_opportunity_score"] = (
                self.calculate_enhanced_opportunity_score(keyword_dict)
            )

            enhanced_keywords.append(keyword_dict)

        enhanced_keywords.sort(
            key=lambda x: x.get("enhanced_opportunity_score", 0), reverse=True
        )

        return enhanced_keywords

    def calculate_efficiency_score(
        self, volume: int, cpc: float, difficulty: int
    ) -> float:
        """Calculate keyword efficiency score (volume per dollar per difficulty)"""
        if cpc <= 0 or difficulty <= 0:
            return 0

        difficulty_factor = max(1, 101 - difficulty) / 100

        efficiency = (volume / max(cpc, 0.1)) * difficulty_factor

        normalized_efficiency = min(efficiency / 1000, 10)

        return round(normalized_efficiency, 2)

    def calculate_budget_fit(self, cpc: float, budget_range: str) -> float:
        """Calculate how well keyword fits the budget"""
        budget_map = {
            "Low ($0-$500/month)": (0, 500),
            "Medium ($500-$2000/month)": (500, 2000),
            "High ($2000-$5000/month)": (2000, 5000),
            "Enterprise ($5000+/month)": (5000, float("inf")),
        }

        min_budget, max_budget = budget_map.get(budget_range, (500, 2000))

        estimated_monthly_cost = cpc * 1000

        if estimated_monthly_cost <= min_budget * 0.1:
            return 10
        elif estimated_monthly_cost <= min_budget * 0.3:
            return 8
        elif estimated_monthly_cost <= max_budget * 0.5:
            return 6
        elif estimated_monthly_cost <= max_budget:
            return 4
        else:
            return 2

    def calculate_goal_alignment(self, intent: str, campaign_goals: List[str]) -> float:
        """Calculate how well keyword intent aligns with campaign goals"""
        goal_intent_map = {
            "Lead Generation": ["Commercial", "Investigation", "Local"],
            "Brand Awareness": ["Informational", "Navigational", "Mixed"],
            "Sales Conversion": ["Commercial", "Investigation"],
            "Traffic Growth": ["Informational", "Mixed", "Navigational"],
            "Local Visibility": ["Local", "Commercial"],
            "Competitor Analysis": ["Investigation", "Commercial"],
        }

        alignment_score = 0
        for goal in campaign_goals:
            if intent in goal_intent_map.get(goal, []):
                alignment_score += 2
            elif intent in ["Mixed", "Investigation"]:
                alignment_score += 1

        return min(alignment_score, 10)

    def analyze_competition_level(
        self, competition: str, difficulty: int, cpc: float
    ) -> Dict[str, Any]:
        """Analyze competition level and provide insights"""
        analysis = {
            "level": competition,
            "difficulty_score": difficulty,
            "market_indicators": [],
            "strategy_recommendation": "",
        }

        if cpc > 5.0:
            analysis["market_indicators"].append("High commercial value")
        elif cpc > 2.0:
            analysis["market_indicators"].append("Moderate commercial value")
        else:
            analysis["market_indicators"].append("Low commercial value")

        if difficulty > 80:
            analysis["market_indicators"].append("Highly competitive market")
            analysis["strategy_recommendation"] = (
                "Consider long-tail variations or niche targeting"
            )
        elif difficulty > 60:
            analysis["market_indicators"].append("Competitive market")
            analysis["strategy_recommendation"] = (
                "Requires strong content and backlink strategy"
            )
        elif difficulty > 40:
            analysis["market_indicators"].append("Moderately competitive")
            analysis["strategy_recommendation"] = (
                "Good opportunity with proper optimization"
            )
        else:
            analysis["market_indicators"].append("Low competition opportunity")
            analysis["strategy_recommendation"] = "High potential for quick wins"

        return analysis

    def generate_keyword_recommendation(self, keyword_data: Dict[str, Any]) -> str:
        """Generate specific recommendation for each keyword"""
        volume = keyword_data.get("search_volume", 0)
        cpc = keyword_data.get("cpc", 0)
        difficulty = keyword_data.get("difficulty", 50)
        intent = keyword_data.get("intent", "Mixed")
        efficiency = keyword_data.get("efficiency_score", 0)

        if efficiency >= 8 and volume >= 1000:
            return "🎯 High Priority: Excellent opportunity with great efficiency"
        elif intent == "Commercial" and cpc >= 2.0:
            return "💰 Commercial Focus: High-value keyword for conversion campaigns"
        elif intent == "Local" and volume >= 500:
            return "📍 Local Opportunity: Great for geo-targeted campaigns"
        elif difficulty <= 30 and volume >= 100:
            return "🚀 Quick Win: Low competition with decent volume"
        elif intent == "Informational" and volume >= 1000:
            return "📚 Content Marketing: Ideal for educational campaigns"
        elif efficiency >= 6:
            return "✅ Recommended: Good balance of metrics"
        elif difficulty >= 80:
            return "⚠️ High Competition: Consider long-tail alternatives"
        elif volume < 100:
            return "📊 Low Volume: Monitor and test carefully"
        else:
            return "🔍 Consider: Evaluate based on specific campaign needs"

    def calculate_enhanced_opportunity_score(
        self, keyword_data: Dict[str, Any]
    ) -> float:
        """Calculate enhanced opportunity score using all available metrics"""
        base_score = keyword_data.get("opportunity_score", 0)
        efficiency_score = keyword_data.get("efficiency_score", 0)
        budget_fit = keyword_data.get("budget_fit_score", 0)
        goal_alignment = keyword_data.get("goal_alignment_score", 0)

        enhanced_score = (
            base_score * 0.4
            + efficiency_score * 0.3
            + budget_fit * 0.2
            + goal_alignment * 0.1
        )

        return round(min(enhanced_score, 10), 2)

    def get_summary_stats(self, keywords: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive summary statistics"""
        if not keywords:
            return {}

        df = pd.DataFrame(keywords)

        stats = {
            "total_keywords": len(keywords),
            "avg_search_volume": int(df.get("search_volume", pd.Series([0])).mean()),
            "total_search_volume": int(df.get("search_volume", pd.Series([0])).sum()),
            "avg_cpc": round(df.get("cpc", pd.Series([0])).mean(), 2),
            "avg_difficulty": round(df.get("difficulty", pd.Series([0])).mean(), 1),
            "avg_opportunity_score": round(
                df.get(
                    "enhanced_opportunity_score",
                    df.get("opportunity_score", pd.Series([0])),
                ).mean(),
                2,
            ),
        }

        stats["volume_distribution"] = self.analyze_volume_distribution(df)
        stats["cpc_distribution"] = self.analyze_cpc_distribution(df)
        stats["intent_distribution"] = self.analyze_intent_distribution(df)
        stats["competition_distribution"] = self.analyze_competition_distribution(df)

        stats["insights"] = self.generate_insights(df)
        stats["recommendations"] = self.generate_recommendations(df, stats)

        stats["top_keywords"] = self.get_top_performers(keywords)

        return stats

    def analyze_volume_distribution(self, df: pd.DataFrame) -> Dict[str, int]:
        """Analyze search volume distribution"""
        volume_col = df.get("search_volume", pd.Series([0]))

        return {
            "high_volume": len(volume_col[volume_col >= 10000]),
            "medium_volume": len(
                volume_col[(volume_col >= 1000) & (volume_col < 10000)]
            ),
            "low_volume": len(volume_col[volume_col < 1000]),
        }

    def analyze_cpc_distribution(self, df: pd.DataFrame) -> Dict[str, int]:
        """Analyze CPC distribution"""
        cpc_col = df.get("cpc", pd.Series([0]))

        return {
            "high_cpc": len(cpc_col[cpc_col >= 3.0]),
            "medium_cpc": len(cpc_col[(cpc_col >= 1.0) & (cpc_col < 3.0)]),
            "low_cpc": len(cpc_col[cpc_col < 1.0]),
        }

    def analyze_intent_distribution(self, df: pd.DataFrame) -> Dict[str, int]:
        """Analyze search intent distribution"""
        intent_col = df.get("intent", pd.Series(["Mixed"]))
        intent_counts = intent_col.value_counts()
        return intent_counts.to_dict()

    def analyze_competition_distribution(self, df: pd.DataFrame) -> Dict[str, int]:
        """Analyze competition level distribution"""
        competition_col = df.get("competition", pd.Series(["Medium"]))
        competition_counts = competition_col.value_counts()
        return competition_counts.to_dict()

    def generate_insights(self, df: pd.DataFrame) -> List[str]:
        """Generate data-driven insights"""
        insights = []

        volume_col = df.get("search_volume", pd.Series([0]))
        avg_volume = volume_col.mean()

        if avg_volume >= 5000:
            insights.append(
                "High-volume keywords dominate this topic - excellent traffic potential"
            )
        elif avg_volume >= 1000:
            insights.append(
                "Good search volume across keywords - solid traffic opportunities"
            )
        else:
            insights.append(
                "Mostly long-tail keywords - focus on conversion over volume"
            )

        cpc_col = df.get("cpc", pd.Series([0]))
        avg_cpc = cpc_col.mean()

        if avg_cpc >= 3.0:
            insights.append(
                "High CPC indicates strong commercial value and competition"
            )
        elif avg_cpc >= 1.0:
            insights.append("Moderate CPC suggests balanced commercial opportunity")
        else:
            insights.append(
                "Low CPC keywords - cost-effective traffic acquisition possible"
            )

        intent_col = df.get("intent", pd.Series(["Mixed"]))
        commercial_ratio = len(intent_col[intent_col == "Commercial"]) / len(intent_col)

        if commercial_ratio >= 0.3:
            insights.append("Strong commercial intent - good for conversion campaigns")
        elif commercial_ratio >= 0.1:
            insights.append(
                "Mixed intent keywords - diversified campaign strategy recommended"
            )
        else:
            insights.append(
                "Primarily informational keywords - focus on content marketing"
            )

        difficulty_col = df.get("difficulty", pd.Series([50]))
        avg_difficulty = difficulty_col.mean()

        if avg_difficulty >= 70:
            insights.append("High competition market - long-term SEO strategy needed")
        elif avg_difficulty >= 40:
            insights.append(
                "Moderate competition - good opportunities with proper optimization"
            )
        else:
            insights.append("Low competition environment - quick wins possible")

        return insights

    def generate_recommendations(
        self, df: pd.DataFrame, stats: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        avg_cpc = stats.get("avg_cpc", 0)
        total_keywords = stats.get("total_keywords", 0)

        estimated_daily_budget = avg_cpc * 50
        recommendations.append(
            f"Recommended daily budget: ${estimated_daily_budget:.2f} for moderate coverage"
        )

        high_volume_count = stats.get("volume_distribution", {}).get("high_volume", 0)

        if high_volume_count >= 5:
            recommendations.append("Focus on high-volume keywords for maximum reach")
        else:
            recommendations.append(
                "Prioritize long-tail keywords for better conversion rates"
            )

        intent_dist = stats.get("intent_distribution", {})

        if intent_dist.get("Commercial", 0) >= 3:
            recommendations.append(
                "Create dedicated commercial intent campaigns for better ROI"
            )

        if intent_dist.get("Local", 0) >= 3:
            recommendations.append(
                "Implement geo-targeted campaigns for local keywords"
            )

        if intent_dist.get("Informational", 0) >= 5:
            recommendations.append(
                "Develop content marketing strategy for informational keywords"
            )

        avg_difficulty = stats.get("avg_difficulty", 0)

        if avg_difficulty >= 70:
            recommendations.append("Consider PPC focus due to high organic competition")
        elif avg_difficulty <= 30:
            recommendations.append(
                "Organic SEO could be highly effective for these keywords"
            )

        return recommendations

    def get_top_performers(
        self, keywords: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Identify top performing keywords by different metrics"""
        if not keywords:
            return {}

        by_opportunity = sorted(
            keywords,
            key=lambda x: x.get(
                "enhanced_opportunity_score", x.get("opportunity_score", 0)
            ),
            reverse=True,
        )[:5]

        by_volume = sorted(
            keywords, key=lambda x: x.get("search_volume", 0), reverse=True
        )[:5]

        by_efficiency = sorted(
            keywords, key=lambda x: x.get("efficiency_score", 0), reverse=True
        )[:5]

        commercial_keywords = [
            kw for kw in keywords if kw.get("intent") == "Commercial"
        ]
        by_commercial_value = sorted(
            commercial_keywords, key=lambda x: x.get("cpc", 0), reverse=True
        )[:5]

        return {
            "highest_opportunity": by_opportunity,
            "highest_volume": by_volume,
            "most_efficient": by_efficiency,
            "highest_commercial_value": by_commercial_value,
        }

    def export_analysis_report(
        self, keywords: List[Dict[str, Any]], summary_stats: Dict[str, Any]
    ) -> str:
        """Export comprehensive analysis report"""
        report = []

        report.append("# KEYWORD ANALYSIS REPORT")
        report.append("=" * 50)
        report.append("")

        report.append("## EXECUTIVE SUMMARY")
        report.append(
            f"Total Keywords Analyzed: {summary_stats.get('total_keywords', 0)}"
        )
        report.append(
            f"Average Search Volume: {summary_stats.get('avg_search_volume', 0):,}"
        )
        report.append(f"Average CPC: ${summary_stats.get('avg_cpc', 0):.2f}")
        report.append(
            f"Average Difficulty: {summary_stats.get('avg_difficulty', 0):.1f}/100"
        )
        report.append("")

        insights = summary_stats.get("insights", [])
        if insights:
            report.append("## KEY INSIGHTS")
            for i, insight in enumerate(insights, 1):
                report.append(f"{i}. {insight}")
            report.append("")

        recommendations = summary_stats.get("recommendations", [])
        if recommendations:
            report.append("## RECOMMENDATIONS")
            for i, rec in enumerate(recommendations, 1):
                report.append(f"{i}. {rec}")
            report.append("")

        top_performers = summary_stats.get("top_keywords", {})
        if top_performers:
            report.append("## TOP PERFORMING KEYWORDS")

            for category, kw_list in top_performers.items():
                if kw_list:
                    report.append(f"### {category.replace('_', ' ').title()}")
                    for kw in kw_list:
                        report.append(
                            f"- {kw.get('keyword', '')} "
                            f"(Vol: {kw.get('search_volume', 0):,}, "
                            f"CPC: ${kw.get('cpc', 0):.2f}, "
                            f"Score: {kw.get('enhanced_opportunity_score', kw.get('opportunity_score', 0)):.1f})"
                        )
                    report.append("")

        return "\n".join(report)


if __name__ == "__main__":
    analyzer = DataAnalyzer()

    sample_keywords = [
        {
            "keyword": "best tire shop",
            "search_volume": 1200,
            "cpc": 2.50,
            "difficulty": 45,
            "intent": "Commercial",
            "opportunity_score": 8.2,
        },
        {
            "keyword": "tire installation near me",
            "search_volume": 800,
            "cpc": 3.20,
            "difficulty": 35,
            "intent": "Local",
            "opportunity_score": 7.8,
        },
    ]

    analyzed = analyzer.analyze_keywords(
        sample_keywords, "Medium ($500-$2000/month)", ["Lead Generation"]
    )

    stats = analyzer.get_summary_stats(analyzed)

    print("Analysis completed!")
    print(f"Analyzed {len(analyzed)} keywords")
    print(f"Average opportunity score: {stats.get('avg_opportunity_score', 0)}")
