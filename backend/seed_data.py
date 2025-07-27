"""
Run this script to populate the database with initial categories and sample trends.
Usage: python seed_data.py
"""

from sqlalchemy.orm import sessionmaker
from database import engine
from models import TrendCategory, Trend, User
from datetime import datetime, timedelta
import random

SessionLocal = sessionmaker(bind=engine)

def seed_categories():
    db = SessionLocal()
    
    categories = [
        {
            "name": "Technology", 
            "description": "Tech stocks, product launches, and industry trends",
            "icon": "💻"
        },
        {
            "name": "Cryptocurrency", 
            "description": "Digital currency prices and blockchain adoption",
            "icon": "₿"
        },
        {
            "name": "Finance", 
            "description": "Stock market, economic indicators, and market trends",
            "icon": "📈"
        },
        {
            "name": "Social Media", 
            "description": "Platform growth, viral content, and user engagement",
            "icon": "📱"
        },
        {
            "name": "Sports", 
            "description": "Game outcomes, player performance, and league standings",
            "icon": "⚽"
        },
        {
            "name": "Entertainment", 
            "description": "Box office results, streaming numbers, and award shows",
            "icon": "🎬"
        },
        {
            "name": "Climate", 
            "description": "Weather patterns, environmental data, and sustainability metrics",
            "icon": "🌍"
        },
        {
            "name": "Politics", 
            "description": "Election outcomes, policy changes, and approval ratings",
            "icon": "🏛️"
        }
    ]
    
    for cat_data in categories:
        existing = db.query(TrendCategory).filter(TrendCategory.name == cat_data["name"]).first()
        if not existing:
            category = TrendCategory(**cat_data)
            db.add(category)
    
    db.commit()
    print("Categories seeded successfully!")
    db.close()

def seed_sample_trends():
    db = SessionLocal()
    
    # Get categories
    tech_cat = db.query(TrendCategory).filter(TrendCategory.name == "Technology").first()
    crypto_cat = db.query(TrendCategory).filter(TrendCategory.name == "Cryptocurrency").first()
    finance_cat = db.query(TrendCategory).filter(TrendCategory.name == "Finance").first()
    social_cat = db.query(TrendCategory).filter(TrendCategory.name == "Social Media").first()
    
    if not all([tech_cat, crypto_cat, finance_cat, social_cat]):
        print("Categories not found. Please seed categories first.")
        return
    
    sample_trends = [
        {
            "title": "Apple Stock Price to Hit $200",
            "description": "Will Apple Inc. (AAPL) reach $200 per share by the end of Q2 2024? Recent iPhone sales and AI developments could drive significant growth.",
            "category_id": tech_cat.id,
            "current_value": 185.50,
            "target_value": 200.00,
            "deadline": datetime.now() + timedelta(days=45),
            "creator_id": 1
        },
        {
            "title": "Bitcoin to Break $75,000",
            "description": "Bitcoin has been showing strong momentum. Will it break the $75,000 resistance level within the next 30 days?",
            "category_id": crypto_cat.id,
            "current_value": 68500.00,
            "target_value": 75000.00,
            "deadline": datetime.now() + timedelta(days=30),
            "creator_id": 1
        },
        {
            "title": "S&P 500 Index Above 5,200",
            "description": "The S&P 500 has been climbing steadily. Will it reach 5,200 points before the Federal Reserve's next meeting?",
            "category_id": finance_cat.id,
            "current_value": 5050.00,
            "target_value": 5200.00,
            "deadline": datetime.now() + timedelta(days=35),
            "creator_id": 1
        },
        {
            "title": "TikTok User Base to Reach 2 Billion",
            "description": "TikTok's growth continues globally. Will it achieve 2 billion monthly active users by year-end?",
            "category_id": social_cat.id,
            "current_value": 1800000000,
            "target_value": 2000000000,
            "deadline": datetime.now() + timedelta(days=120),
            "creator_id": 1
        },
        {
            "title": "Tesla Deliveries Exceed 500K This Quarter",
            "description": "Tesla has ramped up production significantly. Will they deliver more than 500,000 vehicles this quarter?",
            "category_id": tech_cat.id,
            "current_value": 435000,
            "target_value": 500000,
            "deadline": datetime.now() + timedelta(days=60),
            "creator_id": 1
        },
        {
            "title": "Ethereum Price Above $4,000",
            "description": "With upcoming network upgrades and increased adoption, will Ethereum break $4,000 in the next 6 weeks?",
            "category_id": crypto_cat.id,
            "current_value": 3650.00,
            "target_value": 4000.00,
            "deadline": datetime.now() + timedelta(days=42),
            "creator_id": 1
        }
    ]
    
    for trend_data in sample_trends:
        existing = db.query(Trend).filter(Trend.title == trend_data["title"]).first()
        if not existing:
            trend = Trend(**trend_data)
            db.add(trend)
    
    db.commit()
    print("Sample trends seeded successfully!")
    db.close()

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
            balance=10000.00
        )
        db.add(admin)
        db.commit()
        print("Admin user created successfully! (username: admin, password: admin123)")
    else:
        print("Admin user already exists.")
    
    db.close()

if __name__ == "__main__":
    print("Seeding TrendBet database...")
    create_admin_user()
    seed_categories()
    seed_sample_trends()
    print("Database seeding completed!")