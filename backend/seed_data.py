# backend/seed_data.py
"""
Improved seed data script with fallback support for when Google Trends is rate limited
ATTENTION ONLY - NO SHARE PRICES
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from database import SessionLocal
from models import AttentionTarget, AttentionHistory, TargetType
from google_trends_service import GoogleTrendsService
import random

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample targets to seed
SAMPLE_TARGETS = [
    # Politicians
    {"name": "Donald Trump", "type": "politician", "search_term": "donald trump"},
    {"name": "Joe Biden", "type": "politician", "search_term": "joe biden"},
    {"name": "Kamala Harris", "type": "politician", "search_term": "kamala harris"},
    {"name": "Ron DeSantis", "type": "politician", "search_term": "ron desantis"},
    
    # Billionaires
    {"name": "Elon Musk", "type": "billionaire", "search_term": "elon musk"},
    {"name": "Jeff Bezos", "type": "billionaire", "search_term": "jeff bezos"},
    {"name": "Bill Gates", "type": "billionaire", "search_term": "bill gates"},
    {"name": "Warren Buffett", "type": "billionaire", "search_term": "warren buffett"},
    
    # Countries
    {"name": "United States", "type": "country", "search_term": "united states"},
    {"name": "China", "type": "country", "search_term": "china"},
    {"name": "Japan", "type": "country", "search_term": "japan"},
    {"name": "Germany", "type": "country", "search_term": "germany"},
    
    # Stocks/Crypto
    {"name": "Tesla", "type": "stock", "search_term": "tesla"},
    {"name": "Bitcoin", "type": "stock", "search_term": "bitcoin"},
    {"name": "Apple", "type": "stock", "search_term": "apple stock"},
    {"name": "Artificial Intelligence", "type": "stock", "search_term": "artificial intelligence"},
]

async def create_target_with_data(target_data: dict, service: GoogleTrendsService, db: SessionLocal) -> bool:
    """Create a single target with real or fallback data"""
    try:
        name = target_data["name"]
        search_term = target_data["search_term"]
        target_type = target_data["type"]
        
        # Check if target already exists
        existing = db.query(AttentionTarget).filter(
            AttentionTarget.name == name
        ).first()
        
        if existing:
            logger.info(f"Target {name} already exists, skipping")
            return False
        
        # Get initial attention score from Google Trends
        trends_data = await service.get_google_trends_data(search_term)
        initial_score = trends_data.get("attention_score", 50.0)
        
        # Map string type to enum
        type_mapping = {
            "politician": TargetType.POLITICIAN,
            "billionaire": TargetType.BILLIONAIRE,
            "country": TargetType.COUNTRY,
            "stock": TargetType.STOCK
        }
        
        # Create the target (NO SHARE PRICE)
        target = AttentionTarget(
            name=name,
            type=type_mapping[target_type],
            search_term=search_term,
            current_attention_score=Decimal(str(initial_score)),
            description=f"Real-time Google Trends attention score for {name}"
        )
        
        db.add(target)
        db.commit()
        db.refresh(target)
        
        logger.info(f"✅ Created target: {name} (Initial Score: {initial_score:.1f})")
        
        # Seed historical data
        await seed_historical_data_for_target(target, days=90)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to create target {target_data['name']}: {e}")
        db.rollback()
        return False

async def seed_sample_targets():
    """Seed database with sample targets"""
    logger.info("🌱 Seeding sample targets with real or fallback Google Trends data...")
    
    db = SessionLocal()
    created_count = 0
    
    try:
        # Use the improved Google Trends service
        async with GoogleTrendsService() as service:
            for i, target_data in enumerate(SAMPLE_TARGETS):
                try:
                    success = await create_target_with_data(target_data, service, db)
                    if success:
                        created_count += 1
                    
                    # Small delay between targets to respect rate limits
                    if i < len(SAMPLE_TARGETS) - 1:
                        await asyncio.sleep(2)
                        
                except Exception as e:
                    logger.error(f"Error creating target {target_data['name']}: {e}")
                    continue
        
        logger.info(f"✅ Sample data seeding completed: {created_count}/{len(SAMPLE_TARGETS)} targets created")
        
    except Exception as e:
        logger.error(f"❌ Seeding failed: {e}")
        
    finally:
        db.close()

async def seed_historical_data_for_target(target: AttentionTarget, days: int = 90):
    """Create historical data for a target (last 90 days) - ATTENTION ONLY"""
    db = SessionLocal()
    try:
        # Check if we already have historical data
        existing_count = db.query(AttentionHistory).filter(
            AttentionHistory.target_id == target.id
        ).count()
        
        if existing_count > 10:  # If we already have some history, skip
            logger.info(f"Historical data already exists for {target.name}")
            return
        
        logger.info(f"🌱 Creating historical data for {target.name}...")
        
        # Generate realistic historical data
        base_score = float(target.current_attention_score)
        
        for day in range(days, 0, -1):  # Go backwards from today
            # Create 4 data points per day (every 6 hours)
            for hour in [0, 6, 12, 18]:
                timestamp = datetime.utcnow() - timedelta(days=day, hours=hour)
                
                # Add some realistic variation
                daily_variation = random.uniform(-10, 10)
                hourly_variation = random.uniform(-5, 5)
                
                # Create a trend over time
                trend_factor = (90 - day) / 90  # 0 to 1 over the period
                trend_adjustment = trend_factor * random.uniform(-15, 15)
                
                # Calculate score
                score = base_score + daily_variation + hourly_variation + trend_adjustment
                score = max(0, min(100, score))  # Keep between 0-100
                
                # Create history entry (NO SHARE PRICE)
                history = AttentionHistory(
                    target_id=target.id,
                    attention_score=Decimal(str(score)),
                    timestamp=timestamp,
                    data_source="google_trends",
                    timeframe_used="5_year",
                    confidence_score=Decimal("0.85")
                )
                
                db.add(history)
        
        db.commit()
        logger.info(f"✅ Created {days * 4} historical data points for {target.name}")
        
    except Exception as e:
        logger.error(f"Error creating historical data for {target.name}: {e}")
        db.rollback()
    finally:
        db.close()

async def verify_data():
    """Verify that all targets have data"""
    db = SessionLocal()
    try:
        targets = db.query(AttentionTarget).all()
        logger.info(f"\n📊 Data Verification:")
        logger.info(f"Total targets: {len(targets)}")
        
        for target in targets:
            history_count = db.query(AttentionHistory).filter(
                AttentionHistory.target_id == target.id
            ).count()
            
            logger.info(f"  {target.name}: {history_count} historical records, "
                       f"Current Score: {float(target.current_attention_score):.1f}")
    finally:
        db.close()

if __name__ == "__main__":
    # Run the seeding process
    asyncio.run(seed_sample_targets())
    
    # Verify the data
    asyncio.run(verify_data())