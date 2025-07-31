"""
Complete seed_data.py - Uses actual Google Trends timestamps
"""

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from database import SessionLocal
from models import AttentionTarget, AttentionHistory, TargetType
from google_trends_service import GoogleTrendsService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample targets
SAMPLE_TARGETS = [
    {"name": "Donald Trump", "type": "politician", "search_term": "donald trump"},
    {"name": "Elon Musk", "type": "billionaire", "search_term": "elon musk"},
    {"name": "Bitcoin", "type": "stock", "search_term": "bitcoin"},
    {"name": "Tesla", "type": "stock", "search_term": "tesla"},
    {"name": "Joe Biden", "type": "politician", "search_term": "joe biden"},
    {"name": "Apple", "type": "stock", "search_term": "apple stock"},
]

async def create_target_with_data(target_data: dict, service: GoogleTrendsService, db: SessionLocal) -> bool:
    """Create target with multiple timeframe data using real Google timestamps"""
    try:
        name = target_data["name"]
        search_term = target_data["search_term"]
        target_type = target_data["type"]
        
        # Check if exists
        existing = db.query(AttentionTarget).filter(AttentionTarget.name == name).first()
        if existing:
            logger.info(f"✅ Target {name} already exists")
            return False
        
        # Get current score
        current_data = await service.get_google_trends_data(search_term, timeframe="now 1-d")
        if not current_data or not current_data.get('success'):
            logger.error(f"❌ Failed to get current data for {name}")
            return False
        
        current_score = current_data.get("attention_score", 50.0)
        
        # Create target
        type_mapping = {
            "politician": TargetType.POLITICIAN,
            "billionaire": TargetType.BILLIONAIRE,
            "stock": TargetType.STOCK
        }
        
        target = AttentionTarget(
            name=name,
            type=type_mapping[target_type],
            search_term=search_term,
            current_attention_score=Decimal(str(current_score)),
            description=f"Google Trends attention score for {name}"
        )
        
        db.add(target)
        db.commit()
        db.refresh(target)
        
        logger.info(f"✅ Created target: {name} (Score: {current_score:.1f})")
        
        # Standard Google Trends timeframes with proper data source names
        timeframes = [
            ("now 1-d", "1d"),
            ("now 7-d", "7d"), 
            ("today 1-m", "1m"),
            ("today 3-m", "3m"),
            ("today 12-m", "1y"),
            ("today 5-y", "5y")
        ]
        
        # Get data for each timeframe using real timestamps
        for timeframe_code, timeframe_name in timeframes:
            try:
                logger.info(f"📅 Getting {timeframe_name} data for {name}...")
                data = await service.get_google_trends_data(search_term, timeframe=timeframe_code)
                
                if data and data.get('success') and data.get('timeline'):
                    await store_timeframe_data_with_real_timestamps(target, data, timeframe_name, timeframe_code, db)
                else:
                    logger.error(f"❌ No {timeframe_name} data for {name}")
                
                # Rate limit
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.error(f"❌ Failed to get {timeframe_name} data for {name}: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create target {target_data['name']}: {e}")
        db.rollback()
        return False


async def store_timeframe_data_with_real_timestamps(target: AttentionTarget, data: dict, timeframe_name: str, timeframe_code: str, db: SessionLocal):
    """Store data using actual Google Trends timestamps"""
    try:
        timeline_values = data.get('timeline', [])
        timeline_timestamps = data.get('timeline_timestamps', [])
        
        if not timeline_values:
            logger.error(f"❌ No timeline values for {target.name} ({timeframe_name})")
            return
        
        # Check if we have real timestamps (should be datetime objects now)
        if not timeline_timestamps or len(timeline_timestamps) != len(timeline_values):
            logger.error(f"❌ No timestamps or count mismatch for {target.name} ({timeframe_name}): {len(timeline_timestamps)} vs {len(timeline_values)}")
            return
        
        logger.info(f"💾 Storing {timeframe_name}: {len(timeline_values)} points with real timestamps for {target.name}")
        
        entries = []
        stored_count = 0
        
        for i, (timestamp_dt, value) in enumerate(zip(timeline_timestamps, timeline_values)):
            try:
                # timestamp_dt should already be a datetime object from the service
                if not isinstance(timestamp_dt, datetime):
                    logger.error(f"❌ Expected datetime object, got {type(timestamp_dt)}: {timestamp_dt}")
                    continue
                
                # Log first few timestamps for debugging
                if i < 3:
                    logger.info(f"🕐 Sample timestamp {i}: {timestamp_dt}")
                
                entry = AttentionHistory(
                    target_id=target.id,
                    attention_score=Decimal(str(value)),
                    timestamp=timestamp_dt,  # Use real Google timestamp
                    data_source=f"google_trends_{timeframe_name}",
                    timeframe_used=timeframe_code,
                    confidence_score=Decimal("1.0")
                )
                entries.append(entry)
                stored_count += 1
                
            except Exception as e:
                logger.error(f"❌ Failed to process timestamp {timestamp_dt}: {e}")
        
        if not entries:
            logger.error(f"❌ No valid entries created for {target.name} ({timeframe_name})")
            return
        
        # Insert in batches
        batch_size = 1000
        for i in range(0, len(entries), batch_size):
            batch = entries[i:i+batch_size]
            db.add_all(batch)
            db.commit()
        
        # Show timestamp range for verification
        first_ts = entries[0].timestamp
        last_ts = entries[-1].timestamp
        logger.info(f"✅ Stored {stored_count} {timeframe_name} points: {first_ts} to {last_ts}")
        
        # Verify current time
        current_utc = datetime.utcnow()
        logger.info(f"🕐 Current UTC time: {current_utc}")
        logger.info(f"🕐 Last data timestamp: {last_ts}")
        
        # Check if last timestamp is in future (indicates timezone issue)
        if last_ts > current_utc:
            time_diff = (last_ts - current_utc).total_seconds() / 3600
            logger.warning(f"⚠️ Last timestamp is {time_diff:.1f} hours in the future - possible timezone issue")
        
    except Exception as e:
        logger.error(f"❌ Error storing {timeframe_name} data for {target.name}: {e}")
        db.rollback()


async def seed_sample_targets():
    """Seed database with sample targets using real Google timestamps"""
    logger.info("🚀 Seeding targets with real Google Trends timestamps...")
    
    db = SessionLocal()
    created_count = 0
    
    try:
        async with GoogleTrendsService() as service:
            for i, target_data in enumerate(SAMPLE_TARGETS):
                try:
                    logger.info(f"📈 [{i+1}/{len(SAMPLE_TARGETS)}] Processing: {target_data['name']}")
                    
                    success = await create_target_with_data(target_data, service, db)
                    if success:
                        created_count += 1
                    
                    # Wait between targets
                    if i < len(SAMPLE_TARGETS) - 1:
                        logger.info("⏱️ Waiting 30 seconds between targets...")
                        await asyncio.sleep(30)
                        
                except Exception as e:
                    logger.error(f"❌ Error processing {target_data['name']}: {e}")
        
        logger.info(f"🎉 Successfully created {created_count} targets with real timestamps")
        
        # Verify timestamp ranges
        logger.info("🔍 Verifying timestamp ranges...")
        targets = db.query(AttentionTarget).all()
        current_utc = datetime.utcnow()
        
        for target in targets[:2]:  # Check first 2
            latest_point = db.query(AttentionHistory).filter(
                AttentionHistory.target_id == target.id
            ).order_by(AttentionHistory.timestamp.desc()).first()
            
            if latest_point:
                time_diff = (latest_point.timestamp - current_utc).total_seconds() / 3600
                logger.info(f"📊 {target.name}: Latest timestamp {latest_point.timestamp} ({time_diff:+.1f}h from now)")
        
    except Exception as e:
        logger.error(f"❌ Seeding failed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(seed_sample_targets())