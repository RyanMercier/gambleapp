"""
Google Trends Data Service for TrendBet
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
import urllib.parse
from sqlalchemy.orm import Session
from database import SessionLocal
from models import AttentionTarget, AttentionHistory, TargetType, Portfolio

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleTrendsService:
    """
    Real Google Trends API Service for TrendBet
    Uses actual Google Trends data with 5-year baseline for new terms
    """
    
    def __init__(self, update_interval_minutes: int = 3):
        self.hl = 'en-US'
        self.tz = 360
        self.geo = 'US'  # Default to US for consistent data
        self.cookies = {}
        
        # Update interval (default 3 minutes as requested)
        self.update_interval = update_interval_minutes * 60  # Convert to seconds
        
        # Google Trends API endpoints
        self.base_url = 'https://trends.google.com/trends'
        self.explore_url = f"{self.base_url}/api/explore"
        self.interest_over_time_url = f"{self.base_url}/api/widgetdata/multiline"
        
        # Session management for API calls
        self.session = None
        self.last_request_time = 0
        self.min_delay = 2  # 2 seconds between requests to avoid rate limiting
        self.session_created_at = None
        self.session_lifetime = timedelta(hours=2)
        
        # Headers to mimic real browser
        self.headers = {
            'accept-language': self.hl,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br',
            'connection': 'keep-alive',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin'
        }
        
        # Timeframes for different data needs
        self.timeframes = {
            'long_term': 'today 5-y',      # 5 years for initial data
            'medium_term': 'today 12-m',   # 12 months 
            'short_term': 'now 7-d',       # 7 days for recent updates
            'real_time': 'now 1-h'         # 1 hour for very fresh data
        }
        
    async def __aenter__(self):
        await self._ensure_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._close_session()

    async def get_google_trends_data(self, search_term: str, timeframe: str = 'today 5-y') -> Dict:
        """
        Get real Google Trends data for a search term
        """
        await self._ensure_session()
        await self._rate_limit()
        
        try:
            logger.info(f"🔍 Fetching real trends data for: {search_term}")
            
            # Step 1: Get explore data to build proper request
            explore_data = await self._get_explore_data(search_term, timeframe)
            if not explore_data:
                raise Exception("Failed to get explore data")
            
            # Step 2: Extract widget token and request ID
            widget_data = self._extract_widget_data(explore_data)
            if not widget_data:
                raise Exception("Failed to extract widget data")
            
            # Step 3: Get actual interest over time data
            interest_data = await self._get_interest_over_time(widget_data)
            if not interest_data:
                raise Exception("Failed to get interest over time data")
            
            # Step 4: Process the data
            processed_data = self._process_trends_data(interest_data, search_term, timeframe)
            
            logger.info(f"✅ Got real trends data for {search_term}: {processed_data.get('attention_score', 0)}%")
            return processed_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get real trends data for {search_term}: {e}")
            raise Exception(f"Google Trends API error: {e}")

    async def _get_explore_data(self, search_term: str, timeframe: str) -> Optional[Dict]:
        """Get explore data from Google Trends"""
        try:
            # Build the explore request
            params = {
                'hl': self.hl,
                'tz': self.tz,
                'req': json.dumps({
                    "comparisonItem": [{
                        "keyword": search_term,
                        "geo": self.geo,
                        "time": timeframe
                    }],
                    "category": 0,
                    "property": ""
                })
            }
            
            url = f"{self.explore_url}?{urllib.parse.urlencode(params)}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    text = await response.text()
                    # Remove the ")]}'," prefix that Google adds
                    if text.startswith(")]},"):
                        text = text[5:]
                    return json.loads(text)
                else:
                    logger.error(f"Explore request failed: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error in explore request: {e}")
            return None

    def _extract_widget_data(self, explore_data: Dict) -> Optional[Dict]:
        """Extract widget token and request data from explore response"""
        try:
            widgets = explore_data.get('widgets', [])
            for widget in widgets:
                if widget.get('id') == 'TIMESERIES':
                    return {
                        'token': widget.get('token'),
                        'request': widget.get('request')
                    }
            return None
        except Exception as e:
            logger.error(f"Error extracting widget data: {e}")
            return None

    async def _get_interest_over_time(self, widget_data: Dict) -> Optional[Dict]:
        """Get the actual interest over time data"""
        try:
            params = {
                'hl': self.hl,
                'tz': self.tz,
                'req': json.dumps(widget_data['request']),
                'token': widget_data['token']
            }
            
            url = f"{self.interest_over_time_url}?{urllib.parse.urlencode(params)}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    text = await response.text()
                    # Remove the ")]}'," prefix
                    if text.startswith(")]},"):
                        text = text[5:]
                    return json.loads(text)
                else:
                    logger.error(f"Interest over time request failed: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting interest over time: {e}")
            return None

    def _process_trends_data(self, interest_data: Dict, search_term: str, timeframe: str) -> Dict:
        """Process raw Google Trends data into our format"""
        try:
            default_data = interest_data.get('default', {})
            timeline_data = default_data.get('timelineData', [])
            
            if not timeline_data:
                raise Exception("No timeline data found")
            
            # Extract values from timeline
            values = []
            timestamps = []
            
            for point in timeline_data:
                if 'value' in point and len(point['value']) > 0:
                    # Google Trends values are 0-100
                    value = point['value'][0]
                    values.append(value)
                    
                    # Extract timestamp if available
                    if 'time' in point:
                        timestamps.append(point['time'])
            
            if not values:
                raise Exception("No values found in timeline data")
            
            # Calculate current attention score (latest value)
            current_score = values[-1]
            
            # Calculate statistics
            avg_score = sum(values) / len(values)
            max_score = max(values)
            min_score = min(values)
            
            # Calculate volatility (standard deviation)
            volatility = 0
            if len(values) > 1:
                variance = sum((x - avg_score) ** 2 for x in values) / len(values)
                volatility = variance ** 0.5
            
            return {
                'success': True,
                'attention_score': float(current_score),
                'timeline': values,
                'timestamps': timestamps,
                'timeline_length': len(values),
                'average_score': round(avg_score, 2),
                'max_score': max_score,
                'min_score': min_score,
                'volatility': round(volatility, 2),
                'search_term': search_term,
                'timeframe': timeframe,
                'source': 'google_trends_api',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing trends data: {e}")
            raise Exception(f"Data processing error: {e}")

    async def seed_historical_data(self, target: AttentionTarget, days: int = 1825):
        """Create real 5-year historical data for new targets"""
        db = SessionLocal()
        try:
            # Check if we already have historical data
            existing_history = db.query(AttentionHistory).filter(
                AttentionHistory.target_id == target.id
            ).count()
            
            if existing_history > 0:
                logger.info(f"Historical data already exists for {target.name}")
                return
            
            logger.info(f"🌱 Seeding 5-year historical data for {target.name}...")
            
            # Get 5-year data from Google Trends
            trends_data = await self.get_google_trends_data(target.search_term, 'today 5-y')
            
            if not trends_data.get('success'):
                raise Exception("Failed to get historical trends data")
            
            timeline = trends_data.get('timeline', [])
            timestamps = trends_data.get('timestamps', [])
            
            # If we have timestamps, use them; otherwise create weekly intervals
            if len(timestamps) == len(timeline):
                # Use actual timestamps from Google
                for i, (score, timestamp) in enumerate(zip(timeline, timestamps)):
                    # Convert Google timestamp to datetime
                    if isinstance(timestamp, (int, float)):
                        dt = datetime.fromtimestamp(timestamp)
                    else:
                        # Fallback to weekly intervals
                        dt = datetime.utcnow() - timedelta(days=days) + timedelta(weeks=i)
                    
                    history_entry = AttentionHistory(
                        target_id=target.id,
                        attention_score=Decimal(str(score)),
                        timestamp=dt,
                        data_source='google_trends_api',
                        timeframe_used='5_year'
                    )
                    db.add(history_entry)
            else:
                # Create weekly intervals for the timeline data
                weeks_back = len(timeline)
                for i, score in enumerate(timeline):
                    timestamp = datetime.utcnow() - timedelta(weeks=weeks_back-i)
                    
                    history_entry = AttentionHistory(
                        target_id=target.id,
                        attention_score=Decimal(str(score)),
                        timestamp=timestamp,
                        data_source='google_trends_api',
                        timeframe_used='5_year'
                    )
                    db.add(history_entry)
            
            # Update target baseline statistics
            timeline_scores = [float(s) for s in timeline]
            target.baseline_average = Decimal(str(round(sum(timeline_scores) / len(timeline_scores), 2)))
            target.baseline_max = Decimal(str(max(timeline_scores)))
            target.baseline_min = Decimal(str(min(timeline_scores)))
            target.baseline_period = '5_year'
            
            db.commit()
            logger.info(f"✅ Created {len(timeline)} historical entries for {target.name}")
            
        except Exception as e:
            logger.error(f"❌ Error seeding historical data for {target.name}: {e}")
            db.rollback()
            raise
        finally:
            db.close()

    async def update_target_data(self, target: AttentionTarget, db: Session) -> bool:
        """Update a single target's attention data with real Google Trends data"""
        try:
            # Get fresh data from Google Trends (use shorter timeframe for updates)
            trends_data = await self.get_google_trends_data(target.search_term, 'now 7-d')
            new_score = trends_data["attention_score"]
            
            # Update target with new attention score
            target.current_attention_score = Decimal(str(new_score))
            target.last_updated = datetime.utcnow()
            
            # Save history entry
            history = AttentionHistory(
                target_id=target.id,
                attention_score=Decimal(str(new_score)),
                data_source='google_trends_api',
                timeframe_used='7_day'
            )
            db.add(history)
            db.commit()
            
            logger.info(f"✅ Updated {target.name}: {new_score}%")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update {target.name}: {e}")
            db.rollback()
            return False

    async def cleanup_unused_targets(self):
        """Remove targets that no one is holding positions in"""
        db = SessionLocal()
        try:
            # Find targets with no portfolio positions
            targets_with_positions = db.query(Portfolio.target_id).distinct().all()
            position_target_ids = [t[0] for t in targets_with_positions]
            
            # Get all targets not in positions
            unused_targets = db.query(AttentionTarget).filter(
                ~AttentionTarget.id.in_(position_target_ids),
                AttentionTarget.is_active == True
            ).all()
            
            logger.info(f"🧹 Found {len(unused_targets)} unused targets to clean up")
            
            for target in unused_targets:
                # Delete historical data first
                db.query(AttentionHistory).filter(
                    AttentionHistory.target_id == target.id
                ).delete()
                
                # Delete the target
                db.delete(target)
                logger.info(f"🗑️ Deleted unused target: {target.name}")
            
            db.commit()
            logger.info(f"✅ Cleanup complete: removed {len(unused_targets)} unused targets")
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
            db.rollback()
        finally:
            db.close()

    async def _ensure_session(self):
        """Ensure we have a valid session"""
        now = datetime.utcnow()
        
        if (self.session is None or 
            self.session.closed or 
            (self.session_created_at and now - self.session_created_at > self.session_lifetime)):
            
            await self._close_session()
            await self._create_session()
    
    async def _create_session(self):
        """Create new session with proper configuration"""
        connector = aiohttp.TCPConnector(
            limit=10,
            limit_per_host=2,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.headers,
            cookie_jar=aiohttp.CookieJar()
        )
        
        self.session_created_at = datetime.utcnow()
        logger.info("🍪 Created new Google Trends session")
        
    async def _close_session(self):
        """Close existing session"""
        if self.session and not self.session.closed:
            await self.session.close()
        self.session = None
        self.session_created_at = None

    async def _rate_limit(self):
        """Rate limiting to avoid being blocked by Google"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_delay:
            sleep_time = self.min_delay - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()


# Background task functions
async def run_data_updates():
    """
    Background task to update all active targets every 3 minutes with real data
    Also runs cleanup every hour to remove unused targets
    """
    logger.info("🔄 Starting real-time data updates (3-minute intervals)...")
    
    cleanup_counter = 0
    
    while True:
        try:
            db = SessionLocal()
            
            # Get all active targets
            active_targets = db.query(AttentionTarget).filter(
                AttentionTarget.is_active == True
            ).all()
            
            if active_targets:
                logger.info(f"📊 Updating {len(active_targets)} targets with real Google Trends data...")
                
                # Update targets with real data
                async with GoogleTrendsService() as service:
                    for target in active_targets:
                        try:
                            await service.update_target_data(target, db)
                            
                            # Small delay between requests to respect rate limits
                            await asyncio.sleep(3)
                            
                        except Exception as e:
                            logger.error(f"Failed to update target {target.name}: {e}")
                            continue
                
                logger.info("✅ Real-time data update cycle completed")
            
            db.close()
            
            # Run cleanup every 20 cycles (every hour if updates are every 3 minutes)
            cleanup_counter += 1
            if cleanup_counter >= 20:
                async with GoogleTrendsService() as service:
                    await service.cleanup_unused_targets()
                cleanup_counter = 0
            
            # Wait for next update (3 minutes)
            await asyncio.sleep(180)  # 3 minutes
            
        except Exception as e:
            logger.error(f"❌ Background update error: {e}")
            await asyncio.sleep(60)  # Wait 1 minute on error before retrying

async def update_all_targets():
    """Manual trigger to update all targets immediately"""
    logger.info("🔄 Manual real-time update of all targets...")
    
    db = SessionLocal()
    try:
        active_targets = db.query(AttentionTarget).filter(
            AttentionTarget.is_active == True
        ).all()
        
        updated_count = 0
        async with GoogleTrendsService() as service:
            for target in active_targets:
                success = await service.update_target_data(target, db)
                if success:
                    updated_count += 1
                
                # Rate limiting
                await asyncio.sleep(3)
        
        logger.info(f"✅ Manual update completed: {updated_count}/{len(active_targets)} targets updated")
        
    except Exception as e:
        logger.error(f"❌ Manual update failed: {e}")
    finally:
        db.close()

def get_service_status() -> Dict:
    """Get status information about the Google Trends service"""
    return {
        "service": "GoogleTrendsService",
        "version": "3.0_real_data_only",
        "data_source": "google_trends_api",
        "update_interval": "3_minutes",
        "cleanup_enabled": True,
        "mock_data": False,
        "timestamp": datetime.utcnow().isoformat()
    }