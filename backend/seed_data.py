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
    """Create target with multiple timeframe data"""
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
        
        # Standard Google Trends timeframes
        timeframes = [
            ("now 1-d", "1d"),
            ("now 7-d", "7d"), 
            ("today 1-m", "1m"),
            ("today 3-m", "3m"),
            ("today 12-m", "1y"),
            ("today 5-y", "5y")
        ]
        
        # Get data for each timeframe
        for timeframe_code, timeframe_name in timeframes:
            try:
                logger.info(f"📅 Getting {timeframe_name} data for {name}...")
                data = await service.get_google_trends_data(search_term, timeframe=timeframe_code)
                
                if data and data.get('success') and data.get('timeline'):
                    await store_timeframe_data(target, data, timeframe_name, timeframe_code, db)
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


async def store_timeframe_data(target: AttentionTarget, data: dict, timeframe_name: str, timeframe_code: str, db: SessionLocal):
    """Store data for a timeframe - no fallbacks, just works or logs error"""
    try:
        timeline_values = data.get('timeline', [])
        timeline_timestamps = data.get('timeline_timestamps', [])
        
        if not timeline_values:
            logger.error(f"❌ No timeline values for {target.name} ({timeframe_name})")
            return
        
        if not timeline_timestamps or len(timeline_timestamps) != len(timeline_values):
            logger.error(f"❌ No timestamps or count mismatch for {target.name} ({timeframe_name}): {len(timeline_timestamps)} vs {len(timeline_values)}")
            return
        
        logger.info(f"💾 Storing {timeframe_name}: {len(timeline_values)} points for {target.name}")
        
        # Parse and store data
        entries = []
        for ts_str, value in zip(timeline_timestamps, timeline_values):
            try:
                # Parse Unix timestamp
                timestamp_float = float(ts_str)
                parsed_timestamp = datetime.fromtimestamp(timestamp_float, tz=timezone.utc).replace(tzinfo=None)
                
                entry = AttentionHistory(
                    target_id=target.id,
                    attention_score=Decimal(str(value)),
                    timestamp=parsed_timestamp,
                    data_source=f"google_trends_{timeframe_name}",
                    timeframe_used=timeframe_code,
                    confidence_score=Decimal("1.0")
                )
                entries.append(entry)
                
            except Exception as e:
                logger.error(f"❌ Failed to parse timestamp {ts_str}: {e}")
        
        if not entries:
            logger.error(f"❌ No valid entries created for {target.name} ({timeframe_name})")
            return
        
        # Insert in batches
        batch_size = 1000
        for i in range(0, len(entries), batch_size):
            batch = entries[i:i+batch_size]
            db.add_all(batch)
            db.commit()
        
        first_ts = entries[0].timestamp
        last_ts = entries[-1].timestamp
        logger.info(f"✅ Stored {len(entries)} {timeframe_name} points: {first_ts} to {last_ts}")
        
    except Exception as e:
        logger.error(f"❌ Error storing {timeframe_name} data for {target.name}: {e}")
        db.rollback()


async def seed_sample_targets():
    """Seed database with sample targets"""
    logger.info("🚀 Seeding targets with standard Google Trends timeframes...")
    
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
        
        logger.info(f"🎉 Successfully created {created_count} targets")
        
    except Exception as e:
        logger.error(f"❌ Seeding failed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(seed_sample_targets())