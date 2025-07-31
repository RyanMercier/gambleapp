# backend/seed_data.py
"""
Optimized Real Google Trends data seeder - NO DUPLICATE API CALLS
Smart storage: 5-minute intervals for last 24 hours, hourly for older data
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from database import SessionLocal
from models import AttentionTarget, AttentionHistory, TargetType
from google_trends_service import GoogleTrendsService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample targets to seed with REAL Google Trends data
SAMPLE_TARGETS = [
    # Just include the most important ones to avoid too many API calls
    {"name": "Donald Trump", "type": "politician", "search_term": "donald trump"},
    {"name": "Elon Musk", "type": "billionaire", "search_term": "elon musk"},
    {"name": "Bitcoin", "type": "stock", "search_term": "bitcoin"},
    {"name": "Tesla", "type": "stock", "search_term": "tesla"},
    {"name": "Artificial Intelligence", "type": "stock", "search_term": "artificial intelligence"},
    {"name": "Joe Biden", "type": "politician", "search_term": "joe biden"},
    {"name": "Apple", "type": "stock", "search_term": "apple stock"},
    {"name": "United States", "type": "country", "search_term": "united states"},
]

async def create_target_with_real_data(target_data: dict, service: GoogleTrendsService, db: SessionLocal) -> bool:
    """Create target with REAL Google Trends data - 5 years + 1 day"""
    try:
        name = target_data["name"]
        search_term = target_data["search_term"]
        target_type = target_data["type"]
        
        # Check if target already exists
        existing = db.query(AttentionTarget).filter(AttentionTarget.name == name).first()
        if existing:
            logger.info(f"✅ Target {name} already exists, skipping")
            return False
        
        logger.info(f"📊 Getting REAL Google Trends data for: {name}")
        
        # 1. Get 5 years of data (gives us ~260 weekly data points)
        logger.info(f"📅 Getting 5 years of data for {name}...")
        long_term_data = await service.get_google_trends_data(search_term, timeframe="today 5-y")
        
        # 2. Get 1 day of data (gives us ~24 hourly data points)  
        logger.info(f"⏰ Getting 1 day of data for {name}...")
        short_term_data = await service.get_google_trends_data(search_term, timeframe="now 1-d")
        
        if not long_term_data or not long_term_data.get('timeline'):
            logger.warning(f"⚠️ No long-term data for {name}")
            return False
        
        # Use latest score from short-term data if available, otherwise long-term
        current_score = short_term_data.get("attention_score", long_term_data.get("attention_score", 50.0))
        
        # Create the target
        type_mapping = {
            "politician": TargetType.POLITICIAN,
            "billionaire": TargetType.BILLIONAIRE,
            "country": TargetType.COUNTRY,
            "stock": TargetType.STOCK
        }
        
        target = AttentionTarget(
            name=name,
            type=type_mapping[target_type],
            search_term=search_term,
            current_attention_score=Decimal(str(current_score)),
            description=f"Real-time Google Trends attention score for {name}"
        )
        
        db.add(target)
        db.commit()
        db.refresh(target)
        
        logger.info(f"✅ Created target: {name} (Current Score: {current_score:.1f})")
        
        # Store the actual Google Trends data with proper timestamps
        await store_trends_data(target, long_term_data, "5_year", db)
        
        if short_term_data and short_term_data.get('timeline'):
            await store_trends_data(target, short_term_data, "1_day", db)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create target {target_data['name']}: {e}")
        db.rollback()
        return False


async def store_trends_data(target: AttentionTarget, trends_data: dict, data_type: str, db: SessionLocal):
    """Store Google Trends data using ACTUAL timestamps from Google"""
    try:
        timeline_values = trends_data.get('timeline', [])
        timeline_timestamps = trends_data.get('timeline_timestamps', [])
        
        if not timeline_values:
            logger.warning(f"⚠️ No timeline data for {target.name} ({data_type})")
            return
        
        logger.info(f"🔍 {target.name} ({data_type}): {len(timeline_values)} values, {len(timeline_timestamps)} timestamps")
        
        historical_entries = []
        
        # Check if we have timestamps
        if timeline_timestamps and len(timeline_timestamps) == len(timeline_values):
            logger.info(f"✅ Using REAL Google timestamps for {target.name} ({data_type})")
            
            for i, (ts_str, value) in enumerate(zip(timeline_timestamps, timeline_values)):
                try:
                    # Google returns Unix timestamps as strings
                    timestamp_float = float(ts_str)
                    parsed_timestamp = datetime.fromtimestamp(timestamp_float, tz=timezone.utc).replace(tzinfo=None)
                    
                    # Log first few to verify
                    if i < 3:
                        logger.info(f"🕐 Sample {i}: {ts_str} -> {parsed_timestamp}")
                    
                    historical_entries.append({
                        'timestamp': parsed_timestamp,
                        'attention_score': float(value),
                        'data_source': f'google_trends_{data_type}_real_ts',
                        'timeframe_used': trends_data.get('timeframe', 'unknown')
                    })
                    
                except Exception as e:
                    logger.error(f"❌ Failed to parse timestamp {ts_str}: {e}")
                    continue
        
        elif timeline_timestamps and len(timeline_timestamps) != len(timeline_values):
            logger.warning(f"⚠️ Timestamp/value count mismatch for {target.name}: {len(timeline_timestamps)} vs {len(timeline_values)}")
            # Fall back to creating timestamps
            historical_entries = create_fallback_timestamps(timeline_values, data_type, trends_data)
        
        else:
            logger.warning(f"⚠️ No timestamps available for {target.name} ({data_type})")
            # Fall back to creating timestamps
            historical_entries = create_fallback_timestamps(timeline_values, data_type, trends_data)
        
        if not historical_entries:
            logger.error(f"❌ No entries created for {target.name} ({data_type})")
            return
        
        # Insert into database
        logger.info(f"💾 Inserting {len(historical_entries)} entries for {target.name} ({data_type})")
        
        db_entries = []
        for entry in historical_entries:
            db_entry = AttentionHistory(
                target_id=target.id,
                attention_score=Decimal(str(entry['attention_score'])),
                timestamp=entry['timestamp'],
                data_source=entry['data_source'],
                timeframe_used=entry['timeframe_used'],
                confidence_score=Decimal("1.0")
            )
            db_entries.append(db_entry)
        
        # Batch insert
        batch_size = 1000
        for i in range(0, len(db_entries), batch_size):
            batch = db_entries[i:i+batch_size]
            db.add_all(batch)
            db.commit()
        
        # Verify what was stored
        first_ts = historical_entries[0]['timestamp']
        last_ts = historical_entries[-1]['timestamp']
        logger.info(f"✅ Stored {len(historical_entries)} {data_type} points for {target.name}")
        logger.info(f"📅 Range: {first_ts} to {last_ts}")
        
    except Exception as e:
        logger.error(f"❌ Error storing {data_type} data for {target.name}: {e}")
        db.rollback()


def create_fallback_timestamps(timeline_values: list, data_type: str, trends_data: dict) -> list:
    """Create reasonable fallback timestamps when Google doesn't provide them"""
    historical_entries = []
    end_time = datetime.utcnow()
    
    if data_type == "1_day":
        start_time = end_time - timedelta(days=1)
        logger.info(f"📅 Creating fallback 1-day timestamps: {start_time} to {end_time}")
    else:  # 5_year
        start_time = end_time - timedelta(days=5*365)
        logger.info(f"📅 Creating fallback 5-year timestamps: {start_time} to {end_time}")
    
    # Create evenly spaced timestamps
    total_duration = end_time - start_time
    interval = total_duration / len(timeline_values)
    
    current_time = start_time
    for value in timeline_values:
        historical_entries.append({
            'timestamp': current_time,
            'attention_score': float(value),
            'data_source': f'google_trends_{data_type}_fallback_ts',
            'timeframe_used': trends_data.get('timeframe', 'unknown')
        })
        current_time += interval
    
    return historical_entries

# Update the main seeding function to use the new approach
async def seed_sample_targets():
    """Seed database with sample targets using REAL Google Trends data"""
    logger.info("🚀 Seeding targets with REAL Google Trends data (5 years + 1 day)...")
    
    db = SessionLocal()
    created_count = 0
    
    try:
        async with GoogleTrendsService() as service:
            for i, target_data in enumerate(SAMPLE_TARGETS):
                try:
                    logger.info(f"📈 [{i+1}/{len(SAMPLE_TARGETS)}] Processing: {target_data['name']}")
                    
                    success = await create_target_with_real_data(target_data, service, db)
                    if success:
                        created_count += 1
                    
                    # Rate limiting delay between targets  
                    if i < len(SAMPLE_TARGETS) - 1:
                        logger.info("⏱️ Waiting 8 seconds to respect rate limits...")
                        await asyncio.sleep(8)
                        
                except Exception as e:
                    logger.error(f"❌ Error processing {target_data['name']}: {e}")
                    continue
        
        logger.info(f"🎉 Successfully created {created_count} targets with REAL Google Trends data")
        
    except Exception as e:
        logger.error(f"❌ Seeding failed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(seed_sample_targets())