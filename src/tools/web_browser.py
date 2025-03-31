from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import time
import newspaper
import undetected_chromedriver  as uc

class WebBrowser:
    def __init__(self, use_selenium=True, headless=True, timeout=15):
        self.use_selenium = use_selenium
        self.timeout = timeout
        self.current_page = None
        
        if self.use_selenium:
            options = uc.ChromeOptions()
            if headless:
                options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            # Set a realistic user-agent
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
            self.driver = uc.Chrome(options=options)
        else:
            import requests
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
            })

    def navigate(self, url):
        """Load a web page using Selenium (or Requests)."""
        self.current_page = url
        try:
            if self.use_selenium:
                self.driver.get(url)
                time.sleep(self.timeout)  # Wait for full page load
                # If it's Yahoo News, try scrolling a bit
                if "yahoo.com" in url.lower():
                    self.scroll_page(times=5, delay=2)
            else:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response.text
        except Exception as e:
            print(f"Error loading {url}: {str(e)}")
            return None

    def scroll_page(self, times=3, delay=3):
        """Scroll down the page multiple times to trigger dynamic content loading."""
        if self.use_selenium:
            for _ in range(times):
                try:
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(delay)
                except Exception as e:
                    print(f"Error during scrolling: {e}")

    def find_elements(self, *selectors):
        """Find elements using CSS selectors."""
        if self.use_selenium:
            try:
                # Join selectors with commas
                return self.driver.find_elements(By.CSS_SELECTOR, ', '.join(selectors))
            except Exception as e:
                print(f"Error finding elements with selectors {selectors}: {e}")
                return []
        else:
            from bs4 import BeautifulSoup
            try:
                page_source = self.navigate(self.current_page)
                soup = BeautifulSoup(page_source, 'html.parser')
                return soup.select(', '.join(selectors))
            except Exception as e:
                print(f"Error parsing page source: {e}")
                return []

    def extract_text(self, element, selector=None):
        """Extract text from an element or sub-selector."""
        try:
            if self.use_selenium:
                if selector:
                    elem = element.find_element(By.CSS_SELECTOR, selector)
                    return elem.text.strip()
                return element.text.strip()
            else:
                if selector:
                    elem = element.select_one(selector)
                    return elem.get_text(strip=True) if elem else None
                return element.get_text(strip=True)
        except Exception as e:
            print(f"Error extracting text: {e}")
            return None

    def extract_attribute(self, element, attribute, selector=None):
        """Extract an attribute from an element or sub-selector."""
        try:
            if self.use_selenium:
                if selector:
                    elem = element.find_element(By.CSS_SELECTOR, selector)
                    return elem.get_attribute(attribute)
                return element.get_attribute(attribute)
            else:
                from bs4 import BeautifulSoup
                if selector:
                    elem = element.select_one(selector)
                    return elem[attribute] if elem and attribute in elem.attrs else None
                return element[attribute] if attribute in element.attrs else None
        except Exception as e:
            print(f"Error extracting attribute: {e}")
            return None

    def extract_full_article(self, url):
        """Extract full article text using Newspaper3k as fallback."""
        try:
            import newspaper
            art = newspaper.Article(url)
            art.download()
            art.parse()
            return art.text
        except Exception as e:
            print(f"Error extracting full article content from {url}: {e}")
            return ""

    def close(self):
        """Clean up resources."""
        if self.use_selenium and self.driver:
            self.driver.quit()
        else:
            self.session.close()

    def execute_js(self, script):
        if self.use_selenium:
            return self.driver.execute_script(script)
        return None

    def wait_for_element(self, selector, timeout=10):
        if self.use_selenium:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            try:
                return WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
            except Exception as e:
                print(f"Error waiting for element {selector}: {e}")
                return None
        return None

# class WebBrowser:
#     def __init__(self, use_selenium=True, headless=True, timeout=10):
#         self.use_selenium = use_selenium
#         self.timeout = timeout
#         self.current_page = None
#         
#         if self.use_selenium:
#             options = webdriver.ChromeOptions()
#             if headless:
#                 options.add_argument("--headless=new")
#             options.add_argument("--no-sandbox")
#             options.add_argument("--disable-dev-shm-usage")
#             options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36")
#             self.driver = webdriver.Chrome(options=options)
#         else:
#             self.session = requests.Session()
#             self.session.headers.update({
#                 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
#             })
# 
#     # def navigate(self, url):
#     #     """Load a web page using either Selenium or Requests"""
#     #     self.current_page = url
#     #     try:
#     #         if self.use_selenium:
#     #             self.driver.get(url)
#     #             WebDriverWait(self.driver, self.timeout).until(
#     #                 EC.presence_of_element_located((By.TAG_NAME, 'body'))
#     #             )
#     #         else:
#     #             response = self.session.get(url, timeout=self.timeout)
#     #             response.raise_for_status()
#     #             return response.text
#     #     except Exception as e:
#     #         print(f"Error loading {url}: {str(e)}")
#     #         return None
#     def navigate(self, url):
#         """Load a web page using either Selenium or Requests. For dynamic pages (like Yahoo News), scroll to load additional content."""
#         self.current_page = url
#         try:
#             if self.use_selenium:
#                 self.driver.get(url)
#                 WebDriverWait(self.driver, self.timeout).until(
#                     EC.presence_of_element_located((By.TAG_NAME, 'body'))
#                 )
#                 # If the URL is from Yahoo (or similar dynamic site), scroll to load more content.
#                 if "yahoo.com" in url.lower():
#                     self.scroll_page(times=3, delay=3)
#             else:
#                 response = self.session.get(url, timeout=self.timeout)
#                 response.raise_for_status()
#                 return response.text
#         except Exception as e:
#             print(f"Error loading {url}: {str(e)}")
#             return None
# 
#     def scroll_page(self, times=3, delay=3):
#         """Scroll down the page multiple times to load dynamic content."""
#         if self.use_selenium:
#             for _ in range(times):
#                 try:
#                     self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
#                     time.sleep(delay)
#                 except Exception as e:
#                     print(f"Error during scrolling: {e}")
# 
#     def find_elements(self, *selectors):
#         """Find elements using CSS selectors"""
#         if self.use_selenium:
#             try:
#                 return self.driver.find_elements(By.CSS_SELECTOR, ', '.join(selectors))
#             except:
#                 return []
#         else:
#             try:
#                 page_source = self.navigate(self.current_page)  # Re-fetch with Requests if needed
#                 soup = BeautifulSoup(page_source, 'html.parser')
#                 return soup.select(', '.join(selectors))
#             except:
#                 return []
# 
#     def extract_text(self, element, selector=None):
#         """Extract text from an element or selector"""
#         try:
#             if self.use_selenium:
#                 if selector:
#                     elem = element.find_element(By.CSS_SELECTOR, selector)
#                     return elem.text.strip()
#                 return element.text.strip()
#             else:
#                 if selector:
#                     elem = element.select_one(selector)
#                     return elem.get_text(strip=True) if elem else None
#                 return element.get_text(strip=True)
#         except:
#             return None
# 
#     def extract_attribute(self, element, attribute, selector=None):
#         """Extract attribute from an element or selector"""
#         try:
#             if self.use_selenium:
#                 if selector:
#                     elem = element.find_element(By.CSS_SELECTOR, selector)
#                     return elem.get_attribute(attribute)
#                 return element.get_attribute(attribute)
#             else:
#                 if selector:
#                     elem = element.select_one(selector)
#                     return elem[attribute] if elem and attribute in elem.attrs else None
#                 return element[attribute] if attribute in element.attrs else None
#         except:
#             return None
# 
#     def extract_full_article(self, url):
#         try:
#             article = newspaper.Article(url)
#             article.download()
#             article.parse()
#             return article.text
#         except Exception as e:
#             print(f"Error extracting full article content from {url}: {e}")
#             return ""
# 
# 
#     def close(self):
#         """Clean up resources"""
#         if self.use_selenium and self.driver:
#             self.driver.quit()
#         elif not self.use_selenium:
#             self.session.close()
# 
#     def execute_js(self, script):
#         """Execute JavaScript (Selenium only)"""
#         if self.use_selenium:
#             return self.driver.execute_script(script)
#         return None
# 
#     def wait_for_element(self, selector, timeout=10):
#         """Wait for element to appear (Selenium only)"""
#         if self.use_selenium:
#             try:
#                 return WebDriverWait(self.driver, timeout).until(
#                     EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
#             except:
#                 return None
#         return None

class WebBrowserTool:
    def browse_web(self, url):
         return f"Placeholder: Web content from {url}"

class NewsCrawler:
    def __init__(self, news_sources, keywords=None, max_depth=2):
        self.news_sources = news_sources
        self.keywords = keywords or []
        self.max_depth = max_depth
        self.visited_urls = set()
        self.posted_articles = []
        # Initialize browser (assuming Selenium-based WebBrowser class)
        self.web_browser = WebBrowser() 

    def extract_with_keywords(self, element, selector, attribute=None):
        """Extract content with keyword filtering"""
        # found = element.find(selector)
        # if not found:
        #     return None
        found = None
        try:
            # Check if we're using Selenium (WebElement) or BeautifulSoup element
            if self.web_browser.use_selenium and hasattr(element, "find_element"):
                found = element.find_element(By.CSS_SELECTOR, selector)
            elif hasattr(element, "select_one"):
                found = element.select_one(selector)
        except Exception as e:
            found = None

        if not found:
            return None

        if attribute:
            content = found.get_attribute(attribute)
        else:
            content = found.text.strip()

        if content and self.keywords:
            if any(kw.lower() in content.lower() for kw in self.keywords):
                return content
        elif content:
            return content
        return None

    def crawl_page(self, url, current_depth=0):
        """Recursive crawling method with depth control"""
        if url in self.visited_urls or current_depth > self.max_depth:
            return

        self.visited_urls.add(url)
        print(f"Crawling: {url} (Depth {current_depth})")

        try:
            self.web_browser.navigate(url)
            
            # Extract main content
            main_content = self.web_browser.extract_text("main, article, .content-area")
            
            # Extract article elements using CSS selector
            article_elements = self.web_browser.find_elements("article, div.article, .news-item")

            for element in article_elements:
                # Extract details with keyword filtering
                headline = self.extract_with_keywords(element, "h2, h3, .headline")
                link = self.extract_with_keywords(element, "a", "href")
                date_text = self.extract_with_keywords(element, ".date, .timestamp")

                # Normalize link
                if link and not link.startswith(("http://", "https://")):
                    link = urljoin(url, link)

                if headline and link:
                    if link not in [a["link"] for a in self.posted_articles]:
                        article_data = {
                            "headline": headline,
                            "link": link,
                            "source": url,
                            "date": date_text,
                            "content": main_content if self.keyword_in_content(main_content) else None
                        }
                        self.posted_articles.append(article_data)

                        # Recursive crawl if we have keywords
                        if self.keywords and current_depth < self.max_depth:
                            self.crawl_page(link, current_depth + 1)

        except Exception as e:
            print(f"Error crawling {url}: {str(e)}")

    def keyword_in_content(self, text):
        return any(kw.lower() in text.lower() for kw in self.keywords) if self.keywords else True

    def run_crawler(self):
        for source in self.news_sources:
            self.crawl_page(source)
        return self.posted_articles

# Usage
# if __name__ == "__main__":
#     sources = [
#         "https://news-site-1.com",
#         "https://news-site-2.com"
#     ]
#     
#     crawler = NewsCrawler(
#         news_sources=sources,
#         keywords=["climate", "technology"],  # Set to None for all content
#         max_depth=2  # 0 = only seed pages, 1 = follow links from seed pages
#     )
#     
#     articles = crawler.run_crawler()
