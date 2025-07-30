import asyncio
from database import SessionLocal
from models import AttentionTarget, TargetType, AttentionHistory
from google_trends_service import GoogleTrendsService
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

async def seed_sample_targets():
    """Seed database with sample targets using real Google Trends data"""
    
    logger.info("🌱 Seeding sample targets with real Google Trends data...")
    
    # Sample targets to create
    sample_targets = [
        # Politicians
        ("Donald Trump", "donald trump", TargetType.POLITICIAN),
        ("Joe Biden", "joe biden", TargetType.POLITICIAN),
        ("Kamala Harris", "kamala harris", TargetType.POLITICIAN),
        
        # Billionaires  
        ("Elon Musk", "elon musk", TargetType.BILLIONAIRE),
        ("Jeff Bezos", "jeff bezos", TargetType.BILLIONAIRE),
        ("Bill Gates", "bill gates", TargetType.BILLIONAIRE),
        
        # Countries
        ("United States", "united states", TargetType.COUNTRY),
        ("China", "china", TargetType.COUNTRY),
        ("Japan", "japan", TargetType.COUNTRY),
        
        # Stocks/Crypto/Tech
        ("Tesla", "tesla", TargetType.STOCK),
        ("Bitcoin", "bitcoin", TargetType.STOCK),
        ("Artificial Intelligence", "artificial intelligence", TargetType.STOCK),
    ]
    
    db = SessionLocal()
    
    try:
        # Check if targets already exist
        existing_count = db.query(AttentionTarget).count()
        if existing_count > 0:
            logger.info(f"Database already has {existing_count} targets, skipping seed")
            return
        
        created_count = 0
        
        async with GoogleTrendsService() as service:
            for name, search_term, target_type in sample_targets:
                try:
                    logger.info(f"📊 Creating target: {name}")
                    
                    # Get real Google Trends data
                    trends_data = await service.get_google_trends_data(search_term, 'now 7-d')
                    attention_score = trends_data.get("attention_score", 50.0)
                    
                    # Create the target
                    target = AttentionTarget(
                        name=name,
                        type=target_type,
                        search_term=search_term,
                        current_attention_score=Decimal(str(attention_score)),
                        description=f"Real-time attention tracking for {name}",
                        baseline_period="5_year"
                    )
                    
                    db.add(target)
                    db.commit()
                    db.refresh(target)
                    
                    # Initial history entry
                    history = AttentionHistory(
                        target_id=target.id,
                        attention_score=Decimal(str(attention_score)),
                        data_source='google_trends_api',
                        timeframe_used='7_day'
                    )
                    db.add(history)
                    db.commit()
                    
                    created_count += 1
                    logger.info(f"✅ Created {name}: {attention_score}%")
                    
                    # Seed 5-year historical data in background (don't wait)
                    asyncio.create_task(service.seed_historical_data(target, days=1825))
                    
                    # Rate limiting to avoid overwhelming Google Trends
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    logger.error(f"❌ Failed to create target {name}: {e}")
                    db.rollback()
                    continue
        
        logger.info(f"✅ Sample data seeding completed: {created_count} targets created")
        
        # Start background historical data seeding
        logger.info("🔄 Historical data seeding started in background...")
        
    except Exception as e:
        logger.error(f"❌ Sample data seeding failed: {e}")
        db.rollback()
        raise
    
    finally:
        db.close()

def create_test_user():
    """Create a test user for development"""
    from models import User
    from auth import hash_password
    from decimal import Decimal
    
    db = SessionLocal()
    
    try:
        # Check if test user exists
        test_user = db.query(User).filter(User.username == "testuser").first()
        if test_user:
            logger.info("Test user already exists")
            return
        
        # Create test user
        test_user = User(
            username="testuser",
            email="test@trendbet.com",
            password_hash=hash_password("password123"),
            balance=Decimal("1000.00")
        )
        
        db.add(test_user)
        db.commit()
        
        logger.info("✅ Test user created (username: testuser, password: password123)")
        
    except Exception as e:
        logger.error(f"❌ Failed to create test user: {e}")
        db.rollback()
    
    finally:
        db.close()

async def seed_development_data():
    """Seed all development data"""
    logger.info("🌱 Seeding development data...")
    
    # Create test user
    create_test_user()
    
    # Create sample targets with real data
    await seed_sample_targets()
    
    logger.info("✅ Development data seeding completed")

if __name__ == "__main__":
    # Run seeding directly
    asyncio.run(seed_development_data())