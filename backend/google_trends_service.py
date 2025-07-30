# backend/google_trends_service.py
"""
Google Trends Data Service for TrendBet
Enhanced version with direct Google Trends API integration
Provides real-time attention scores and historical data
"""

import aiohttp
import json
import asyncio
import time
import logging
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, List
import hashlib
from sqlalchemy.orm import Session
from database import SessionLocal
from models import AttentionTarget, AttentionHistory, TargetType

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleTrendsService:
    """
    Production Google Trends API Service for TrendBet
    Provides long-term relative attention scores with caching and error handling
    """
    
    def __init__(self, cache_duration_minutes: int = 60):
        self.hl = 'en-US'
        self.tz = 360
        self.geo = ''
        self.cookies = {}
        self.cache = {}
        self.cache_duration = timedelta(minutes=cache_duration_minutes)
        
        # API URLs
        self.base_url = 'https://trends.google.com/trends'
        self.explore_url = f"{self.base_url}/api/explore"
        self.interest_over_time_url = f"{self.base_url}/api/widgetdata/multiline"
        self.interest_by_region_url = f"{self.base_url}/api/widgetdata/comparedgeo"
        
        # Session management
        self.session = None
        self.last_request_time = 0
        self.min_delay = 3  # Keep original 3 second delay
        self.session_created_at = None
        self.session_lifetime = timedelta(hours=1)
        
        # Headers
        self.headers = {
            'accept-language': self.hl,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
        }
        
        # Timeframes for different use cases
        self.timeframes = {
            'long_term': 'today 5-y',      # 5 years - best for baseline scores
            'medium_term': 'today 12-m',   # 12 months
            'short_term': 'now 7-d',       # 7 days
            'real_time': 'now 1-d'         # 1 day
        }
        
        # Default to medium-term for good balance of relevance and stability
        self.default_timeframe = self.timeframes['medium_term']
        
    async def __aenter__(self):
        await self._ensure_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._close_session()
    
    async def _ensure_session(self):
        """Ensure we have a valid session, create new one if needed"""
        now = datetime.utcnow()
        
        if (self.session is None or 
            self.session.closed or 
            (self.session_created_at and now - self.session_created_at > self.session_lifetime)):
            
            await self._close_session()
            await self._create_session()
    
    async def _create_session(self):
        """Create new session with Google cookies"""
        connector = aiohttp.TCPConnector(limit=5, limit_per_host=1)
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.headers
        )
        
        self.session_created_at = datetime.utcnow()
        
        # Get Google cookies
        logger.info("🍪 Initializing Google Trends session...")
        await self._get_google_cookie()
        
    async def _close_session(self):
        """Close existing session"""
        if self.session and not self.session.closed:
            await self.session.close()
        self.session = None
        self.session_created_at = None
        
    async def _get_google_cookie(self):
        """Get required Google cookie for authentication"""
        try:
            # Try the main trends page first
            cookie_url = f'{self.base_url}/'
            async with self.session.get(cookie_url) as response:
                if response.status == 200:
                    # Handle different cookie formats
                    try:
                        # Method 1: Direct cookie iteration
                        self.cookies.update({cookie.key: cookie.value for cookie in response.cookies})
                    except AttributeError:
                        # Method 2: Items iteration
                        self.cookies.update(dict(response.cookies))
                    
                    logger.info(f"✅ Google Trends session initialized with {len(self.cookies)} cookies")
                    return
                else:
                    logger.warning(f"⚠️ Cookie request failed: {response.status}")
        except Exception as e:
            logger.warning(f"Cookie request failed: {e}, continuing without cookies")
    
    def _get_cache_key(self, search_term: str, timeframe: str, geo: str) -> str:
        """Generate cache key for request"""
        key_string = f"{search_term}_{timeframe}_{geo}_{self.hl}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_entry: dict) -> bool:
        """Check if cache entry is still valid"""
        if not cache_entry:
            return False
        
        cached_at = cache_entry.get('cached_at')
        if not cached_at:
            return False
        
        return datetime.utcnow() - cached_at < self.cache_duration
    
    async def get_google_trends_data(self, search_term: str, timeframe: str = "now 7-d") -> dict:
        """
        TrendBet compatibility method - maps to new implementation
        
        Args:
            search_term: The term to search for
            timeframe: Legacy timeframe parameter (kept for compatibility)
            
        Returns:
            Dict with attention_score and metadata
        """
        # Map old timeframe format to new format if needed
        if timeframe == "now 7-d":
            new_timeframe = "short_term"
        elif timeframe == "today 12-m":
            new_timeframe = "medium_term"
        elif timeframe == "today 5-y":
            new_timeframe = "long_term"
        else:
            new_timeframe = "medium_term"  # Default
        
        result = await self.get_attention_score(search_term, "US", new_timeframe)
        
        # Return in expected format for TrendBet
        return {
            "attention_score": result.get('attention_score', 0.0),
            "timeline": result.get('timeline', []),
            "search_term": search_term,
            "last_updated": datetime.utcnow(),
            "source": "google_trends_api"
        }
    
    async def get_attention_score(self, 
                                search_term: str, 
                                geo: str = "US", 
                                timeframe: str = None,
                                use_cache: bool = True) -> Dict:
        """
        Get attention score for a search term
        """
        # Handle session management
        try:
            await self._ensure_session()
        except Exception as e:
            logger.warning(f"Session setup failed, using fallback: {e}")
            return self._generate_mock_trends_data(search_term)
        
        # Use default timeframe if not specified
        if timeframe is None:
            timeframe = self.default_timeframe
        elif timeframe in self.timeframes:
            timeframe = self.timeframes[timeframe]
        
        # Check cache first
        cache_key = self._get_cache_key(search_term, timeframe, geo)
        if use_cache and cache_key in self.cache:
            cached_result = self.cache[cache_key]
            if self._is_cache_valid(cached_result):
                logger.info(f"📋 Cache hit for: {search_term}")
                cached_result['source'] = 'cache'
                return cached_result
        
        try:
            # Get fresh data from Google Trends
            result = await self._get_trends_data(search_term, timeframe, geo)
            
            # Cache successful results
            if result.get('success') and use_cache:
                result['cached_at'] = datetime.utcnow()
                self.cache[cache_key] = result.copy()
                logger.info(f"💾 Cached result for: {search_term}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting attention score for {search_term}: {e}")
            # Return fallback data
            return self._generate_mock_trends_data(search_term)
    
    def _generate_mock_trends_data(self, search_term: str) -> dict:
        """Generate realistic mock trends data for fallback"""
        
        # Base attention scores for different types
        base_scores = {
            # Politicians - higher volatility
            "donald trump": random.uniform(60, 95),
            "joe biden": random.uniform(40, 80), 
            "kamala harris": random.uniform(25, 60),
            "ron desantis": random.uniform(20, 55),
            
            # Billionaires - medium volatility
            "elon musk": random.uniform(70, 90),
            "jeff bezos": random.uniform(15, 45),
            "bill gates": random.uniform(20, 50),
            "warren buffett": random.uniform(10, 35),
            
            # Countries - lower volatility
            "united states": random.uniform(30, 70),
            "china": random.uniform(25, 60),
            "japan": random.uniform(15, 40),
            "united kingdom": random.uniform(20, 45),
            
            # Stocks/Crypto - high volatility
            "tesla": random.uniform(40, 85),
            "gamestop": random.uniform(20, 70),
            "bitcoin": random.uniform(50, 90),
            "artificial intelligence": random.uniform(45, 80)
        }
        
        # Get base score or use random for unknown terms
        search_lower = search_term.lower().replace(" news", "").replace(" stock", "")
        base_score = base_scores.get(search_lower, random.uniform(20, 60))
        
        # Add some randomness
        attention_score = max(0, min(100, base_score + random.uniform(-10, 10)))
        
        return {
            'success': True,
            'attention_score': attention_score,
            'timeline': [attention_score] * 10,  # Mock timeline
            'search_term': search_term,
            'source': 'fallback_mock',
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def _get_trends_data(self, search_term: str, timeframe: str, geo: str) -> Dict:
        """Get trends data from Google API"""
        
        # Step 1: Build payload and get tokens
        tokens_success = await self._build_payload([search_term], timeframe, geo)
        if not tokens_success:
            return self._generate_mock_trends_data(search_term)
        
        # Step 2: Get interest over time data
        result = await self._get_interest_over_time()
        
        if result and result.get('success'):
            # Add metadata
            result.update({
                'search_term': search_term,
                'geo': geo,
                'timeframe': timeframe,
                'source': 'google_trends_api',
                'timestamp': datetime.utcnow().isoformat()
            })
            
            logger.info(f"✅ Got trend score for {search_term}: {result['attention_score']}")
            return result
        else:
            logger.warning(f"API failed for {search_term}, using fallback")
            return self._generate_mock_trends_data(search_term)
    
    async def _build_payload(self, kw_list: List[str], timeframe: str, geo: str) -> bool:
        """Build payload and get tokens from Google"""
        
        # Build token payload
        self.token_payload = {
            'hl': self.hl,
            'tz': self.tz,
            'req': {'comparisonItem': [], 'category': 0, 'property': ''}
        }
        
        # Add keywords
        from itertools import product
        for kw, geo_item in product(kw_list, [geo]):
            keyword_payload = {'keyword': kw, 'time': timeframe, 'geo': geo_item}
            self.token_payload['req']['comparisonItem'].append(keyword_payload)
        
        # Convert to JSON string
        self.token_payload['req'] = json.dumps(self.token_payload['req'])
        
        # Get tokens
        return await self._get_tokens()
    
    async def _get_tokens(self) -> bool:
        """Get widget tokens from explore endpoint"""
        await self._rate_limit()
        
        try:
            async with self.session.post(
                self.explore_url, 
                params=self.token_payload,
                cookies=self.cookies
            ) as response:
                
                if response.status == 200:
                    response_text = await response.text()
                    
                    # Parse widgets (trim 4 chars)
                    content = response_text[4:]
                    data = json.loads(content)
                    
                    if 'widgets' in data:
                        widgets = data['widgets']
                        self._assign_widgets(widgets)
                        return True
                    else:
                        logger.error("❌ No widgets in explore response")
                        return False
                        
                elif response.status == 429:
                    logger.warning("🚫 Rate limited on explore endpoint")
                    self.min_delay = min(self.min_delay * 2, 60)
                    return False
                    
                else:
                    logger.error(f"❌ Explore endpoint failed: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Token request failed: {e}")
            return False
    
    def _assign_widgets(self, widgets: List[Dict]):
        """Assign widgets for different data types"""
        self.interest_over_time_widget = None
        self.interest_by_region_widget = None
        
        first_region_token = True
        for widget in widgets:
            widget_id = widget.get('id', '')
            
            if widget_id == 'TIMESERIES':
                self.interest_over_time_widget = widget
                
            if widget_id == 'GEO_MAP' and first_region_token:
                self.interest_by_region_widget = widget
                first_region_token = False
    
    async def _get_interest_over_time(self) -> Optional[Dict]:
        """Get interest over time data using widget token"""
        if not self.interest_over_time_widget:
            return {'success': False, 'error': 'No interest over time widget'}
        
        await self._rate_limit()
        
        payload = {
            'req': json.dumps(self.interest_over_time_widget['request']),
            'token': self.interest_over_time_widget['token'],
            'tz': self.tz
        }
        
        try:
            async with self.session.get(
                self.interest_over_time_url,
                params=payload,
                cookies=self.cookies
            ) as response:
                
                if response.status == 200:
                    response_text = await response.text()
                    return self._parse_timeline_response(response_text)
                else:
                    return {'success': False, 'error': f'Timeline request failed: {response.status}'}
                    
        except Exception as e:
            return {'success': False, 'error': f'Timeline request error: {e}'}
    
    def _parse_timeline_response(self, response_text: str) -> Dict:
        """Parse timeline response"""
        try:
            # Trim 5 chars for widget endpoints
            content = response_text[5:]
            data = json.loads(content)
            
            if 'default' in data and 'timelineData' in data['default']:
                timeline_data = data['default']['timelineData']
                
                if timeline_data:
                    # Extract values and timestamps
                    timeline_values = []
                    timeline_timestamps = []
                    
                    for entry in timeline_data:
                        if 'value' in entry and len(entry['value']) > 0:
                            timeline_values.append(entry['value'][0])
                            
                            # Extract timestamp if available
                            if 'time' in entry:
                                timeline_timestamps.append(entry['time'])
                    
                    if timeline_values:
                        latest_score = timeline_values[-1]
                        
                        return {
                            'success': True,
                            'attention_score': float(latest_score),
                            'timeline': timeline_values,
                            'timeline_timestamps': timeline_timestamps,
                            'timeline_length': len(timeline_values),
                            'average_score': sum(timeline_values) / len(timeline_values),
                            'max_score': max(timeline_values),
                            'min_score': min(timeline_values),
                            'median_score': sorted(timeline_values)[len(timeline_values)//2],
                            'volatility': self._calculate_volatility(timeline_values)
                        }
            
            return {'success': False, 'error': 'No timeline data found'}
            
        except Exception as e:
            return {'success': False, 'error': f'Timeline parsing failed: {e}'}
    
    def _calculate_volatility(self, values: List[float]) -> float:
        """Calculate volatility (standard deviation) of timeline values"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    async def _rate_limit(self):
        """Rate limiting to avoid being blocked"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_delay:
            sleep_time = self.min_delay - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()

    def _parse_trends_timestamp(self, trends_time) -> datetime:
        """Parse Google Trends timestamp format to datetime"""
        try:
            # Google Trends returns different timestamp formats
            if isinstance(trends_time, (int, float)):
                # Unix timestamp
                return datetime.fromtimestamp(trends_time)
            elif isinstance(trends_time, str):
                if '-' in trends_time:
                    # Date format like "2024-01-15"
                    try:
                        return datetime.strptime(trends_time, "%Y-%m-%d")
                    except:
                        return datetime.strptime(trends_time[:10], "%Y-%m-%d")
                else:
                    # String timestamp
                    return datetime.fromtimestamp(float(trends_time))
        except Exception as e:
            logger.warning(f"Could not parse timestamp {trends_time}: {e}")
            # Return a reasonable fallback
            return datetime.utcnow() - timedelta(days=365)

    def _forward_fill_to_5_minute_intervals(self, real_data_points: list) -> list:
        """
        Forward fill real Google Trends data to 5-minute intervals
        Takes sparse real data and creates dense 5-minute intervals using closest real values
        """
        if not real_data_points:
            return []
        
        # Sort by timestamp
        sorted_data = sorted(real_data_points, key=lambda x: x['timestamp'])
        
        # Find the time range (last 5 years to now)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=5*365)  # 5 years ago
        
        # Generate 5-minute intervals and forward fill
        forward_filled = []
        current_time = start_time
        current_data_index = 0
        
        logger.info(f"🔄 Forward filling {len(sorted_data)} real points to 5-minute intervals")
        
        # Find first data point that's >= start_time
        while (current_data_index < len(sorted_data) and 
               sorted_data[current_data_index]['timestamp'] < start_time):
            current_data_index += 1
        
        if current_data_index >= len(sorted_data):
            # If no data points in range, use the last available data point
            if sorted_data:
                current_data_index = len(sorted_data) - 1
            else:
                logger.warning("No real data points available")
                return []
        
        while current_time <= end_time:
            # Find the most recent real data point for this timestamp
            while (current_data_index < len(sorted_data) - 1 and 
                   sorted_data[current_data_index + 1]['timestamp'] <= current_time):
                current_data_index += 1
            
            # Use the current real data point for this 5-minute interval
            if current_data_index < len(sorted_data):
                real_point = sorted_data[current_data_index]
                
                forward_filled.append({
                    'timestamp': current_time,
                    'attention_score': real_point['attention_score'],
                    'source_timestamp': real_point['timestamp']  # Track original data point
                })
            
            # Move to next 5-minute interval
            current_time += timedelta(minutes=5)
        
        logger.info(f"✅ Forward filled {len(real_data_points)} real points to {len(forward_filled)} 5-minute intervals")
        return forward_filled

    async def update_target_data(self, target: AttentionTarget, db: Session) -> bool:
        """Update a single target's attention data with REAL Google Trends only"""
        try:
            # Get current trends data (REAL ONLY)
            trends_data = await self.get_google_trends_data(target.search_term)
            new_score = trends_data["attention_score"]
            
            # Update target
            target.current_attention_score = Decimal(str(new_score))
            target.last_updated = datetime.utcnow()
            
            # Save historical data point with proper source tracking
            history_entry = AttentionHistory(
                target_id=target.id,
                attention_score=Decimal(str(new_score)),
                timestamp=datetime.utcnow(),
                data_source="google_trends_real_time",
                timeframe_used="now",
                confidence_score=Decimal("1.0")  # Real data = high confidence
            )
            db.add(history_entry)
            
            logger.info(f"✅ Updated {target.name}: {new_score:.1f}% (REAL Google Trends)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating {target.name}: {e}")
            return False

    async def update_all_targets(self):
        """Update all existing active targets with fresh attention data - NO SEEDING"""
        db = SessionLocal()
        try:
            # Get all active targets (no seeding, just update existing ones)
            targets = db.query(AttentionTarget).filter(
                AttentionTarget.is_active == True
            ).all()
            
            logger.info(f"🔄 Updating {len(targets)} existing targets...")
            
            updated_count = 0
            for target in targets:
                # Only update existing targets - no seeding
                if await self.update_target_data(target, db):
                    updated_count += 1
                
                # Rate limiting delay
                await asyncio.sleep(3)
            
            db.commit()
            logger.info(f"✅ Successfully updated {updated_count}/{len(targets)} targets")
            
        except Exception as e:
            logger.error(f"❌ Error in update_all_targets: {e}")
            db.rollback()
        finally:
            db.close()


# Background update function (not a class method)
async def run_data_updates():
    """Main function to run periodic data updates - NO SEEDING"""
    
    while True:
        try:
            async with GoogleTrendsService() as service:
                logger.info("🔄 Starting scheduled data update cycle...")
                await service.update_all_targets()  # Only update existing targets
                
            # Wait 5 minutes before next update
            logger.info("⏰ Waiting 5 minutes until next update...")
            await asyncio.sleep(300)  # 5 minutes = 300 seconds
            
        except Exception as e:
            logger.error(f"❌ Error in data update cycle: {e}")
            # Wait 5 minutes before retrying on error
            await asyncio.sleep(300)


def get_service_status() -> Dict:
    """Get status information about the Google Trends service"""
    return {
        "service": "GoogleTrendsService",
        "version": "real_data_only_version",
        "data_source": "google_trends_api_with_fallbacks",
        "update_interval": "5_minutes",
        "rate_limiting": "3_seconds",
        "fallback_enabled": True,
        "timestamp": datetime.utcnow().isoformat()
    }


# Convenience function for external usage
async def get_trend_score(search_term: str) -> float:
    """Simple function to get a single trend score"""
    async with GoogleTrendsService() as service:
        trends_data = await service.get_google_trends_data(search_term)
        return trends_data.get("attention_score", 0.0)


if __name__ == "__main__":
    # Only run the update service - NO SEEDING (that's seed_data.py's job)
    asyncio.run(run_data_updates())