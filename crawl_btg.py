import os
import requests
import time
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

def crawl(url, base_domain, visited, output_dir, depth=0, max_depth=3):
    """Recursively crawl a website and save pages locally."""
    if depth > max_depth or url in visited:
        return
    print(f"Crawling (depth {depth}): {url}")
    visited.add(url)
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=20)
        # response = requests.get(url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to retrieve {url}: {e}")
        return
    
    # Create a local file path based on the URL
    parsed_url = urlparse(url)
    # Determine a filename: if the path is empty or ends with '/', use 'index.html'
    if parsed_url.path == "" or parsed_url.path.endswith("/"):
        file_path = os.path.join(output_dir, parsed_url.netloc, parsed_url.path.lstrip("/"), "index.html")
    else:
        # Use the last part of the path; if no extension, append '.html'
        filename = os.path.basename(parsed_url.path)
        if not os.path.splitext(filename)[1]:
            filename += ".html"
        file_path = os.path.join(output_dir, parsed_url.netloc, os.path.dirname(parsed_url.path).lstrip("/"), filename)
    
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"Saved: {file_path}")
    except Exception as e:
        print(f"Error saving {file_path}: {e}")
    
    # Parse the page to extract links
    soup = BeautifulSoup(response.text, "html.parser")
    for link in soup.find_all("a", href=True):
        href = link["href"]
        # Resolve relative URLs
        next_url = urljoin(url, href)
        # Only follow links within the same domain
        if urlparse(next_url).netloc == base_domain:
            crawl(next_url, base_domain, visited, output_dir, depth+1, max_depth)
    # Sleep briefly to be polite
    time.sleep(1)

def main():
    start_url = "https://btgenomics.com"
    visited = set()
    output_dir = "btg_site"
    base_domain = urlparse(start_url).netloc
    crawl(start_url, base_domain, visited, output_dir, depth=0, max_depth=5)
    print("Crawling complete.")

if __name__ == "__main__":
    main()

