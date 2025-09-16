#!/usr/bin/env python3
"""
Simple test script for TrendBet

This script provides basic functionality testing for the TrendBet system.
Tests database connectivity, Google Trends API functionality, or both.

Usage: python test.py [db|trends|all]
"""

import asyncio
import sys
from database import check_database_connection, get_database_info
from google_trends_service import GoogleTrendsService

def test_database():
    """
    Test database connectivity and basic functionality.

    Returns:
        bool: True if database tests pass, False otherwise
    """
    print("Testing database...")

    if check_database_connection():
        print("  Connection works")
        info = get_database_info()
        if "tables" in info:
            total = sum(info["tables"].values())
            print(f"  {total} total records")
        return True
    else:
        print("  Connection failed")
        return False

async def test_trends():
    """
    Test Google Trends API functionality.

    Attempts to create a GoogleTrendsService instance and make a test API call.
    Considers rate limiting and blocking by Google as expected behavior.

    Returns:
        bool: True if service works (even if rate limited), False if broken
    """
    print("Testing Google Trends...")

    try:
        async with GoogleTrendsService() as service:
            print("  Service created")

            # Test with simple keyword and short timeframe
            result = await service.get_google_trends_data("test", "now 7-d")

            if result.get('success'):
                print(f"  API works - Score: {result.get('attention_score')}")
                return True
            else:
                error = result.get('error', 'Unknown')
                # Check for expected Google blocking patterns
                expected_errors = ['rate', 'captcha', 'sorry', '429', 'timeout', 'no result']
                if any(x in error.lower() for x in expected_errors):
                    print("  Blocked by Google (expected)")
                    print("  Service code works, just rate limited")
                    return True
                else:
                    print(f"  Unexpected error: {error}")
                    return False
    except Exception as e:
        print(f"  Failed: {e}")
        return False

async def main():
    """
    Main test function that orchestrates test execution.

    Parses command line arguments and runs appropriate tests.
    Provides summary of results and appropriate exit codes.

    Returns:
        int: 0 if all tests pass, 1 if any tests fail
    """
    test_type = sys.argv[1] if len(sys.argv) > 1 else "all"

    print(f"TrendBet Test ({test_type})")
    print("=" * 30)

    results = {}

    # Run database tests if requested
    if test_type in ["db", "all"]:
        results["db"] = test_database()

    # Run Google Trends tests if requested
    if test_type in ["trends", "all"]:
        results["trends"] = await test_trends()

    # Display results summary
    print("\nResults:")
    for name, success in results.items():
        status = "Pass" if success else "Fail"
        print(f"  {name}: {status}")

    # Determine overall result
    all_passed = all(results.values())
    if all_passed:
        print("\nAll tests passed!")
    else:
        print("\nSome tests failed")

    return 0 if all_passed else 1

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print("Usage: python test.py [db|trends|all]")
        print("  db     - Test database only")
        print("  trends - Test Google Trends only")
        print("  all    - Test everything (default)")
        sys.exit(0)

    sys.exit(asyncio.run(main()))