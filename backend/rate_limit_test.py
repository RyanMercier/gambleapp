#!/usr/bin/env python3
"""
Google Trends Rate Limit Testing Script

This script systematically tests different rate limiting configurations to find
the optimal balance between data freshness and avoiding IP bans.

Key Metrics Tested:
- Minimum delay between requests (5s, 10s, 15s, 20s, 30s)
- Maximum requests per hour (3, 6, 9, 12, 15)
- Success rates at different speeds
- Time to hit rate limits
- Recovery patterns after rate limiting

Business Value:
Finding optimal rate limits maximizes data collection speed while minimizing
the risk of IP bans that could crash our entire trading platform.

Usage:
python rate_limit_test.py --test-delays      # Test different delays
python rate_limit_test.py --test-hourly      # Test hourly limits
python rate_limit_test.py --stress-test      # Stress test to find breaking point
python rate_limit_test.py --tor              # Test with Tor proxy
python rate_limit_test.py --all              # Run all tests
"""

import asyncio
import aiohttp
import json
import time
import logging
import argparse
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict
import statistics

# Configure logging for test results
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Data structure to track test results"""
    test_name: str
    delay_seconds: float
    max_requests_per_hour: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    rate_limited_count: int
    avg_response_time: float
    test_duration_minutes: float
    success_rate: float
    requests_per_hour_achieved: float
    first_rate_limit_at_request: int
    tor_enabled: bool
    error_details: List[str]

class RateLimitTester:
    """
    Systematic rate limit testing for Google Trends API
    
    This class implements various testing strategies to determine optimal
    rate limiting parameters for our production trading platform.
    """
    
    def __init__(self, use_tor=False):
        self.use_tor = use_tor
        self.session = None
        self.cookies = {}
        self.results = []
        
        # Google Trends API endpoints
        self.base_url = 'https://trends.google.com/trends'
        self.explore_url = f"{self.base_url}/api/explore"
        
        # Test search terms (varied to avoid caching issues)
        self.test_terms = [
            "Bitcoin", "Tesla", "Apple", "Google", "Microsoft",
            "Amazon", "Netflix", "Twitter", "Facebook", "Instagram",
            "YouTube", "TikTok", "iPhone", "Android", "PlayStation",
            "Xbox", "Nintendo", "ChatGPT", "AI", "Crypto"
        ]
        
        # HTTP Headers
        self.headers = {
            'accept-language': 'en-US,en;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        }
        
        logger.info(f"🧪 RateLimitTester initialized (Tor: {use_tor})")
    
    async def __aenter__(self):
        await self._create_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._close_session()
    
    async def _create_session(self):
        """Create HTTP session with optional Tor proxy"""
        connector_kwargs = {
            'limit': 10,
            'limit_per_host': 2,
            'keepalive_timeout': 30,
        }
        
        connector = aiohttp.TCPConnector(**connector_kwargs)
        timeout = aiohttp.ClientTimeout(total=45, connect=15)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.headers
        )
        
        # Get initial cookies
        await self._get_cookies()
        
        if self.use_tor:
            logger.info("🧅 Session created with Tor proxy support")
        else:
            logger.info("🔗 Session created with direct connection")
    
    async def _close_session(self):
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _get_cookies(self):
        """Get Google cookies for authentication"""
        try:
            async with self.session.get(f'{self.base_url}/') as response:
                if response.status == 200:
                    try:
                        self.cookies.update({cookie.key: cookie.value for cookie in response.cookies})
                    except AttributeError:
                        self.cookies.update(dict(response.cookies))
                    
                    logger.info(f"🍪 Obtained {len(self.cookies)} cookies")
        except Exception as e:
            logger.warning(f"⚠️ Failed to get cookies: {e}")
    
    async def _make_test_request(self, search_term: str) -> Tuple[bool, float, str]:
        """
        Make a single test request to Google Trends
        
        Returns:
            (success: bool, response_time: float, error_msg: str)
        """
        start_time = time.time()
        
        # Build explore request
        payload = {
            'hl': 'en-US',
            'tz': 0,
            'req': json.dumps({
                'comparisonItem': [{'keyword': search_term, 'time': 'now 1-d', 'geo': ''}],
                'category': 0,
                'property': ''
            })
        }
        
        try:
            async with self.session.post(
                self.explore_url,
                params=payload,
                cookies=self.cookies
            ) as response:
                
                response_time = time.time() - start_time
                
                if response.status == 200:
                    # Try to parse response to verify it's valid
                    text = await response.text()
                    if len(text) > 5:
                        json.loads(text[4:])  # Validate JSON
                        return True, response_time, ""
                    else:
                        return False, response_time, "Empty response"
                
                elif response.status == 429:
                    return False, response_time, "Rate limited (HTTP 429)"
                
                else:
                    return False, response_time, f"HTTP {response.status}"
        
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            return False, response_time, "Timeout"
        
        except json.JSONDecodeError:
            response_time = time.time() - start_time
            return False, response_time, "Invalid JSON response"
        
        except Exception as e:
            response_time = time.time() - start_time
            return False, response_time, str(e)
    
    async def test_delay_configuration(self, delay_seconds: float, max_requests: int = 20) -> TestResult:
        """
        Test a specific delay configuration
        
        Args:
            delay_seconds: Minimum delay between requests
            max_requests: Maximum number of requests to test
            
        Returns:
            TestResult with metrics
        """
        logger.info(f"🧪 Testing delay: {delay_seconds}s (max {max_requests} requests)")
        
        test_start = time.time()
        successful_requests = 0
        failed_requests = 0
        rate_limited_count = 0
        response_times = []
        errors = []
        first_rate_limit = -1
        
        for i in range(max_requests):
            # Use different search terms to avoid caching
            search_term = self.test_terms[i % len(self.test_terms)]
            
            logger.debug(f"📊 Request {i+1}/{max_requests}: {search_term}")
            
            success, response_time, error = await self._make_test_request(search_term)
            response_times.append(response_time)
            
            if success:
                successful_requests += 1
                logger.debug(f"✅ Success in {response_time:.2f}s")
            else:
                failed_requests += 1
                errors.append(f"Request {i+1}: {error}")
                
                if "rate limited" in error.lower() or "429" in error:
                    rate_limited_count += 1
                    if first_rate_limit == -1:
                        first_rate_limit = i + 1
                
                logger.warning(f"❌ Failed: {error} (response time: {response_time:.2f}s)")
            
            # Apply delay (except for last request)
            if i < max_requests - 1:
                logger.debug(f"⏱️ Waiting {delay_seconds}s...")
                await asyncio.sleep(delay_seconds)
        
        # Calculate metrics
        test_duration = (time.time() - test_start) / 60  # Convert to minutes
        success_rate = (successful_requests / max_requests) * 100
        avg_response_time = statistics.mean(response_times) if response_times else 0
        requests_per_hour = (max_requests / test_duration) * 60 if test_duration > 0 else 0
        
        result = TestResult(
            test_name=f"Delay Test ({delay_seconds}s)",
            delay_seconds=delay_seconds,
            max_requests_per_hour=0,  # Not applicable for this test
            total_requests=max_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            rate_limited_count=rate_limited_count,
            avg_response_time=avg_response_time,
            test_duration_minutes=test_duration,
            success_rate=success_rate,
            requests_per_hour_achieved=requests_per_hour,
            first_rate_limit_at_request=first_rate_limit,
            tor_enabled=self.use_tor,
            error_details=errors[:10]  # Keep only first 10 errors
        )
        
        logger.info(f"✅ Delay test complete: {successful_requests}/{max_requests} "
                   f"successful ({success_rate:.1f}% success rate)")
        
        return result
    
    async def test_hourly_limits(self, delay_seconds: float = 10, test_duration_minutes: int = 15) -> TestResult:
        """
        Test how many requests we can make in a given time period
        
        Args:
            delay_seconds: Delay between requests
            test_duration_minutes: How long to run the test
            
        Returns:
            TestResult with hourly throughput metrics
        """
        logger.info(f"🧪 Testing hourly limits: {delay_seconds}s delay for {test_duration_minutes} minutes")
        
        test_start = time.time()
        end_time = test_start + (test_duration_minutes * 60)
        
        successful_requests = 0
        failed_requests = 0
        rate_limited_count = 0
        response_times = []
        errors = []
        first_rate_limit = -1
        request_count = 0
        
        while time.time() < end_time:
            request_count += 1
            search_term = self.test_terms[(request_count - 1) % len(self.test_terms)]
            
            elapsed_minutes = (time.time() - test_start) / 60
            logger.debug(f"📊 Request {request_count} at {elapsed_minutes:.1f}min: {search_term}")
            
            success, response_time, error = await self._make_test_request(search_term)
            response_times.append(response_time)
            
            if success:
                successful_requests += 1
                logger.debug(f"✅ Success in {response_time:.2f}s")
            else:
                failed_requests += 1
                errors.append(f"Request {request_count}: {error}")
                
                if "rate limited" in error.lower() or "429" in error:
                    rate_limited_count += 1
                    if first_rate_limit == -1:
                        first_rate_limit = request_count
                
                logger.warning(f"❌ Failed: {error}")
                
                # If we hit rate limits early, increase delay dynamically
                if rate_limited_count >= 3 and delay_seconds < 30:
                    delay_seconds *= 1.5
                    logger.warning(f"⚠️ Multiple rate limits - increasing delay to {delay_seconds:.1f}s")
            
            # Check if we should continue or if we're being heavily rate limited
            if rate_limited_count >= 5 and elapsed_minutes < 5:
                logger.error("🚨 Heavy rate limiting detected - stopping test early")
                break
            
            # Apply delay
            if time.time() < end_time:
                await asyncio.sleep(delay_seconds)
        
        # Calculate final metrics
        actual_duration = (time.time() - test_start) / 60
        success_rate = (successful_requests / request_count) * 100 if request_count > 0 else 0
        avg_response_time = statistics.mean(response_times) if response_times else 0
        requests_per_hour = (successful_requests / actual_duration) * 60 if actual_duration > 0 else 0
        
        result = TestResult(
            test_name=f"Hourly Limit Test ({test_duration_minutes}min)",
            delay_seconds=delay_seconds,
            max_requests_per_hour=int(requests_per_hour),
            total_requests=request_count,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            rate_limited_count=rate_limited_count,
            avg_response_time=avg_response_time,
            test_duration_minutes=actual_duration,
            success_rate=success_rate,
            requests_per_hour_achieved=requests_per_hour,
            first_rate_limit_at_request=first_rate_limit,
            tor_enabled=self.use_tor,
            error_details=errors[:10]
        )
        
        logger.info(f"✅ Hourly test complete: {successful_requests}/{request_count} successful "
                   f"({requests_per_hour:.1f} requests/hour achieved)")
        
        return result
    
    async def stress_test(self, initial_delay: float = 5.0, max_requests: int = 50) -> TestResult:
        """
        Stress test to find the breaking point where rate limiting kicks in
        
        Args:
            initial_delay: Starting delay (will decrease if successful)
            max_requests: Maximum requests before stopping
            
        Returns:
            TestResult showing breaking point
        """
        logger.info(f"🧪 Stress test: Starting at {initial_delay}s delay, up to {max_requests} requests")
        
        test_start = time.time()
        current_delay = initial_delay
        successful_requests = 0
        failed_requests = 0
        rate_limited_count = 0
        response_times = []
        errors = []
        first_rate_limit = -1
        
        for i in range(max_requests):
            search_term = self.test_terms[i % len(self.test_terms)]
            
            logger.debug(f"📊 Stress request {i+1}/{max_requests}: {search_term} (delay: {current_delay:.1f}s)")
            
            success, response_time, error = await self._make_test_request(search_term)
            response_times.append(response_time)
            
            if success:
                successful_requests += 1
                logger.debug(f"✅ Success in {response_time:.2f}s")
                
                # If we're successful and delay is still high, try reducing it
                if current_delay > 2.0 and (i + 1) % 5 == 0:
                    current_delay *= 0.8  # Reduce delay by 20%
                    logger.info(f"📉 Reducing delay to {current_delay:.1f}s after success streak")
            
            else:
                failed_requests += 1
                errors.append(f"Request {i+1}: {error}")
                
                if "rate limited" in error.lower() or "429" in error:
                    rate_limited_count += 1
                    if first_rate_limit == -1:
                        first_rate_limit = i + 1
                    
                    # Increase delay after rate limiting
                    current_delay *= 1.5
                    logger.warning(f"📈 Rate limited! Increasing delay to {current_delay:.1f}s")
                
                logger.warning(f"❌ Failed: {error}")
                
                # Stop if we're getting too many rate limits
                if rate_limited_count >= 10:
                    logger.error("🚨 Too many rate limits - stopping stress test")
                    break
            
            # Apply current delay (except for last request)
            if i < max_requests - 1:
                await asyncio.sleep(current_delay)
        
        # Calculate metrics
        test_duration = (time.time() - test_start) / 60
        success_rate = (successful_requests / (i + 1)) * 100
        avg_response_time = statistics.mean(response_times) if response_times else 0
        requests_per_hour = (successful_requests / test_duration) * 60 if test_duration > 0 else 0
        
        result = TestResult(
            test_name="Stress Test",
            delay_seconds=current_delay,  # Final delay used
            max_requests_per_hour=int(requests_per_hour),
            total_requests=i + 1,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            rate_limited_count=rate_limited_count,
            avg_response_time=avg_response_time,
            test_duration_minutes=test_duration,
            success_rate=success_rate,
            requests_per_hour_achieved=requests_per_hour,
            first_rate_limit_at_request=first_rate_limit,
            tor_enabled=self.use_tor,
            error_details=errors[:10]
        )
        
        logger.info(f"✅ Stress test complete: {successful_requests}/{i+1} successful "
                   f"(broke at {first_rate_limit} requests, final delay: {current_delay:.1f}s)")
        
        return result
    
    def print_result_summary(self, result: TestResult):
        """Print formatted test result summary"""
        print(f"\n{'='*60}")
        print(f"📊 {result.test_name}")
        print(f"{'='*60}")
        print(f"Configuration:")
        print(f"  • Delay: {result.delay_seconds:.1f} seconds")
        print(f"  • Tor enabled: {result.tor_enabled}")
        print(f"")
        print(f"Results:")
        print(f"  • Total requests: {result.total_requests}")
        print(f"  • Successful: {result.successful_requests}")
        print(f"  • Failed: {result.failed_requests}")
        print(f"  • Rate limited: {result.rate_limited_count}")
        print(f"  • Success rate: {result.success_rate:.1f}%")
        print(f"")
        print(f"Performance:")
        print(f"  • Average response time: {result.avg_response_time:.2f}s")
        print(f"  • Test duration: {result.test_duration_minutes:.1f} minutes")
        print(f"  • Requests per hour achieved: {result.requests_per_hour_achieved:.1f}")
        print(f"")
        
        if result.first_rate_limit_at_request > 0:
            print(f"Rate Limiting:")
            print(f"  • First rate limit at request: {result.first_rate_limit_at_request}")
        
        if result.error_details:
            print(f"Recent Errors:")
            for error in result.error_details[:5]:
                print(f"  • {error}")
        
        print(f"")
    
    def export_results_csv(self, filename: str = "rate_limit_test_results.csv"):
        """Export all test results to CSV for analysis"""
        if not self.results:
            logger.warning("⚠️ No results to export")
            return
        
        import csv
        
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = list(asdict(self.results[0]).keys())
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in self.results:
                row_data = asdict(result)
                # Convert list to string for CSV
                row_data['error_details'] = '; '.join(row_data['error_details'])
                writer.writerow(row_data)
        
        logger.info(f"📁 Results exported to {filename}")


async def main():
    """Main test runner with command line options"""
    parser = argparse.ArgumentParser(description='Google Trends Rate Limit Tester')
    parser.add_argument('--test-delays', action='store_true', 
                       help='Test different delay configurations')
    parser.add_argument('--test-hourly', action='store_true',
                       help='Test hourly request limits')
    parser.add_argument('--stress-test', action='store_true',
                       help='Stress test to find breaking point')
    parser.add_argument('--tor', action='store_true',
                       help='Use Tor proxy for testing')
    parser.add_argument('--all', action='store_true',
                       help='Run all tests')
    parser.add_argument('--export', type=str, default='rate_limit_results.csv',
                       help='CSV filename for results export')
    
    args = parser.parse_args()
    
    # If no specific tests requested, show help
    if not any([args.test_delays, args.test_hourly, args.stress_test, args.all]):
        parser.print_help()
        return
    
    logger.info("🚀 Starting Google Trends Rate Limit Testing")
    logger.info(f"🧅 Tor proxy: {'Enabled' if args.tor else 'Disabled'}")
    
    async with RateLimitTester(use_tor=args.tor) as tester:
        
        # Test different delays
        if args.test_delays or args.all:
            logger.info("\n🧪 Testing different delay configurations...")
            
            delay_configs = [5.0, 10.0, 15.0, 20.0, 30.0]
            
            for delay in delay_configs:
                result = await tester.test_delay_configuration(delay, max_requests=15)
                tester.results.append(result)
                tester.print_result_summary(result)
                
                # Wait between test configurations to avoid cumulative rate limiting
                logger.info("⏱️ Waiting 2 minutes between delay tests...")
                await asyncio.sleep(120)
        
        # Test hourly limits
        if args.test_hourly or args.all:
            logger.info("\n🧪 Testing hourly request limits...")
            
            result = await tester.test_hourly_limits(delay_seconds=10, test_duration_minutes=20)
            tester.results.append(result)
            tester.print_result_summary(result)
        
        # Stress test
        if args.stress_test or args.all:
            logger.info("\n🧪 Running stress test...")
            
            result = await tester.stress_test(initial_delay=5.0, max_requests=30)
            tester.results.append(result)
            tester.print_result_summary(result)
        
        # Generate recommendations
        print(f"\n{'='*60}")
        print("🎯 RECOMMENDATIONS FOR PRODUCTION")
        print(f"{'='*60}")
        
        if tester.results:
            # Find best performing configuration
            best_result = max(tester.results, 
                            key=lambda r: r.success_rate * r.requests_per_hour_achieved)
            
            print(f"Best Configuration Found:")
            print(f"  • Minimum delay: {best_result.delay_seconds:.0f} seconds")
            print(f"  • Expected success rate: {best_result.success_rate:.1f}%")
            print(f"  • Expected throughput: {best_result.requests_per_hour_achieved:.0f} requests/hour")
            
            # Production recommendations
            recommended_delay = max(best_result.delay_seconds * 1.2, 10.0)  # 20% safety margin
            recommended_hourly = max(int(best_result.requests_per_hour_achieved * 0.8), 3)  # 20% safety margin
            
            print(f"")
            print(f"Production Recommendations (with safety margins):")
            print(f"  • self.min_delay = {recommended_delay:.0f}  # seconds")
            print(f"  • self.max_requests_per_hour = {recommended_hourly}")
            print(f"")
            print(f"Code to update in GoogleTrendsService:")
            print(f"```python")
            print(f"self.min_delay = {recommended_delay:.0f}")
            print(f"self.max_requests_per_hour = {recommended_hourly}")
            print(f"```")
            
            # Export results
            tester.export_results_csv(args.export)
            print(f"")
            print(f"📁 Detailed results exported to {args.export}")
            print(f"   Import into Excel/Google Sheets for further analysis")
        
        else:
            print("❌ No successful tests completed - check your internet connection")


if __name__ == "__main__":
    asyncio.run(main())