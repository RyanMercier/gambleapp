"""
Production server runner with database initialization
"""

import uvicorn
from sqlalchemy import text
from database import engine, SessionLocal
from models import Base
from seed_data import create_admin_user, seed_sample_targets

def init_database():
    """Initialize database with tables and seed data"""
    print("Initializing database...")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
    
    # Check if database is empty and seed if needed
    db = SessionLocal()
    try:
        # Check if we have any attention targets
        result = db.execute(text("SELECT COUNT(*) FROM attention_targets")).scalar()
        if result == 0:
            print("Database is empty, seeding initial data...")
            create_admin_user()
            seed_sample_targets()
            print("✅ Database seeded with initial data")
        else:
            print("✅ Database already contains data")
    except Exception as e:
        print(f"Note: Could not check database contents: {e}")
        # Try to seed anyway
        try:
            create_admin_user()
            seed_sample_targets() 
            print("✅ Database seeded")
        except Exception as seed_error:
            print(f"Warning: Could not seed database: {seed_error}")
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