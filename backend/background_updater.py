"""
Complete Background Updater - Matches main.py expectations
"""

import asyncio
import logging
from datetime import datetime
from google_trends_service import GoogleTrendsService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global status tracking
_updater_status = {
    "running": False,
    "last_update": None,
    "cycle_count": 0,
    "errors": 0,
    "targets_updated": 0
}

async def start_background_updates():
    """Start background updates - function name that main.py expects"""
    global _updater_status
    
    _updater_status["running"] = True
    update_count = 0
    
    logger.info("🚀 Starting background real-time updates...")
    
    while _updater_status["running"]:
        try:
            update_count += 1
            _updater_status["cycle_count"] = update_count
            
            logger.info(f"🔄 Starting update cycle #{update_count}")
            
            async with GoogleTrendsService() as service:
                await service.update_all_targets()
            
            _updater_status["last_update"] = datetime.utcnow()
            logger.info(f"✅ Cycle #{update_count} completed successfully")
            
            # Wait 5 minutes before next update
            logger.info("⏰ Waiting 5 minutes until next update...")
            await asyncio.sleep(300)  # 5 minutes
            
        except Exception as e:
            _updater_status["errors"] += 1
            logger.error(f"❌ Update cycle #{update_count} failed: {e}")
            logger.info("⏰ Waiting 5 minutes before retry...")
            await asyncio.sleep(300)

async def run_background_updates():
    """Alternative function name for compatibility"""
    await start_background_updates()

def stop_background_updates():
    """Stop the background updater"""
    global _updater_status
    _updater_status["running"] = False
    logger.info("🛑 Background updates stopped")

def get_updater_status():
    """Get current status of the background updater"""
    return {
        "status": "running" if _updater_status["running"] else "stopped",
        "last_update": _updater_status["last_update"].isoformat() if _updater_status["last_update"] else None,
        "cycle_count": _updater_status["cycle_count"],
        "error_count": _updater_status["errors"],
        "targets_updated": _updater_status["targets_updated"]
    }

# Single target update function for testing
async def update_single_target(target_name: str):
    """Update a single target by name - useful for testing"""
    try:
        from database import SessionLocal
        from models import AttentionTarget
        
        db = SessionLocal()
        target = db.query(AttentionTarget).filter(
            AttentionTarget.name == target_name
        ).first()
        
        if not target:
            logger.error(f"❌ Target '{target_name}' not found")
            return False
        
        async with GoogleTrendsService() as service:
            success = await service.update_target_data(target, db)
            
        db.close()
        return success
        
    except Exception as e:
        logger.error(f"❌ Failed to update single target {target_name}: {e}")
        return False

if __name__ == "__main__":
    # Can be run directly for testing
    asyncio.run(start_background_updates())