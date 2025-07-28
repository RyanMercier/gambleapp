"""
EXACT PyTrends Implementation - Stolen from GitHub
Key fixes:
1. POST method for /api/explore (not GET!)
2. Proper cookie management 
3. Correct trim_chars values
4. Exact payload structure
"""

import aiohttp
import json
import asyncio
import time
import logging
from datetime import datetime
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class ExactPyTrendsAPI:
    def __init__(self):
        self.session = None
        self.hl = 'en-US'
        self.tz = 360
        self.geo = ''
        self.cookies = {}
        
        # Exact URLs from pytrends
        self.base_url = 'https://trends.google.com/trends'
        self.explore_url = f"{self.base_url}/api/explore"
        self.interest_over_time_url = f"{self.base_url}/api/widgetdata/multiline"
        self.interest_by_region_url = f"{self.base_url}/api/widgetdata/comparedgeo"
        
        # Payloads (like pytrends)
        self.token_payload = {}
        self.interest_over_time_widget = {}
        self.interest_by_region_widget = {}
        
        self.last_request_time = 0
        self.min_delay = 2
        
        # Headers like pytrends
        self.headers = {
            'accept-language': self.hl,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
        }
        
    async def __aenter__(self):
        await self._create_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def _create_session(self):
        """Create session and get Google cookies (like pytrends does)"""
        connector = aiohttp.TCPConnector(limit=1, limit_per_host=1)
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.headers
        )
        
        # Get Google cookie (stolen from pytrends)
        logger.info("🍪 Getting Google cookies...")
        await self._get_google_cookie()
        
    async def _get_google_cookie(self):
        """Get Google cookie like pytrends does"""
        try:
            cookie_url = f'{self.base_url}/explore/?geo={self.hl[-2:]}'
            async with self.session.get(cookie_url) as response:
                if response.status == 200:
                    # Extract NID cookie (like pytrends does)
                    for cookie in response.cookies:
                        if cookie.key == 'NID':
                            self.cookies = {cookie.key: cookie.value}
                            logger.info(f"✅ Got Google cookie: {cookie.value[:20]}...")
                            return
                    logger.warning("⚠️ No NID cookie found")
                else:
                    logger.warning(f"⚠️ Cookie request failed: {response.status}")
        except Exception as e:
            logger.error(f"Cookie request failed: {e}")
    
    async def build_payload(self, kw_list, cat=0, timeframe='today 5-y', geo='', gprop=''):
        """
        EXACT build_payload implementation from pytrends
        """
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
        """
        EXACT _tokens implementation from pytrends
        Makes POST request to get widget tokens
        """
        await self._rate_limit()
        
        logger.info("🔑 Getting tokens from explore endpoint...")
        logger.info(f"📋 Token payload: {self.token_payload}")
        
        try:
            # CRITICAL: Use POST method (not GET!) and pass as params
            async with self.session.post(
                self.explore_url, 
                params=self.token_payload,  # Pass as params, not data!
                cookies=self.cookies
            ) as response:
                
                logger.info(f"🔑 Explore response status: {response.status}")
                logger.info(f"📄 Content type: {response.headers.get('content-type', 'unknown')}")
                
                if response.status == 200:
                    response_text = await response.text()
                    logger.info(f"📝 Response length: {len(response_text)} chars")
                    logger.info(f"📄 Response preview: {response_text[:200]}...")
                    
                    # Parse response (trim 4 chars like pytrends)
                    widget_dicts = self._parse_explore_response(response_text, trim_chars=4)
                    
                    if widget_dicts:
                        self._assign_widgets(widget_dicts)
                        logger.info("✅ Successfully got tokens and assigned widgets")
                        return True
                    else:
                        logger.error("❌ Failed to parse widget data")
                        return False
                        
                elif response.status == 429:
                    logger.warning("🚫 Rate limited on explore endpoint")
                    self.min_delay = min(self.min_delay * 2, 60)
                    return False
                    
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Explore endpoint failed: {response.status}")
                    logger.error(f"📄 Error response: {error_text[:300]}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Explore request failed: {e}")
            return False
    
    def _parse_explore_response(self, response_text: str, trim_chars: int = 4):
        """Parse explore response to get widgets (like pytrends)"""
        try:
            # Trim chars like pytrends (4 for explore, 5 for widgets)
            content = response_text[trim_chars:]
            data = json.loads(content)
            
            logger.info(f"🔑 Parsed explore data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            if 'widgets' in data:
                widgets = data['widgets']
                logger.info(f"✅ Found {len(widgets)} widgets")
                return widgets
            else:
                logger.warning("⚠️ No 'widgets' key in response")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing failed: {e}")
            logger.error(f"📄 Response preview: {response_text[:500]}")
            return None
        except Exception as e:
            logger.error(f"❌ Response parsing failed: {e}")
            return None
    
    def _assign_widgets(self, widget_dicts):
        """Assign widgets exactly like pytrends does"""
        first_region_token = True
        
        for widget in widget_dicts:
            widget_id = widget.get('id', '')
            
            if widget_id == 'TIMESERIES':
                self.interest_over_time_widget = widget
                logger.info("✅ Assigned TIMESERIES widget")
                
            if widget_id == 'GEO_MAP' and first_region_token:
                self.interest_by_region_widget = widget
                first_region_token = False
                logger.info("✅ Assigned GEO_MAP widget")
    
    async def interest_over_time(self):
        """
        EXACT interest_over_time implementation from pytrends
        """
        if not self.interest_over_time_widget:
            logger.error("❌ No interest_over_time_widget available. Call build_payload first.")
            return None
        
        await self._rate_limit()
        
        # Build payload exactly like pytrends
        over_time_payload = {
            'req': json.dumps(self.interest_over_time_widget['request']),
            'token': self.interest_over_time_widget['token'],
            'tz': self.tz
        }
        
        logger.info("📈 Getting interest over time data...")
        logger.info(f"🔗 URL: {self.interest_over_time_url}")
        logger.info(f"🎫 Token: {over_time_payload['token'][:20]}...")
        
        try:
            async with self.session.get(
                self.interest_over_time_url,
                params=over_time_payload,
                cookies=self.cookies
            ) as response:
                
                logger.info(f"📈 Timeline response status: {response.status}")
                
                if response.status == 200:
                    response_text = await response.text()
                    logger.info(f"📝 Timeline response length: {len(response_text)} chars")
                    
                    # Parse response (trim 5 chars for widget endpoints)
                    return self._parse_timeline_response(response_text, trim_chars=5)
                    
                elif response.status == 429:
                    logger.warning("🚫 Rate limited on timeline endpoint")
                    return None
                    
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Timeline endpoint failed: {response.status}")
                    logger.error(f"📄 Error: {error_text[:200]}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Timeline request failed: {e}")
            return None
    
    async def interest_by_region(self, resolution='COUNTRY', inc_low_vol=False):
        """
        EXACT interest_by_region implementation from pytrends
        """
        if not self.interest_by_region_widget:
            logger.error("❌ No interest_by_region_widget available. Call build_payload first.")
            return None
        
        await self._rate_limit()
        
        # Modify request like pytrends does
        if self.geo == '':
            self.interest_by_region_widget['request']['resolution'] = resolution
        elif self.geo == 'US' and resolution in ['DMA', 'CITY', 'REGION']:
            self.interest_by_region_widget['request']['resolution'] = resolution
        
        self.interest_by_region_widget['request']['includeLowSearchVolumeGeos'] = inc_low_vol
        
        # Build payload exactly like pytrends
        region_payload = {
            'req': json.dumps(self.interest_by_region_widget['request']),
            'token': self.interest_by_region_widget['token'],
            'tz': self.tz
        }
        
        logger.info("🗺️ Getting interest by region data...")
        logger.info(f"🔗 URL: {self.interest_by_region_url}")
        logger.info(f"🎫 Token: {region_payload['token'][:20]}...")
        
        try:
            async with self.session.get(
                self.interest_by_region_url,
                params=region_payload,
                cookies=self.cookies
            ) as response:
                
                logger.info(f"🗺️ Region response status: {response.status}")
                
                if response.status == 200:
                    response_text = await response.text()
                    logger.info(f"📝 Region response length: {len(response_text)} chars")
                    
                    # Parse response (trim 5 chars for widget endpoints)
                    return self._parse_region_response(response_text, trim_chars=5)
                    
                elif response.status == 429:
                    logger.warning("🚫 Rate limited on region endpoint")
                    return None
                    
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Region endpoint failed: {response.status}")
                    logger.error(f"📄 Error: {error_text[:200]}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Region request failed: {e}")
            return None
    
    def _parse_timeline_response(self, response_text: str, trim_chars: int = 5):
        """Parse timeline response like pytrends"""
        try:
            content = response_text[trim_chars:]
            data = json.loads(content)
            
            logger.info(f"📊 Timeline data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            # Extract timeline data like pytrends
            if 'default' in data and 'timelineData' in data['default']:
                timeline_data = data['default']['timelineData']
                logger.info(f"✅ Found {len(timeline_data)} timeline points")
                
                # Extract latest value
                if timeline_data:
                    latest_entry = timeline_data[-1]
                    if 'value' in latest_entry and len(latest_entry['value']) > 0:
                        latest_score = latest_entry['value'][0]
                        
                        # Extract all values for timeline
                        timeline_values = []
                        for entry in timeline_data:
                            if 'value' in entry and len(entry['value']) > 0:
                                timeline_values.append(entry['value'][0])
                        
                        return {
                            'success': True,
                            'search_term': self.kw_list[0] if self.kw_list else 'unknown',
                            'attention_score': float(latest_score),
                            'timeline': timeline_values,
                            'timeline_length': len(timeline_values),
                            'average_score': sum(timeline_values) / len(timeline_values) if timeline_values else 0,
                            'max_score': max(timeline_values) if timeline_values else 0,
                            'source': 'exact_pytrends',
                            'timestamp': datetime.utcnow().isoformat()
                        }
            
            logger.warning("⚠️ No timeline data found in expected format")
            return {
                'success': False,
                'error': 'No timeline data found',
                'raw_keys': list(data.keys()) if isinstance(data, dict) else []
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Timeline JSON parsing failed: {e}")
            return {'success': False, 'error': f'JSON parsing failed: {e}'}
        except Exception as e:
            logger.error(f"❌ Timeline parsing failed: {e}")
            return {'success': False, 'error': f'Parsing failed: {e}'}
    
    def _parse_region_response(self, response_text: str, trim_chars: int = 5):
        """Parse region response like pytrends"""
        try:
            content = response_text[trim_chars:]
            data = json.loads(content)
            
            logger.info(f"🗺️ Region data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            # Extract region data like pytrends
            if 'default' in data and 'geoMapData' in data['default']:
                geo_data = data['default']['geoMapData']
                logger.info(f"✅ Found {len(geo_data)} regions")
                
                # Parse region data
                regions = []
                for region in geo_data:
                    if 'geoName' in region and 'value' in region:
                        regions.append({
                            'region': region['geoName'],
                            'value': region['value'][0] if region['value'] else 0
                        })
                
                return {
                    'success': True,
                    'search_term': self.kw_list[0] if self.kw_list else 'unknown',
                    'regions': regions,
                    'region_count': len(regions),
                    'source': 'exact_pytrends',
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            logger.warning("⚠️ No region data found in expected format")
            return {
                'success': False,
                'error': 'No region data found',
                'raw_keys': list(data.keys()) if isinstance(data, dict) else []
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Region JSON parsing failed: {e}")
            return {'success': False, 'error': f'JSON parsing failed: {e}'}
        except Exception as e:
            logger.error(f"❌ Region parsing failed: {e}")
            return {'success': False, 'error': f'Parsing failed: {e}'}
    
    async def _rate_limit(self):
        """Rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_delay:
            sleep_time = self.min_delay - time_since_last
            logger.info(f"⏱️ Rate limiting: sleeping for {sleep_time:.1f} seconds")
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    # Convenience method that mimics the working pytrends pattern
    async def get_trend_score(self, search_term: str, timeframe: str = "now 7-d", geo: str = "US") -> dict:
        """
        Get trend score using the exact pytrends workflow:
        1. build_payload()
        2. interest_over_time()
        """
        try:
            # Step 1: Build payload (like pytrends)
            await self.build_payload(kw_list=[search_term], timeframe=timeframe, geo=geo)
            
            # Step 2: Get interest over time (like pytrends)
            result = await self.interest_over_time()
            
            return result or {
                'success': False,
                'error': 'Failed to get timeline data',
                'search_term': search_term,
                'attention_score': -1.0
            }
            
        except Exception as e:
            logger.error(f"get_trend_score failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'search_term': search_term,
                'attention_score': -1.0
            }

# Test function that mimics working pytrends usage
async def test_exact_pytrends():
    """Test the exact pytrends implementation"""
    
    logging.basicConfig(level=logging.INFO)
    
    test_terms = [
        ("Taylor Swift", "now 7-d"),
        ("bitcoin", "now 7-d"),
        ("tesla", "now 7-d")
    ]
    
    print("🎯 Testing EXACT PyTrends Implementation")
    print("=" * 60)
    print("✨ Key fixes applied:")
    print("  - POST method for /api/explore (not GET!)")
    print("  - Proper cookie management with NID cookie")
    print("  - Exact payload structure from pytrends source")
    print("  - Correct trim_chars values (4 for explore, 5 for widgets)")
    print("  - Widget assignment logic stolen from pytrends")
    print("")
    
    results = []
    
    async with ExactPyTrendsAPI() as api:
        for i, (term, timeframe) in enumerate(test_terms):
            print(f"🔍 Test {i+1}/{len(test_terms)}: {term} ({timeframe})")
            
            result = await api.get_trend_score(term, timeframe)
            
            if result.get("success"):
                score = result["attention_score"]
                timeline_length = result.get("timeline_length", 0)
                avg_score = result.get("average_score", 0)
                max_score = result.get("max_score", 0)
                
                print(f"  ✅ SUCCESS!")
                print(f"    📈 Latest score: {score}")
                print(f"    📊 Timeline points: {timeline_length}")
                print(f"    📉 Average score: {avg_score:.1f}")
                print(f"    📈 Max score: {max_score}")
                
                results.append({"term": term, "success": True, "score": score})
                
                # Test interest_by_region too (since you mentioned it works)
                print(f"  🗺️ Testing interest by region...")
                region_result = await api.interest_by_region()
                if region_result and region_result.get("success"):
                    region_count = region_result.get("region_count", 0)
                    print(f"    🗺️ Found {region_count} regions")
                else:
                    print(f"    🗺️ Region failed: {region_result.get('error', 'unknown') if region_result else 'no result'}")
            else:
                print(f"  ❌ FAILED: {result.get('error', 'unknown error')}")
                results.append({"term": term, "success": False, "error": result.get('error', 'unknown')})
            
            print("")
            
            # Progressive delay
            if i < len(test_terms) - 1:
                delay = 3 + (i * 2)
                print(f"⏱️ Waiting {delay} seconds before next request...")
                await asyncio.sleep(delay)
    
    # Summary
    successful = [r for r in results if r["success"]]
    print("=" * 60)
    print("📊 FINAL RESULTS")
    print("=" * 60)
    print(f"✅ Successful: {len(successful)}/{len(results)}")
    print(f"❌ Failed: {len(results) - len(successful)}/{len(results)}")
    
    if successful:
        avg_score = sum(r["score"] for r in successful) / len(successful)
        print(f"📈 Average score: {avg_score:.1f}")
        print("")
        print("🎉 SUCCESS! Exact PyTrends implementation works!")
        print("💡 Key insights:")
        print("  - POST method is CRITICAL for /api/explore")
        print("  - Cookie management is essential")
        print("  - Widget token system works exactly like pytrends")
        print("  - Trim characters matter (4 vs 5)")
        print("")
        print("💰 You've successfully reverse-engineered Google Trends!")
        print("🚀 This can replace SerpAPI and save costs!")
    else:
        print("")
        print("🔧 Still need debugging")
        print("💡 Check logs for specific error details")
    
    return len(successful) > 0

# Simple usage function
async def get_trend_score_simple(search_term: str, timeframe: str = "now 7-d", geo: str = "US") -> float:
    """
    Simple function to get a trend score
    """
    async with ExactPyTrendsAPI() as api:
        result = await api.get_trend_score(search_term, timeframe, geo)
        return result.get("attention_score", -1.0)

if __name__ == "__main__":
    # Run the test
    import asyncio
    asyncio.run(test_exact_pytrends())
    
    # Example usage:
    # score = asyncio.run(get_trend_score_simple("Taylor Swift"))
    # print(f"Taylor Swift trend score: {score}")