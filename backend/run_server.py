"""
Production server runner with database initialization
"""

import uvicorn
from sqlalchemy import text
from database import engine, SessionLocal
from models import Base
from seed_data import create_admin_user, seed_categories, seed_sample_trends

def init_database():
    """Initialize database with tables and seed data"""
    print("Initializing database...")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
    
    # Check if database is empty and seed if needed
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT COUNT(*) FROM trend_categories")).scalar()
        if result == 0:
            print("Database is empty, seeding initial data...")
            create_admin_user()
            seed_categories()
            seed_sample_trends()
            print("✅ Database seeded with initial data")
        else:
            print("✅ Database already contains data")
    except Exception as e:
        print(f"Note: Could not check database contents: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_database()
    print("🚀 Starting TrendBet API server...")
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )