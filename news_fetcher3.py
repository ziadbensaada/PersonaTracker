import feedparser
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging
import urllib.parse
import time
import re
import json
import os
import hashlib
from pathlib import Path

# Ensure cache directory exists
os.makedirs('cache/rss_cache', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Cache configuration
CACHE_DIR = Path("./cache/rss_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_TTL = timedelta(hours=24)  # Cache for 24 hours

# User agent for requests
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Headers to mimic a browser
HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'DNT': '1',
    'Referer': 'https://www.google.com/'
}

def setup_selenium_driver():
    """Set up and return a Selenium WebDriver with Chrome."""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920x1080')
    chrome_options.add_argument(f'user-agent={USER_AGENT}')
    
    # Disable images for faster loading
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize Selenium: {str(e)}")
        return None

def get_cache_key(query: str, feed_url: str) -> str:
    """Generate a cache key for the query and feed URL"""
    key_str = f"{query.lower()}:{feed_url}"
    return hashlib.md5(key_str.encode('utf-8')).hexdigest()

def load_from_cache(cache_key: str) -> Optional[List[Dict]]:
    """Load data from cache if it exists and is not expired"""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if not cache_file.exists():
        return None
        
    try:
        mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - mtime > CACHE_TTL:
            return None
            
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Error reading cache file {cache_file}: {e}")
        return None

def save_to_cache(cache_key: str, data: List[Dict]) -> None:
    """Save data to cache"""
    try:
        cache_file = CACHE_DIR / f"{cache_key}.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Error writing to cache file {cache_file}: {e}")

# List of RSS feeds to search
RSS_FEEDS = [
    "https://leconomiste.com/rss-leconomiste",
    "https://www.moroccoworldnews.com/feed/",
    "https://lematin.ma/rssFeed/2",
    "https://lavieeco.com/feed",
    "https://akhbarona.com/feed/index.rss",
    "https://feeds.bbci.co.uk/news/rss.xml",
    "http://rss.cnn.com/rss/edition.rss",
    "https://www.cbsnews.com/latest/rss/main",
    "https://techcrunch.com/feed/",
    "https://www.wired.com/feed/rss",
    "https://www.theverge.com/rss/index.xml",
    "https://moroccotimes.tv/feed/"

]

def clean_text(text: str) -> str:
    """Clean and normalize text"""
    if not text:
        return ""
    return ' '.join(text.split())

def clean_url(url: str) -> str:
    """Clean and decode URL if needed"""
    try:
        return urllib.parse.unquote(url)
    except:
        return url

def extract_article_content(url: str) -> Optional[Dict[str, str]]:
    """Extract article content and first image using BeautifulSoup"""
    try:
        logger.info(f"\n{'='*80}\nProcessing URL: {url}\n{'='*80}")
        
        # Use requests with session
        session = requests.Session()
        session.headers.update(HEADERS)
        response = session.get(url, timeout=20)
        response.raise_for_status()
        
        # Check if the response is HTML
        content_type = response.headers.get('content-type', '').lower()
        if 'text/html' not in content_type:
            logger.warning(f"URL does not return HTML (Content-Type: {content_type})")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script, style, and other non-content elements
        for element in soup(["script", "style", "nav", "footer", "header", "iframe", "form"]):
            element.decompose()
        
        # Try multiple strategies to find the main content
        article_body = None
        
        # Strategy 1: Look for common semantic tags
        selectors = [
            'article',
            'main',
            'div.article',
            'div.article-content',
            'div.post-content',
            'div.entry-content',
            'div.content',
            'div.main-content',
            'div.story',
            'div.story-content',
            'div.article-body',
            'div.article__body',
            'div.article-content',
            'div.article__content',
            'div.article-content__content',
            'div.post',
            'div.post__content',
            'div.entry',
            'div.entry__content'
        ]
        
        for selector in selectors:
            if not article_body:
                article_body = soup.select_one(selector)
                if article_body:
                    logger.info(f"Found content using selector: {selector}")
        
        # Strategy 2: Look for elements with high text density
        if not article_body:
            logger.info("Trying text density analysis...")
            candidates = []
            for elem in soup.find_all(['article', 'div', 'section']):
                # Skip small elements
                if len(elem.text) < 100:
                    continue
                    
                # Calculate text to HTML ratio
                text_length = len(elem.get_text(strip=True))
                html_length = len(str(elem))
                
                if html_length > 0 and text_length > 0:
                    density = text_length / html_length
                    if density > 0.1:  # Reasonable text density threshold
                        candidates.append((density, elem))
            
            if candidates:
                candidates.sort(reverse=True, key=lambda x: x[0])
                article_body = candidates[0][1]
                logger.info("Found content using text density analysis")
        
        # Strategy 3: Fall back to body if nothing else works
        if not article_body:
            logger.warning("Falling back to body tag for content")
            article_body = soup.body
            logger.warning("Using entire body as fallback")
            
        if not article_body:
            logger.error("Could not find main content area")
            return None
            
        # Clean up the text
        text = article_body.get_text(separator='\n', strip=True)
        text = '\n'.join(line for line in text.split('\n') if line.strip())
        
        # Extract title
        title = clean_text(soup.title.string if soup.title else "")
        
        # Extract first image from article
        image_url = None
        
        # 1. Try Open Graph image
        og_image = soup.find('meta', property=['og:image', 'og:image:url'])
        if og_image and og_image.get('content'):
            image_url = og_image.get('content', '').strip()
            if image_url and not image_url.startswith(('data:', 'javascript:')):
                logger.info(f"[1/6] Found OG image: {image_url}")
            else:
                image_url = None
        
        # 2. Try Twitter card image
        if not image_url:
            twitter_image = soup.find('meta', {'name': ['twitter:image', 'twitter:image:src']})
            if twitter_image and twitter_image.get('content'):
                image_url = twitter_image.get('content', '').strip()
                if image_url and not image_url.startswith(('data:', 'javascript:')):
                    logger.info(f"[2/6] Found Twitter image: {image_url}")
                else:
                    image_url = None
        
        # 3. Try article:image meta tag
        if not image_url:
            article_image = soup.find('meta', {'property': 'article:image'})
            if article_image and article_image.get('content'):
                image_url = article_image.get('content', '').strip()
                if image_url and not image_url.startswith(('data:', 'javascript:')):
                    logger.info(f"[3/6] Found article:image: {image_url}")
                else:
                    image_url = None
        
        # 4. Try JSON-LD data
        if not image_url:
            json_ld = soup.find('script', type='application/ld+json')
            if json_ld:
                try:
                    ld_data = json.loads(json_ld.string)
                    if isinstance(ld_data, dict) and 'image' in ld_data:
                        if isinstance(ld_data['image'], dict):
                            if '@list' in ld_data['image'] and ld_data['image']['@list']:
                                image_url = ld_data['image']['@list'][0]
                            elif 'url' in ld_data['image']:
                                image_url = ld_data['image']['url']
                        elif isinstance(ld_data['image'], str):
                            image_url = ld_data['image']
                        
                        if image_url and not isinstance(image_url, str):
                            image_url = None
                        
                        if image_url and not image_url.startswith(('http://', 'https://')):
                            parsed_uri = urllib.parse.urlparse(url)
                            base_url = f"{parsed_uri.scheme}://{parsed_uri.netloc}"
                            if image_url.startswith('/'):
                                image_url = f"{base_url}{image_url}"
                            else:
                                image_url = f"{base_url}/{image_url}"
                        
                        if image_url:
                            logger.info(f"[4/6] Found JSON-LD image: {image_url}")
                except Exception as e:
                    logger.warning(f"Error parsing JSON-LD: {str(e)}")
        
        # 5. Try to find image in article body with common classes
        if not image_url and article_body:
            # Common image classes used in news articles
            img_selectors = [
                'img.article-image', 'img.wp-post-image', 'img.attachment-post-thumbnail',
                'img.entry-image', 'img.article-hero', 'img.article-featured-image',
                'img.article__image', 'img.article__hero', 'img.article__featured',
                'img.article__thumbnail', 'img.article__cover', 'img.article__header-image',
                'img.wp-image', 'img.size-full', 'img.attachment-full', 'img.attachment-large',
                'figure img', '.post-thumbnail img', '.featured-image img', '.entry-thumbnail img'
            ]
            
            for selector in img_selectors:
                if image_url:
                    break
                    
                try:
                    img = article_body.select_one(selector)
                    if img and img.get('src'):
                        src = img.get('src', '').strip()
                        if src and not src.startswith(('data:', 'javascript:')) and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                            # Handle relative URLs
                            if not src.startswith(('http://', 'https://')):
                                parsed_uri = urllib.parse.urlparse(url)
                                base_url = f"{parsed_uri.scheme}://{parsed_uri.netloc}"
                                if src.startswith('//'):
                                    src = f"{parsed_uri.scheme}:{src}"
                                elif src.startswith('/'):
                                    src = f"{base_url}{src}"
                                else:
                                    # Handle relative paths
                                    path = parsed_uri.path.rsplit('/', 1)[0] if '/' in parsed_uri.path else ''
                                    src = f"{base_url}{'/' if path and not path.endswith('/') else ''}{path}/{src}"
                            
                            if src.startswith(('http://', 'https://')):
                                image_url = src
                                logger.info(f"[5/6] Found image with class {selector}: {image_url}")
                except Exception as e:
                    logger.warning(f"Error processing image selector {selector}: {str(e)}")
        
        # 6. Try to find first image in article body with size > 100px
        if not image_url and article_body:
            for img in article_body.find_all(['img', 'div', 'figure', 'picture']):
                try:
                    # Try to get image URL from various attributes
                    src = None
                    for attr in ['src', 'data-src', 'data-lazy-src', 'data-original', 'data-image', 'data-srcset']:
                        if img.has_attr(attr):
                            src_attr = img[attr].strip()
                            if src_attr and not src_attr.startswith(('data:', 'javascript:')):
                                # Handle srcset if needed
                                if attr == 'data-srcset':
                                    src_parts = [p.strip().split()[0] for p in src_attr.split(',') if p.strip()]
                                    if src_parts:
                                        src = src_parts[0]
                                else:
                                    src = src_attr
                                break
                    
                    if not src:
                        # Check for picture/source elements
                        source = img.find('source')
                        if source and (source.has_attr('srcset') or source.has_attr('data-srcset')):
                            srcset = source.get('srcset', '') or source.get('data-srcset', '')
                            if srcset:
                                src = srcet.split(',')[0].split(' ')[0].strip()
                    
                    if not src or not any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                        continue
                        
                    # Skip if likely an icon/tracker
                    src_lower = src.lower()
                    if any(x in src_lower for x in ['icon', 'logo', 'pixel', 'spacer', '1x1', 'blank.gif', 'loading', 'placeholder', 'avatar']):
                        continue
                        
                    # Convert relative URLs
                    if not src.startswith(('http://', 'https://')):
                        parsed_uri = urllib.parse.urlparse(url)
                        base_url = f"{parsed_uri.scheme}://{parsed_uri.netloc}"
                        if src.startswith('//'):
                            src = f"{parsed_uri.scheme}:{src}"
                        elif src.startswith('/'):
                            src = f"{base_url}{src}"
                        else:
                            # Handle relative paths
                            path = parsed_uri.path.rsplit('/', 1)[0] if '/' in parsed_uri.path else ''
                            src = f"{base_url}{'/' if path and not path.endswith('/') else ''}{path}/{src}"
                    
                    # If we have a valid image URL, use it
                    if src.startswith(('http://', 'https://')):
                        image_url = src
                        logger.info(f"[6/6] Found suitable article image: {image_url}")
                        break
                        
                except Exception as img_e:
                    logger.warning(f"Error processing image tag: {str(img_e)}")
                    continue
                logger.info(f"Found content using text density analysis (density: {candidates[0][0]:.2f})")
        
        # Strategy 3: Fall back to body if nothing else works
        if not article_body:
            logger.warning("Falling back to body tag for content")
            article_body = soup.body
            logger.warning("Using entire body as fallback")
            
        if not article_body:
            logger.error("Could not find main content area")
            return None
            
        # Clean up the text
        text = article_body.get_text(separator='\n', strip=True)
        text = '\n'.join(line for line in text.split('\n') if line.strip())
        
        # Extract title
        title = clean_text(soup.title.string if soup.title else "")
        
        # Extract first image from article
        image_url = None
        try:
            logger.info(f"\n{'='*80}\nExtracting image for: {url}\n{'='*80}")
            
            # 1. First try Open Graph image
            og_image = None
            for prop in ['og:image', 'og:image:url', 'og:image:secure_url']:
                og_image = soup.find('meta', property=prop) or soup.find('meta', {'name': prop})
                if og_image and og_image.get('content'):
                    image_url = og_image.get('content', '').strip()
                    if image_url and not image_url.startswith(('data:', 'javascript:')):
                        logger.info(f"[1/8] Found OG image ({prop}): {image_url}")
                        break
                    else:
                        og_image = None
            
            # 2. Try Twitter card image
            if not image_url:
                twitter_image = soup.find('meta', {'name': ['twitter:image', 'twitter:image:src']})
                if twitter_image and twitter_image.get('content'):
                    image_url = twitter_image.get('content', '').strip()
                    if image_url and not image_url.startswith(('data:', 'javascript:')):
                        logger.info(f"[2/6] Found Twitter image: {image_url}")
                    else:
                        image_url = None
            
            # 3. Try article:image meta tag
            if not image_url:
                article_image = soup.find('meta', {'property': 'article:image'})
                if article_image and article_image.get('content'):
                    image_url = article_image.get('content', '').strip()
                    if image_url and not image_url.startswith(('data:', 'javascript:')):
                        logger.info(f"[3/6] Found article:image: {image_url}")
                    else:
                        image_url = None
            
            # 4. Try JSON-LD data for image
            if not image_url:
                json_ld = soup.find('script', type='application/ld+json')
                if json_ld:
                    try:
                        ld_data = json.loads(json_ld.string)
                        if isinstance(ld_data, dict):
                            if 'image' in ld_data:
                                if isinstance(ld_data['image'], dict) and '@list' in ld_data['image']:
                                    image_url = ld_data['image']['@list'][0]
                                elif isinstance(ld_data['image'], str):
                                    image_url = ld_data['image']
                                elif isinstance(ld_data['image'], dict) and 'url' in ld_data['image']:
                                    image_url = ld_data['image']['url']
                                
                                if image_url and not isinstance(image_url, str):
                                    image_url = None
                                
                                if image_url and not image_url.startswith(('http://', 'https://')):
                                    parsed_uri = urllib.parse.urlparse(url)
                                    base_url = f"{parsed_uri.scheme}://{parsed_uri.netloc}"
                                    if image_url.startswith('/'):
                                        image_url = f"{base_url}{image_url}"
                                    else:
                                        image_url = f"{base_url}/{image_url}"
                                
                                if image_url:
                                    logger.info(f"[4/6] Found JSON-LD image: {image_url}")
                    except Exception as e:
                        logger.warning(f"Error parsing JSON-LD: {str(e)}")
            
            # 5. Try to find image in article body with common classes and attributes
            if not image_url and article_body:
                # Common image classes and attributes used in news articles
                img_selectors = [
                    # Common class names
                    'img.article-image', 'img.wp-post-image', 'img.attachment-post-thumbnail',
                    'img.entry-image', 'img.article-hero', 'img.article-featured-image',
                    'img.article__image', 'img.article__hero', 'img.article__featured',
                    'img.article__thumbnail', 'img.article__cover', 'img.article__header-image',
                    'img.wp-image', 'img.size-full', 'img.attachment-full', 'img.attachment-large',
                    'img.lazy', 'img.lazy-loaded', 'img.news-image', 'img.story-image',
                    'img.featured-image', 'img.main-image', 'img.hero-image', 'img.lead-image',
                    # Common data attributes
                    'img[data-src]', 'img[data-lazy-src]', 'img[data-srcset]',
                    # Common parent containers
                    'figure.image img', 'div.image img', 'div.media img', 'div.photo img',
                    'div.article-media img', 'div.article-image img', 'div.entry-media img',
                    # Common image IDs
                    'img#main-image', 'img#featured-image', 'img#hero-image',
                    # Common data attributes in parent elements
                    'div[data-image] img', 'div[data-src] img', 'figure[data-image] img'
                ]
                
                for selector in img_selectors:
                    try:
                        elements = article_body.select(selector)
                        for img in elements:
                            # Try different attributes that might contain the image URL
                            for attr in ['src', 'data-src', 'data-lazy-src', 'data-original', 'data-image', 'data-srcset']:
                                src = img.get(attr, '').strip()
                                if not src:
                                    continue
                                    
                                # Clean and normalize the URL
                                src = src.split('?')[0].split('#')[0].strip()
                                
                                # Handle relative URLs
                                if src.startswith('//'):
                                    src = f"{urllib.parse.urlparse(url).scheme}:{src}"
                                elif src.startswith('/'):
                                    src = f"{urllib.parse.urlparse(url).scheme}://{urllib.parse.urlparse(url).netloc}{src}"
                                
                                # Check if it's a valid image URL
                                if (src.startswith(('http://', 'https://')) and 
                                    any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']) and
                                    not any(ext in src.lower() for ext in ['logo', 'icon', 'avatar', 'spacer', 'pixel', 'placeholder'])):
                                    image_url = src
                                    logger.info(f"[5/8] Found image with selector {selector} (attr: {attr}): {image_url}")
                                    break
                            
                            if image_url:
                                break
                                
                    except Exception as e:
                        logger.warning(f"Error processing selector {selector}: {str(e)}")
                        continue
                        
                    if image_url:
                        break
            
            # 6. Try to find first image in article body with size > 100px
            if not image_url and article_body:
                for img in article_body.find_all(['img', 'div', 'figure', 'picture', 'section', 'article']):
                    try:
                        # Try to get image URL from various attributes
                        src = None
                        
                        # Check for different attributes that might contain the image URL
                        for attr in ['src', 'data-src', 'data-lazy-src', 'data-original', 'data-image', 'data-srcset']:
                            src = img.get(attr, '').strip()
                            if src:
                                break
                        
                        if not src or src.startswith(('data:', 'javascript:')) or any(ext in src.lower() for ext in ['.svg', '.gif', '.ico', 'logo', 'icon', 'avatar']):
                            continue
                        
                        # Clean and normalize the URL
                        src = src.split('?')[0].split('#')[0].strip()
                        
                        # Handle relative URLs
                        if src.startswith('//'):
                            src = f"{urllib.parse.urlparse(url).scheme}:{src}"
                        elif src.startswith('/'):
                            src = f"{urllib.parse.urlparse(url).scheme}://{urllib.parse.urlparse(url).netloc}{src}"
                        
                        # Check if it's a valid image URL
                        if (src.startswith(('http://', 'https://')) and 
                            any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']) and
                            not any(ext in src.lower() for ext in ['logo', 'icon', 'avatar', 'spacer', 'pixel', 'placeholder'])):
                            image_url = src
                            logger.info(f"[6/8] Found image in page: {image_url}")
                            break
                            
                    except Exception as img_e:
                        logger.debug(f"Skipping image processing: {str(img_e)}")
                        continue
            
            # 1. Try Open Graph image
            if not image_url:
                og_image = soup.find('meta', property=['og:image', 'og:image:url'])
                if og_image and og_image.get('content'):
                    image_url = og_image['content']
                    logger.info(f"[1/8] Found OG image: {image_url}")
            
            # 2. Try Twitter card image
            if not image_url:
                twitter_image = soup.find('meta', attrs={'name': ['twitter:image', 'twitter:image:src']})
                if twitter_image and twitter_image.get('content'):
                    image_url = twitter_image['content']
                    logger.info(f"[2/8] Found Twitter image: {image_url}")
            
            # 3. Try article:image meta tag
            if not image_url:
                article_image = soup.find('meta', attrs={'property': 'article:image'})
                if article_image and article_image.get('content'):
                    image_url = article_image['content']
                    logger.info(f"[3/8] Found article:image: {image_url}")
            
            # 4. Try JSON-LD data
            if not image_url:
                json_ld = soup.find('script', type='application/ld+json')
                if json_ld:
                    try:
                        ld_data = json.loads(json_ld.string)
                        if isinstance(ld_data, dict):
                            if 'image' in ld_data:
                                if isinstance(ld_data['image'], dict) and '@list' in ld_data['image']:
                                    image_url = ld_data['image']['@list'][0] if ld_data['image']['@list'] else None
                                elif isinstance(ld_data['image'], str):
                                    image_url = ld_data['image']
                                elif isinstance(ld_data['image'], dict) and 'url' in ld_data['image']:
                                    image_url = ld_data['image']['url']
                                if image_url:
                                    logger.info(f"[4/8] Found JSON-LD image: {image_url}")
                    except Exception as e:
                        logger.warning(f"Error parsing JSON-LD: {str(e)}")
            
            # 5. Try to find first image in article body with size > 100px
            if not image_url and article_body:
                for img in article_body.find_all(['img', 'div', 'figure', 'picture']):
                    try:
                        # Try to get image URL from various attributes
                        src = None
                        for attr in ['src', 'data-src', 'data-lazy-src', 'data-original', 'data-image']:
                            if img.has_attr(attr):
                                src = img[attr].strip()
                                if src and not src.startswith('data:') and not src.endswith(('.svg', '.gif')):
                                    break
                        
                        if not src:
                            # Check for picture/source elements
                            source = img.find('source')
                            if source and source.has_attr('srcset'):
                                src = source['srcset'].split(',')[0].split(' ')[0].strip()
                        
                        if not src or not any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                            continue
                            
                        # Get image dimensions from attributes or style
                        width = int(img.get('width', 0) or 0)
                        height = int(img.get('height', 0) or 0)
                        
                        # Check image size from style if dimensions not in attributes
                        if width <= 1 or height <= 1:
                            style = img.get('style', '')
                            size_matches = re.findall(r'width[\s:]+(\d+)px', style + ' ' + (img.get('width', '') or ''))
                            if size_matches:
                                width = int(size_matches[0])
                            size_matches = re.findall(r'height[\s:]+(\d+)px', style + ' ' + (img.get('height', '') or ''))
                            if size_matches:
                                height = int(size_matches[0])
                        
                        # Skip if too small (unless we have no other choice)
                        if width > 0 and height > 0 and (width < 50 or height < 50):
                            continue
                            
                        # Skip if likely an icon/tracker (less strict now)
                        src_lower = src.lower()
                        if any(x in src_lower for x in ['icon', 'logo', 'pixel', 'spacer', '1x1', 'blank.gif', 'loading', 'placeholder', 'avatar']):
                            continue
                            
                        # Convert relative URLs
                        if src.startswith('/'):
                            parsed_uri = urllib.parse.urlparse(url)
                            base_url = f"{parsed_uri.scheme}://{parsed_uri.netloc}"
                            src = f"{base_url}{src}"
                        elif src.startswith('//'):
                            parsed_uri = urllib.parse.urlparse(url)
                            src = f"{parsed_uri.scheme}:{src}"
                            
                        image_url = src
                        logger.info(f"[5/8] Found suitable article image: {image_url} (Size: {width}x{height})")
                        break
                        
                    except Exception as img_e:
                        logger.warning(f"Error processing image tag: {str(img_e)}")
                        continue
            
            # 6. Try to find any image in the article body (less strict)
            if not image_url and article_body:
                for img in article_body.find_all('img', {'src': True}):
                    src = img.get('src', '').strip()
                    if src and not src.startswith('data:') and not any(x in src.lower() for x in ['icon', 'logo', 'pixel']):
                        image_url = src
                        logger.info(f"[6/8] Found any image in article: {image_url}")
                        break
            
            # 7. Try to find any image in the entire page as last resort
            if not image_url:
                for img in soup.find_all('img', {'src': True}):
                    src = img.get('src', '').strip()
                    if src and not src.startswith('data:') and not any(x in src.lower() for x in ['icon', 'logo', 'pixel']):
                        image_url = src
                        logger.info(f"[7/8] Found any image in page: {image_url}")
                        break
            
            # 8. Try background images in article body
            if not image_url and article_body:
                for element in article_body.find_all(style=re.compile(r'background[-image]*\s*:', re.I)):
                    style = element.get('style', '')
                    match = re.search(r'url\s*\(\s*["\']?(.*?)["\']?\s*\)', style, re.I)
                    if match:
                        bg_url = match.group(1).strip('"\'')
                        if bg_url and not bg_url.startswith('data:') and any(ext in bg_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                            image_url = bg_url
                            logger.info(f"[8/8] Found background image: {image_url}")
                            break
            
            # Clean and normalize the URL if found
            if image_url:
                # Remove query parameters and fragments
                image_url = image_url.split('?')[0].split('#')[0].strip()
                
                # Convert relative URLs to absolute
                if image_url.startswith('//'):
                    image_url = f'https:{image_url}'
                elif image_url.startswith('/'):
                    parsed_uri = urllib.parse.urlparse(url)
                    image_url = f"{parsed_uri.scheme}://{parsed_uri.netloc}{image_url}"
                elif not image_url.startswith(('http://', 'https://')):
                    # Handle relative URLs without leading slash
                    parsed_uri = urllib.parse.urlparse(url)
                    base_url = f"{parsed_uri.scheme}://{parsed_uri.netloc}"
                    path = parsed_uri.path.rsplit('/', 1)[0] if '/' in parsed_uri.path else ''
                    image_url = f"{base_url}{'/' if path and not path.endswith('/') else ''}{path}/{image_url}"
                
                logger.info(f"✅ Final image URL: {image_url}")
            else:
                logger.warning(f"❌ No image found for {url}")
                
                # Log potential image sources for debugging
                if article_body:
                    all_imgs = article_body.find_all('img', {'src': True})
                    logger.info(f"Found {len(all_imgs)} potential image(s) in article body")
                    for i, img in enumerate(all_imgs[:5], 1):
                        logger.info(f"  {i}. {img.get('src', '')}")
                        
                    # Also log any background images
                    bg_images = []
                    for el in article_body.find_all(style=re.compile(r'background[-image]*\s*:', re.I)):
                        style = el.get('style', '')
                        match = re.search(r'url\s*\(\s*["\']?(.*?)["\']?\s*\)', style, re.I)
                        if match:
                            bg_images.append(match.group(1).strip('"\''))
                    
                    if bg_images:
                        logger.info(f"Found {len(bg_images)} background images:")
                        for i, bg in enumerate(bg_images[:3], 1):
                            logger.info(f"  BG {i}. {bg}")
            
        except Exception as e:
            logger.error(f"❌ Error extracting image URL from {url}: {str(e)}", exc_info=True)
            image_url = None
        
        # Extract publish date with better parsing
        publish_date = None
        date_selectors = [
            {'selector': 'meta[property="article:published_time"]', 'attr': 'content'},
            {'selector': 'meta[property="og:published_time"]', 'attr': 'content'},
            {'selector': 'meta[name="pubdate"]', 'attr': 'content'},
            {'selector': 'meta[property="article:published"]', 'attr': 'content'},
            {'selector': 'time[datetime]', 'attr': 'datetime'},
            {'selector': 'time.published', 'attr': 'datetime'},
            {'selector': 'time.entry-date', 'attr': 'datetime'},
            {'selector': '.date-published', 'attr': 'text'},
            {'selector': '.date', 'attr': 'text'},
            {'selector': '.entry-date', 'attr': 'text'},
            {'selector': '.post-date', 'attr': 'text'},
            {'selector': '.publish-date', 'attr': 'text'}
        ]
        
        for selector in date_selectors:
            element = soup.select_one(selector['selector'])
            if element:
                date_str = element.get(selector['attr'])
                if date_str:
                    try:
                        # Clean up the date string
                        date_str = str(date_str).strip()
                        
                        # Try different date formats
                        date_formats = [
                            '%Y-%m-%dT%H:%M:%S%z',  # ISO format with timezone
                            '%Y-%m-%dT%H:%M:%S',    # ISO format without timezone
                            '%Y-%m-%d',             # Simple date format
                            '%d/%m/%Y',             # European date format
                            '%m/%d/%Y',             # US date format
                            '%B %d, %Y',            # Full month name
                            '%b %d, %Y',            # Abbreviated month
                            '%Y/%m/%d',             # Another common format
                            '%d-%m-%Y',             # Day first format
                            '%Y%m%d'                # Compact format
                        ]
                        
                        # Try parsing with each format
                        parsed_date = None
                        for fmt in date_formats:
                            try:
                                parsed_date = datetime.strptime(date_str, fmt)
                                break
                            except ValueError:
                                continue
                        
                        if parsed_date:
                            # Convert to YYYY-MM-DD format
                            publish_date = parsed_date.strftime('%Y-%m-%d')
                            logger.info(f"Parsed date: {date_str} -> {publish_date}")
                            break
                            
                    except Exception as e:
                        logger.warning(f"Error parsing date '{date_str}': {str(e)}")
                        continue
        
        return {
            'title': title,
            'content': text,
            'publish_date': publish_date or datetime.now().strftime('%Y-%m-%d'),
            'url': url,
            'source': urllib.parse.urlparse(url).netloc,
            'image_url': image_url
        }
        
    except Exception as e:
        logger.error(f"Failed to extract content from {url}: {str(e)}")
        return None

def create_name_pattern(name: str) -> Tuple[re.Pattern, List[str]]:
    """
    Create a strict regex pattern for exact name matching.
    Only matches the exact name or common variations with initials.
    """
    name = name.strip('"\'').strip()
    if not name:
        return None, []
    
    # Convert to lowercase for case-insensitive matching
    exact_phrase = name.lower()
    name_parts = [p for p in exact_phrase.split() if p.strip()]
    
    if not name_parts:
        return None, []
    
    # Only create patterns for the exact phrase and its variations
    # No partial name matching
    patterns = []
    
    # 1. Exact full name with word boundaries
    full_name = ' '.join(name_parts)
    patterns.append(r'(?<!\w)' + re.escape(full_name) + r'(?!\w)')
    
    # 2. Reversed name order (only for multi-word names)
    if len(name_parts) > 1:
        reversed_name = ' '.join(reversed(name_parts))
        patterns.append(r'(?<!\w)' + re.escape(reversed_name) + r'(?!\w)')
        
        # 3. First name + last initial (e.g., "Amine R.")
        first_last_initial = f"{name_parts[0]} {name_parts[-1][0]}."
        patterns.append(r'(?<!\w)' + re.escape(first_last_initial) + r'(?!\w)')
        
        # 4. First initial + last name (e.g., "A. Raghib")
        first_initial_last = f"{name_parts[0][0]}. {name_parts[-1]}"
        patterns.append(r'(?<!\w)' + re.escape(first_initial_last) + r'(?!\w)')
    
    # Combine all patterns with OR
    pattern = '(?i)(?:' + '|'.join(patterns) + ')'
    
    # For search terms, use the exact phrase and common variations
    search_terms = [' '.join(name_parts)]
    if len(name_parts) > 1:
        search_terms.extend([
            ' '.join(reversed(name_parts)),
            f"{name_parts[0]} {name_parts[-1][0]}.",
            f"{name_parts[0][0]}. {name_parts[-1]}"
        ])
    
    logger.info("\n=== NAME SEARCH PATTERNS ===")
    logger.info(f"Original name: {name}")
    logger.info(f"Search terms: {search_terms}")
    logger.info(f"Regex pattern: {pattern}")
    
    # Make sure we're not doing any partial matching
    logger.warning("Partial name matching is DISABLED. Only exact name matches will be returned.")
    
    try:
        return re.compile(pattern), search_terms
    except re.error as e:
        logger.error(f"Error compiling regex pattern: {e}")
        return None, search_terms

def search_rss_feeds(query: str, max_articles: int = 20) -> List[Dict[str, str]]:
    """Search for articles across all RSS feeds with exact name matching"""
    # Create name pattern and get search terms
    name_pattern, search_terms = create_name_pattern(query)
    logger.info(f"Search terms being used: {search_terms}")
    logger.info(f"Using name pattern: {name_pattern.pattern if name_pattern else 'None'}")
    
    articles = []
    processed_urls = set()
    
    # Check cache first
    cache_key = get_cache_key(query, "all_feeds")
    cached_results = load_from_cache(cache_key)
    if cached_results:
        logger.info(f"Using cached results for query: {query}")
        return cached_results[:max_articles]
    
    for feed_url in RSS_FEEDS:
        if len(articles) >= max_articles:
            break
            
        try:
            logger.info(f"Searching in feed: {feed_url}")
            feed = feedparser.parse(feed_url)
            
            # Sort entries by date (newest first) if available
            entries = feed.entries
            if hasattr(entries[0], 'published_parsed') and entries[0].published_parsed:
                entries.sort(key=lambda x: x.get('published_parsed') or (0, 0, 0, 0, 0, 0, 0, 0, 0), reverse=True)
            
            for entry in entries:
                if len(articles) >= max_articles:
                    break
                    
                try:
                    url = clean_url(entry.get('link', ''))
                    if not url or url in processed_urls:
                        continue
                        
                    # Get entry content for searching
                    title = entry.get('title', '').lower()
                    description = entry.get('description', '').lower()
                    content = ''
                    if hasattr(entry, 'content'):
                        content = ' '.join([c.get('value', '').lower() for c in entry.content if hasattr(c, 'value')])
                    
                    # Combine all text for searching (lowercase for case-insensitive matching)
                    search_text = f"{title} {description} {content}".lower()
                    
                    # Debug logging
                    logger.info(f"Searching for pattern in: {search_text[:200]}...")
                    
                    # Debug: Log the search text and pattern
                    logger.info(f"\n=== SEARCHING IN ARTICLE ===")
                    logger.info(f"Title: {title}")
                    logger.info(f"Pattern: {name_pattern.pattern}")
                    
                    # Skip this article if it doesn't match the name pattern
                    if not name_pattern or not name_pattern.search(search_text):
                        logger.info("❌ NO MATCH in this article")
                        continue
                        
                    # If we get here, we have a match
                    match = name_pattern.search(search_text)
                    logger.info(f"✅ MATCH FOUND: '{match.group(0)}' in text")
                    logger.info(f"   Context: ...{search_text[max(0, match.start()-30):match.end()+30]}...")
                    
                    # Initialize article data with basic info
                    entry_data = {
                        'title': title,
                        'url': url,
                        'published': published,
                        'content': content,
                        'source': feed_url,
                        'author': author if author else 'Unknown',
                        'sentiment': None,
                        'sentiment_score': None,
                        'summary': None,
                        'image_url': None
                    }
                    
                    # Set default publish date from entry if available
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            entry_data['published'] = datetime(*entry.published_parsed[:6]).strftime('%Y-%m-%d')
                        except Exception as e:
                            logger.warning(f"Error parsing publish date: {e}")
                    
                    # Try to extract full article content and image
                    try:
                        article_data = extract_article_content(url)
                        if article_data:
                            # Update entry data with extracted content and image
                            if article_data.get('content'):
                                entry_data['content'] = article_data['content']
                            if article_data.get('image_url'):
                                entry_data['image_url'] = article_data['image_url']
                            if article_data.get('publish_date') and not entry_data.get('published'):
                                entry_data['published'] = article_data['publish_date']
                    except Exception as e:
                        logger.warning(f"Error extracting article content from {url}: {e}")
                    
                    # Ensure we have at least the basic content
                    if not entry_data.get('content'):
                        entry_data['content'] = f"No content available. Please visit the source: {url}"
                    
                    # Add the entry data to articles list
                    articles.append(entry_data)
                    processed_urls.add(url)
                    logger.info(f"Found article: {title} - Image: {'Yes' if entry_data.get('image_url') else 'No'}")
                        
                except Exception as e:
                    logger.error(f"Error processing entry: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error processing feed {feed_url}: {str(e)}")
            continue
    
    return articles

def get_news_about(query: str, max_articles: int = 50, start_date: str = None, end_date: str = None) -> List[Dict[str, str]]:
    """
    Get news articles about a person or company with date range filtering
    
    Args:
        query: Name of the person or company to search for
        max_articles: Maximum number of articles to return
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
        
    Returns:
        List of article dictionaries with title, content, url, publish_date, and source
    """
    logger.info(f"Searching for news about: {query}")
    if start_date and end_date:
        logger.info(f"Date range: {start_date} to {end_date}")
    
    # Generate cache key based on query and date range
    date_range = f"{start_date or ''}_{end_date or ''}"
    cache_key = get_cache_key(f"{query}_{date_range}", "news_about")
    
    # Try to load from cache first
    cached_results = load_from_cache(cache_key)
    if cached_results:
        logger.info(f"Using cached results for query: {query} (date range: {date_range})")
        return cached_results[:max_articles]
    
    all_articles = []
    
    # 1. First try to get articles from RSS feeds
    logger.info("Searching RSS feeds...")
    rss_articles = search_rss_feeds(query, max_articles * 2)  # Get more to account for date filtering
    all_articles.extend(rss_articles)
    
    # 2. Try to fetch from NewsAPI if available
    try:
        from news_fetcher import fetch_news as fetch_news_api
        logger.info("Trying NewsAPI...")
        api_articles = fetch_news_api(query, max_articles)
        
        # Convert the format to match our structure
        for article in api_articles:
            all_articles.append({
                'title': article['title'],
                'content': article['content'],
                'url': article['url'],
                'publish_date': article['publish_date'],
                'source': urllib.parse.urlparse(article['url']).netloc
            })
    except Exception as e:
        logger.warning(f"Error fetching from NewsAPI: {str(e)}")
    
    # 3. Remove duplicates based on URL
    seen_urls = set()
    unique_articles = []
    
    for article in all_articles:
        if article['url'] not in seen_urls:
            seen_urls.add(article['url'])
            
            # Convert publish_date to datetime for comparison if it exists
            article_date = None
            if article.get('publish_date'):
                try:
                    article_date = datetime.strptime(article['publish_date'].split('T')[0], '%Y-%m-%d')
                except (ValueError, AttributeError):
                    pass
            
            # Apply date filtering if dates are provided
            include_article = True
            if start_date and article_date:
                if article_date < datetime.strptime(start_date, '%Y-%m-%d'):
                    include_article = False
            if end_date and article_date:
                if article_date > datetime.strptime(end_date, '%Y-%m-%d'):
                    include_article = False
            
            if include_article:
                unique_articles.append(article)
    
    # Sort by date (newest first)
    unique_articles.sort(
        key=lambda x: (
            datetime.strptime(x.get('publish_date', '1970-01-01').split('T')[0], '%Y-%m-%d') 
            if x.get('publish_date') 
            else datetime.min
        ),
        reverse=True
    )
    
    # Cache the results if we have any
    if unique_articles:
        try:
            save_to_cache(cache_key, unique_articles)
        except Exception as e:
            logger.warning(f"Error saving to cache: {e}")
    
    # Return the requested number of articles
    return unique_articles[:max_articles]

if __name__ == "__main__":
    # Example usage
    name = input("Enter a person or company name: ")
    print(f"\nSearching for news about: {name}\n")
    
    start_time = time.time()
    articles = get_news_about(name, max_articles=10)
    
    print(f"\nFound {len(articles)} articles in {time.time() - start_time:.2f} seconds\n")
    
    for i, article in enumerate(articles, 1):
        print(f"{i}. {article['title']}")
        print(f"   URL: {article['url']}")
        print(f"   Date: {article.get('publish_date', 'Unknown date')}")
        print(f"   Source: {article.get('source', 'Unknown')}")
        print(f"   Content: {article['content'][:150]}...\n")
