"""
Web Intelligence Module for GlyphMind AI
Handles web scraping, API integration, and real-time information gathering
"""
import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
from urllib.parse import urlencode, quote_plus
import json
from bs4 import BeautifulSoup
import re

from logs.logger import log_info, log_error, log_search, log_warning
from config.config_manager import get_config

@dataclass
class SearchResult:
    """Search result data structure"""
    title: str
    url: str
    snippet: str
    source: str
    relevance_score: float = 0.0
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class WebIntelRequest:
    """Web intelligence request structure"""
    query: str
    source_types: List[str] = None  # ['google', 'youtube', 'reddit', 'news']
    max_results: int = 10
    language: str = 'en'
    region: str = 'us'
    time_filter: Optional[str] = None  # 'day', 'week', 'month', 'year'

class BaseWebSource(ABC):
    """Abstract base class for web sources"""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.is_available = False
        self.rate_limit_delay = 1.0  # seconds between requests
        self.last_request_time = 0
        
    @abstractmethod
    async def search(self, request: WebIntelRequest) -> List[SearchResult]:
        """Perform search on this source"""
        pass
        
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if source is available"""
        pass
        
    async def _rate_limit_wait(self):
        """Ensure rate limiting compliance"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

class GoogleSearchSource(BaseWebSource):
    """Google Custom Search API integration"""
    
    def __init__(self):
        super().__init__("google")
        self.api_key = None
        self.search_engine_id = None
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        
    async def initialize(self) -> bool:
        """Initialize Google Search API"""
        try:
            config = get_config()
            self.api_key = config.api.google_search_api_key
            self.search_engine_id = config.api.google_search_engine_id
            
            if not self.api_key or not self.search_engine_id:
                log_warning("Google Search API credentials not configured")
                return False
                
            self.is_available = True
            log_info("Google Search API initialized successfully")
            return True
        except Exception as e:
            log_error("Failed to initialize Google Search API", e)
            return False
            
    async def search(self, request: WebIntelRequest) -> List[SearchResult]:
        """Perform Google search"""
        if not self.is_available:
            return []
            
        await self._rate_limit_wait()
        
        params = {
            'key': self.api_key,
            'cx': self.search_engine_id,
            'q': request.query,
            'num': min(request.max_results, 10),  # Google API limit
            'lr': f'lang_{request.language}',
            'gl': request.region
        }
        
        if request.time_filter:
            # Map time filters to Google's date restrict format
            date_restrict_map = {
                'day': 'd1',
                'week': 'w1', 
                'month': 'm1',
                'year': 'y1'
            }
            if request.time_filter in date_restrict_map:
                params['dateRestrict'] = date_restrict_map[request.time_filter]
                
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_google_results(data)
                    else:
                        log_error(f"Google Search API error: {response.status}")
                        return []
        except Exception as e:
            log_error("Error performing Google search", e)
            return []
            
    def _parse_google_results(self, data: Dict[str, Any]) -> List[SearchResult]:
        """Parse Google API response"""
        results = []
        
        if 'items' not in data:
            return results
            
        for item in data['items']:
            result = SearchResult(
                title=item.get('title', ''),
                url=item.get('link', ''),
                snippet=item.get('snippet', ''),
                source='google',
                metadata={
                    'display_link': item.get('displayLink', ''),
                    'formatted_url': item.get('formattedUrl', ''),
                    'page_map': item.get('pagemap', {})
                }
            )
            results.append(result)
            
        return results
        
    async def health_check(self) -> bool:
        """Check Google API health"""
        return self.is_available and self.api_key is not None

class YouTubeSource(BaseWebSource):
    """YouTube Data API integration"""
    
    def __init__(self):
        super().__init__("youtube")
        self.api_key = None
        self.base_url = "https://www.googleapis.com/youtube/v3"
        
    async def initialize(self) -> bool:
        """Initialize YouTube API"""
        try:
            config = get_config()
            self.api_key = config.api.youtube_api_key
            
            if not self.api_key:
                log_warning("YouTube API key not configured")
                return False
                
            self.is_available = True
            log_info("YouTube API initialized successfully")
            return True
        except Exception as e:
            log_error("Failed to initialize YouTube API", e)
            return False
            
    async def search(self, request: WebIntelRequest) -> List[SearchResult]:
        """Search YouTube videos"""
        if not self.is_available:
            return []
            
        await self._rate_limit_wait()
        
        params = {
            'key': self.api_key,
            'part': 'snippet',
            'q': request.query,
            'type': 'video',
            'maxResults': min(request.max_results, 50),  # YouTube API limit
            'regionCode': request.region.upper(),
            'relevanceLanguage': request.language
        }
        
        if request.time_filter:
            # Map time filters to YouTube's published after format
            from datetime import datetime, timedelta
            time_map = {
                'day': timedelta(days=1),
                'week': timedelta(weeks=1),
                'month': timedelta(days=30),
                'year': timedelta(days=365)
            }
            if request.time_filter in time_map:
                published_after = datetime.utcnow() - time_map[request.time_filter]
                params['publishedAfter'] = published_after.isoformat() + 'Z'
                
        try:
            async with aiohttp.ClientSession() as session:
                search_url = f"{self.base_url}/search"
                async with session.get(search_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_youtube_results(data)
                    else:
                        log_error(f"YouTube API error: {response.status}")
                        return []
        except Exception as e:
            log_error("Error searching YouTube", e)
            return []
            
    def _parse_youtube_results(self, data: Dict[str, Any]) -> List[SearchResult]:
        """Parse YouTube API response"""
        results = []
        
        if 'items' not in data:
            return results
            
        for item in data['items']:
            snippet = item.get('snippet', {})
            video_id = item.get('id', {}).get('videoId', '')
            
            result = SearchResult(
                title=snippet.get('title', ''),
                url=f"https://www.youtube.com/watch?v={video_id}",
                snippet=snippet.get('description', '')[:300],  # Truncate description
                source='youtube',
                metadata={
                    'video_id': video_id,
                    'channel_title': snippet.get('channelTitle', ''),
                    'published_at': snippet.get('publishedAt', ''),
                    'channel_id': snippet.get('channelId', ''),
                    'thumbnails': snippet.get('thumbnails', {})
                }
            )
            results.append(result)
            
        return results
        
    async def health_check(self) -> bool:
        """Check YouTube API health"""
        return self.is_available and self.api_key is not None

class RedditSource(BaseWebSource):
    """Reddit scraping (using public JSON API)"""
    
    def __init__(self):
        super().__init__("reddit")
        self.base_url = "https://www.reddit.com"
        self.is_available = True  # No API key required
        
    async def initialize(self) -> bool:
        """Initialize Reddit source"""
        self.is_available = True
        log_info("Reddit source initialized")
        return True
        
    async def search(self, request: WebIntelRequest) -> List[SearchResult]:
        """Search Reddit posts"""
        await self._rate_limit_wait()
        
        # Use Reddit's search JSON endpoint
        search_url = f"{self.base_url}/search.json"
        params = {
            'q': request.query,
            'limit': min(request.max_results, 25),
            'sort': 'relevance',
            't': self._map_time_filter(request.time_filter)
        }
        
        headers = {
            'User-Agent': 'GlyphMind AI Bot 1.0 (Educational/Research)'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_reddit_results(data)
                    else:
                        log_error(f"Reddit API error: {response.status}")
                        return []
        except Exception as e:
            log_error("Error searching Reddit", e)
            return []
            
    def _map_time_filter(self, time_filter: Optional[str]) -> str:
        """Map time filter to Reddit format"""
        if not time_filter:
            return 'all'
        
        time_map = {
            'day': 'day',
            'week': 'week',
            'month': 'month',
            'year': 'year'
        }
        return time_map.get(time_filter, 'all')
        
    def _parse_reddit_results(self, data: Dict[str, Any]) -> List[SearchResult]:
        """Parse Reddit API response"""
        results = []
        
        if 'data' not in data or 'children' not in data['data']:
            return results
            
        for item in data['data']['children']:
            post_data = item.get('data', {})
            
            result = SearchResult(
                title=post_data.get('title', ''),
                url=f"https://www.reddit.com{post_data.get('permalink', '')}",
                snippet=post_data.get('selftext', '')[:300] or post_data.get('title', ''),
                source='reddit',
                relevance_score=post_data.get('score', 0) / 100,  # Normalize score
                metadata={
                    'subreddit': post_data.get('subreddit', ''),
                    'author': post_data.get('author', ''),
                    'score': post_data.get('score', 0),
                    'num_comments': post_data.get('num_comments', 0),
                    'created_utc': post_data.get('created_utc', 0),
                    'is_self': post_data.get('is_self', False)
                }
            )
            results.append(result)
            
        return results
        
    async def health_check(self) -> bool:
        """Check Reddit availability"""
        return True

class WebIntelligence:
    """Main web intelligence coordinator"""
    
    def __init__(self):
        self.sources: Dict[str, BaseWebSource] = {}
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 300  # 5 minutes
        
    async def initialize(self):
        """Initialize all web sources"""
        log_info("Initializing Web Intelligence module")
        
        # Initialize Google Search
        google_source = GoogleSearchSource()
        if await google_source.initialize():
            self.sources['google'] = google_source
            
        # Initialize YouTube
        youtube_source = YouTubeSource()
        if await youtube_source.initialize():
            self.sources['youtube'] = youtube_source
            
        # Initialize Reddit
        reddit_source = RedditSource()
        if await reddit_source.initialize():
            self.sources['reddit'] = reddit_source
            
        log_info(f"Web Intelligence initialized with {len(self.sources)} sources")
        
    async def search(self, request: WebIntelRequest) -> List[SearchResult]:
        """Perform comprehensive web search"""
        start_time = time.time()
        
        # Check cache first
        cache_key = self._generate_cache_key(request)
        cached_results = self._get_cached_results(cache_key)
        if cached_results:
            log_info(f"Returning cached results for query: {request.query}")
            return cached_results
            
        all_results = []
        
        # Determine which sources to use
        sources_to_use = request.source_types or list(self.sources.keys())
        
        # Search all sources concurrently
        search_tasks = []
        for source_name in sources_to_use:
            if source_name in self.sources:
                source = self.sources[source_name]
                if await source.health_check():
                    task = asyncio.create_task(source.search(request))
                    search_tasks.append((source_name, task))
                    
        # Collect results
        for source_name, task in search_tasks:
            try:
                results = await task
                all_results.extend(results)
                log_info(f"Retrieved {len(results)} results from {source_name}")
            except Exception as e:
                log_error(f"Error getting results from {source_name}", e)
                
        # Sort by relevance and limit results
        all_results.sort(key=lambda x: x.relevance_score, reverse=True)
        final_results = all_results[:request.max_results]
        
        # Cache results
        self._cache_results(cache_key, final_results)
        
        execution_time = time.time() - start_time
        log_search(
            request.query,
            ','.join(sources_to_use),
            len(final_results),
            execution_time
        )
        
        return final_results
        
    async def get_latest_news(self, topic: str, max_results: int = 5) -> List[SearchResult]:
        """Get latest news on a topic"""
        request = WebIntelRequest(
            query=f"{topic} news",
            source_types=['google'],
            max_results=max_results,
            time_filter='day'
        )
        return await self.search(request)
        
    async def search_videos(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Search for videos on a topic"""
        request = WebIntelRequest(
            query=query,
            source_types=['youtube'],
            max_results=max_results
        )
        return await self.search(request)
        
    async def search_discussions(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Search for discussions on a topic"""
        request = WebIntelRequest(
            query=query,
            source_types=['reddit'],
            max_results=max_results
        )
        return await self.search(request)
        
    def _generate_cache_key(self, request: WebIntelRequest) -> str:
        """Generate cache key for request"""
        key_data = {
            'query': request.query,
            'sources': sorted(request.source_types or []),
            'max_results': request.max_results,
            'time_filter': request.time_filter
        }
        return json.dumps(key_data, sort_keys=True)
        
    def _get_cached_results(self, cache_key: str) -> Optional[List[SearchResult]]:
        """Get cached results if still valid"""
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return cached_data
        return None
        
    def _cache_results(self, cache_key: str, results: List[SearchResult]):
        """Cache search results"""
        self.cache[cache_key] = (results, time.time())
        
    async def get_source_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all web sources"""
        status = {}
        
        for name, source in self.sources.items():
            health = await source.health_check()
            status[name] = {
                'source_name': source.source_name,
                'is_available': source.is_available,
                'health_check': health,
                'rate_limit_delay': source.rate_limit_delay
            }
            
        return status

# Global web intelligence instance
web_intelligence = WebIntelligence()

async def web_search(query: str, sources: Optional[List[str]] = None, 
                    max_results: int = 10) -> List[SearchResult]:
    """Convenience function for web search"""
    request = WebIntelRequest(
        query=query,
        source_types=sources,
        max_results=max_results
    )
    return await web_intelligence.search(request)
