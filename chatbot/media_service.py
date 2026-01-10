# media_service.py - FREE Media Search Service
# 🚨 FIXED: STRICT 3-VIDEO MAXIMUM ENFORCEMENT
import os
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()


class MediaService:
    """
    Free media search service for YouTube videos and images
    🚨 ENFORCES STRICT MAXIMUM OF 3 RESULTS
    - YouTube Data API v3 (10,000 requests/day)
    - Pexels API (unlimited requests)
    """
    
    # 🚨 HARD LIMIT: Absolute maximum results
    MAX_RESULTS = 3
    
    def __init__(self):
        self.youtube_key = os.getenv('YOUTUBE_API_KEY', '')
        self.pexels_key = os.getenv('PEXELS_API_KEY', '')
        
        if not self.youtube_key:
            print("⚠️ YOUTUBE_API_KEY not found in .env")
        if not self.pexels_key:
            print("⚠️ PEXELS_API_KEY not found in .env")
    
    # ========================================================================
    # YOUTUBE VIDEO SEARCH - WITH STRICT 3-VIDEO LIMIT
    # ========================================================================
    
    def search_youtube_videos(
        self, 
        query: str, 
        max_results: int = 3,
        safe_search: str = 'moderate'
    ) -> List[Dict]:
        """
        Search YouTube for videos
        
        🚨 STRICT LIMIT: Maximum 3 results, even if requested more
        
        Args:
            query: Search query (e.g., "healthy relationships advice")
            max_results: Number of videos to return (will be capped at 3)
            safe_search: 'none', 'moderate', or 'strict'
        
        Returns:
            List of video dictionaries (max 3)
        """
        if not self.youtube_key:
            print("❌ YouTube API key not configured")
            return []
        
        # 🚨 ENFORCE STRICT LIMIT
        max_results = max(1, min(max_results, self.MAX_RESULTS))
        
        try:
            # Step 1: Search for videos
            response = requests.get(
                'https://www.googleapis.com/youtube/v3/search',
                params={
                    'part': 'snippet',
                    'q': query,
                    'type': 'video',
                    'maxResults': max_results,
                    'safeSearch': safe_search,
                    'order': 'relevance',
                    'key': self.youtube_key
                },
                timeout=10
            )
            
            response.raise_for_status()
            data = response.json()
            
            if 'items' not in data:
                print(f"⚠️ No YouTube results for: {query}")
                return []
            
            results = []
            
            # 🚨 DOUBLE-CHECK: Only process up to MAX_RESULTS
            for item in data['items'][:self.MAX_RESULTS]:
                video_id = item['id']['videoId']
                snippet = item['snippet']
                
                video_data = {
                    'video_id': video_id,
                    'url': f"https://www.youtube.com/watch?v={video_id}",
                    'title': snippet['title'],
                    'description': snippet['description'][:200],  # Truncate
                    'thumbnail': snippet['thumbnails']['high']['url'],
                    'channel_title': snippet['channelTitle'],
                    'channel_url': f"https://www.youtube.com/channel/{snippet['channelId']}",
                    'published_at': snippet['publishedAt'][:10]  # YYYY-MM-DD
                }
                
                results.append(video_data)
            
            print(f"✅ Found {len(results)} YouTube videos for: {query} (max: {self.MAX_RESULTS})")
            return results
        
        except requests.exceptions.Timeout:
            print("⚠️ YouTube API request timed out")
            return []
        
        except requests.exceptions.RequestException as e:
            print(f"❌ YouTube API error: {str(e)}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text[:200]}")
            return []
        
        except Exception as e:
            print(f"❌ Unexpected error in YouTube search: {str(e)}")
            return []
    
    # ========================================================================
    # PEXELS IMAGE SEARCH - WITH STRICT 3-IMAGE LIMIT
    # ========================================================================
    
    def search_images(
        self, 
        query: str, 
        per_page: int = 3,
        orientation: str = 'landscape'
    ) -> List[Dict]:
        """
        Search Pexels for high-quality images
        
        🚨 STRICT LIMIT: Maximum 3 results, even if requested more
        """
        if not self.pexels_key:
            print("❌ Pexels API key not configured")
            return []
        
        # 🚨 ENFORCE STRICT LIMIT
        per_page = max(1, min(per_page, self.MAX_RESULTS))
        
        try:
            response = requests.get(
                'https://api.pexels.com/v1/search',
                headers={
                    'Authorization': self.pexels_key
                },
                params={
                    'query': query,
                    'per_page': per_page,
                    'orientation': orientation
                },
                timeout=10
            )
            
            response.raise_for_status()
            data = response.json()
            
            if 'photos' not in data or not data['photos']:
                print(f"⚠️ No Pexels images found for: {query}")
                return []
            
            results = []
            
            # 🚨 DOUBLE-CHECK: Only process up to MAX_RESULTS
            for photo in data['photos'][:self.MAX_RESULTS]:
                image_data = {
                    'id': photo['id'],
                    'url': photo['src']['large2x'],
                    'width': photo['width'],
                    'height': photo['height'],
                    'photographer': photo['photographer'],
                    'photographer_url': photo['photographer_url'],
                    'alt': photo.get('alt', query),
                    'sizes': {
                        'original': photo['src']['original'],
                        'large': photo['src']['large2x'],
                        'medium': photo['src']['large'],
                        'small': photo['src']['medium']
                    }
                }
                
                results.append(image_data)
            
            print(f"✅ Found {len(results)} Pexels images for: {query} (max: {self.MAX_RESULTS})")
            return results
        
        except requests.exceptions.Timeout:
            print("⚠️ Pexels API request timed out")
            return []
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Pexels API error: {str(e)}")
            return []
        
        except Exception as e:
            print(f"❌ Unexpected error in Pexels search: {str(e)}")
            return []
    
    # ========================================================================
    # COMBINED SEARCH - WITH STRICT 3-RESULT LIMIT
    # ========================================================================
    
    def search_media(
        self,
        query: str,
        media_type: str = 'video',
        count: int = 3
    ) -> Dict:
        """
        Unified media search interface
        
        🚨 STRICT LIMIT: Maximum 3 results, enforced at multiple levels
        
        Returns:
            {
                'success': True,
                'media_type': 'video',
                'query': 'healthy relationships',
                'count': 3,
                'results': [...] (max 3 items)
            }
        """
        # 🚨 ENFORCE STRICT LIMIT at this level too
        count = max(1, min(count, self.MAX_RESULTS))
        
        if media_type == 'video':
            results = self.search_youtube_videos(query, max_results=count)
        elif media_type == 'image':
            results = self.search_images(query, per_page=count)
        else:
            print(f"❌ Unknown media type: {media_type}")
            return {
                'success': False,
                'error': f'Unknown media type: {media_type}',
                'results': []
            }
        
        # 🚨 FINAL CHECK: Triple ensure we never return more than MAX_RESULTS
        if len(results) > self.MAX_RESULTS:
            print(f"⚠️ CRITICAL: Got {len(results)} results, truncating to {self.MAX_RESULTS}")
            results = results[:self.MAX_RESULTS]
        
        return {
            'success': len(results) > 0,
            'media_type': media_type,
            'query': query,
            'count': len(results),
            'results': results
        }