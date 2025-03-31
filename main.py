import json
import datetime
import time
from urllib.parse import urljoin, quote
from selenium.webdriver.common.by import By
import os
import sys
import re  # For regex extraction

# Add the src directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.append(src_dir)

# Import from the correct module structure based on the directory listing
from agents.browser_agent import BrowserAgent
from agents.coordinator import TaskCoordinator, PlannerAgent, ExecutionAgent, ToolAgent
from tools.web_browser import WebBrowser, NewsCrawler
# from components.memory import Memory
# from tools.web_browser import WebBrowserTool
# from tools.document import DocumentProcessor
# from components.scheduler import Scheduler

from typing import List, Dict, Any, Optional
import random
import openai
from bs4 import BeautifulSoup
import webbrowser
import newspaper
import warnings
warnings.filterwarnings("ignore", category=SyntaxWarning)

class OpenAIProvider:
    """Custom provider for OpenAI API integration."""
    def __init__(self, model="gpt-4o", api_key=None):
        self.model = model
        openai.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not openai.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass it directly.")
    def generate(self, prompt, max_tokens=1000, temperature=0.7):
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error calling OpenAI API: {str(e)}")
            return ""

class GeneticsBizNewsAgent(BrowserAgent):
    def __init__(self, config_path: str = "config.json"):
        """Initialize the GeneticsBizNewsAgent with configuration."""
        super().__init__()
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.web_browser = WebBrowser()
        self.coordinator = TaskCoordinator()
        self.planner = PlannerAgent()
        self.execute = ExecutionAgent()
        self.tool = ToolAgent()
        
        self.llm_provider = OpenAIProvider(
            model=self.config.get("openai_model", "gpt-4o"),
            api_key=self.config.get("openai_api_key")
        )
        
        # Initialize posted_articles to track duplicates if needed
        self.posted_articles = []
    
    def analyze_article(self, article: dict, company_summary: str = "") -> dict:
        """Fetch and analyze a single article, then assign a relevance score based on similarity to BTG's work."""
        try:
            # Navigate to the article's link and extract content
            self.web_browser.navigate(article["link"])
            content_elements = self.web_browser.find_elements("article", ".content", "#main-content")
            if content_elements:
                extracted = self.web_browser.extract_text(content_elements[0])
            else:
                extracted = ""
            
            # Optionally, use a fallback if the extracted content is too short
            if not extracted or len(extracted) < 500:
                print(f"Extracted content too short for '{article['headline']}'. Consider fallback extraction.")
                # You could try using Newspaper3k as a fallback here:
                extracted = self.web_browser.extract_full_article(article["link"])
            
            article["content"] = extracted
            
            if article.get("content") and len(article["content"]) > 100:
                analysis_prompt = f"""
                Analyze the following article about genetics and AI. Please answer the following questions concisely:
                
                1. Is the article primarily about business or technological developments in genetics/AI? (Answer Yes or No)
                2. What is the main news or development?
                3. What companies or organizations are mentioned or involved?
                4. Why is this significant for the genetics and AI sectors?
                
                Article headline: {article["headline"]}
                Article content (first 3000 characters): {article["content"][:3000]}...
                """
                analysis = self.llm_provider.generate(analysis_prompt)
                article["analysis"] = analysis
                print(f"Analysis for '{article['headline']}': {analysis}")
                
                # Revised relevance prompt: include the company summary context
                relevance_prompt = (
                    f"Given the analysis above and the following company overview:\n\n{company_summary}\n\n"
                    "Rate the relevance of this article to what Breakthrough Genomics is working on. "
                    "Respond with ONLY a single integer between 0 and 10 (where 10 means highly relevant and 0 means not relevant at all), and nothing else. "
                    "If you cannot determine a rating, output 0."
                )
                relevance_str = self.llm_provider.generate(relevance_prompt).strip()
                print(f"Raw relevance for '{article['headline']}': {relevance_str}")
                import re
                match = re.search(r'\d+', relevance_str)
                if match:
                    article["relevance_score"] = int(match.group(0))
                else:
                    print(f"No numeric relevance found for '{article['headline']}' - defaulting to 0")
                    article["relevance_score"] = 0
            else:
                print(f"Insufficient content extracted for '{article['headline']}', defaulting relevance to 0")
                article["analysis"] = "No content extracted or content too short."
                article["relevance_score"] = 0
            return article
        except Exception as e:
            print(f"Error analyzing article {article['link']}: {str(e)}")
            article["analysis"] = None
            article["relevance_score"] = 0
            return article

   
    def search_and_process_articles(self, query, max_links=20) -> list:
        """Search for news using Bing search and process the first max_links."""
        search_url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
        print(f"Searching for '{query}' on Bing...")
        self.web_browser.navigate(search_url)
        time.sleep(5)
        link_elements = self.web_browser.find_elements("li.b_algo h2 a")
        print(f"Found {len(link_elements)} link elements from Bing search.")
        articles = []
        for element in link_elements[:max_links]:
            link = self.web_browser.extract_attribute(element, "href")
            headline = self.web_browser.extract_text(element)
            if link and headline:
                article = {
                    "headline": headline,
                    "link": link,
                    "source": "bing",
                    "date": "",
                    "content": None
                }
                articles.append(article)
        print(f"Found {len(articles)} articles from Bing search.")
        return articles

    def search_yahoo_news(self, query, max_links=20) -> list:
        encoded_query = quote(query)
        search_url = f"https://search.yahoo.com/search?p={encoded_query}&fr=uh3_news_web&fr2=p%3Anews%2Cm%3Asb&.tsrc=uh3_news_web"
        print(f"Searching Yahoo News for '{query}' with URL: {search_url}")
        self.web_browser.navigate(search_url)
        
        # Wait longer to allow dynamic content to load
        time.sleep(7)
        
        # Scroll multiple times to trigger loading of all results
        try:
            for _ in range(4):
                self.web_browser.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(3)
        except Exception as e:
            print(f"Error scrolling Yahoo News page: {e}")
        
        # Try multiple selectors for Yahoo News results
        selectors = ["h4 a", "h3 a", "h3.title a", "div.title a"]
        all_elements = []
        for selector in selectors:
            elems = self.web_browser.find_elements(selector)
            if elems:
                all_elements.extend(elems)
        # Deduplicate based on href attribute
        unique_elements = {}
        for elem in all_elements:
            href = self.web_browser.extract_attribute(elem, "href")
            if href and href not in unique_elements:
                unique_elements[href] = elem
        link_elements = list(unique_elements.values())
        
        print(f"Found {len(link_elements)} link elements from Yahoo News search using selectors {selectors}.")
        
        articles = []
        for element in link_elements[:max_links]:
            link = self.web_browser.extract_attribute(element, "href")
            headline = self.web_browser.extract_text(element)
            if link and headline:
                article = {
                    "headline": headline,
                    "link": link,
                    "source": "yahoo",
                    "date": "",
                    "content": None
                }
                articles.append(article)
        print(f"Found {len(articles)} articles from Yahoo News search.")
        return articles

    def search_ap_news(self, query, max_links=20) -> list:
        """Search for news articles on AP News using the query."""
        encoded_query = quote(query)
        search_url = f"https://apnews.com/search?query={encoded_query}"
        print(f"Searching AP News for '{query}' with URL: {search_url}")
        self.web_browser.navigate(search_url)
        time.sleep(5)
        link_elements = self.web_browser.find_elements("div.Feed a")
        print(f"Found {len(link_elements)} link elements from AP News search.")
        articles = []
        for element in link_elements[:max_links]:
            link = self.web_browser.extract_attribute(element, "href")
            headline = self.web_browser.extract_text(element)
            if link and headline:
                article = {
                    "headline": headline,
                    "link": link,
                    "source": "ap",
                    "date": "",
                    "content": None
                }
                articles.append(article)
        print(f"Found {len(articles)} articles from AP News search.")
        return articles

    def search_all_sources(self, query, yahoo_query, ap_query, max_links_per_source=20) -> list:
        """Combine search results from Bing, Yahoo News, and AP News."""
        articles_bing = self.search_and_process_articles(query, max_links=max_links_per_source)
        articles_yahoo = self.search_yahoo_news(yahoo_query, max_links=max_links_per_source)
        articles_ap = self.search_ap_news(ap_query, max_links=max_links_per_source) if ap_query else []
        all_articles = articles_bing + articles_yahoo + articles_ap
        print(f"Total articles found from all sources: {len(all_articles)}")
        return all_articles

    def load_website_content(self, directory):
        """Recursively load and extract text from all HTML files in a directory."""
        all_text = ""
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith(".html"):
                    path = os.path.join(root, file)
                    with open(path, "r", encoding="utf-8") as f:
                        html = f.read()
                        soup = BeautifulSoup(html, "html.parser")
                        for script in soup(["script", "style"]):
                            script.extract()
                        text = soup.get_text(separator="\n", strip=True)
                        all_text += text + "\n"
        return all_text

    def summarize_website_content(self, content: str) -> str:
        prompt = f"""
Read the following content from the Breakthrough Genomics website and produce a detailed analysis that focuses on the company's mission, key projects, and technological focus relevant to genetics and AI. Make sure this analysis includes specific details and products. Do this in 12 sentences or less. 

Content:
{content}

Summary:
"""
        return self.llm_provider.generate(prompt)

    def create_daily_post_via_search(self):
        """Create a daily post using search results for genetics AI news and website context."""
        keywords = [
            "genomics testing", 
            "rare diseases", 
            "rare disease diagnosis", 
            "cancer screening", 
            "newborn screening"
        ]
        query = "Today's news on " + ", ".join(keywords) + " and AI in genomics"
        print(f"Using search query: {query}")

        yahoo_query = "Today's News on Genetics Testing and AI in Genomics"
        ap_query = ""  # Set to a valid query if needed

        all_articles = self.search_all_sources(query, yahoo_query, ap_query, max_links_per_source=10)
        if not all_articles:
            print("No relevant genetics AI news articles found.")
            return None

        # relevant_articles = all_articles
        btg_site = "btg_site"  # Folder where BTG website HTML files are stored
        loaded_btg = self.load_website_content(btg_site)
        company_summary = self.summarize_website_content(loaded_btg)
        print("Company Summary:")
        print(company_summary)
        
        analyzed_articles = []
        for article in all_articles:
            analyzed = self.analyze_article(article, company_summary=company_summary)
            analyzed_articles.append(analyzed)
        
        threshold = self.config.get("relevance_threshold", 5)
        relevant_articles = [a for a in analyzed_articles if a.get("relevance_score", 0) >= threshold]
        relevant_articles = sorted(relevant_articles, key=lambda x: x.get("relevance_score", 0), reverse=True)
        if not relevant_articles:
            print("No relevant articles after filtering, defaulting to using all articles")
            relevant_articles = all_articles
            # return None

        # Load BTG website content and (optionally) summarize it
        # btg_site = "btg_site"  # Folder where BTG website HTML files are stored
        # loaded_btg = self.load_website_content(btg_site)
        # company_summary = self.summarize_website_content(loaded_btg)
        # print("Company Summary:")
        # print(company_summary)
        
        post_prompt = f""" 
        You are an agent designed to read news articles related to Genetics, Genetics Testing, and Genetics AI and connect them to the work of a company called Breakthrough Genomics.
        
        First, create a concise and professional report summarizing the following genetics AI news articles:
        {json.dumps([{"headline": a["headline"], "link": a["link"], "analysis": a.get("analysis", ""), "relevance_score": a.get("relevance_score", 0)} for a in relevant_articles], indent=2)}
        
        Second, review the Breakthrough Genomics website content provided below and connect the news to what the company is currently doing:
        {company_summary}
        
        Requirements:
        1. Start with a hook based on the current news.
        2. Provide a two-sentence summary of the breaking news, including specifics and source links.
        3. Follow with one or two sentences connecting the news to Breakthrough Genomics’ current work.
        4. Format the post for a CEO’s LinkedIn update (using two or three brief passages).
        5. End with 3-5 relevant hashtags.
        """
        summary = self.llm_provider.generate(post_prompt)
        print("Final Post:")
        print(summary)
        return summary

    def create_email_draft(self, recipient: str, subject: str, body: str):
        recipient_encoded = quote(recipient)
        subject_encoded = quote(subject)
        body_encoded = quote(body)
        mailto_link = f"mailto:{recipient_encoded}?subject={subject_encoded}&body={body_encoded}"
        webbrowser.open(mailto_link)

    def run(self):
        """Main execution method for the agent using search approach."""
        post = self.create_daily_post_via_search()
        if post:
            subject = "Re: Daily BTG News Post"
            recipient_email = "laura@btgenomics.com"
            body = post
            self.create_email_draft(recipient_email, subject, body)

if __name__ == "__main__":
    agent = GeneticsBizNewsAgent("config.json")
    agent.run()

