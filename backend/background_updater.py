# Replace or create background_updater.py

import asyncio
import logging
from google_trends_service import GoogleTrendsService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_background_updates():
    """Simple background updater - just works"""
    
    update_count = 0
    
    while True:
        try:
            update_count += 1
            logger.info(f"🔄 Starting update cycle #{update_count}")
            
            async with GoogleTrendsService() as service:
                await service.update_all_targets()
            
            logger.info(f"✅ Cycle #{update_count} completed")
            logger.info("⏰ Waiting 5 minutes until next update...")
            await asyncio.sleep(300)  # 5 minutes
            
        except Exception as e:
            logger.error(f"❌ Update cycle #{update_count} failed: {e}")
            logger.info("⏰ Waiting 5 minutes before retry...")
            await asyncio.sleep(300)

if __name__ == "__main__":
    logger.info("🚀 Starting background real-time updates...")
    asyncio.run(run_background_updates())