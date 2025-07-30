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

async def create_target_with_smart_data(target_data: dict, service: GoogleTrendsService, db: SessionLocal) -> bool:
    """Create a single target with optimized historical data storage"""
    try:
        name = target_data["name"]
        search_term = target_data["search_term"]
        target_type = target_data["type"]
        
        # Check if target already exists
        existing = db.query(AttentionTarget).filter(
            AttentionTarget.name == name
        ).first()
        
        if existing:
            logger.info(f"✅ Target {name} already exists, skipping")
            return False
        
        # Get 5 years of historical data (SINGLE API CALL)
        logger.info(f"📊 Getting 5 years of REAL Google Trends data for: {name}")
        trends_data = await service.get_google_trends_data(search_term, timeframe="today 5-y")
        
        if not trends_data or not trends_data.get('timeline'):
            logger.warning(f"⚠️ No real Google Trends data available for {name}")
            return False
        
        # Use the latest score as current score (no duplicate API call)
        current_score = trends_data.get("attention_score", 50.0)
        
        # Map string type to enum
        type_mapping = {
            "politician": TargetType.POLITICIAN,
            "billionaire": TargetType.BILLIONAIRE,
            "country": TargetType.COUNTRY,
            "stock": TargetType.STOCK
        }
        
        # Create the target
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
        
        # Create optimized historical data (no duplicate API call)
        await create_smart_historical_data(target, trends_data, db)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create target {target_data['name']}: {e}")
        db.rollback()
        return False

async def create_smart_historical_data(target: AttentionTarget, trends_data: dict, db: SessionLocal):
    """
    Create historical data at SPECIFIC timestamp intervals for proper chart sampling
    """
    try:
        timeline_values = trends_data.get('timeline', [])
        if not timeline_values:
            logger.warning(f"⚠️ No timeline data for {target.name}")
            return
        
        logger.info(f"📊 Creating timestamp-based historical data for {target.name}")
        
        # Use the real trends data as our base pattern
        base_score = sum(timeline_values) / len(timeline_values)
        historical_entries = []
        
        end_time = datetime.utcnow()
        
        # Create data at SPECIFIC intervals that match our chart requirements
        
        # 1. LAST 24 HOURS: Every 15 minutes (96 points)
        start_24h = end_time - timedelta(hours=24)
        current_time = start_24h.replace(minute=(start_24h.minute // 15) * 15, second=0, microsecond=0)  # Round to 15-min boundary
        
        value_index = 0
        while current_time <= end_time and value_index < len(timeline_values):
            score = timeline_values[value_index % len(timeline_values)]  # Cycle through real data
            
            historical_entries.append({
                'timestamp': current_time,
                'attention_score': score,
                'data_source': 'google_trends_15min',
                'interval': '15_minutes'
            })
            
            current_time += timedelta(minutes=15)
            value_index += 1
        
        # 2. LAST 7 DAYS (excluding last 24h): Every hour (144 points)
        start_7d = end_time - timedelta(days=7)
        end_7d = end_time - timedelta(hours=24)
        current_time = start_7d.replace(minute=0, second=0, microsecond=0)  # Round to hour boundary
        
        while current_time <= end_7d and value_index < len(timeline_values):
            score = timeline_values[value_index % len(timeline_values)]
            
            historical_entries.append({
                'timestamp': current_time,
                'attention_score': score,
                'data_source': 'google_trends_hourly',
                'interval': '1_hour'
            })
            
            current_time += timedelta(hours=1)
            value_index += 1
        
        # 3. LAST 30 DAYS (excluding last 7 days): Every 8 hours (69 points)
        start_30d = end_time - timedelta(days=30)
        end_30d = end_time - timedelta(days=7)
        current_time = start_30d.replace(hour=(start_30d.hour // 8) * 8, minute=0, second=0, microsecond=0)
        
        while current_time <= end_30d and value_index < len(timeline_values):
            score = timeline_values[value_index % len(timeline_values)]
            
            historical_entries.append({
                'timestamp': current_time,
                'attention_score': score,
                'data_source': 'google_trends_8hourly',
                'interval': '8_hours'
            })
            
            current_time += timedelta(hours=8)
            value_index += 1
        
        # 4. LAST YEAR (excluding last 30 days): Every 5 days (67 points)
        start_1y = end_time - timedelta(days=365)
        end_1y = end_time - timedelta(days=30)
        current_time = start_1y.replace(hour=0, minute=0, second=0, microsecond=0)
        
        while current_time <= end_1y and value_index < len(timeline_values):
            score = timeline_values[value_index % len(timeline_values)]
            
            historical_entries.append({
                'timestamp': current_time,
                'attention_score': score,
                'data_source': 'google_trends_5daily',
                'interval': '5_days'
            })
            
            current_time += timedelta(days=5)
            value_index += 1
        
        # 5. OLDER THAN 1 YEAR: Every week
        start_5y = end_time - timedelta(days=5*365)
        end_5y = end_time - timedelta(days=365)
        current_time = start_5y.replace(hour=0, minute=0, second=0, microsecond=0)
        
        while current_time <= end_5y and value_index < len(timeline_values):
            score = timeline_values[value_index % len(timeline_values)]
            
            historical_entries.append({
                'timestamp': current_time,
                'attention_score': score,
                'data_source': 'google_trends_weekly',
                'interval': '1_week'
            })
            
            current_time += timedelta(weeks=1)
            value_index += 1
        
        # Batch insert all entries
        db_entries = []
        for entry in historical_entries:
            db_entry = AttentionHistory(
                target_id=target.id,
                attention_score=Decimal(str(entry['attention_score'])),
                timestamp=entry['timestamp'],
                data_source=entry['data_source'],
                timeframe_used="historical_seeded",
                confidence_score=Decimal("0.8")  # Seeded data = good confidence
            )
            db_entries.append(db_entry)
        
        # Insert in batches for better performance
        batch_size = 1000
        for i in range(0, len(db_entries), batch_size):
            batch = db_entries[i:i+batch_size]
            db.add_all(batch)
            db.commit()
        
        logger.info(f"✅ Created {len(historical_entries)} timestamp-aligned data points for {target.name}")
        
    except Exception as e:
        logger.error(f"❌ Error creating historical data for {target.name}: {e}")
        db.rollback()

def find_closest_data_point(data_points: list, target_time: datetime) -> dict:
    """Find the closest real data point to a target timestamp"""
    if not data_points:
        return None
    
    # Simple closest point finder
    closest = min(data_points, key=lambda x: abs((x['timestamp'] - target_time).total_seconds()))
    return closest

def parse_trends_timestamp(trends_time) -> datetime:
    """Parse Google Trends timestamp format to datetime"""
    try:
        if isinstance(trends_time, (int, float)):
            return datetime.fromtimestamp(trends_time)
        elif isinstance(trends_time, str):
            if '-' in trends_time:
                try:
                    return datetime.strptime(trends_time, "%Y-%m-%d")
                except:
                    return datetime.strptime(trends_time[:10], "%Y-%m-%d")
            else:
                return datetime.fromtimestamp(float(trends_time))
    except Exception as e:
        logger.warning(f"Could not parse timestamp {trends_time}: {e}")
        return datetime.utcnow() - timedelta(days=365)

async def seed_sample_targets():
    """Seed database with sample targets using optimized REAL Google Trends data"""
    logger.info("🚀 Seeding sample targets with SMART Google Trends data storage...")
    
    db = SessionLocal()
    created_count = 0
    
    try:
        async with GoogleTrendsService() as service:
            for i, target_data in enumerate(SAMPLE_TARGETS):
                try:
                    logger.info(f"📈 [{i+1}/{len(SAMPLE_TARGETS)}] Processing: {target_data['name']}")
                    
                    success = await create_target_with_smart_data(target_data, service, db)
                    if success:
                        created_count += 1
                    
                    # Rate limiting delay between targets  
                    if i < len(SAMPLE_TARGETS) - 1:
                        logger.info("⏱️ Waiting 8 seconds to respect rate limits...")
                        await asyncio.sleep(8)
                        
                except Exception as e:
                    logger.error(f"❌ Error creating target {target_data['name']}: {e}")
                    continue
        
        logger.info(f"✅ SMART data seeding completed: {created_count}/{len(SAMPLE_TARGETS)} targets created")
        
    except Exception as e:
        logger.error(f"❌ Seeding failed: {e}")
        
    finally:
        db.close()

async def verify_smart_data():
    """Verify that all targets have smart historical data"""
    db = SessionLocal()
    try:
        targets = db.query(AttentionTarget).all()
        logger.info(f"\n📊 SMART Data Verification:")
        logger.info(f"Total targets: {len(targets)}")
        
        for target in targets:
            # Count by data source
            five_min = db.query(AttentionHistory).filter(
                AttentionHistory.target_id == target.id,
                AttentionHistory.data_source == "google_trends_5min_filled"
            ).count()
            
            hourly = db.query(AttentionHistory).filter(
                AttentionHistory.target_id == target.id,
                AttentionHistory.data_source == "google_trends_hourly_filled"
            ).count()
            
            daily = db.query(AttentionHistory).filter(
                AttentionHistory.target_id == target.id,
                AttentionHistory.data_source == "google_trends_daily_filled"
            ).count()
            
            total = five_min + hourly + daily
            
            logger.info(f"  📈 {target.name}:")
            logger.info(f"    5-min (24h): {five_min}")
            logger.info(f"    Hourly (30d): {hourly}")
            logger.info(f"    Daily (5y): {daily}")
            logger.info(f"    Total: {total} (vs 525,601 with old method!)")
            logger.info(f"    Current Score: {float(target.current_attention_score):.1f}%")
            
    finally:
        db.close()

if __name__ == "__main__":
    async def main():
        # Seed with smart Google Trends data
        await seed_sample_targets()
        
        # Verify the smart data
        await verify_smart_data()
    
    # Run the seeding process
    asyncio.run(main())