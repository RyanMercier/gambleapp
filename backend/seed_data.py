# backend/seed_data.py
"""
Improved seed data script with fallback support for when Google Trends is rate limited
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
        
        logger.info(f"📊 Creating target: {name}")
        
        # Check if target already exists
        existing = db.query(AttentionTarget).filter(
            AttentionTarget.search_term == search_term
        ).first()
        
        if existing:
            logger.info(f"Target {name} already exists, skipping")
            return True
        
        # Try to get Google Trends data (will fallback automatically if needed)
        try:
            attention_data = await service.get_attention_score(search_term)
            
            if attention_data and attention_data.get('success'):
                current_score = attention_data['attention_score']  # Fixed: was 'current_score'
                data_source = attention_data.get('source', 'unknown')
            else:
                # This shouldn't happen with the new service, but just in case
                current_score = random.uniform(30, 80)
                data_source = 'fallback'
                
        except Exception as e:
            logger.warning(f"Error getting data for {name}: {e}, using fallback")
            current_score = random.uniform(30, 80)
            data_source = 'fallback'
        
        # Create the target
        target = AttentionTarget(
            name=name,
            type=TargetType(target_type),
            search_term=search_term,
            description=f"Attention trading target for {name}",
            current_attention_score=Decimal(str(current_score))
        )
        
        db.add(target)
        db.commit()
        db.refresh(target)
        
        # Add initial history entry
        history = AttentionHistory(
            target_id=target.id,
            attention_score=target.current_attention_score,
            data_source=data_source
        )
        db.add(history)
        db.commit()
        
        logger.info(f"✅ Created {name} with score {current_score:.1f} (source: {data_source})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create target {target_data['name']}: {e}")
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
    """Create historical data for a target (last 90 days)"""
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
            # Create realistic variations
            daily_variation = random.uniform(-5, 5)
            seasonal_factor = 1 + 0.1 * random.sin(day / 7)  # Weekly pattern
            
            score = max(0, min(100, base_score + daily_variation * seasonal_factor))
            timestamp = datetime.utcnow() - timedelta(days=day)
            
            # Don't create entries for every day, just a few per week
            if day % 3 == 0:  # Every 3rd day
                history = AttentionHistory(
                    target_id=target.id,
                    attention_score=Decimal(str(score)),
                    timestamp=timestamp,
                    data_source='historical_seed'
                )
                db.add(history)
        
        db.commit()
        logger.info(f"✅ Historical data created for {target.name}")
        
    except Exception as e:
        logger.error(f"❌ Failed to create historical data for {target.name}: {e}")
        db.rollback()
    finally:
        db.close()

async def seed_all_historical_data():
    """Create historical data for all targets"""
    logger.info("🔄 Historical data seeding started...")
    
    db = SessionLocal()
    try:
        targets = db.query(AttentionTarget).filter(
            AttentionTarget.is_active == True
        ).all()
        
        for target in targets:
            await seed_historical_data_for_target(target)
            await asyncio.sleep(1)  # Small delay between targets
            
        logger.info("✅ Historical data seeding completed")
        
    except Exception as e:
        logger.error(f"❌ Historical data seeding failed: {e}")
    finally:
        db.close()

def create_sample_targets_sync():
    """Synchronous wrapper for creating sample targets"""
    return asyncio.run(seed_sample_targets())

def create_historical_data_sync():
    """Synchronous wrapper for creating historical data"""
    return asyncio.run(seed_all_historical_data())

if __name__ == "__main__":
    # Run both seeding operations
    asyncio.run(seed_sample_targets())
    asyncio.run(seed_all_historical_data())