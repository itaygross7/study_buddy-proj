"""
Capybara Image Fetcher - Fetches random funny capybara photos from Unsplash API
with proper caching and fallback mechanisms.
"""
import os
import json
import time
from typing import Optional, Dict
from datetime import datetime, timedelta
import requests

from sb_utils.logger_utils import logger


class CapybaraImageFetcher:
    """
    Fetches random capybara images from Unsplash API with intelligent caching.
    Falls back to local images if API is unavailable.
    """
    
    def __init__(self):
        self.api_key = os.getenv('UNSPLASH_ACCESS_KEY', '')
        self.cache_file = '/tmp/capybara_image_cache.json'
        self.cache_duration_hours = 24  # Cache images for 24 hours
        self.api_base_url = 'https://api.unsplash.com'
    
    def _load_cache(self) -> Optional[Dict]:
        """Load cached images from file."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                    
                # Check if cache is still valid
                cached_time = datetime.fromisoformat(cache.get('timestamp', '2000-01-01'))
                if datetime.now() - cached_time < timedelta(hours=self.cache_duration_hours):
                    logger.info(f"Using cached capybara images (age: {datetime.now() - cached_time})")
                    return cache
                else:
                    logger.info("Cache expired, will fetch new images")
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
        
        return None
    
    def _save_cache(self, cache_data: Dict) -> None:
        """Save images to cache file."""
        try:
            cache_data['timestamp'] = datetime.now().isoformat()
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f)
            logger.info("Capybara images cached successfully")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def _fetch_from_unsplash(self, count: int = 12) -> Optional[list]:
        """
        Fetch random capybara photos from Unsplash API.
        
        Args:
            count: Number of images to fetch (default 12 for family members)
            
        Returns:
            List of image URLs or None if fetch fails
        """
        if not self.api_key or self.api_key == 'your_unsplash_access_key':
            logger.warning("Unsplash API key not configured, using fallback images")
            return None
        
        try:
            # Search for capybara photos
            url = f"{self.api_base_url}/search/photos"
            params = {
                'query': 'capybara',
                'per_page': min(count, 30),  # Max 30 per request
                'order_by': 'popular',
                'content_filter': 'high'  # Family-friendly content
            }
            headers = {
                'Authorization': f'Client-ID {self.api_key}'
            }
            
            logger.info(f"Fetching {count} capybara images from Unsplash...")
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                if not results:
                    logger.warning("No capybara images found on Unsplash")
                    return None
                
                # Extract image URLs (using 'regular' size - good balance)
                images = []
                for photo in results:
                    images.append({
                        'url': photo['urls']['regular'],
                        'photographer': photo['user']['name'],
                        'photographer_url': photo['user']['links']['html'],
                        'photo_url': photo['links']['html']
                    })
                
                logger.info(f"Successfully fetched {len(images)} capybara images")
                return images
                
            elif response.status_code == 401:
                logger.error("Unsplash API authentication failed - check your access key")
            elif response.status_code == 403:
                logger.error("Unsplash API rate limit exceeded")
            else:
                logger.error(f"Unsplash API error: {response.status_code}")
            
            return None
            
        except requests.exceptions.Timeout:
            logger.error("Unsplash API request timed out")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch from Unsplash: {e}", exc_info=True)
            return None
    
    def get_capybara_images(self, count: int = 12, force_refresh: bool = False) -> Optional[list]:
        """
        Get capybara images with intelligent caching.
        Returns None if API is not available or fails.
        
        Args:
            count: Number of images needed
            force_refresh: Force refresh from API even if cache exists
            
        Returns:
            List of image data (URLs for Unsplash) or None if unavailable
        """
        # Try cache first (unless force refresh)
        if not force_refresh:
            cache = self._load_cache()
            if cache and 'images' in cache:
                images = cache['images']
                if len(images) >= count:
                    return images[:count]
        
        # Try fetching from Unsplash
        unsplash_images = self._fetch_from_unsplash(count)
        
        if unsplash_images:
            # Cache the results
            self._save_cache({'images': unsplash_images})
            return unsplash_images
        
        # Return None if API is unavailable - don't show the section
        logger.warning("Capybara images unavailable - Meet the Family section will be hidden")
        return None
    
    def get_image_for_day(self, day_of_year: int) -> Optional[Dict]:
        """
        Get a specific capybara image for the day.
        Returns None if images are unavailable.
        
        Args:
            day_of_year: Day of year (1-366) for deterministic selection
            
        Returns:
            Image data dict with URL and attribution, or None
        """
        images = self.get_capybara_images()
        
        if not images:
            return None
        
        # Select image deterministically based on day
        index = day_of_year % len(images)
        return images[index]


# Global instance
_fetcher = None


def get_fetcher() -> CapybaraImageFetcher:
    """Get or create global fetcher instance."""
    global _fetcher
    if _fetcher is None:
        _fetcher = CapybaraImageFetcher()
    return _fetcher
