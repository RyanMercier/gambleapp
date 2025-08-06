import aiohttp
import asyncio
import logging
import json
import asyncio
import time
import logging
import sys
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_cookie_extraction():
    """Debug exactly what cookie format we're getting"""
    
    print("🔍 Debugging cookie extraction...")
    print("=" * 50)
    
    base_url = 'https://trends.google.com/trends'
    hl = 'en-US'
    
    # EXACT headers from working code
    headers = {
        'accept-language': hl,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
    }
    
    # EXACT session config from working code
    connector = aiohttp.TCPConnector(limit=1, limit_per_host=1)
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    
    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        headers=headers
    ) as session:
        
        # EXACT URL from working code
        cookie_url = f'{base_url}/explore/?geo={hl[-2:]}'
        print(f"🍪 Cookie URL: {cookie_url}")
        
        async with session.get(cookie_url) as response:
            print(f"📊 Response status: {response.status}")
            print(f"📄 Content type: {response.headers.get('content-type', 'unknown')}")
            
            if response.status == 200:
                # Debug: What type is response.cookies?
                print(f"🔍 Cookie object type: {type(response.cookies)}")
                print(f"🔍 Cookie object dir: {[attr for attr in dir(response.cookies) if not attr.startswith('_')]}")
                
                try:
                    # Try to see what's in cookies
                    print(f"🔍 Raw cookies: {response.cookies}")
                    print(f"🔍 Cookie length: {len(response.cookies) if hasattr(response.cookies, '__len__') else 'No len'}")
                    
                    # Method 1: Working code method - iterate with .key/.value
                    print("\n🧪 Testing Method 1 (working code method):")
                    cookies_method1 = {}
                    try:
                        for i, cookie in enumerate(response.cookies):
                            print(f"   Cookie {i}: type={type(cookie)}, value={cookie}")
                            if hasattr(cookie, 'key') and hasattr(cookie, 'value'):
                                print(f"   Cookie {i}: {cookie.key} = {cookie.value[:20]}...")
                                cookies_method1[cookie.key] = cookie.value
                                if cookie.key == 'NID':
                                    print(f"   ✅ Found NID cookie!")
                            else:
                                print(f"   ❌ Cookie {i} has no .key/.value attributes")
                        
                        print(f"   Result: {len(cookies_method1)} cookies extracted")
                        
                    except Exception as e:
                        print(f"   ❌ Method 1 failed: {e}")
                    
                    # Method 2: Dict conversion
                    print("\n🧪 Testing Method 2 (dict conversion):")
                    try:
                        cookies_method2 = dict(response.cookies)
                        print(f"   Result: {len(cookies_method2)} cookies: {list(cookies_method2.keys())}")
                    except Exception as e:
                        print(f"   ❌ Method 2 failed: {e}")
                    
                    # Method 3: Alternative iteration
                    print("\n🧪 Testing Method 3 (alternative iteration):")
                    try:
                        cookies_method3 = {}
                        if hasattr(response.cookies, 'items'):
                            for name, value in response.cookies.items():
                                print(f"   Cookie: {name} = {value[:20] if isinstance(value, str) else value}...")
                                cookies_method3[name] = value
                        print(f"   Result: {len(cookies_method3)} cookies")
                    except Exception as e:
                        print(f"   ❌ Method 3 failed: {e}")
                    
                    # Method 4: Check for specific aiohttp version differences
                    print("\n🧪 Testing Method 4 (version-specific):")
                    try:
                        print(f"   aiohttp version: {aiohttp.__version__}")
                        
                        cookies_method4 = {}
                        # Try accessing cookies as a list
                        if hasattr(response.cookies, '__iter__'):
                            for cookie in response.cookies:
                                print(f"   Cookie object: {type(cookie)} = {cookie}")
                                
                                # Try different attribute names
                                for attr_pair in [('key', 'value'), ('name', 'value'), ('k', 'v')]:
                                    key_attr, val_attr = attr_pair
                                    if hasattr(cookie, key_attr) and hasattr(cookie, val_attr):
                                        key = getattr(cookie, key_attr)
                                        value = getattr(cookie, val_attr)
                                        print(f"   Found: {key} = {value[:20] if isinstance(value, str) else value}...")
                                        cookies_method4[key] = value
                                        break
                        
                        print(f"   Result: {len(cookies_method4)} cookies")
                    except Exception as e:
                        print(f"   ❌ Method 4 failed: {e}")
                
                except Exception as e:
                    print(f"❌ All cookie debugging failed: {e}")
            else:
                print(f"❌ HTTP request failed: {response.status}")
                error_text = await response.text()
                print(f"📄 Error response: {error_text[:200]}...")

async def test_working_implementation():
    """Test the exact working implementation from ExactPyTrendsAPI"""
    print("\n" + "="*50)
    print("🧪 Testing EXACT working implementation")
    print("="*50)
    
    from google_trends_service import GoogleTrendsService
    
    try:
        async with GoogleTrendsService() as service:
            result = await service.get_google_trends_data("Bitcoin", "now 7-d")
            
            if result.get('success'):
                print(f"✅ Working implementation SUCCESS!")
                print(f"   Score: {result['attention_score']}")
                print(f"   Timeline points: {len(result.get('timeline', []))}")
            else:
                print(f"❌ Working implementation FAILED: {result.get('error')}")
                
    except Exception as e:
        print(f"❌ Working implementation EXCEPTION: {e}")

async def main():
    """Run all cookie debugging"""
    await debug_cookie_extraction()
    await test_working_implementation()
    
    print("\n" + "="*50)
    print("🎯 DIAGNOSIS")
    print("="*50)
    print("Run this script and check the output above.")
    print("This will show exactly what cookie format you're getting")
    print("and help us fix the cookie extraction logic.")

if __name__ == "__main__":
    asyncio.run(main())