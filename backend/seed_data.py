"""
Run this script to populate the database with initial data.
Usage: python seed_data.py
"""

import asyncio
from sqlalchemy.orm import sessionmaker
from database import engine
from models import AttentionTarget, User, TargetType
from datetime import datetime, timedelta
from decimal import Decimal
import random

SessionLocal = sessionmaker(bind=engine)

def create_admin_user():
    db = SessionLocal()
    
    # Check if admin user exists
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        from auth import hash_password
        admin = User(
            username="admin",
            email="admin@trendbet.com",
            password_hash=hash_password("admin123"),
            balance=Decimal("10000.00")
        )
        db.add(admin)
        db.commit()
        print("Admin user created successfully! (username: admin, password: admin123)")
    else:
        print("Admin user already exists.")
    
    db.close()

async def seed_sample_targets():
    """Seed initial attention targets for each category"""
    db = SessionLocal()
    
    sample_targets = [
        # Politicians
        {
            "name": "Donald Trump",
            "type": TargetType.POLITICIAN,
            "search_term": "Donald Trump",
            "description": "Former and current US President - attention tracking"
        },
        {
            "name": "Joe Biden", 
            "type": TargetType.POLITICIAN,
            "search_term": "Joe Biden",
            "description": "US President - political attention tracking"
        },
        {
            "name": "Kamala Harris",
            "type": TargetType.POLITICIAN, 
            "search_term": "Kamala Harris",
            "description": "US Vice President - political attention tracking"
        },
        {
            "name": "Ron DeSantis",
            "type": TargetType.POLITICIAN,
            "search_term": "Ron DeSantis", 
            "description": "Florida Governor - political attention tracking"
        },
        
        # Billionaires
        {
            "name": "Elon Musk",
            "type": TargetType.BILLIONAIRE,
            "search_term": "Elon Musk",
            "description": "CEO of Tesla and SpaceX - billionaire attention tracking"
        },
        {
            "name": "Jeff Bezos",
            "type": TargetType.BILLIONAIRE,
            "search_term": "Jeff Bezos", 
            "description": "Founder of Amazon - billionaire attention tracking"
        },
        {
            "name": "Bill Gates",
            "type": TargetType.BILLIONAIRE,
            "search_term": "Bill Gates",
            "description": "Microsoft founder - billionaire attention tracking"
        },
        {
            "name": "Warren Buffett",
            "type": TargetType.BILLIONAIRE,
            "search_term": "Warren Buffett",
            "description": "Berkshire Hathaway CEO - investor attention tracking"
        },
        
        # Countries
        {
            "name": "United States",
            "type": TargetType.COUNTRY,
            "search_term": "United States",
            "description": "USA - country attention tracking"
        },
        {
            "name": "China",
            "type": TargetType.COUNTRY,
            "search_term": "China",
            "description": "People's Republic of China - country attention tracking"
        },
        {
            "name": "Japan",
            "type": TargetType.COUNTRY,
            "search_term": "Japan", 
            "description": "Japan - country attention tracking"
        },
        {
            "name": "United Kingdom",
            "type": TargetType.COUNTRY,
            "search_term": "United Kingdom",
            "description": "UK - country attention tracking"
        },
        
        # Stocks/Meme Stocks
        {
            "name": "Tesla",
            "type": TargetType.STOCK,
            "search_term": "Tesla",
            "description": "Tesla Inc - meme stock attention tracking"
        },
        {
            "name": "GameStop", 
            "type": TargetType.STOCK,
            "search_term": "GameStop",
            "description": "GameStop Corp - meme stock attention tracking"
        },
        {
            "name": "AMC",
            "type": TargetType.STOCK,
            "search_term": "AMC",
            "description": "AMC Entertainment - meme stock attention tracking"
        },
        {
            "name": "Bitcoin",
            "type": TargetType.STOCK,
            "search_term": "Bitcoin",
            "description": "Bitcoin cryptocurrency - digital asset attention tracking"
        }
    ]
    
    try:
        from google_trends_service import GoogleTrendsService
        
        async with GoogleTrendsService() as service:
            for target_data in sample_targets:
                existing = db.query(AttentionTarget).filter(
                    AttentionTarget.name == target_data["name"]
                ).first()
                
                if not existing:
                    # Get initial attention score from Google Trends
                    try:
                        trends_data = await service.get_google_trends_data(target_data["search_term"])
                        base_attention_score = trends_data.get("attention_score", random.uniform(20.0, 80.0))
                    except Exception as e:
                        print(f"Failed to get trends data for {target_data['name']}: {e}")
                        base_attention_score = random.uniform(20.0, 80.0)
                    
                    base_price = random.uniform(8.0, 15.0)
                    
                    target = AttentionTarget(
                        name=target_data["name"],
                        type=target_data["type"],
                        search_term=target_data["search_term"],
                        description=target_data["description"],
                        current_attention_score=Decimal(str(base_attention_score)),
                        current_share_price=Decimal(str(base_price))
                    )
                    db.add(target)
                    db.commit()
                    db.refresh(target)
                    
                    # Seed historical data
                    await service.seed_historical_data(target, days=7)
                    
                    print(f"Added target: {target_data['name']} (Score: {base_attention_score:.1f}, Price: ${base_price:.2f})")
                    
                    # Add delay between requests to be nice to Google
                    await asyncio.sleep(service.min_delay)
    
    except ImportError:
        print("Google Trends service not available, using random data...")
        # Fallback to random data if service not available
        for target_data in sample_targets:
            existing = db.query(AttentionTarget).filter(
                AttentionTarget.name == target_data["name"]
            ).first()
            
            if not existing:
                base_attention_score = random.uniform(20.0, 80.0)
                base_price = random.uniform(8.0, 15.0)
                
                target = AttentionTarget(
                    name=target_data["name"],
                    type=target_data["type"],
                    search_term=target_data["search_term"],
                    description=target_data["description"],
                    current_attention_score=Decimal(str(base_attention_score)),
                    current_share_price=Decimal(str(base_price))
                )
                db.add(target)
                print(f"Added target: {target_data['name']} (Score: {base_attention_score:.1f}, Price: ${base_price:.2f})")
    
    db.commit()
    print("Sample attention targets seeded successfully!")
    db.close()

# For backwards compatibility with the old function names
def seed_categories():
    """Legacy function - categories are now handled by TargetType enum"""
    print("Categories are now handled by TargetType enum - no separate table needed")

async def seed_sample_trends():
    """Legacy function - redirects to seed_sample_targets"""
    await seed_sample_targets()

async def main():
    """Main seeding function"""
    print("Seeding TrendBet database...")
    create_admin_user()
    seed_categories()
    await seed_sample_targets()
    print("Database seeding completed!")

if __name__ == "__main__":
    asyncio.run(main())