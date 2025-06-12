import asyncio
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import Config
from dataforseo_labs import DataForSEOLabs
from llm_generator import LLMGenerator
from trends import TrendsAnalyzer

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
    text-align: center;
    margin-bottom: 2rem;
}
.keyword-card {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 0.75rem;
    margin-bottom: 1rem;
    border-left: 5px solid #007bff;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    transition: all 0.2s ease-in-out;
}
.keyword-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 6px 12px rgba(0,0,0,0.15);
}
.keyword-title {
    font-size: 1.25rem;
    font-weight: 600;
    color: #333;
    margin-bottom: 1rem;
}
.competition-label {
    display: inline-block;
    padding: 0.3rem 0.6rem;
    border-radius: 1rem;
    font-weight: 600;
    font-size: 0.85rem;
    color: white;
    text-transform: uppercase;
}
.competition-low { background-color: #28a745; }
.competition-medium { background-color: #ffc107; }
.competition-high { background-color: #dc3545; }
.competition-unknown { background-color: #6c757d; } 

.metric-highlight {
    font-size: 1.1rem;
    font-weight: 600;
    color: #007bff;
}
.related-keyword-tag {
    display: inline-block;
    background-color: #e9ecef;
    color: #495057;
    padding: 0.25rem 0.6rem;
    margin: 0.2rem;
    border-radius: 0.375rem;
    font-size: 0.875rem;
    border: 1px solid #ced4da;
}
</style>
""",
    unsafe_allow_html=True,
)


class KeywordsCampaignsApp:
    def __init__(self):
        self.config = Config()
        api_credentials = self.config.get_dataforseo_credentials()
        if api_credentials["login"] and api_credentials["password"]:
            self.dataforseo = DataForSEOLabs(
                login=api_credentials["login"], password=api_credentials["password"]
            )
        else:
            self.dataforseo = None
        self.llm_generator = LLMGenerator(self.config)
        self.trends_analyzer = TrendsAnalyzer(self.config)

    def validate_api_keys(self) -> Dict[str, bool]:
        """Validate that required API keys are present"""
        return self.config.get_api_status()

    async def process_topic(self, topic: str) -> Dict[str, Any]:
        """Main processing pipeline for topic analysis and campaign generation"""

        if not self.dataforseo:
            st.error(
                "DataForSEO credentials not configured. Please add DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD to your .env file or environment variables."
            )
            return {}

        results = {
            "topic": topic,
            "keywords": [],
            "campaigns": [],
            "analysis": {},
            "timestamp": datetime.now().isoformat(),
        }

        progress_bar = st.progress(0, text="Initializing...")

        try:
            progress_bar.progress(20, text="🔍 Fetching related keywords...")
            api_response = self.dataforseo.get_related_keywords(topic)
            if not api_response:
                st.error(
                    "Failed to fetch keywords. The API might be down or the request timed out."
                )
                progress_bar.empty()
                return results

            progress_bar.progress(50, text="📊 Processing keyword data...")
            keywords_data = self.dataforseo.extract_keyword_data(api_response)
            if not keywords_data:
                st.warning(
                    "DataForSEO did not return any related keywords for this topic. Try a different or broader topic."
                )
                progress_bar.empty()
                return results

            results["keywords"] = keywords_data
            results["analysis"] = self.dataforseo.get_keyword_analysis_data(
                keywords_data
            )

            progress_bar.progress(75, text="🚀 Generating AI campaign ideas...")
            campaigns = await self.llm_generator.generate_campaigns_from_keywords(
                keywords_data, topic
            )
            results["campaigns"] = campaigns

            progress_bar.progress(100, text="✅ Analysis complete!")

        except Exception as e:
            st.error(f"An unexpected error occurred during processing: {str(e)}")
            progress_bar.empty()

        return results

    def get_competition_class(self, competition_level: str) -> str:
        """Get CSS class for competition level"""
        return f"competition-{competition_level.lower()}"

    def render_main_settings(self) -> Dict[str, Any]:
        """Render campaign settings in main area"""
        st.markdown("#### 📋 Inputs")

        col1, col2 = st.columns([1, 1])

        with col1:
            topic = st.text_input(
                "**Enter a Topic**",
                value=st.session_state.get("topic", ""),
                placeholder="e.g., tyre dealers, insurance providers, digital marketing",
                help="Enter the main topic to research. The tool will find related keywords and generate campaign ideas.",
            )
        with col2:
            st.markdown("**Don't know what to search for?**")
            st.markdown(
                ":rainbow-background[**Let the tool analyze current trending topics keywords for you!**]"
            )
        return {"topic": topic}

    def render_sidebar(self):
        """Render sidebar with help information"""
        api_status = self.validate_api_keys()
        missing_keys = [k for k, v in api_status.items() if not v]

        if missing_keys:
            st.sidebar.warning(f"⚠️ Missing API keys: {', '.join(missing_keys)}")
            st.sidebar.info("💡 Configure API keys in a .env file.")
        else:
            st.sidebar.success("✔️ All API keys are configured!")

        st.sidebar.markdown("## 💡 What The Tool Does")
        st.sidebar.info(
            """
            🔍 Finds related keywords using DataForSEO Labs

            📊 Shows real search metrics & competition

            🚀 Generates AI-powered campaign ideas

            📈 Provides detailed keyword analysis
            
            🔥 Suggests campaign topics from Google Trends
            """
        )

        st.sidebar.markdown("## 📊 Metrics")
        st.sidebar.markdown(
            """
        - **Search Volume**: Monthly searches
        - **CPC**: Cost per click in advertising
        - **Competition**: LOW/MEDIUM/HIGH
        - **Keyword Difficulty**: 0-100 scale
        - **Top of Page Bid**: Ad bid range estimates
        """
        )

    def render_keywords_tab(self, keywords: List[Dict]):
        """Render keywords analysis tab"""
        if not keywords:
            st.warning("No keywords found to display.")
            return

        with st.expander("🔑 Keyword Details & Filters", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                difficulty_filter = st.slider("Maximum Keyword Difficulty", 0, 100, 100)
            with col2:
                min_volume_filter = st.number_input(
                    "Minimum Search Volume", 0, value=0, step=100
                )
            with col3:
                competition_filter = st.selectbox(
                    "Filter by Competition Level", ["ALL", "LOW", "MEDIUM", "HIGH"]
                )

        filtered_keywords = [
            kw
            for kw in keywords
            if (kw.get("keyword_difficulty", 0) or 0) <= difficulty_filter
            and (kw.get("search_volume", 0) or 0) >= min_volume_filter
            and (
                competition_filter == "ALL"
                or kw.get("competition_level", "").upper() == competition_filter
            )
        ]

        st.markdown(f"**Showing {len(filtered_keywords)} of {len(keywords)} keywords**")

        for keyword in filtered_keywords:
            with st.container():
                st.markdown(
                    f"""
                    <div class="keyword-card">
                        <div class="keyword-title">"{keyword.get("keyword", "N/A")}"</div>
                    """,
                    unsafe_allow_html=True,
                )

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(
                        "📊 Search Volume",
                        self.dataforseo.format_number(keyword.get("search_volume", 0)),
                    )
                with col2:
                    st.metric(
                        "💰 Avg. CPC",
                        self.dataforseo.format_currency(keyword.get("cpc", 0)),
                    )
                with col3:
                    st.metric(
                        "🎯 SEO Difficulty",
                        f"{keyword.get('keyword_difficulty', 0)}/100",
                    )

                col4, col5 = st.columns([1, 2])
                with col4:
                    competition_level = keyword.get("competition_level", "UNKNOWN")
                    comp_class = self.get_competition_class(competition_level)
                    st.markdown(
                        f'**Competition** <span class="competition-label {comp_class}">{competition_level}</span>',
                        unsafe_allow_html=True,
                    )
                with col5:
                    low_bid = self.dataforseo.format_currency(
                        keyword.get("low_top_of_page_bid", 0)
                    )
                    high_bid = self.dataforseo.format_currency(
                        keyword.get("high_top_of_page_bid", 0)
                    )
                    st.metric("💵 Est. Top of Page Bid", f"{low_bid} - {high_bid}")

                related_keywords = keyword.get("related_keywords", [])
                if related_keywords:
                    with st.expander(f"🔗 Related Ideas"):
                        related_html = "".join(
                            [
                                f'<span class="related-keyword-tag">{kw}</span>'
                                for kw in related_keywords[:25]
                            ]
                        )
                        st.markdown(
                            f"<div>{related_html}</div>", unsafe_allow_html=True
                        )

                st.markdown("</div>", unsafe_allow_html=True)

        if filtered_keywords:
            df = pd.DataFrame(filtered_keywords)
            csv = df.to_csv(index=False).encode("utf-8")

    def render_full_ad_preview(self, ad_copy: Dict) -> str:
        """Generates a realistic HTML preview of a search ad."""
        headlines = ad_copy.get("headlines", [])
        descriptions = ad_copy.get("descriptions", [])
        display_path = ad_copy.get("display_path", "")

        h1 = headlines[0] if len(headlines) > 0 else "Your Awesome Product"
        h2 = headlines[1] if len(headlines) > 1 else "Special Offer Inside"
        h3 = headlines[2] if len(headlines) > 2 else "Shop Now"

        full_description = (
            " ".join(descriptions)
            if descriptions
            else "Get the best deals and top-rated service. Click here to learn more about our exclusive offers and find the perfect solution for your needs today."
        )

        full_ad_html = f"""
        <div style="font-family: Arial, sans-serif; border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; margin: 10px 0; max-width: 600px; background-color: #ffffff;">
            <div style="display: flex; align-items: center; margin-bottom: 4px;">
                <span style="font-weight: bold; font-size: 14px; color: #202124;">Ad</span>
                <span style="font-size: 14px; color: #5f6368; margin: 0 4px;">·</span>
                <span style="font-size: 14px; color: #202124;">www.yourwebsite.com{display_path}</span>
            </div>
            <h3 style="color: #1a0dab; font-size: 20px; font-weight: 400; margin: 0 0 4px 0; line-height: 1.3;">
                {' | '.join([h for h in [h1, h2, h3] if h])}
            </h3>
            <p style="font-size: 14px; color: #4d5156; line-height: 1.57; margin: 0;">
                {full_description}
            </p>
        </div>
        """
        return full_ad_html

    def render_campaigns_tab(self, campaigns: List[Dict]):
        """Render campaigns tab"""
        if not campaigns:
            st.info(
                "No AI campaigns were generated. This can happen if the Gemini API is not configured or if the API call failed. A fallback may be used."
            )
            return

        for i, campaign in enumerate(campaigns):
            with st.expander(
                f"**[Campaign Idea {i+1}] {campaign.get('title', 'Untitled')}**",
                expanded=i == 0,
            ):
                st.markdown(f"**🎯 Objective:** {campaign.get('objective', 'N/A')}")
                st.markdown(f"**📝 Strategy:** {campaign.get('description', 'N/A')}")
                st.markdown(
                    f"**💡 Targeting & Bidding:** {campaign.get('targeting_suggestions', 'N/A')}"
                )
                st.markdown(
                    f"**📈 Expected Performance:** *{campaign.get('expected_performance', 'N/A')}*"
                )

                col1, col2 = st.columns(2)
                with col1:
                    if campaign.get("keywords"):
                        st.markdown("**🔑 Target Keywords**")
                        st.dataframe(
                            pd.DataFrame(campaign["keywords"], columns=["Keyword"]),
                            use_container_width=True,
                        )

                with col2:
                    ad_copies = campaign.get("ad_copies")
                    if ad_copies and isinstance(ad_copies, list) and len(ad_copies) > 0:
                        st.markdown("**📢 Example Ad Copy**")
                        ad_copy = ad_copies[0]

                        if isinstance(ad_copy, dict) and "headlines" in ad_copy:
                            with st.container(border=True):
                                headlines = ad_copy.get("headlines", [])
                                descriptions = ad_copy.get("descriptions", [])

                                h1 = headlines[0] if headlines else "Example Headline 1"
                                d1 = (
                                    descriptions[0]
                                    if descriptions
                                    else "Example description..."
                                )

                                ad_preview_html = f"""
                                <div style="padding: 5px 5px 0 5px;">
                                    <p style="font-size: 1.1em; color: #1a0dab; font-weight: bold; margin: 0;">{h1}</p>
                                    <p style="color: #545454; margin-top: 5px; margin-bottom: 5px;">{d1}</p>
                                </div>
                                """
                                st.markdown(ad_preview_html, unsafe_allow_html=True)

                                popover = st.popover(
                                    "View Details",
                                    use_container_width=True,
                                )

                                with popover:
                                    st.markdown("##### :rainbow-background[Ad Preview]")
                                    full_ad_html = self.render_full_ad_preview(ad_copy)
                                    st.markdown(full_ad_html, unsafe_allow_html=True)

                                    st.markdown("##### :rainbow-background[Components]")
                                    st.markdown("**Headlines:**")
                                    for h in headlines:
                                        st.info(h)

                                    st.markdown("**Descriptions:**")
                                    for d in descriptions:
                                        st.info(d)
                        else:
                            st.info("No ad copy generated for this campaign.")

    def render_analysis_tab(self, analysis: Dict, keywords: List[Dict]):
        """Render analysis tab with charts and insights"""
        st.markdown("### :green-background[Overview]")

        if not keywords or not analysis:
            st.warning("No data available for analysis.")
            return

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Keywords Found", analysis.get("total_keywords", 0))
        with col2:
            st.metric(
                "Avg. Monthly Volume",
                self.dataforseo.format_number(
                    int(analysis.get("avg_search_volume", 0))
                ),
            )
        with col3:
            st.metric(
                "Avg. CPC", self.dataforseo.format_currency(analysis.get("avg_cpc", 0))
            )
        with col4:
            st.metric(
                "Avg. SEO Difficulty", f"{analysis.get('avg_difficulty', 0):.1f}/100"
            )

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### :rainbow-background[Competition Distribution]")
            if analysis.get("competition_counts"):
                comp_df = pd.DataFrame(
                    list(analysis["competition_counts"].items()),
                    columns=["Competition Level", "Count"],
                ).sort_values("Competition Level")
                fig = px.pie(
                    comp_df,
                    values="Count",
                    names="Competition Level",
                    title="",
                    color="Competition Level",
                    color_discrete_map={
                        "LOW": "#28a745",
                        "MEDIUM": "#ffc107",
                        "HIGH": "#dc3545",
                        "UNKNOWN": "#6c757d",
                    },
                )
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### :rainbow-background[Search Volume vs. CPC]")
            if keywords:
                kw_df = pd.DataFrame(keywords)
                if "search_volume" in kw_df.columns and "cpc" in kw_df.columns:
                    fig = px.scatter(
                        kw_df,
                        x="search_volume",
                        y="cpc",
                        hover_data=["keyword", "competition_level"],
                        color="competition_level",
                        color_discrete_map={
                            "LOW": "#28a745",
                            "MEDIUM": "#ffc107",
                            "HIGH": "#dc3545",
                            "UNKNOWN": "#6c757d",
                        },
                        title="",
                        log_x=True,
                    )
                    fig.update_layout(
                        xaxis_title="Search Volume (Log Scale)",
                        yaxis_title="Average CPC ($)",
                    )
                    st.plotly_chart(fig, use_container_width=True)

        if keywords:
            st.markdown("#### :rainbow-background[Top Keywords by Search Volume]")
            kw_df = pd.DataFrame(keywords)
            if "search_volume" in kw_df.columns:
                top_keywords = kw_df.nlargest(15, "search_volume").sort_values(
                    "search_volume", ascending=True
                )
                fig = px.bar(
                    top_keywords,
                    x="search_volume",
                    y="keyword",
                    orientation="h",
                    title="",
                    text="search_volume",
                )
                fig.update_traces(texttemplate="%{text:,.0s}", textposition="outside")
                fig.update_layout(
                    height=600, yaxis_title=None, xaxis_title="Monthly Search Volume"
                )
                st.plotly_chart(fig, use_container_width=True)

    def render_results(self, results: Dict[str, Any]):
        """Render the analysis results"""
        if not results or not results.get("keywords"):
            return

        st.markdown(f"#### 📊 Results for '{results['topic']}'")

        tab1, tab2, tab3 = st.tabs(["🔑 Keywords", "🚀 Campaign Ideas", "📈 Analysis"])

        with tab1:
            self.render_keywords_tab(results["keywords"])

        with tab2:
            self.render_campaigns_tab(results["campaigns"])

        with tab3:
            self.render_analysis_tab(results["analysis"], results["keywords"])

    def run(self):
        """Main application runner"""
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(
                "resources/logo.png",
                use_container_width=True,
            )
        self.render_sidebar()
        inputs = self.render_main_settings()

        if inputs["topic"]:
            st.session_state["topic"] = inputs["topic"]
        elif "topic" in st.session_state and not inputs["topic"]:
            del st.session_state["topic"]

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button(
                "🚀 Analyze & Generate Campaigns",
                type="primary",
                use_container_width=True,
            ):
                if "topic" in st.session_state and st.session_state["topic"]:
                    if "results" in st.session_state:
                        del st.session_state["results"]

                    results = asyncio.run(self.process_topic(st.session_state["topic"]))

                    if results and results.get("keywords"):
                        st.session_state["results"] = results
                    else:
                        st.error(
                            "Analysis could not be completed. Please check the topic and try again."
                        )
                else:
                    st.warning("👆 Please enter a topic above to get started.")

        with col2:
            search_api_available = bool(self.config.SEARCHAPI_KEY)
            if st.button(
                "💡 Search Trends",
                use_container_width=True,
                disabled=not search_api_available,
            ):
                if "results" in st.session_state:
                    del st.session_state["results"]
                if "suggested_topics" in st.session_state:
                    del st.session_state["suggested_topics"]

                st.session_state["fetch_trending_topics"] = True
                st.rerun()

            if (
                "suggested_topics" in st.session_state
                and st.session_state["suggested_topics"]
            ):
                topics = st.session_state["suggested_topics"]
                col1, col2, col3 = st.columns([1, 1.75, 1])
                with col2:
                    popover = st.popover("🔥 View Trending", use_container_width=True)
                with popover:
                    for i, topic in enumerate(topics):
                        if st.button(topic, key=f"trend_{i}", use_container_width=True):
                            st.session_state["topic"] = topic
                            st.session_state["auto_run_analysis"] = True
                            del st.session_state["suggested_topics"]
                            st.rerun()

        if st.session_state.get("fetch_trending_topics"):
            st.session_state["fetch_trending_topics"] = False
            with st.spinner("Analyzing Google Trends to find hot topics..."):
                suggested_topics = asyncio.run(
                    self.trends_analyzer.get_promising_topics()
                )
            if suggested_topics:
                st.session_state["suggested_topics"] = suggested_topics
            else:
                st.error(
                    "Could not fetch or analyze trending topics. Please try again later."
                )
            st.rerun()

        if st.session_state.get("auto_run_analysis") and st.session_state.get("topic"):
            st.session_state.pop("auto_run_analysis", None)
            if "results" in st.session_state:
                del st.session_state["results"]

            results = asyncio.run(self.process_topic(st.session_state["topic"]))

            if results and results.get("keywords"):
                st.session_state["results"] = results
            else:
                st.error(
                    "Analysis could not be completed. Please check the topic and try again."
                )

        if "results" in st.session_state:
            if st.session_state.get("topic") == st.session_state["results"].get(
                "topic"
            ):
                self.render_results(st.session_state["results"])
        elif "topic" not in st.session_state or not st.session_state["topic"]:
            st.info(
                "👆 Please enter a topic above and click 'Analyze', or click 'Search Trends' for AI-suggested topics."
            )


if __name__ == "__main__":
    app = KeywordsCampaignsApp()
    app.run()
