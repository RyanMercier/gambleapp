"""
Complete Google Trends Service - Fixed timestamp handling
"""

import aiohttp
import json
import asyncio
import time
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List
from sqlalchemy.orm import Session
from database import SessionLocal
from models import AttentionTarget, AttentionHistory

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleTrendsService:
    """Google Trends API service with proper timestamp handling"""
    
    def __init__(self, websocket_manager=None):
        self.session = None
        self.session_created_at = None
        self.last_request_time = 0
        self.min_delay = 3
        self.cookies = {}
        
        # API URLs
        self.base_url = 'https://trends.google.com/trends'
        self.explore_url = f"{self.base_url}/api/explore"
        self.timeline_url = f"{self.base_url}/api/widgetdata/multiline"
        
        # Headers
        self.headers = {
            'accept-language': 'en-US',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
        }
        
        # Widget storage
        self.timeline_widget = None

        self.websocket_manager = websocket_manager
        
    async def __aenter__(self):
        await self._create_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._close_session()

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

    async def get_google_trends_data(self, search_term: str, timeframe: str = "now 1-d") -> dict:
        """Get Google Trends data with proper timestamp handling"""
        try:
            # Step 1: Get widget token
            if not await self._get_widget_token(search_term, timeframe):
                logger.error(f"❌ Failed to get widget token for {search_term}")
                return {"success": False}
            
            # Step 2: Get timeline data
            timeline_data = await self._get_timeline_data()
            if not timeline_data or not timeline_data.get('success'):
                logger.error(f"❌ Failed to get timeline data for {search_term}")
                return {"success": False}
            
            # Add metadata
            timeline_data.update({
                'search_term': search_term,
                'timeframe': timeframe,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            logger.info(f"✅ Got trend score for {search_term}: {timeline_data['attention_score']:.1f}")
            return timeline_data
            
        except Exception as e:
            logger.error(f"❌ Error getting data for {search_term}: {e}")
            return {"success": False}

    async def _get_widget_token(self, search_term: str, timeframe: str) -> bool:
        """Get widget token from explore endpoint"""
        await self._rate_limit()
        
        # Build payload
        payload = {
            'hl': 'en-US',
            'tz': 0,
            'req': json.dumps({
                'comparisonItem': [{'keyword': search_term, 'time': timeframe, 'geo': ''}],
                'category': 0,
                'property': ''
            })
        }
        
        try:
            async with self.session.post(self.explore_url, params=payload, cookies=self.cookies) as response:
                if response.status != 200:
                    logger.error(f"❌ Explore request failed: {response.status}")
                    return False
                
                text = await response.text()
                # Trim 4 characters and parse
                data = json.loads(text[4:])
                
                # Find timeline widget
                widgets = data.get('widgets', [])
                for widget in widgets:
                    if widget.get('id') == 'TIMESERIES':
                        self.timeline_widget = widget
                        return True
                
                logger.error("❌ No TIMESERIES widget found")
                return False
                
        except Exception as e:
            logger.error(f"❌ Widget token request failed: {e}")
            return False

    async def _get_timeline_data(self) -> Dict:
        """Get timeline data using widget token"""
        if not self.timeline_widget:
            return {"success": False, "error": "No timeline widget"}
        
        await self._rate_limit()
        
        # Build timeline request
        payload = {
            'req': json.dumps(self.timeline_widget['request']),
            'token': self.timeline_widget['token'],
            'tz': 0
        }
        
        try:
            async with self.session.get(self.timeline_url, params=payload, cookies=self.cookies) as response:
                if response.status != 200:
                    return {"success": False, "error": f"Timeline request failed: {response.status}"}
                
                text = await response.text()
                # Trim 5 characters and parse
                data = json.loads(text[5:])
                
                # Extract timeline data
                timeline_data = data.get('default', {}).get('timelineData', [])
                if not timeline_data:
                    return {"success": False, "error": "No timeline data"}
                
                # Parse values and timestamps with proper timezone handling
                values = []
                timestamps = []
                
                for entry in timeline_data:
                    if 'value' in entry and entry['value']:
                        values.append(entry['value'][0])
                        if 'time' in entry:
                            # Convert Google's timestamp to proper datetime
                            timestamp_str = str(entry['time'])
                            try:
                                # Google returns Unix timestamp as string
                                timestamp_float = float(timestamp_str)
                                # Convert to UTC datetime
                                dt = datetime.fromtimestamp(timestamp_float, tz=timezone.utc)
                                dt = dt - timedelta(hours=4)  # Subtract the 4-hour offset for NY Time
                                # Store as UTC but without timezone info for database compatibility
                                timestamps.append(dt.replace(tzinfo=None))
                                logger.debug(f"🕐 Parsed timestamp: {timestamp_str} -> {dt}")
                            except (ValueError, OSError) as e:
                                logger.error(f"❌ Failed to parse timestamp {timestamp_str}: {e}")
                                # Use current time as fallback
                                timestamps.append(datetime.utcnow())
                
                if not values:
                    return {"success": False, "error": "No values in timeline"}
                
                return {
                    'success': True,
                    'attention_score': float(values[-1]),
                    'timeline': values,
                    'timeline_timestamps': timestamps  # Now datetime objects, not strings
                }
                
        except Exception as e:
            return {"success": False, "error": f"Timeline parsing failed: {e}"}

    async def _rate_limit(self):
        """Simple rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_delay:
            sleep_time = self.min_delay - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()

    async def update_target_data(self, target: AttentionTarget, db: Session) -> bool:
        """Update target with real-time data using current timestamp"""
        try:
            logger.info(f"🔄 Updating {target.name}...")
            
            # Get real-time data
            data = await self.get_google_trends_data(target.search_term, timeframe="now 1-d")
            
            if not data.get('success'):
                logger.error(f"❌ Failed to get data for {target.name}")
                return False
            
            new_score = data["attention_score"]
            old_score = float(target.current_attention_score)
            
            # Update target
            target.current_attention_score = Decimal(str(new_score))
            target.last_updated = datetime.utcnow()
            
            # Store real-time data point with current UTC time
            current_utc = datetime.utcnow()
            current_utc = current_utc - timedelta(hours=4) # Adjust for NY Time offset
            
            history_entry = AttentionHistory(
                target_id=target.id,
                attention_score=Decimal(str(new_score)),
                timestamp=current_utc,  # Use current UTC time for real-time updates
                data_source="google_trends_realtime",
                timeframe_used="now 1-d",
                confidence_score=Decimal("1.0")
            )
            db.add(history_entry)
            
            # Clean up old real-time data (keep 48 hours)
            cutoff = current_utc - timedelta(hours=48)
            deleted = db.query(AttentionHistory).filter(
                AttentionHistory.target_id == target.id,
                AttentionHistory.data_source == "google_trends_realtime",
                AttentionHistory.timestamp < cutoff
            ).delete()
            
            db.commit()
            
            change = new_score - old_score
            logger.info(f"✅ {target.name}: {old_score:.1f} → {new_score:.1f} ({change:+.1f}) at {current_utc}")
            if deleted > 0:
                logger.info(f"🗑️ Cleaned up {deleted} old real-time points")

            # FIX: Send WebSocket notification for real-time chart updates
            if self.websocket_manager:
                try:
                    await self.websocket_manager.send_target_update(target.id, {
                        "type": "attention_update",
                        "target_id": target.id,
                        "attention_score": float(new_score),
                        "timestamp": current_utc.isoformat(),
                        "change": float(change),
                        "target_name": target.name
                    })
                    logger.info(f"📡 Sent WebSocket update for {target.name}")
                except Exception as e:
                    logger.error(f"❌ Failed to send WebSocket update for {target.name}: {e}")
            else:
                logger.debug(f"⚠️ No WebSocket manager - skipping real-time notification for {target.name}")
            
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating {target.name}: {e}")
            db.rollback()
            return False

    async def update_all_targets(self):
        """Update all active targets"""
        db = SessionLocal()
        try:
            targets = db.query(AttentionTarget).filter(
                AttentionTarget.is_active == True
            ).all()
            
            logger.info(f"🔄 Updating {len(targets)} targets...")
            
            updated = 0
            for target in targets:
                if await self.update_target_data(target, db):
                    updated += 1
                await asyncio.sleep(3)  # Rate limit
            
            logger.info(f"✅ Updated {updated}/{len(targets)} targets")
            
        except Exception as e:
            logger.error(f"❌ Update cycle failed: {e}")
        finally:
            db.close()


# Background updater function for compatibility
async def run_background_updates(websocket_manager=None):
    """Run background updates every 5 minutes"""
    cycle = 0
    
    while True:
        try:
            cycle += 1
            logger.info(f"🔄 Starting update cycle #{cycle}")
            
            # FIX: Pass WebSocket manager to service
            async with GoogleTrendsService(websocket_manager=websocket_manager) as service:
                await service.update_all_targets()
            
            logger.info(f"✅ Cycle #{cycle} complete")
            await asyncio.sleep(300)  # 5 minutes
            
        except Exception as e:
            logger.error(f"❌ Cycle #{cycle} failed: {e}")
            await asyncio.sleep(300)

if __name__ == "__main__":
    asyncio.run(run_background_updates())