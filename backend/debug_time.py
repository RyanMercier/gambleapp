# debug_timestamps.py - Check what timestamps we're actually getting

import asyncio
from google_trends_service import GoogleTrendsService
from database import SessionLocal
from models import AttentionHistory
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_google_timestamps():
    """Debug what timestamps Google Trends actually returns"""
    
    async with GoogleTrendsService() as service:
        # Test 1: Get 1-day data for Trump
        logger.info("🔍 Testing 1-day data...")
        day_data = await service.get_google_trends_data("donald trump", timeframe="now 1-d")

        print(day_data)  # Debug output
        
        if day_data and day_data.get('timeline_timestamps'):
            timestamps = day_data['timeline_timestamps']
            values = day_data['timeline']
            
            logger.info(f"📊 1-day data: {len(values)} values, {len(timestamps)} timestamps")
            logger.info(f"🕐 First few timestamps:")
            for i in range(min(5, len(timestamps))):
                logger.info(f"  {i}: {timestamps[i]} (type: {type(timestamps[i])})")
            
            logger.info(f"🕐 Last few timestamps:")
            for i in range(max(0, len(timestamps)-3), len(timestamps)):
                logger.info(f"  {i}: {timestamps[i]} (type: {type(timestamps[i])})")
        else:
            logger.warning("❌ No timestamps in 1-day data")
        
        # Wait a bit to respect rate limits
        await asyncio.sleep(5)
        
        # Test 2: Get 5-year data for Trump
        logger.info("\n🔍 Testing 5-year data...")
        year_data = await service.get_google_trends_data("donald trump", timeframe="today 5-y")
        
        if year_data and year_data.get('timeline_timestamps'):
            timestamps = year_data['timeline_timestamps']
            values = year_data['timeline']
            
            logger.info(f"📊 5-year data: {len(values)} values, {len(timestamps)} timestamps")
            logger.info(f"🕐 First few timestamps:")
            for i in range(min(5, len(timestamps))):
                logger.info(f"  {i}: {timestamps[i]} (type: {type(timestamps[i])})")
            
            logger.info(f"🕐 Last few timestamps:")
            for i in range(max(0, len(timestamps)-3), len(timestamps)):
                logger.info(f"  {i}: {timestamps[i]} (type: {type(timestamps[i])})")
        else:
            logger.warning("❌ No timestamps in 5-year data")

def debug_stored_timestamps():
    """Check what timestamps are actually stored in the database"""
    
    db = SessionLocal()
    try:
        # Get Trump's data (target_id=1)
        target_id = 1
        
        # Check 1-day data source
        day_data = db.query(AttentionHistory).filter(
            AttentionHistory.target_id == target_id,
            AttentionHistory.data_source.like('%1_day%')
        ).order_by(AttentionHistory.timestamp.asc()).all()
        
        logger.info(f"\n📊 Stored 1-day data: {len(day_data)} points")
        if day_data:
            logger.info(f"🕐 First timestamp: {day_data[0].timestamp}")
            logger.info(f"🕐 Last timestamp: {day_data[-1].timestamp}")
            logger.info(f"🕐 Data source: {day_data[0].data_source}")
            
            # Show time gaps
            if len(day_data) > 1:
                gaps = []
                for i in range(1, min(10, len(day_data))):
                    gap = day_data[i].timestamp - day_data[i-1].timestamp
                    gaps.append(gap.total_seconds() / 60)  # minutes
                
                logger.info(f"🕐 Time gaps (first 10, in minutes): {gaps}")
        
        # Check 5-year data source
        year_data = db.query(AttentionHistory).filter(
            AttentionHistory.target_id == target_id,
            AttentionHistory.data_source.like('%5_year%')
        ).order_by(AttentionHistory.timestamp.asc()).all()
        
        logger.info(f"\n📊 Stored 5-year data: {len(year_data)} points")
        if year_data:
            logger.info(f"🕐 First timestamp: {year_data[0].timestamp}")
            logger.info(f"🕐 Last timestamp: {year_data[-1].timestamp}")
            logger.info(f"🕐 Data source: {year_data[0].data_source}")
            
            # Show time gaps
            if len(year_data) > 1:
                gaps = []
                for i in range(1, min(10, len(year_data))):
                    gap = year_data[i].timestamp - year_data[i-1].timestamp
                    gaps.append(gap.total_seconds() / (24*3600))  # days
                
                logger.info(f"🕐 Time gaps (first 10, in days): {gaps}")
        
    finally:
        db.close()

async def main():
    logger.info("🚀 Debugging timestamp handling...")
    
    # Check what Google returns
    await debug_google_timestamps()
    
    # Check what we stored
    debug_stored_timestamps()
    
    logger.info("✅ Debug complete!")

if __name__ == "__main__":
    asyncio.run(main())