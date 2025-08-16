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
from pymongo import MongoClient
from datetime import datetime, timedelta
import os

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

# Database connection
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
client = MongoClient(MONGODB_URI)
db = client['news_scraper_db']
rss_feeds_collection = db['rss_feeds']

def get_active_rss_feeds():
    """Fetch active RSS feeds from the database"""
    try:
        feeds = list(rss_feeds_collection.find(
            {"is_active": True},
            {"url": 1, "name": 1, "category": 1, "_id": 0}
        ))
        return [feed['url'] for feed in feeds if 'url' in feed]
    except Exception as e:
        logger.error(f"Error fetching RSS feeds from database: {e}")
        # Fallback to default feeds if database is not available
        return [
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

def validate_image_url(url: str) -> bool:
    """Validate if URL is likely to be a valid image"""
    if not url or not isinstance(url, str):
        return False
    
    url = url.strip().lower()
    
    # Skip data URLs, JavaScript, and common non-image patterns
    if any(pattern in url for pattern in ['data:', 'javascript:', 'mailto:', 'tel:']):
        return False
    
    # Skip common non-image files
    if any(pattern in url for pattern in ['.pdf', '.doc', '.txt', '.xml', '.json']):
        return False
    
    # Skip very small tracking pixels and ads
    if any(pattern in url for pattern in ['1x1', 'pixel', 'tracker', 'beacon', 'blank.gif']):
        return False
    
    # Skip common icon/logo patterns (but allow some flexibility)
    if any(pattern in url for pattern in ['favicon', 'apple-touch-icon']):
        return False
    
    # Prefer images with explicit image extensions
    image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff']
    if any(ext in url for ext in image_extensions):
        return True
    
    # Allow URLs that contain image-related keywords
    if any(keyword in url for keyword in ['image', 'img', 'photo', 'picture', 'media']):
        return True
    
    # If no extension but starts with http/https, it might be a valid image URL
    return url.startswith(('http://', 'https://'))

def extract_image_from_rss(entry) -> Optional[str]:
    """Extract image URL from RSS entry data with improved validation and logging"""
    # List of potential image sources to check, in order of preference
    image_sources = [
        # 1. Media content (highest priority)
        {
            'name': 'media_content',
            'check': lambda: hasattr(entry, 'media_content') and entry.media_content,
            'extract': lambda: [
                media.get('url', '').strip() 
                for media in entry.media_content 
                if media.get('type', '').startswith(('image/', 'application/'))
            ]
        },
        # 2. Media thumbnail
        {
            'name': 'media_thumbnail',
            'check': lambda: hasattr(entry, 'media_thumbnail') and entry.media_thumbnail,
            'extract': lambda: [
                thumb.get('url', '').strip() 
                for thumb in entry.media_thumbnail
            ]
        },
        # 3. Enclosures
        {
            'name': 'enclosures',
            'check': lambda: hasattr(entry, 'enclosures') and entry.enclosures,
            'extract': lambda: [
                enc.get('href', '').strip() 
                for enc in entry.enclosures 
                if enc.get('type', '').startswith(('image/', 'application/'))
            ]
        },
        # 4. Content fields with HTML images
        {
            'name': 'html_content',
            'check': lambda: True,  # Always check content fields
            'extract': lambda: [
                img.get('src', '').strip()
                for field in ['description', 'summary', 'content']
                if hasattr(entry, field)
                for content in [getattr(entry, field)]
                if content
                for html in [
                    content[0].get('value', '') 
                    if isinstance(content, list) and content and isinstance(content[0], dict) 
                    else str(content)
                ]
                for img in BeautifulSoup(html, 'html.parser').find_all('img')
                if img.get('src')
            ]
        },
        # 5. Common image URL patterns in the entry
        {
            'name': 'common_image_fields',
            'check': lambda: True,
            'extract': lambda: [
                entry[field].strip()
                for field in ['image', 'image_url', 'thumbnail']
                if hasattr(entry, field) and entry[field]
            ]
        }
    ]
    
    # Check each potential image source
    for source in image_sources:
        try:
            if source['check']():
                for img_url in source['extract']():
                    if img_url and validate_image_url(img_url):
                        logger.info(f"✅ Found image from {source['name']}: {img_url}")
                        return img_url
        except Exception as e:
            logger.debug(f"Error checking {source['name']} for images: {e}")
            continue
    
    logger.debug("No valid image found in RSS entry")
    return None

def extract_article_content(url: str) -> Optional[Dict[str, str]]:
    """Extract article content and first image using BeautifulSoup with improved image extraction"""
    try:
        logger.info(f"\n{'='*80}\nProcessing URL: {url}\n{'='*80}")
        
        # Use requests with session and timeout
        session = requests.Session()
        session.headers.update(HEADERS)
        response = session.get(url, timeout=15)
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
                logger.info(f"Found content using text density analysis (density: {candidates[0][0]:.2f})")
        
        # Strategy 3: Fall back to body if nothing else works
        if not article_body:
            logger.warning("Falling back to body tag for content")
            article_body = soup.body
            
        if not article_body:
            logger.error("Could not find main content area")
            return None
            
        # Clean up the text
        text = article_body.get_text(separator='\n', strip=True)
        text = '\n'.join(line for line in text.split('\n') if line.strip())
        
        # Extract title
        title = clean_text(soup.title.string if soup.title else "")
        
        # IMPROVED IMAGE EXTRACTION
        image_url = None
        logger.info(f"Starting image extraction for: {url}")
        
        try:
            # Priority 1: Open Graph image (most reliable)
            for prop in ['og:image', 'og:image:url', 'og:image:secure_url']:
                og_meta = soup.find('meta', property=prop) or soup.find('meta', {'name': prop})
                if og_meta and og_meta.get('content'):
                    candidate_url = og_meta.get('content', '').strip()
                    if validate_image_url(candidate_url):
                        image_url = candidate_url
                        logger.info(f"✅ Found OG image ({prop}): {image_url}")
                        break
            
            # Priority 2: Twitter Card image
            if not image_url:
                for name in ['twitter:image', 'twitter:image:src']:
                    twitter_meta = soup.find('meta', {'name': name})
                    if twitter_meta and twitter_meta.get('content'):
                        candidate_url = twitter_meta.get('content', '').strip()
                        if validate_image_url(candidate_url):
                            image_url = candidate_url
                            logger.info(f"✅ Found Twitter image ({name}): {image_url}")
                            break
            
            # Priority 3: Article meta tags
            if not image_url:
                for prop in ['article:image', 'article:image:url']:
                    article_meta = soup.find('meta', {'property': prop})
                    if article_meta and article_meta.get('content'):
                        candidate_url = article_meta.get('content', '').strip()
                        if validate_image_url(candidate_url):
                            image_url = candidate_url
                            logger.info(f"✅ Found article meta image ({prop}): {image_url}")
                            break
            
            # Priority 4: JSON-LD structured data
            if not image_url:
                json_scripts = soup.find_all('script', type='application/ld+json')
                for script in json_scripts:
                    try:
                        ld_data = json.loads(script.string)
                        if isinstance(ld_data, list):
                            ld_data = ld_data[0] if ld_data else {}
                        
                        if isinstance(ld_data, dict) and 'image' in ld_data:
                            image_data = ld_data['image']
                            candidate_url = None
                            
                            if isinstance(image_data, str):
                                candidate_url = image_data
                            elif isinstance(image_data, dict):
                                candidate_url = image_data.get('url') or image_data.get('@url')
                            elif isinstance(image_data, list) and image_data:
                                first_image = image_data[0]
                                if isinstance(first_image, str):
                                    candidate_url = first_image
                                elif isinstance(first_image, dict):
                                    candidate_url = first_image.get('url') or first_image.get('@url')
                            
                            if candidate_url and validate_image_url(candidate_url):
                                image_url = candidate_url
                                logger.info(f"✅ Found JSON-LD image: {image_url}")
                                break
                    except (json.JSONDecodeError, KeyError, TypeError) as e:
                        logger.debug(f"Error parsing JSON-LD: {e}")
                        continue
            
            # Priority 5: Featured image in article content
            if not image_url and article_body:
                # Look for images with specific classes that indicate featured/main images
                featured_selectors = [
                    'img.wp-post-image',
                    'img.attachment-post-thumbnail', 
                    'img.featured-image',
                    'img.article-image',
                    'img.hero-image',
                    'img.lead-image',
                    'img.main-image',
                    '.featured-image img',
                    '.article-featured-image img',
                    '.post-thumbnail img',
                    '.entry-thumbnail img',
                    'figure.wp-block-image img',
                    '.article-hero img'
                ]
                
                for selector in featured_selectors:
                    img = article_body.select_one(selector)
                    if img:
                        for attr in ['src', 'data-src', 'data-lazy-src', 'data-original']:
                            candidate_url = img.get(attr, '').strip()
                            if candidate_url and validate_image_url(candidate_url):
                                image_url = candidate_url
                                logger.info(f"✅ Found featured image with selector {selector}: {image_url}")
                                break
                        if image_url:
                            break
            
            # Priority 6: First large image in article content
            if not image_url and article_body:
                for img in article_body.find_all('img'):
                    # Try different src attributes
                    for attr in ['src', 'data-src', 'data-lazy-src', 'data-original', 'data-srcset']:
                        candidate_url = img.get(attr, '').strip()
                        if not candidate_url:
                            continue
                        
                        # Handle srcset - take the first URL
                        if attr == 'data-srcset' or attr == 'srcset':
                            srcset_parts = candidate_url.split(',')
                            if srcset_parts:
                                candidate_url = srcset_parts[0].split()[0].strip()
                        
                        if not validate_image_url(candidate_url):
                            continue
                        
                        # Check image dimensions to prefer larger images
                        width = img.get('width')
                        height = img.get('height')
                        
                        # Convert width/height to int if possible
                        try:
                            width = int(width) if width else 0
                            height = int(height) if height else 0
                        except (ValueError, TypeError):
                            width = height = 0
                        
                        # Skip very small images (likely icons/thumbnails)
                        if width > 0 and height > 0 and (width < 100 or height < 100):
                            continue
                        
                        # Skip images with suspicious names
                        url_lower = candidate_url.lower()
                        if any(skip in url_lower for skip in ['logo', 'icon', 'avatar', 'thumbnail', 'thumb']):
                            continue
                        
                        image_url = candidate_url
                        logger.info(f"✅ Found suitable article image: {image_url} (Size: {width}x{height})")
                        break
                    
                    if image_url:
                        break
            
            # Priority 7: Any reasonable image as fallback
            if not image_url:
                all_imgs = soup.find_all('img', src=True)
                for img in all_imgs:
                    candidate_url = img.get('src', '').strip()
                    if validate_image_url(candidate_url):
                        # Skip very obvious non-content images
                        if any(skip in candidate_url.lower() for skip in ['logo', 'favicon', 'icon', 'banner', 'ad']):
                            continue
                        image_url = candidate_url
                        logger.info(f"✅ Found fallback image: {image_url}")
                        break
            
            # Clean and normalize the final image URL
            if image_url:
                # Handle relative URLs
                if image_url.startswith('//'):
                    image_url = f'https:{image_url}'
                elif image_url.startswith('/'):
                    parsed_uri = urllib.parse.urlparse(url)
                    image_url = f"{parsed_uri.scheme}://{parsed_uri.netloc}{image_url}"
                elif not image_url.startswith(('http://', 'https://')):
                    # Handle relative paths
                    parsed_uri = urllib.parse.urlparse(url)
                    base_url = f"{parsed_uri.scheme}://{parsed_uri.netloc}"
                    path_parts = parsed_uri.path.rsplit('/', 1)
                    if len(path_parts) > 1:
                        base_path = path_parts[0]
                        image_url = f"{base_url}{base_path}/{image_url}"
                    else:
                        image_url = f"{base_url}/{image_url}"
                
                # Remove query parameters and fragments that might break image loading
                image_url = image_url.split('?')[0].split('#')[0]
                
                logger.info(f"🎯 Final processed image URL: {image_url}")
            else:
                logger.warning(f"❌ No suitable image found for: {url}")
        
        except Exception as e:
            logger.error(f"❌ Error during image extraction: {str(e)}")
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
        
        for selector_info in date_selectors:
            element = soup.select_one(selector_info['selector'])
            if element:
                if selector_info['attr'] == 'text':
                    date_str = element.get_text(strip=True)
                else:
                    date_str = element.get(selector_info['attr'])
                
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
    
    try:
        return re.compile(pattern), search_terms
    except re.error as e:
        logger.error(f"Error compiling regex pattern: {e}")
        return None, search_terms

def search_rss_feeds(query: str, max_articles: int = 20) -> List[Dict[str, str]]:
    """Search for articles across all active RSS feeds with exact name matching"""
    # Create name pattern and get search terms
    name_pattern, search_terms = create_name_pattern(query)
    
    if not name_pattern:
        return []
        
    articles = []
    processed_urls = set()
    
    # Check cache first
    cache_key = hashlib.md5(f"rss_search_{query}".encode()).hexdigest()
    if cached_results := load_from_cache(cache_key):
        logger.info(f"Using cached results for query: {query}")
        return cached_results[:max_articles]
    
    # Get active RSS feeds from database
    active_feeds = get_active_rss_feeds()
    logger.info(f"Found {len(active_feeds)} active RSS feeds to search")
    
    for feed_url in active_feeds:
        if len(articles) >= max_articles:
            break
            
        try:
            logger.info(f"Searching in feed: {feed_url}")
            feed = feedparser.parse(feed_url, request_headers=HEADERS, agent=USER_AGENT)
            if hasattr(feed, 'bozo_exception'):
                logger.warning(f"Error parsing feed {feed_url}: {feed.bozo_exception}")
                continue
                
            # Update last_checked timestamp in database
            try:
                rss_feeds_collection.update_one(
                    {"url": feed_url},
                    {"$set": {"last_checked": datetime.utcnow()}},
                    upsert=False
                )
            except Exception as e:
                logger.warning(f"Could not update last_checked for {feed_url}: {e}")
            
            entries = feed.entries[:20]  # Limit entries to process per feed
            
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
                    
                    # Skip this article if it doesn't match the name pattern
                    if not name_pattern or not name_pattern.search(search_text):
                        continue
                        
                    # If we get here, we have a match
                    match = name_pattern.search(search_text)
                    logger.info(f"✅ MATCH FOUND: '{match.group(0)}' in {entry.get('title', 'Untitled')}")
                    
                    try:
                        # Initialize article data with basic info
                        entry_data = {
                            'title': clean_text(entry.get('title', '')),
                            'url': url,
                            'publish_date': '',
                            'content': clean_text(entry.get('description', '')),
                            'source': clean_text(feed.get('feed', {}).get('title', urllib.parse.urlparse(feed_url).netloc)),
                            'author': clean_text(entry.get('author', 'Unknown')),
                            'image_url': None
                        }
                        
                        # Try to extract image from RSS entry first
                        rss_image = extract_image_from_rss(entry)
                        if rss_image:
                            entry_data['image_url'] = clean_url(rss_image)
                            logger.info(f"📸 Found RSS image: {entry_data['image_url']}")
                        
                        # Set publish date from entry if available
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            try:
                                entry_data['publish_date'] = datetime(*entry.published_parsed[:6]).strftime('%Y-%m-%d')
                            except Exception as e:
                                logger.warning(f"Error parsing publish date: {e}")
                        
                        # If no date from published_parsed, try other date fields
                        if not entry_data['publish_date']:
                            for date_field in ['updated', 'published', 'pubDate', 'dc:date']:
                                if hasattr(entry, date_field):
                                    entry_data['publish_date'] = clean_text(str(getattr(entry, date_field)))
                                    break
                        
                        # Try to extract full article content and image if we don't have enough content
                        if len(entry_data['content']) < 200:  # If content is too short
                            try:
                                article_data = extract_article_content(url)
                                if article_data:
                                    # Update entry data with extracted content
                                    if article_data.get('content'):
                                        entry_data['content'] = clean_text(article_data['content'])
                                    
                                    # Use extracted image if we don't have one from RSS
                                    if article_data.get('image_url') and not entry_data.get('image_url'):
                                        entry_data['image_url'] = clean_url(article_data['image_url'])
                                        logger.info(f"📸 Added extracted image: {entry_data['image_url']}")
                                    
                                    # Update publish date if we don't have one
                                    if article_data.get('publish_date') and not entry_data.get('publish_date'):
                                        entry_data['publish_date'] = article_data['publish_date']
                            except Exception as e:
                                logger.warning(f"Error extracting article content from {url}: {e}")
                        
                        # Ensure we have some content
                        if not entry_data.get('content'):
                            entry_data['content'] = clean_text(entry.get('description', f"No content available. Please visit the source: {url}"))
                        
                        # Clean up the image URL if it exists
                        if entry_data.get('image_url'):
                            entry_data['image_url'] = clean_url(entry_data['image_url'])
                            
                            # Convert relative URLs to absolute
                            if entry_data['image_url'].startswith('//'):
                                entry_data['image_url'] = f'https:{entry_data["image_url"]}'
                            elif entry_data['image_url'].startswith('/'):
                                parsed_uri = urllib.parse.urlparse(url)
                                entry_data['image_url'] = f"{parsed_uri.scheme}://{parsed_uri.netloc}{entry_data['image_url']}"
                        
                        # Add the entry data to articles list
                        articles.append(entry_data)
                        processed_urls.add(url)
                        
                        logger.info(f"✅ Added article: {entry_data.get('title')} - Image: {entry_data.get('image_url', 'No image')}")
                        
                    except Exception as e:
                        logger.error(f"Error processing article {url}: {e}", exc_info=True)
                        
                except Exception as e:
                    logger.error(f"Error processing entry: {e}")
                    continue
                    
        except Exception as e:
            logger.warning(f"Error processing feed {feed_url}: {e}")
            # Update error status in database
            try:
                rss_feeds_collection.update_one(
                    {"url": feed_url},
                    {"$set": {"last_error": str(e), "last_checked": datetime.utcnow()}},
                    upsert=False
                )
            except Exception as db_error:
                logger.warning(f"Could not update error status for {feed_url}: {db_error}")
            continue
    
    # Cache the results
    if articles:
        save_to_cache(cache_key, articles)
    
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
        List of article dictionaries with title, content, url, publish_date, image_url, and source
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
    
    # Search RSS feeds
    logger.info("Searching RSS feeds...")
    rss_articles = search_rss_feeds(query, max_articles * 2)  # Get more to account for date filtering
    all_articles.extend(rss_articles)
    
    # Try to fetch from NewsAPI if available
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
                'source': urllib.parse.urlparse(article['url']).netloc,
                'image_url': article.get('image_url')
            })
    except Exception as e:
        logger.warning(f"Error fetching from NewsAPI: {str(e)}")
    
    # Remove duplicates based on URL
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
        print(f"   Image: {article.get('image_url', 'No image')}")
        print(f"   Content: {article['content'][:150]}...\n")