import asyncio
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from modules.data_analyzer import DataAnalyzer
from modules.keyword_researcher import KeywordResearcher
from modules.llm_generator import LLMGenerator
from modules.web_scraper import WebScraper

st.set_page_config(
    page_title="Keywords & Campaigns",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
.main-header {
    font-size: 3rem;
    font-weight: bold;
    color: 
    text-align: center;
    margin-bottom: 2rem;
}
.metric-card {
    background-color: 
    padding: 1rem;
    border-radius: 0.5rem;
    border-left: 0.25rem solid 
    margin-bottom: 1rem;
}
.keyword-card {
    background-color: #f8f9fa;
    padding: 1.2rem;
    border-radius: 0.75rem;
    margin-bottom: 0.8rem;
    border: 1px solid #e9ecef;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.campaign-card {
    background-color: #ffffff;
    padding: 1.8rem;
    border-radius: 0.75rem;
    margin-bottom: 2rem;
    border: 2px solid #dee2e6;
    box-shadow: 0 4px 8px rgba(0,0,0,0.08);
}
.keyword-separator {
    height: 1px;
    background: linear-gradient(to right, transparent, #dee2e6, transparent);
    margin: 1.5rem 0;
}
.campaign-separator {
    height: 2px;
    background: linear-gradient(to right, #007bff, #6f42c1, #007bff);
    margin: 2.5rem 0;
    border-radius: 1px;
}
.progress-text {
    font-size: 0.9rem;
    color: 
    margin-top: 0.5rem;
}
.settings-section {
    background-color: 
    padding: 2rem;
    border-radius: 0.75rem;
    margin-bottom: 2rem;
}
.keyword-tag {
    display: inline-block;
    background-color: #e3f2fd;
    color: #1976d2;
    padding: 0.4rem 0.8rem;
    margin: 0.2rem;
    border-radius: 1rem;
    font-size: 0.85rem;
    font-weight: 500;
    border: 1px solid #bbdefb;
}
.keyword-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #2c3e50;
    margin-bottom: 0.8rem;
}
.campaign-title {
    font-size: 1.3rem;
    font-weight: 700;
    color: #1976d2;
    margin-bottom: 1rem;
    border-bottom: 2px solid #e3f2fd;
    padding-bottom: 0.5rem;
}
</style>
""",
    unsafe_allow_html=True,
)


class KeywordsCampaignsApp:
    def __init__(self):
        self.web_scraper = WebScraper()
        self.keyword_researcher = KeywordResearcher()
        self.llm_generator = LLMGenerator()
        self.data_analyzer = DataAnalyzer()

    def validate_api_keys(self) -> Dict[str, bool]:
        """Validate that required API keys are present"""
        from config import Config

        return Config.get_api_status()

    async def process_topic(
        self,
        topic: str,
        target_audience: str,
        budget_range: str,
        campaign_goals: List[str],
    ) -> Dict[str, Any]:
        """Main processing pipeline for topic analysis and campaign generation"""

        results = {
            "topic": topic,
            "scraped_data": {},
            "keywords": [],
            "campaigns": [],
            "analysis": {},
            "timestamp": datetime.now().isoformat(),
        }

        progress_bar = st.progress(0)
        status_text = st.empty()

        try:

            status_text.text("🔍 Scraping web data for topic analysis...")
            progress_bar.progress(10)

            scraped_data = await self.web_scraper.scrape_topic_data(topic)
            results["scraped_data"] = scraped_data
            progress_bar.progress(20)

            status_text.text("💡 Generating initial keyword ideas...")
            progress_bar.progress(25)

            initial_keywords = await self.llm_generator.generate_initial_keywords(
                topic, scraped_data, target_audience
            )
            progress_bar.progress(40)

            status_text.text("📊 Getting accurate metrics from Google Ads API...")
            progress_bar.progress(45)

            keyword_data = await self.keyword_researcher.research_keywords(
                initial_keywords
            )
            progress_bar.progress(60)

            status_text.text("🔬 Analyzing keyword performance...")
            progress_bar.progress(65)

            analyzed_keywords = self.data_analyzer.analyze_keywords(
                keyword_data, budget_range, campaign_goals
            )
            results["keywords"] = analyzed_keywords
            results["analysis"] = self.data_analyzer.get_summary_stats(
                analyzed_keywords
            )
            progress_bar.progress(80)

            status_text.text("🚀 Generating campaign ideas...")
            progress_bar.progress(85)

            campaigns = await self.llm_generator.generate_campaigns(
                analyzed_keywords,
                target_audience,
                budget_range,
                campaign_goals,
                scraped_data,
            )
            results["campaigns"] = campaigns
            progress_bar.progress(100)

            status_text.text("✅ Analysis complete!")

        except Exception as e:
            st.error(f"Error during processing: {str(e)}")
            status_text.text("❌ Processing failed")

        return results

    def _get_intent_color(self, intent: str) -> str:
        """Get background color for intent type"""
        intent_colors = {
            "Commercial": "#e8f5e8",
            "Informational": "#e3f2fd",
            "Investigation": "#fff3e0",
            "Local": "#f3e5f5",
            "Mixed": "#f5f5f5",
        }
        return intent_colors.get(intent, "#f5f5f5")

    def _get_competition_color(self, competition: str) -> str:
        """Get background color for competition level"""
        competition_colors = {"Low": "#e8f5e8", "Medium": "#fff3e0", "High": "#ffebee"}
        return competition_colors.get(competition, "#f5f5f5")

    def render_main_settings(self) -> Dict[str, Any]:
        """Render campaign settings in main area"""
        st.subheader("📋 Campaign Settings")

        col1, col2 = st.columns(2)

        with col1:
            topic = st.text_input(
                "Topic/Industry",
                placeholder="e.g., tire dealers, insurance providers",
                help="Enter the main topic or industry you want to research",
            )

            target_audience = st.text_area(
                "Target Audience",
                placeholder="e.g., homeowners looking for insurance, car owners needing tires",
                help="Describe your target audience in detail",
                height=68,
            )

        with col2:
            budget_range = st.selectbox(
                "Budget Range",
                [
                    "Low ($0-$500/month)",
                    "Medium ($500-$2000/month)",
                    "High ($2000-$5000/month)",
                    "Enterprise ($5000+/month)",
                ],
            )

            campaign_goals = st.multiselect(
                "Campaign Goals",
                [
                    "Lead Generation",
                    "Brand Awareness",
                    "Sales Conversion",
                    "Traffic Growth",
                    "Local Visibility",
                    "Competitor Analysis",
                ],
                default=["Lead Generation"],
            )

        with st.expander("⚙️ Advanced Options"):
            col3, col4, col5 = st.columns(3)
            with col3:
                max_keywords = st.slider("Max Keywords to Research", 10, 100, 50)
            with col4:
                min_search_volume = st.number_input("Min Search Volume", 0, 10000, 100)
            with col5:
                max_keyword_difficulty = st.slider("Max Keyword Difficulty", 0, 100, 70)

        st.markdown("</div>", unsafe_allow_html=True)

        return {
            "topic": topic,
            "target_audience": target_audience,
            "budget_range": budget_range,
            "campaign_goals": campaign_goals,
            "max_keywords": max_keywords,
            "min_search_volume": min_search_volume,
            "max_keyword_difficulty": max_keyword_difficulty,
        }

    def render_sidebar(self):
        """Render sidebar with help information"""

        api_status = self.validate_api_keys()
        missing_keys = [k for k, v in api_status.items() if not v]

        if missing_keys:
            st.sidebar.warning(
                f"⚠️ Please configure the following API keys in your .env file: {', '.join(missing_keys)}"
            )
        else:
            st.sidebar.success("✔️ All API keys are configured!")

        st.sidebar.markdown("## ⚙️ Usage")
        st.sidebar.markdown(
            """
        1. **Enter Your Topic**: Specify the industry or niche you want to research
        2. **Configure Settings**: Set your target audience, budget, and campaign goals  
        3. **AI Analysis**: Our system will:
           - Scrape relevant web data about your topic
           - Generate initial keyword ideas using Gemini AI
           - Get accurate metrics from Google Ads via DataForSEO API
           - Calculate precise keyword difficulty scores
           - Analyze opportunities and competition
           - Create targeted campaign strategies
        4. **Review Results**: Get comprehensive keyword data and campaign ideas
        """
        )

    def render_results(self, results: Dict[str, Any]):
        """Render the analysis results"""
        if not results or not results.get("keywords"):
            return

        st.markdown("## 📊 Analysis Results")

        col1, col2, col3, col4 = st.columns(4)

        analysis = results.get("analysis", {})

        with col1:
            st.metric(
                "Total Keywords",
                analysis.get("total_keywords", 0),
                help="Total number of keywords analyzed",
            )

        with col2:
            avg_cpc = analysis.get("avg_cpc", 0)
            st.metric(
                "Avg CPC",
                f"${avg_cpc:.2f}",
                help="Average cost per click across all keywords",
            )

        with col3:
            total_volume = analysis.get("total_search_volume", 0)
            st.metric(
                "Total Search Volume",
                f"{total_volume:,}",
                help="Combined monthly search volume",
            )

        with col4:
            avg_difficulty = analysis.get("avg_difficulty", 0)
            st.metric(
                "Avg Difficulty",
                f"{avg_difficulty:.1f}",
                help="Average keyword difficulty score",
            )

        tab1, tab2, tab3 = st.tabs(["🔑 Keywords", "🚀 Campaigns", "📈 Analysis"])

        with tab1:
            self.render_keywords_tab(results["keywords"])

        with tab2:
            self.render_campaigns_tab(results["campaigns"])

        with tab3:
            self.render_analysis_tab(results["analysis"], results["keywords"])

    def render_keywords_tab(self, keywords: List[Dict]):
        """Render keywords analysis tab"""
        st.subheader("🔑 Keywords")

        if not keywords:
            st.warning("No keywords found. Try adjusting your search criteria.")
            return

        col1, col2, col3 = st.columns(3)

        with col1:
            difficulty_filter = st.slider("Max Difficulty", 0, 100, 100)
        with col2:
            min_volume_filter = st.number_input("Min Volume", 0, value=0)
        with col3:
            max_cpc_filter = st.number_input("Max CPC ($)", 0.0, value=100.0, step=0.5)

        filtered_keywords = [
            kw
            for kw in keywords
            if (
                kw.get("difficulty", 0) <= difficulty_filter
                and kw.get("search_volume", 0) >= min_volume_filter
                and kw.get("cpc", 0) <= max_cpc_filter
            )
        ]

        st.markdown("---")

        for keyword in filtered_keywords[:20]:
            with st.container():
                st.markdown(
                    f"""
                    <div class="keyword-card">
                        <div class="keyword-title">"{keyword.get("keyword", "N/A")}"</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric(
                        label="📊 Volume",
                        value=f"{keyword.get('search_volume', 0):,}",
                        help="Monthly search volume",
                    )
                with col2:
                    st.metric(
                        label="💰 CPC",
                        value=f"${keyword.get('cpc', 0):.2f}",
                        help="Cost per click",
                    )
                with col3:
                    st.metric(
                        label="🎯 Difficulty",
                        value=f"{keyword.get('difficulty', 0)}/100",
                        help="Keyword difficulty score",
                    )
                with col4:
                    st.metric(
                        label="⭐ Score",
                        value=f"{keyword.get('opportunity_score', 0):.1f}/10",
                        help="Opportunity score",
                    )

                col5, col6 = st.columns(2)
                with col5:
                    intent_color = self._get_intent_color(keyword.get("intent", "N/A"))
                    st.markdown(
                        f'<div style="padding: 8px; background-color: {intent_color}; border-radius: 4px; text-align: center;">'
                        f'<strong>Intent:</strong> {keyword.get("intent", "N/A")}</div>',
                        unsafe_allow_html=True,
                    )
                with col6:
                    comp_color = self._get_competition_color(
                        keyword.get("competition", "N/A")
                    )
                    st.markdown(
                        f'<div style="padding: 8px; background-color: {comp_color}; border-radius: 4px; text-align: center;">'
                        f'<strong>Competition:</strong> {keyword.get("competition", "N/A")}</div>',
                        unsafe_allow_html=True,
                    )

                st.markdown(
                    '<div class="keyword-separator"></div>', unsafe_allow_html=True
                )

        if filtered_keywords:
            df = pd.DataFrame(filtered_keywords)
            csv = df.to_csv(index=False)

            st.markdown("---")
            st.download_button(
                label="📥 Download Keywords as CSV",
                data=csv,
                file_name=f"keywords_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )

    def render_campaigns_tab(self, campaigns: List[Dict]):
        """Render campaigns tab"""
        st.subheader("🚀 Campaign Ideas & Strategies")

        if not campaigns:
            st.warning("No campaigns generated.")
            return

        for i, campaign in enumerate(campaigns):
            with st.container():
                st.markdown(
                    f'<div class="campaign-title">{campaign.get("title", f"Campaign {i+1}")}</div>',
                    unsafe_allow_html=True,
                )

                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"**🎯 Objective:** {campaign.get('objective', 'N/A')}")
                    st.markdown(
                        f"**📝 Description:** {campaign.get('description', 'N/A')}"
                    )

                with col2:
                    st.markdown(
                        f"**💰 Budget:** {campaign.get('budget_recommendation', 'N/A')}"
                    )
                    st.markdown(
                        f"**📊 Expected Performance:** {campaign.get('expected_performance', 'N/A')}"
                    )

                keywords = campaign.get("keywords", [])[:8]
                if keywords:
                    st.markdown("**🔑 Target Keywords:**")
                    keyword_html = ""
                    for keyword in keywords:
                        keyword_html += f'<span class="keyword-tag">{keyword}</span>'
                    st.markdown(keyword_html, unsafe_allow_html=True)

                st.markdown(
                    '<div class="campaign-separator"></div>', unsafe_allow_html=True
                )

            with st.expander(f"📋 {campaign.get('title', f'Campaign {i+1}')}"):
                st.markdown("### 📢 Ad Copy Suggestions")
                for j, ad_copy in enumerate(campaign.get("ad_copies", [])[:3]):
                    st.markdown(f"**{j+1}.** {ad_copy}")

                st.markdown("---")

                st.markdown("### 🎯 Landing Page Recommendations")
                st.markdown(
                    campaign.get("landing_page_tips", "No recommendations available")
                )

                st.markdown("---")

                st.markdown("### 👥 Targeting Suggestions")
                st.markdown(
                    campaign.get(
                        "targeting_suggestions", "No targeting suggestions available"
                    )
                )

    def render_analysis_tab(self, analysis: Dict, keywords: List[Dict]):
        """Render analysis tab with charts and insights"""
        st.subheader("📈 Data Analysis")

        if not keywords:
            st.warning("No data available for analysis.")
            return

        df = pd.DataFrame(keywords)

        col1, col2 = st.columns(2)

        with col1:
            st.write("**CPC Distribution**")
            if "cpc" in df.columns:
                st.bar_chart(df["cpc"].head(20))

        with col2:
            st.write("**Search Volume Distribution**")
            if "search_volume" in df.columns:
                st.bar_chart(df["search_volume"].head(20))

        # st.write("**Key Insights:**")
        # insights = analysis.get("insights", [])
        # for insight in insights:
        #     st.write(f"• {insight}")

        # st.write("**Recommendations:**")
        # recommendations = analysis.get("recommendations", [])
        # for rec in recommendations:
        #     st.write(f"• {rec}")

    def run(self):
        """Main application runner"""

        st.markdown(
            '<div class="main-header" style="text-align: center; margin: 0 auto; width: 100%;">🔍 Keywords & Campaigns</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            "Comprehensive keyword research and campaign generation using AI and multiple data sources"
        )

        self.render_sidebar()

        inputs = self.render_main_settings()

        if not inputs["topic"]:
            st.info("👆 Please enter a topic above to get started.")
        else:
            if st.button("🚀 Run", type="primary"):
                if not all(self.validate_api_keys().values()):
                    st.error(
                        "❌ Please configure all required API keys before proceeding."
                    )
                    return

                with st.spinner("Processing your request..."):
                    results = asyncio.run(
                        self.process_topic(
                            inputs["topic"],
                            inputs["target_audience"],
                            inputs["budget_range"],
                            inputs["campaign_goals"],
                        )
                    )

                st.session_state["results"] = results

            if "results" in st.session_state and st.session_state["results"]:
                self.render_results(st.session_state["results"])


if __name__ == "__main__":
    app = KeywordsCampaignsApp()
    app.run()
