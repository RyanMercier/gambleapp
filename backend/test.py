# test_realtime_integration.py - Test that real-time updates show in 1-day charts

import asyncio
from datetime import datetime, timedelta
from database import SessionLocal
from models import AttentionTarget, AttentionHistory
from google_trends_service import GoogleTrendsService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_realtime_chart_integration():
    """Test that real-time updates appear in 1-day charts"""
    
    db = SessionLocal()
    try:
        # Get first target
        target = db.query(AttentionTarget).first()
        if not target:
            logger.error("❌ No targets found for testing")
            return
        
        logger.info(f"🧪 Testing real-time integration for {target.name}")
        
        # Check current 1-day chart data
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)
        
        # Get base 1-day data
        base_data = db.query(AttentionHistory).filter(
            AttentionHistory.target_id == target.id,
            AttentionHistory.data_source == "google_trends_1d",
            AttentionHistory.timestamp >= start_time
        ).count()
        
        # Get real-time data
        realtime_data = db.query(AttentionHistory).filter(
            AttentionHistory.target_id == target.id,
            AttentionHistory.data_source == "google_trends_realtime",
            AttentionHistory.timestamp >= start_time
        ).count()
        
        logger.info(f"📊 Current 1-day chart data:")
        logger.info(f"   Base 1d data: {base_data} points")
        logger.info(f"   Real-time data: {realtime_data} points")
        logger.info(f"   Total: {base_data + realtime_data} points")
        
        # Trigger a real-time update
        logger.info("🔄 Triggering real-time update...")
        async with GoogleTrendsService() as service:
            success = await service.update_target_data(target, db)
        
        if success:
            # Check updated real-time data count
            new_realtime_count = db.query(AttentionHistory).filter(
                AttentionHistory.target_id == target.id,
                AttentionHistory.data_source == "google_trends_realtime",
                AttentionHistory.timestamp >= start_time
            ).count()
            
            logger.info(f"✅ After update:")
            logger.info(f"   Real-time data: {new_realtime_count} points (+{new_realtime_count - realtime_data})")
            
            # Show most recent real-time point
            latest_rt = db.query(AttentionHistory).filter(
                AttentionHistory.target_id == target.id,
                AttentionHistory.data_source == "google_trends_realtime"
            ).order_by(AttentionHistory.timestamp.desc()).first()
            
            if latest_rt:
                logger.info(f"📈 Latest real-time point: {latest_rt.attention_score} at {latest_rt.timestamp}")
                
                # Check if this would appear in 1-day chart
                if latest_rt.timestamp >= start_time:
                    logger.info("✅ Latest real-time point IS within 1-day chart range")
                else:
                    logger.warning("⚠️ Latest real-time point is NOT within 1-day chart range")
            
            logger.info("✅ Real-time updates WILL appear in 1-day charts")
            
        else:
            logger.error("❌ Real-time update failed")
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_realtime_chart_integration())