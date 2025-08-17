import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
from typing import Optional, List, Dict, Any
import feedparser
from datetime import datetime, timedelta
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class EnhancedImageExtractor:
    """
    Enhanced image extractor that handles both RSS feeds and direct article URLs
    with multiple fallback strategies for finding the best image.
    """
    
    def __init__(self):
        self.session = self._create_session()
        self.timeout = 15
    
    def _create_session(self):
        """Create a requests session with proper headers and retry logic."""
        session = requests.Session()
        
        # Common headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1',
            'Referer': 'https://www.google.com/'
        }
        
        session.headers.update(headers)
        return session
    
    def extract_image(self, url: str, is_rss_feed: bool = False) -> Optional[str]:
        """
        Extract the best image from a given URL or RSS feed.
        
        Args:
            url: The URL to extract image from (article URL or RSS feed)
            is_rss_feed: Whether the URL is an RSS feed
            
        Returns:
            Optional[str]: The URL of the extracted image, or None if not found
        """
        if is_rss_feed:
            return self._extract_image_from_rss_feed(url)
        else:
            return self._extract_image_from_article(url)
    
    def _extract_image_from_rss_feed(self, feed_url: str) -> Optional[str]:
        """Extract an image from an RSS feed."""
        try:
            # Parse the feed
            feed = feedparser.parse(feed_url)
            
            if hasattr(feed, 'bozo_exception'):
                logger.error(f"Error parsing feed: {feed.bozo_exception}")
                return None
            
            # Try to get image from feed metadata
            if hasattr(feed.feed, 'image') and hasattr(feed.feed.image, 'href'):
                return feed.feed.image.href
                
            # Try to get image from first entry
            if feed.entries:
                entry = feed.entries[0]
                
                # Check for media content
                if hasattr(entry, 'media_content'):
                    for media in entry.media_content:
                        if hasattr(media, 'get') and media.get('type', '').startswith('image/'):
                            return media.get('url')
                
                # Check for media thumbnails
                if hasattr(entry, 'media_thumbnail'):
                    thumbs = entry.media_thumbnail if isinstance(entry.media_thumbnail, list) else [entry.media_thumbnail]
                    for thumb in thumbs:
                        if hasattr(thumb, 'get') and thumb.get('url'):
                            return thumb.get('url')
                
                # Check for enclosures
                if hasattr(entry, 'enclosures'):
                    for enc in entry.enclosures:
                        if hasattr(enc, 'get') and enc.get('type', '').startswith('image/'):
                            return enc.get('href')
                
                # If no image found in RSS entry, try to fetch from article
                if hasattr(entry, 'link'):
                    return self._extract_image_from_article(entry.link)
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting image from RSS feed {feed_url}: {e}")
            return None
    
    def _extract_image_from_article(self, url: str) -> Optional[str]:
        """Extract the best image from an article URL."""
        try:
            # Fetch the page
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to get Open Graph image
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                return self._make_absolute_url(og_image['content'], url)
            
            # Try to get Twitter card image
            twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
            if twitter_image and twitter_image.get('content'):
                return self._make_absolute_url(twitter_image['content'], url)
            
            # Try common image selectors
            selectors = [
                'meta[property="og:image"]',
                'meta[name="twitter:image"]',
                'img[class*="hero"]',
                'img[class*="featured"]',
                'img[class*="article"]',
                'img[class*="main"]',
                'img[class*="lead"]',
                'img[itemprop="image"]',
                'picture source',
                'img'
            ]
            
            for selector in selectors:
                try:
                    elements = soup.select(selector)
                    for element in elements:
                        src = None
                        if element.name == 'meta':
                            src = element.get('content', '')
                        elif element.name == 'img':
                            src = element.get('src', '')
                        elif element.name == 'source':
                            src = element.get('srcset', '').split(',')[0].split()[0] if element.get('srcset') else ''
                        
                        if src and self._is_valid_image_url(src):
                            absolute_url = self._make_absolute_url(src, url)
                            if self._is_image_accessible(absolute_url):
                                return absolute_url
                except Exception as e:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting image from article {url}: {e}")
            return None
    
    def _make_absolute_url(self, url: str, base_url: str) -> str:
        """Convert a relative URL to an absolute URL."""
        if not url:
            return ''
            
        # Already absolute
        if url.startswith(('http://', 'https://')):
            return url
            
        # Protocol-relative URL
        if url.startswith('//'):
            return f'https:{url}'
            
        # Root-relative URL
        if url.startswith('/'):
            parsed = urlparse(base_url)
            return f"{parsed.scheme}://{parsed.netloc}{url}"
            
        # Relative URL
        return urljoin(base_url, url)
    
    def _is_valid_image_url(self, url: str) -> bool:
        """Check if a URL looks like a valid image URL."""
        if not url or not isinstance(url, str):
            return False
            
        url = url.lower()
        
        # Skip data URIs and empty URLs
        if not url or url.startswith('data:image'):
            return False
        
        # Check for common image extensions
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
        if any(url.endswith(ext) for ext in image_extensions):
            return True
        
        # Check for image-related URL patterns
        image_indicators = ['/image', '/img', '/photo', '/pic', '/media', '/upload', 'image=', 'img=']
        if any(indicator in url for indicator in image_indicators):
            return True
            
        return False
    
    def _is_image_accessible(self, url: str) -> bool:
        """Check if an image URL is accessible."""
        if not url:
            return False
            
        try:
            # First try HEAD request
            response = self.session.head(url, timeout=10, allow_redirects=True)
            if response.status_code == 200 and 'image/' in response.headers.get('content-type', ''):
                return True
                
            # If HEAD fails, try GET with stream to only download headers
            response = self.session.get(url, stream=True, timeout=10)
            if response.status_code == 200 and 'image/' in response.headers.get('content-type', ''):
                return True
                
            return False
            
        except Exception as e:
            logger.debug(f"Error checking image accessibility for {url}: {e}")
            return False

def test_extractor():
    """Test the EnhancedImageExtractor with example URLs."""
    extractor = EnhancedImageExtractor()
    
    # Test with RSS feed
    rss_url = "http://feeds.bbci.co.uk/news/rss.xml"
    print(f"\nTesting RSS feed: {rss_url}")
    image_url = extractor.extract_image(rss_url, is_rss_feed=True)
    print(f"Extracted image: {image_url}")
    
    # Test with article URL
    article_url = "https://www.bbc.com/news/world-us-canada-68903712"
    print(f"\nTesting article: {article_url}")
    image_url = extractor.extract_image(article_url, is_rss_feed=False)
    print(f"Extracted image: {image_url}")

if __name__ == "__main__":
    test_extractor()
