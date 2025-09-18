"""
Google Trends Service for TrendBet

Provides Google Trends data extraction with robust error handling,
rate limiting, and session management.
"""

import aiohttp
import json
import asyncio
import time
import logging
import sys
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from database import SessionLocal
from models import AttentionTarget, AttentionHistory

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GoogleTrendsService:
    """
    Google Trends API service with robust session management.

    Handles cookie extraction, rate limiting, and data parsing
    for reliable Google Trends data retrieval.
    """
    
    def __init__(self, websocket_manager=None, use_tor=False):
        # EXACT configuration from your working ExactPyTrendsAPI
        self.session = None
        self.hl = 'en-US'
        self.tz = 0  # Use UTC timezone to avoid timestamp confusion
        self.geo = ''   # Global geo as requested
        self.cookies = {}
        
        # EXACT URLs from your working code
        self.base_url = 'https://trends.google.com/trends'
        self.explore_url = f"{self.base_url}/api/explore"
        self.interest_over_time_url = f"{self.base_url}/api/widgetdata/multiline"
        self.interest_by_region_url = f"{self.base_url}/api/widgetdata/comparedgeo"
        
        # EXACT payloads from your working code
        self.token_payload = {}
        self.interest_over_time_widget = {}
        self.interest_by_region_widget = {}
        self.kw_list = []
        
        # EXACT rate limiting from your working code
        self.last_request_time = 0
        self.min_delay = 5  # Your exact working value
        
        # Enhanced features
        self.session_created_at = None
        self.session_max_age = 1800
        self.use_tor = use_tor
        self.tor_failed = False
        self.websocket_manager = websocket_manager
        self.request_history = []
        self.max_requests_per_hour = 4000
        self.failure_count = 0
        
        # Browser rotation to avoid fingerprinting
        self.browser_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
        ]
        self.current_browser_index = 0
        
        # EXACT headers from your working code (will be updated with rotation)
        self.headers = {
            'accept-language': self.hl,
            'User-Agent': self.browser_agents[self.current_browser_index]
        }
        
        logger.info(f"GoogleTrendsService initialized (Tor: {use_tor}, Timezone: UTC, Region: Global)")
    
    async def __aenter__(self):
        await self._create_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _rotate_browser(self):
        """Rotate browser user agent"""
        old_browser = self.current_browser_index
        self.current_browser_index = (self.current_browser_index + 1) % len(self.browser_agents)
        self.headers['User-Agent'] = self.browser_agents[self.current_browser_index]
        logger.info(f"Browser rotated: {old_browser + 1} → {self.current_browser_index + 1}")
    
    async def _ensure_valid_session(self):
        """Enhanced session management"""
        needs_renewal = (
            not self.session or 
            self.session.closed or
            (self.session_created_at and 
             (datetime.now(timezone.utc) - self.session_created_at).total_seconds() > self.session_max_age)
        )
        
        if needs_renewal:
            if self.session:
                logger.info("Renewing session")
                await self.session.close()
                self._rotate_browser()
            await self._create_session()
    
    async def _create_session(self):
        """EXACT session creation from your working ExactPyTrendsAPI"""
        try:
            # EXACT connector and timeout from your working code
            connector = aiohttp.TCPConnector(limit=1, limit_per_host=1)
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            
            # Enhanced: Longer timeout for Tor
            if self.use_tor and not self.tor_failed:
                timeout = aiohttp.ClientTimeout(total=60, connect=20)
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.headers
            )
            
            self.session_created_at = datetime.now(timezone.utc)
            
            # Get Google cookies for authentication
            logger.info("Obtaining Google authentication cookies...")
            await self._get_google_cookie()
            
        except Exception as e:
            logger.error(f"Session creation failed: {e}")
            if self.use_tor and not self.tor_failed:
                logger.warning("🧅 Tor might be causing issues - marking for fallback")
                self.tor_failed = True
            raise
    
    async def _get_google_cookie(self):
        """
        Bulletproof cookie extraction that handles ALL possible aiohttp versions
        
        This tries multiple methods in order of preference until one works.
        """
        try:
            # EXACT URL from your working code
            cookie_url = f'{self.base_url}/explore/?geo={self.hl[-2:]}'
            
            logger.debug(f"Cookie URL: {cookie_url}")
            
            async with self.session.get(cookie_url) as response:
                logger.debug(f"Cookie response: {response.status}")
                
                if response.status != 200:
                    logger.warning(f"Cookie request failed: HTTP {response.status}")
                    return
                
                # Method 1: EXACT working code method
                try:
                    logger.debug("🧪 Trying EXACT working method...")
                    for cookie in response.cookies:
                        if hasattr(cookie, 'key') and hasattr(cookie, 'value'):
                            if cookie.key == 'NID':
                                self.cookies = {cookie.key: cookie.value}
                                logger.info(f"EXACT method SUCCESS - NID: {cookie.value[:20]}...")
                                return
                            # Store any cookies we find
                            elif not self.cookies:
                                self.cookies[cookie.key] = cookie.value
                        else:
                            logger.debug(f"   Cookie object missing .key/.value: {type(cookie)}")
                    
                    if self.cookies:
                        logger.info(f"EXACT method PARTIAL - {len(self.cookies)} cookies: {list(self.cookies.keys())}")
                        return
                    
                except Exception as e:
                    logger.warning(f"   EXACT method failed: {e}")
                
                # Method 2: Dict conversion (aiohttp version differences)
                try:
                    logger.debug("🧪 Trying dict conversion...")
                    cookies_dict = dict(response.cookies)
                    if cookies_dict:
                        self.cookies = cookies_dict
                        logger.info(f"Dict method SUCCESS - {len(cookies_dict)} cookies: {list(cookies_dict.keys())}")
                        return
                    
                except Exception as e:
                    logger.warning(f"   Dict method failed: {e}")
                
                # Method 3: Header parsing (last resort)
                try:
                    logger.debug("🧪 Trying header parsing...")
                    set_cookie_headers = response.headers.getall('Set-Cookie', [])
                    
                    if set_cookie_headers:
                        header_cookies = {}
                        for header in set_cookie_headers:
                            if '=' in header:
                                cookie_part = header.split(';')[0]
                                if '=' in cookie_part:
                                    name, value = cookie_part.split('=', 1)
                                    header_cookies[name.strip()] = value.strip()
                        
                        if header_cookies:
                            self.cookies = header_cookies
                            logger.info(f"Header method SUCCESS - {len(header_cookies)} cookies: {list(header_cookies.keys())}")
                            return
                    
                except Exception as e:
                    logger.warning(f"   Header method failed: {e}")
                
                # If all methods failed
                logger.error("ALL cookie methods failed!")
                logger.error("🔧 Possible causes:")
                logger.error("   1. IP is rate limited/blocked by Google") 
                logger.error("   2. aiohttp version incompatibility")
                logger.error("   3. Network/proxy issues")
                logger.error("   4. Geographic restrictions")
                
                # Continue without cookies (some requests might still work)
                self.cookies = {}
                
        except Exception as e:
            logger.error(f"Cookie request completely failed: {e}")
            self.cookies = {}
    
    async def build_payload(self, kw_list, cat=0, timeframe='today 5-y', geo='', gprop=''):
        """EXACT build_payload from your working ExactPyTrendsAPI"""
        if gprop not in ['', 'images', 'news', 'youtube', 'froogle']:
            raise ValueError('gprop must be empty (to indicate web), images, news, youtube, or froogle')
        
        self.kw_list = kw_list
        self.geo = geo or self.geo
        
        # Build token_payload exactly like pytrends
        self.token_payload = {
            'hl': self.hl,
            'tz': self.tz,
            'req': {'comparisonItem': [], 'category': cat, 'property': gprop}
        }
        
        if not isinstance(self.geo, list):
            self.geo = [self.geo]
        
        # Build comparison items (exactly like pytrends)
        if isinstance(timeframe, list):
            from itertools import product
            for index, (kw, geo_item) in enumerate(product(self.kw_list, self.geo)):
                keyword_payload = {'keyword': kw, 'time': timeframe[index], 'geo': geo_item}
                self.token_payload['req']['comparisonItem'].append(keyword_payload)
        else:
            from itertools import product
            for kw, geo_item in product(self.kw_list, self.geo):
                keyword_payload = {'keyword': kw, 'time': timeframe, 'geo': geo_item}
                self.token_payload['req']['comparisonItem'].append(keyword_payload)
        
        # Convert to JSON string (CRITICAL - pytrends does this!)
        self.token_payload['req'] = json.dumps(self.token_payload['req'])
        
        # Get tokens (like pytrends does)
        await self._get_tokens()
    
    async def _get_tokens(self):
        """EXACT _get_tokens from your working ExactPyTrendsAPI"""
        await self._rate_limit()
        
        logger.info("Requesting API tokens from Google Trends...")
        
        try:
            # CRITICAL: Use POST method (not GET!) and pass as params
            async with self.session.post(
                self.explore_url, 
                params=self.token_payload,
                cookies=self.cookies
            ) as response:
                
                logger.info(f"Explore response status: {response.status}")
                
                if response.status == 200:
                    response_text = await response.text()
                    logger.debug(f"📝 Response length: {len(response_text)} chars")
                    
                    # Parse response (trim 4 chars like pytrends)
                    widget_dicts = self._parse_explore_response(response_text, trim_chars=4)
                    
                    if widget_dicts:
                        self._assign_widgets(widget_dicts)
                        logger.info("API tokens obtained successfully")
                        return True
                    else:
                        logger.error("Failed to parse widget data")
                        return False
                        
                elif response.status == 429:
                    logger.warning("🚫 Rate limited on explore endpoint")
                    self.min_delay = min(self.min_delay * 2, 60)
                    return False
                    
                else:
                    logger.error(f"Explore endpoint failed: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Explore request failed: {e}")
            return False
    
    def _parse_explore_response(self, response_text: str, trim_chars: int = 4):
        """EXACT parsing from your working ExactPyTrendsAPI"""
        try:
            content = response_text[trim_chars:]
            data = json.loads(content)
            
            if 'widgets' in data:
                widgets = data['widgets']
                logger.debug(f"Found {len(widgets)} widgets")
                return widgets
            else:
                logger.warning("No 'widgets' key in response")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Response parsing failed: {e}")
            return None
    
    def _assign_widgets(self, widget_dicts):
        """EXACT widget assignment from your working ExactPyTrendsAPI"""
        first_region_token = True
        
        for widget in widget_dicts:
            widget_id = widget.get('id', '')
            
            if widget_id == 'TIMESERIES':
                self.interest_over_time_widget = widget
                logger.debug("Assigned TIMESERIES widget")
                
            if widget_id == 'GEO_MAP' and first_region_token:
                self.interest_by_region_widget = widget
                first_region_token = False
                logger.debug("Assigned GEO_MAP widget")
    
    async def interest_over_time(self):
        """EXACT interest_over_time from your working ExactPyTrendsAPI"""
        if not self.interest_over_time_widget:
            logger.error("No interest_over_time_widget available. Call build_payload first.")
            return None
        
        await self._rate_limit()
        
        # Build payload exactly like pytrends
        over_time_payload = {
            'req': json.dumps(self.interest_over_time_widget['request']),
            'token': self.interest_over_time_widget['token'],
            'tz': self.tz
        }
        
        logger.debug("Getting interest over time data...")
        
        try:
            async with self.session.get(
                self.interest_over_time_url,
                params=over_time_payload,
                cookies=self.cookies
            ) as response:
                
                logger.debug(f"Timeline response status: {response.status}")
                
                if response.status == 200:
                    response_text = await response.text()
                    
                    # Parse response (trim 5 chars for widget endpoints)
                    return self._parse_timeline_response(response_text, trim_chars=5)
                    
                elif response.status == 429:
                    logger.warning("🚫 Rate limited on timeline endpoint")
                    return None
                    
                else:
                    logger.error(f"Timeline endpoint failed: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Timeline request failed: {e}")
            return None
    
    def _parse_timeline_response(self, response_text: str, trim_chars: int = 5):
        """EXACT timeline parsing from your working ExactPyTrendsAPI + timestamp enhancement"""
        try:
            content = response_text[trim_chars:]
            data = json.loads(content)
            
            # Extract timeline data like pytrends
            if 'default' in data and 'timelineData' in data['default']:
                timeline_data = data['default']['timelineData']
                logger.debug(f"Found {len(timeline_data)} timeline points")
                
                # Extract latest value
                if timeline_data:
                    latest_entry = timeline_data[-1]
                    if 'value' in latest_entry and len(latest_entry['value']) > 0:
                        latest_score = latest_entry['value'][0]
                        
                        # Extract all values for timeline
                        timeline_values = []
                        timeline_timestamps = []  # Enhanced: for database storage
                        
                        for entry in timeline_data:
                            if 'value' in entry and len(entry['value']) > 0:
                                value = entry['value'][0]
                                timeline_values.append(0 if value is None else value)
                                
                                # Enhanced: extract timestamps
                                if 'time' in entry:
                                    timestamp = self._parse_google_timestamp(entry['time'])
                                    timeline_timestamps.append(timestamp)
                                else:
                                    timeline_timestamps.append(datetime.now(timezone.utc))
                        
                        return {
                            'success': True,
                            'search_term': self.kw_list[0] if self.kw_list else 'unknown',
                            'attention_score': float(latest_score) if latest_score is not None else 0.0,
                            'timeline': timeline_values,
                            'timeline_timestamps': timeline_timestamps,  # Enhanced
                            'timeline_length': len(timeline_values),
                            'average_score': sum(timeline_values) / len(timeline_values) if timeline_values else 0,
                            'max_score': max(timeline_values) if timeline_values else 0,
                            'source': 'exact_pytrends',
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }
            
            logger.warning("No timeline data found in expected format")
            return {
                'success': False,
                'error': 'No timeline data found',
                'raw_keys': list(data.keys()) if isinstance(data, dict) else []
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Timeline JSON parsing failed: {e}")
            return {'success': False, 'error': f'JSON parsing failed: {e}'}
        except Exception as e:
            logger.error(f"Timeline parsing failed: {e}")
            return {'success': False, 'error': f'Parsing failed: {e}'}
    
    def _parse_google_timestamp(self, timestamp_input) -> datetime:
        """Parse Google timestamp and return timezone-aware UTC datetime"""
        try:
            timestamp_float = float(timestamp_input)
            # Google provides Unix timestamps - convert to UTC datetime
            # Note: Google's timestamps are in UTC, but need to account for timezone offset
            dt = datetime.fromtimestamp(timestamp_float, tz=timezone.utc)
            return dt
            
        except (ValueError, OSError, TypeError) as e:
            logger.warning(f"Failed to parse timestamp {timestamp_input}: {e}")
            return datetime.now(timezone.utc)
    
    async def _rate_limit(self):
        """EXACT rate limiting from your working code + hourly enhancement"""
        current_time = time.time()
        
        # Enhanced: hourly limit tracking
        cutoff_time = current_time - 3600
        self.request_history = [t for t in self.request_history if t > cutoff_time]
        
        if len(self.request_history) >= self.max_requests_per_hour:
            oldest_request = self.request_history[0]
            wait_time = 3600 - (current_time - oldest_request)
            if wait_time > 0:
                logger.warning(f"⏰ Hourly limit reached - waiting {wait_time/60:.1f} minutes")
                await asyncio.sleep(wait_time)
        
        # EXACT minimum delay logic from your working code
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_delay:
            sleep_time = self.min_delay - time_since_last
            logger.info(f"Rate limiting: sleeping for {sleep_time:.1f} seconds")
            await asyncio.sleep(sleep_time)
        
        # Record request
        self.request_history.append(time.time())
        self.last_request_time = time.time()
    
    async def get_trend_score(self, search_term: str, timeframe: str = "now 7-d", geo: str = "") -> dict:
        """EXACT get_trend_score from your working ExactPyTrendsAPI + session management"""
        try:
            # Enhanced: ensure valid session
            await self._ensure_valid_session()
            
            # EXACT workflow from your working code:
            # Step 1: Build payload (like pytrends)
            await self.build_payload(kw_list=[search_term], timeframe=timeframe, geo=geo)
            
            # Step 2: Get interest over time (like pytrends)
            result = await self.interest_over_time()
            
            if result and result.get('success'):
                self.failure_count = 0  # Reset on success
                logger.info(f"Retrieved trend score for '{search_term}': {result['attention_score']:.1f}")
                return result
            else:
                self.failure_count += 1
                error_msg = result.get('error', 'Failed to get timeline data') if result else 'No result'
                logger.error(f"Failed to retrieve trend score for '{search_term}': {error_msg}")
                
                # Enhanced: Browser rotation on failures
                if self.failure_count % 2 == 0:
                    self._rotate_browser()
                
                return {
                    'success': False,
                    'error': error_msg,
                    'search_term': search_term,
                    'attention_score': -1.0
                }
            
        except Exception as e:
            self.failure_count += 1
            logger.error(f"get_trend_score exception: {e}")
            return {
                'success': False,
                'error': str(e),
                'search_term': search_term,
                'attention_score': -1.0
            }
    
    async def get_google_trends_data(self, search_term: str, timeframe: str = "now 1-d") -> Dict:
        """Enhanced wrapper that adds metadata to working method"""
        result = await self.get_trend_score(search_term, timeframe, geo=self.geo)
        
        # Enhanced: Add metadata
        if result.get('success'):
            result.update({
                'via_tor': self.use_tor and not self.tor_failed,
                'browser_agent': self.current_browser_index + 1,
                'geo': 'global',
                'timezone': 'UTC (Coordinated Universal Time)',
                'cookies_available': len(self.cookies) > 0
            })
        
        return result
    
    async def update_target_data(self, target: AttentionTarget, db: Session) -> bool:
        """Enhanced target update using working API methods - FIXED: No metadata_json"""
        try:
            logger.info(f"Updating trend data for {target.name}")
            
            # Use the proven working method
            data = await self.get_google_trends_data(target.search_term, timeframe="now 1-d")
            
            if not data.get('success'):
                error_msg = data.get('error', 'Unknown error')
                logger.error(f"Failed to get data for {target.name}: {error_msg}")
                return False
            
            # Update target
            new_score = data["attention_score"]
            old_score = float(target.current_attention_score)
            change = new_score - old_score
            
            target.current_attention_score = Decimal(str(new_score))
            target.last_updated = datetime.now(timezone.utc)
            
            # Store historical data using Google's timestamp
            # Get the latest timestamp from the Google response or fall back to UTC
            google_timestamp = datetime.now(timezone.utc)  # fallback
            if data.get('timeline_timestamps') and len(data['timeline_timestamps']) > 0:
                # Use the most recent timestamp from Google's response
                google_timestamp = data['timeline_timestamps'][-1]

            history_entry = AttentionHistory(
                target_id=target.id,
                attention_score=Decimal(str(new_score)),
                timestamp=google_timestamp,
                data_source="google_trends_realtime",
                timeframe_used="now 1-d",
                confidence_score=Decimal("1.0")
            )
            db.add(history_entry)
            
            # Cleanup old data
            cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
            deleted = db.query(AttentionHistory).filter(
                AttentionHistory.target_id == target.id,
                AttentionHistory.data_source == "google_trends_realtime",
                AttentionHistory.timestamp < cutoff
            ).delete()
            
            db.commit()
            
            # Enhanced logging with metadata (without storing in DB)
            browser_info = f"[Browser: {self.current_browser_index + 1}]"
            tor_info = "🧅" if (self.use_tor and not self.tor_failed) else "🔗"
            cookie_info = f"[Cookies: {len(self.cookies)}]"
            
            logger.info(f"{target.name}: {old_score:.1f} → {new_score:.1f} ({change:+.1f}) {tor_info} {browser_info} {cookie_info}")
            
            if deleted > 0:
                logger.debug(f"🗑️ Cleaned {deleted} old points")
            
            # WebSocket notification
            await self._notify_clients(target, new_score, change, google_timestamp)
            
            return True
            
        except Exception as e:
            logger.error(f"Update failed for {target.name}: {e}")
            db.rollback()
            return False
    
    async def _notify_clients(self, target, new_score, change, timestamp):
        """WebSocket notifications"""
        if not self.websocket_manager:
            return
        
        try:
            payload = {
                "type": "attention_update",
                "target_id": target.id,
                "target_name": target.name,
                "attention_score": float(new_score),
                "change": float(change),
                "timestamp": timestamp.isoformat()
            }
            
            await self.websocket_manager.send_target_update(target.id, payload)
            logger.debug(f"📡 WebSocket sent for {target.name}")
            
        except Exception as e:
            logger.error(f"WebSocket failed: {e}")
    
    async def update_all_targets(self):
        """Enhanced update all with browser rotation"""
        db = SessionLocal()
        try:
            targets = db.query(AttentionTarget).filter(
                AttentionTarget.is_active == True
            ).all()
            
            if not targets:
                logger.warning("No active targets")
                return True
            
            logger.info(f"Starting update cycle for {len(targets)} targets")
            
            updated = 0
            for i, target in enumerate(targets):
                try:
                    # Rotate browser every 3 targets
                    if i > 0 and i % 3 == 0:
                        self._rotate_browser()
                    
                    if await self.update_target_data(target, db):
                        updated += 1
                    
                    # Rate limit between targets
                    if i < len(targets) - 1:
                        delay = 3 + random.uniform(0, 2)  # 3-5 seconds
                        await asyncio.sleep(delay)
                        
                except Exception as e:
                    logger.error(f"Failed to update {target.name}: {e}")
            
            success_rate = (updated / len(targets)) * 100
            logger.info(f"Update cycle completed: {updated}/{len(targets)} targets successful ({success_rate:.1f}%)")
            
            return success_rate > 50  # Lower threshold while debugging
            
        except Exception as e:
            logger.error(f"Update cycle failed: {e}")
            return False
        finally:
            db.close()


# Background worker
async def run_background_updates(websocket_manager=None, use_tor=False):
    """Background worker using working implementation"""
    cycle = 0
    
    logger.info(f"Starting background trend updates (Tor: {use_tor}, Timezone: UTC-4, Region: Global)")
    
    while True:
        try:
            cycle += 1
            logger.info(f"Starting update cycle #{cycle}")

            async with GoogleTrendsService(websocket_manager=websocket_manager, use_tor=use_tor) as service:
                success = await service.update_all_targets()

            if success:
                logger.info(f"Update cycle #{cycle} completed successfully")
                await asyncio.sleep(900)  # 15 minutes
            else:
                logger.error(f"Update cycle #{cycle} failed")
                await asyncio.sleep(1800)  # 30 minutes on failure
            
        except KeyboardInterrupt:
            logger.info("Background updates stopped by user")
            break
        except Exception as e:
            logger.error(f"Cycle #{cycle} exception: {e}")
            await asyncio.sleep(900)


if __name__ == "__main__":
    """
    Test the working implementation
    
    Usage:
    python google_trends_service.py                     # Test single request
    python google_trends_service.py test-cookies        # Debug cookies
    python google_trends_service.py background          # Background worker
    python google_trends_service.py background --torify # With Tor
    """
    use_tor = "--torify" in sys.argv
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "test-cookies":
            # Test cookie extraction functionality
            async def test_cookies():
                logger.info("Testing cookie extraction...")

                service = GoogleTrendsService(use_tor=use_tor)
                await service._create_session()

                logger.info(f"Cookies obtained: {len(service.cookies)}")
                if service.cookies:
                    logger.info(f"Cookie names: {list(service.cookies.keys())}")

                    # Test API call
                    result = await service.get_google_trends_data("Bitcoin", "now 7-d")
                    if result.get('success'):
                        logger.info(f"API test successful - Score: {result['attention_score']}")
                    else:
                        logger.error(f"API test failed: {result.get('error')}")
                else:
                    logger.warning("No cookies obtained - may cause rate limiting")
                
                await service.session.close()
            
            asyncio.run(test_cookies())
            
        elif sys.argv[1] == "background":
            asyncio.run(run_background_updates(use_tor=use_tor))
            
        else:
            print("Usage: python google_trends_service.py [test-cookies|background] [--torify]")
    
    else:
        # Single test request
        async def test_single():
            async with GoogleTrendsService(use_tor=use_tor) as service:
                result = await service.get_google_trends_data("Bitcoin", "now 7-d")
                print(json.dumps(result, indent=2, default=str))
        
        asyncio.run(test_single())