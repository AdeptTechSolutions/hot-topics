import asyncio
import json
import random
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import aiohttp
import requests
from bs4 import BeautifulSoup


@dataclass
class ScrapedContent:
    """Data structure for scraped content"""

    url: str
    title: str
    content: str
    meta_description: str
    headings: List[str]
    keywords: List[str]
    timestamp: str


class WebScraper:
    """Enhanced web scraper for topic research"""

    def __init__(self):
        self.session = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        self.search_engines = [
            "https://www.google.com/search?q={}",
            "https://duckduckgo.com/html/?q={}",
        ]

    async def create_session(self):
        """Create aiohttp session with proper configuration"""
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(
            headers=self.headers, connector=connector, timeout=timeout
        )

    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()

    def generate_search_queries(self, topic: str) -> List[str]:
        """Generate diverse search queries for comprehensive topic coverage"""
        base_queries = [
            f"{topic}",
            f"{topic} industry trends",
            f"{topic} market analysis",
            f"{topic} customer needs",
            f"{topic} problems solutions",
            f"best {topic} companies",
            f"{topic} reviews complaints",
            f"{topic} buying guide",
            f"{topic} cost pricing",
            f"{topic} tips advice",
            f"how to choose {topic}",
            f"{topic} vs alternatives",
            f"{topic} statistics data",
            f"{topic} future outlook",
        ]
        return base_queries[:10]

    async def search_google_results(
        self, query: str, num_results: int = 10
    ) -> List[str]:
        """Extract URLs from Google search results"""
        urls = []
        try:
            search_url = f"https://www.google.com/search?q={query}&num={num_results}"

            response = requests.get(search_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.content, "html.parser")

            for link in soup.find_all("a", href=True):
                href = link["href"]
                if href.startswith("/url?q="):

                    url = href.split("/url?q=")[1].split("&")[0]
                    if url.startswith("http") and "google.com" not in url:
                        urls.append(url)

        except Exception as e:
            print(f"Error searching Google for '{query}': {e}")

        return urls[:num_results]

    async def scrape_url(self, url: str) -> Optional[ScrapedContent]:
        """Scrape content from a single URL"""
        try:
            if not self.session:
                await self.create_session()

            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    return self.parse_html(url, html)
                else:
                    print(f"Failed to fetch {url}: Status {response.status}")

        except Exception as e:
            print(f"Error scraping {url}: {e}")

        return None

    def parse_html(self, url: str, html: str) -> ScrapedContent:
        """Parse HTML content and extract relevant information"""
        soup = BeautifulSoup(html, "html.parser")

        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        title = ""
        if soup.title:
            title = soup.title.string.strip()

        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag:
            meta_desc = meta_tag.get("content", "")

        headings = []
        for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            if heading.string:
                headings.append(heading.string.strip())

        content = ""

        main_content_selectors = [
            "main",
            "article",
            ".content",
            "#content",
            ".main-content",
            ".post-content",
            ".entry-content",
            ".article-content",
        ]

        for selector in main_content_selectors:
            content_element = soup.select_one(selector)
            if content_element:
                content = content_element.get_text(separator=" ", strip=True)
                break

        if not content:
            body = soup.find("body")
            if body:
                content = body.get_text(separator=" ", strip=True)

        content = re.sub(r"\s+", " ", content)
        content = content[:5000]

        keywords = self.extract_keywords(content + " " + title + " " + meta_desc)

        return ScrapedContent(
            url=url,
            title=title,
            content=content,
            meta_description=meta_desc,
            headings=headings,
            keywords=keywords,
            timestamp=str(time.time()),
        )

    def extract_keywords(self, text: str) -> List[str]:
        """Extract potential keywords from text"""

        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())

        stop_words = {
            "the",
            "is",
            "at",
            "which",
            "on",
            "and",
            "a",
            "to",
            "are",
            "as",
            "was",
            "will",
            "an",
            "be",
            "by",
            "this",
            "have",
            "from",
            "or",
            "one",
            "had",
            "but",
            "not",
            "what",
            "all",
            "were",
            "they",
            "we",
            "when",
            "your",
            "can",
            "said",
            "there",
            "each",
            "which",
            "she",
            "do",
            "how",
            "their",
            "if",
            "up",
            "out",
            "many",
            "then",
            "them",
            "these",
            "so",
            "some",
            "her",
            "would",
            "make",
            "like",
            "into",
            "him",
            "has",
            "two",
            "more",
            "very",
            "what",
            "know",
            "just",
            "first",
            "get",
            "over",
            "think",
            "also",
            "its",
            "our",
            "work",
            "life",
            "only",
            "can",
            "still",
            "should",
            "after",
            "being",
            "now",
            "made",
            "before",
            "here",
            "through",
            "when",
            "where",
            "much",
            "good",
            "well",
            "come",
            "could",
            "see",
            "time",
            "way",
            "even",
            "new",
            "want",
            "because",
            "any",
            "these",
            "give",
            "day",
            "most",
            "us",
            "find",
            "back",
            "use",
            "may",
            "water",
            "long",
            "little",
            "down",
            "own",
            "right",
            "never",
            "old",
            "without",
            "another",
            "last",
            "same",
            "great",
            "public",
            "big",
            "such",
            "take",
            "end",
            "why",
            "while",
            "came",
            "help",
            "put",
            "year",
            "different",
            "away",
            "again",
            "off",
            "went",
            "tell",
            "men",
            "say",
            "small",
            "every",
            "found",
            "still",
            "between",
            "name",
            "too",
            "any",
            "high",
            "something",
            "need",
            "want",
            "does",
        }

        word_count = {}
        for word in words:
            if word not in stop_words and len(word) > 3:
                word_count[word] = word_count.get(word, 0) + 1

        return list(
            dict(
                sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:20]
            ).keys()
        )

    async def scrape_topic_data(self, topic: str) -> Dict[str, Any]:
        """Main method to scrape comprehensive data for a topic"""
        results = {
            "topic": topic,
            "sources": [],
            "content": {},
            "keywords": [],
            "insights": [],
            "timestamp": str(time.time()),
        }

        try:
            await self.create_session()

            queries = self.generate_search_queries(topic)
            all_urls = []

            for query in queries[:5]:
                urls = await self.search_google_results(query, 3)
                all_urls.extend(urls)
                await asyncio.sleep(random.uniform(1, 2))

            unique_urls = list(set(all_urls))[:15]

            scraped_contents = []
            for url in unique_urls:
                content = await self.scrape_url(url)
                if content and content.content:
                    scraped_contents.append(content)
                await asyncio.sleep(random.uniform(0.5, 1.5))

            if scraped_contents:
                results["sources"] = [content.url for content in scraped_contents]

                all_text = ""
                all_headings = []
                all_keywords = []

                for content in scraped_contents:
                    all_text += content.content + " "
                    all_headings.extend(content.headings)
                    all_keywords.extend(content.keywords)

                results["content"] = {
                    "combined_text": all_text[:10000],
                    "headings": list(set(all_headings))[:50],
                    "titles": [
                        content.title for content in scraped_contents if content.title
                    ],
                }

                keyword_counts = {}
                for keyword in all_keywords:
                    keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1

                results["keywords"] = list(
                    dict(
                        sorted(
                            keyword_counts.items(), key=lambda x: x[1], reverse=True
                        )[:30]
                    ).keys()
                )

                results["insights"] = self.generate_insights(results["content"], topic)

        except Exception as e:
            print(f"Error in scrape_topic_data: {e}")

        finally:
            await self.close_session()

        return results

    def generate_insights(self, content: Dict[str, Any], topic: str) -> List[str]:
        """Generate insights from scraped content"""
        insights = []

        headings = content.get("headings", [])
        if headings:
            insights.append(
                f"Found {len(headings)} relevant headings across scraped sources"
            )

            theme_words = {}
            for heading in headings:
                words = heading.lower().split()
                for word in words:
                    if len(word) > 4:
                        theme_words[word] = theme_words.get(word, 0) + 1

            top_themes = sorted(theme_words.items(), key=lambda x: x[1], reverse=True)[
                :5
            ]
            if top_themes:
                insights.append(
                    f"Common themes: {', '.join([theme[0] for theme in top_themes])}"
                )

        text = content.get("combined_text", "")
        if text:
            insights.append(
                f"Analyzed {len(text)} characters of content from multiple sources"
            )

            if "cost" in text.lower() or "price" in text.lower():
                insights.append(
                    "Price/cost information is commonly discussed in this topic"
                )

            if "review" in text.lower() or "rating" in text.lower():
                insights.append("User reviews and ratings are important factors")

            if "compare" in text.lower() or "vs" in text.lower():
                insights.append(
                    "Comparison content is prevalent, indicating competitive market"
                )

        return insights


if __name__ == "__main__":

    async def test_scraper():
        scraper = WebScraper()
        results = await scraper.scrape_topic_data("tire dealers")
        print(json.dumps(results, indent=2))
