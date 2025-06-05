import os
from typing import Any, Dict

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Central configuration management"""

    APP_NAME = "Keywords & Campaigns"
    VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-exp-05-20")

    DATAFORSEO_LOGIN = os.getenv("DATAFORSEO_LOGIN")
    DATAFORSEO_PASSWORD = os.getenv("DATAFORSEO_PASSWORD")
    SEMRUSH_API_KEY = os.getenv("SEMRUSH_API_KEY")
    SERPAPI_KEY = os.getenv("SERPAPI_KEY")

    RATE_LIMITS = {
        "dataforseo": int(os.getenv("RATE_LIMIT_DATAFORSEO", 60)),
        "semrush": int(os.getenv("RATE_LIMIT_SEMRUSH", 60)),
        "serpapi": int(os.getenv("RATE_LIMIT_SERPAPI", 30)),
    }

    DEFAULT_LOCATION = int(os.getenv("DEFAULT_LOCATION", 2840))
    DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")
    DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "USD")

    CACHE_DURATION = int(os.getenv("CACHE_DURATION", 3600))

    SCRAPING_DELAY_MIN = float(os.getenv("SCRAPING_DELAY_MIN", 0.5))
    SCRAPING_DELAY_MAX = float(os.getenv("SCRAPING_DELAY_MAX", 2.0))
    MAX_SCRAPING_URLS = int(os.getenv("MAX_SCRAPING_URLS", 15))
    SCRAPING_TIMEOUT = int(os.getenv("SCRAPING_TIMEOUT", 30))

    MAX_KEYWORDS_PER_REQUEST = int(os.getenv("MAX_KEYWORDS_PER_REQUEST", 50))
    MAX_TOTAL_KEYWORDS = int(os.getenv("MAX_TOTAL_KEYWORDS", 100))
    MIN_KEYWORD_LENGTH = int(os.getenv("MIN_KEYWORD_LENGTH", 2))
    MAX_KEYWORD_LENGTH = int(os.getenv("MAX_KEYWORD_LENGTH", 10))

    MAX_CAMPAIGNS = int(os.getenv("MAX_CAMPAIGNS", 5))
    MAX_AD_COPIES_PER_CAMPAIGN = int(os.getenv("MAX_AD_COPIES_PER_CAMPAIGN", 3))

    OPPORTUNITY_WEIGHTS = {
        "volume": float(os.getenv("WEIGHT_VOLUME", 0.3)),
        "cpc": float(os.getenv("WEIGHT_CPC", 0.2)),
        "difficulty": float(os.getenv("WEIGHT_DIFFICULTY", 0.3)),
        "intent": float(os.getenv("WEIGHT_INTENT", 0.2)),
    }

    BUDGET_RANGES = {
        "Low ($0-$500/month)": (0, 500),
        "Medium ($500-$2000/month)": (500, 2000),
        "High ($2000-$5000/month)": (2000, 5000),
        "Enterprise ($5000+/month)": (5000, float("inf")),
    }

    CAMPAIGN_GOALS = [
        "Lead Generation",
        "Brand Awareness",
        "Sales Conversion",
        "Traffic Growth",
        "Local Visibility",
        "Competitor Analysis",
    ]

    INTENT_KEYWORDS = {
        "Commercial": [
            "buy",
            "purchase",
            "price",
            "cost",
            "cheap",
            "deal",
            "discount",
            "sale",
            "offer",
            "shopping",
            "store",
            "order",
            "payment",
        ],
        "Informational": [
            "how to",
            "what is",
            "guide",
            "tips",
            "tutorial",
            "learn",
            "explain",
            "definition",
            "meaning",
            "help",
            "advice",
            "information",
        ],
        "Navigational": [
            "login",
            "website",
            "official",
            "contact",
            "homepage",
            "site",
            "page",
            "portal",
            "dashboard",
            "account",
        ],
        "Local": [
            "near me",
            "local",
            "nearby",
            "in my area",
            "around here",
            "close by",
            "directions",
            "location",
            "address",
            "map",
        ],
        "Investigation": [
            "review",
            "comparison",
            "vs",
            "versus",
            "best",
            "top",
            "rating",
            "evaluate",
            "compare",
            "alternative",
            "option",
        ],
    }

    STREAMLIT_CONFIG = {
        "page_title": APP_NAME,
        "page_icon": "🔍",
        "layout": "wide",
        "initial_sidebar_state": "expanded",
    }

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "keywords_campaigns.log")

    @classmethod
    def get_api_status(cls) -> Dict[str, bool]:
        """Get status of all API configurations"""
        return {
            "Gemini API": bool(cls.GEMINI_API_KEY),
            "DataForSEO": bool(cls.DATAFORSEO_LOGIN and cls.DATAFORSEO_PASSWORD),
            "SEMrush": bool(cls.SEMRUSH_API_KEY),
            "SerpApi": bool(cls.SERPAPI_KEY),
        }

    @classmethod
    def get_available_apis(cls) -> list:
        """Get list of available API services"""
        apis = []
        if cls.GEMINI_API_KEY:
            apis.append("gemini")
        if cls.DATAFORSEO_LOGIN and cls.DATAFORSEO_PASSWORD:
            apis.append("dataforseo")
        if cls.SEMRUSH_API_KEY:
            apis.append("semrush")
        if cls.SERPAPI_KEY:
            apis.append("serpapi")
        return apis

    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """Validate configuration and return status"""
        status = {"valid": True, "errors": [], "warnings": [], "api_count": 0}

        if not cls.GEMINI_API_KEY:
            status["errors"].append("Gemini API key is required")
            status["valid"] = False

        api_count = 0
        if cls.DATAFORSEO_LOGIN and cls.DATAFORSEO_PASSWORD:
            api_count += 1
        if cls.SEMRUSH_API_KEY:
            api_count += 1
        if cls.SERPAPI_KEY:
            api_count += 1

        status["api_count"] = api_count

        if api_count == 0:
            status["warnings"].append(
                "No keyword research APIs configured. System will use fallback methods with limited accuracy."
            )
        elif api_count == 1:
            status["warnings"].append(
                "Consider configuring DataForSEO API for the most accurate Google Ads metrics."
            )

        if cls.MAX_KEYWORDS_PER_REQUEST <= 0:
            status["errors"].append("MAX_KEYWORDS_PER_REQUEST must be positive")
            status["valid"] = False

        if cls.CACHE_DURATION < 0:
            status["errors"].append("CACHE_DURATION cannot be negative")
            status["valid"] = False

        return status

    @classmethod
    def get_config_summary(cls) -> str:
        """Get human-readable configuration summary"""
        api_status = cls.get_api_status()
        validation = cls.validate_config()

        summary = f"""
        🔍 {cls.APP_NAME} v{cls.VERSION} Configuration Summary

        📊 API Status:
        {''.join([f"  {'✅' if status else '❌'} {name}" for name, status in api_status.items()])}

        ⚙️ Settings:
          • Max Keywords: {cls.MAX_TOTAL_KEYWORDS}
          • Cache Duration: {cls.CACHE_DURATION}s
          • Debug Mode: {'On' if cls.DEBUG else 'Off'}
          • Default Location: {cls.DEFAULT_LOCATION} ({cls.DEFAULT_LANGUAGE})

        🎯 Available Features:
          • Keyword Research APIs: {validation['api_count']}
          • Web Scraping: ✅
          • AI Campaign Generation: {'✅' if cls.GEMINI_API_KEY else '❌'}
          • Data Analysis: ✅

        {'✅ Configuration Valid' if validation['valid'] else '❌ Configuration Issues Detected'}
        """

        if validation["errors"]:
            summary += f"\n❌ Errors:\n" + "\n".join(
                [f"  • {error}" for error in validation["errors"]]
            )

        if validation["warnings"]:
            summary += f"\n⚠️ Warnings:\n" + "\n".join(
                [f"  • {warning}" for warning in validation["warnings"]]
            )

        return summary


config = Config()

APP_NAME = config.APP_NAME
VERSION = config.VERSION
DEBUG = config.DEBUG
