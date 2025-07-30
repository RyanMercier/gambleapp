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
    Create smart historical data storage:
    - Last 24 hours: 5-minute intervals (288 points)
    - Last 30 days: Hourly intervals (~720 points)  
    - Older data: Daily intervals (~1,800 points for 5 years)
    Total: ~2,800 points instead of 525,601!
    """
    try:
        timeline_values = trends_data.get('timeline', [])
        timeline_timestamps = trends_data.get('timeline_timestamps', [])
        
        if not timeline_values:
            logger.warning(f"⚠️ No timeline data for {target.name}")
            return
        
        logger.info(f"📊 Creating smart historical data for {target.name} from {len(timeline_values)} real data points")
        
        # Parse real data points
        real_data_points = []
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=5*365)  # 5 years ago
        
        if timeline_timestamps and len(timeline_timestamps) == len(timeline_values):
            # Use actual timestamps if available
            for timestamp, value in zip(timeline_timestamps, timeline_values):
                parsed_timestamp = parse_trends_timestamp(timestamp)
                real_data_points.append({
                    'timestamp': parsed_timestamp,
                    'attention_score': float(value)
                })
        else:
            # Create evenly spaced timestamps over 5 years
            time_interval = (end_time - start_time) / len(timeline_values)
            for i, value in enumerate(timeline_values):
                timestamp = start_time + (time_interval * i)
                real_data_points.append({
                    'timestamp': timestamp,
                    'attention_score': float(value)
                })
        
        # Sort by timestamp
        real_data_points.sort(key=lambda x: x['timestamp'])
        
        # Create smart intervals
        historical_entries = []
        
        # 1. Last 24 hours: 5-minute intervals
        twenty_four_hours_ago = end_time - timedelta(hours=24)
        current_time = twenty_four_hours_ago
        
        while current_time <= end_time:
            # Find closest real data point
            closest_point = find_closest_data_point(real_data_points, current_time)
            if closest_point:
                historical_entries.append({
                    'timestamp': current_time,
                    'attention_score': closest_point['attention_score'],
                    'data_source': 'google_trends_5min_filled',
                    'interval': '5_minutes'
                })
            current_time += timedelta(minutes=5)
        
        # 2. Last 30 days (excluding last 24 hours): Hourly intervals
        thirty_days_ago = end_time - timedelta(days=30)
        current_time = thirty_days_ago
        
        while current_time <= twenty_four_hours_ago:
            closest_point = find_closest_data_point(real_data_points, current_time)
            if closest_point:
                historical_entries.append({
                    'timestamp': current_time,
                    'attention_score': closest_point['attention_score'],
                    'data_source': 'google_trends_hourly_filled',
                    'interval': '1_hour'
                })
            current_time += timedelta(hours=1)
        
        # 3. Older data: Daily intervals
        current_time = start_time
        
        while current_time <= thirty_days_ago:
            closest_point = find_closest_data_point(real_data_points, current_time)
            if closest_point:
                historical_entries.append({
                    'timestamp': current_time,
                    'attention_score': closest_point['attention_score'],
                    'data_source': 'google_trends_daily_filled',
                    'interval': '1_day'
                })
            current_time += timedelta(days=1)
        
        # Save to database in batches
        entries_created = 0
        for entry in historical_entries:
            history_entry = AttentionHistory(
                target_id=target.id,
                attention_score=Decimal(str(entry['attention_score'])),
                timestamp=entry['timestamp'],
                data_source=entry['data_source'],
                timeframe_used="5_year_smart",
                confidence_score=Decimal("1.0")
            )
            db.add(history_entry)
            entries_created += 1
            
            # Commit in batches
            if entries_created % 500 == 0:
                db.commit()
                logger.info(f"   💾 Saved {entries_created} entries...")
        
        # Final commit
        db.commit()
        
        # Log the breakdown
        five_min_count = sum(1 for e in historical_entries if e['interval'] == '5_minutes')
        hourly_count = sum(1 for e in historical_entries if e['interval'] == '1_hour')
        daily_count = sum(1 for e in historical_entries if e['interval'] == '1_day')
        
        logger.info(f"✅ Created {entries_created} SMART historical entries for {target.name}:")
        logger.info(f"   📊 5-minute intervals (24h): {five_min_count}")
        logger.info(f"   📊 Hourly intervals (30d): {hourly_count}")  
        logger.info(f"   📊 Daily intervals (5y): {daily_count}")
        
    except Exception as e:
        logger.error(f"❌ Error creating smart historical data for {target.name}: {e}")
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