# backend/database.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import logging
import re

load_dotenv()

logger = logging.getLogger(__name__)

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/trendbet")

# SQLAlchemy setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False)

# Dependency to get database session
def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Create all database tables"""
    try:
        # Import models to make sure they're registered with Base
        from models import (
            Base, User, AttentionTarget, AttentionHistory, Portfolio, 
            Trade, Tournament, TournamentEntry
        )
        # Use the Base from models.py, not a local one
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}")
        raise

def drop_tables():
    """Drop all database tables (use with caution!)"""
    try:
        # Import Base from models
        from models import Base
        Base.metadata.drop_all(bind=engine)
        logger.info("🗑️ All tables dropped")
    except Exception as e:
        logger.error(f"❌ Failed to drop tables: {e}")
        raise

def seed_initial_data():
    """Seed database with initial required data"""
    try:
        from models import User, Tournament, TournamentDuration
        from auth import hash_password
        from datetime import datetime, timedelta
        from decimal import Decimal
        
        db = SessionLocal()
        try:
            # Create admin user if not exists
            admin_user = db.query(User).filter(User.username == "admin").first()
            if not admin_user:
                admin_user = User(
                    username="admin",
                    email="admin@trendbet.com",
                    password_hash=hash_password("admin123"),
                    balance=Decimal("10000.00")
                )
                db.add(admin_user)
                logger.info("Admin user created successfully! (username: admin, password: admin123)")

            # Create sample tournaments if none exist
            if db.query(Tournament).count() == 0:
                tournaments = [
                    Tournament(
                        name="Daily Attention Challenge",
                        description="24-hour attention trading competition",
                        duration=TournamentDuration.DAILY,
                        entry_fee=Decimal("10.00"),
                        max_participants=100,
                        start_date=datetime.utcnow(),
                        end_date=datetime.utcnow() + timedelta(days=1),
                        status="active"
                    ),
                    Tournament(
                        name="Weekly Attention Wars",
                        description="7-day attention trading battle",
                        duration=TournamentDuration.WEEKLY,
                        entry_fee=Decimal("25.00"),
                        max_participants=500,
                        start_date=datetime.utcnow(),
                        end_date=datetime.utcnow() + timedelta(days=7),
                        status="active"
                    ),
                    Tournament(
                        name="Monthly Attention Championship",
                        description="Ultimate monthly attention trading contest",
                        duration=TournamentDuration.MONTHLY,
                        entry_fee=Decimal("50.00"),
                        max_participants=1000,
                        start_date=datetime.utcnow(),
                        end_date=datetime.utcnow() + timedelta(days=30),
                        status="active"
                    ),
                ]
                db.add_all(tournaments)
                logger.info("✅ Sample tournaments created")

            db.commit()
            logger.info("✅ Initial data seeded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to seed initial data: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    except Exception as e:
        logger.error(f"❌ Error in seed_initial_data: {e}")
        raise

def check_database_connection():
    """Check if database connection is working"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def check_database_exists():
    """Check if the database exists"""
    try:
        db_match = re.search(r'/([^/]+)$', DATABASE_URL)
        if not db_match:
            logger.error("❌ Cannot extract database name from URL")
            return False
        
        db_name = db_match.group(1)
        postgres_url = DATABASE_URL.rsplit('/', 1)[0] + '/postgres'
        postgres_engine = create_engine(postgres_url)

        with postgres_engine.connect() as conn:
            result = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :db_name"), {"db_name": db_name})
            exists = result.fetchone() is not None

        postgres_engine.dispose()

        if exists:
            logger.info(f"✅ Database '{db_name}' exists")
            return True
        else:
            logger.error(f"❌ Database '{db_name}' does not exist")
            return False
    except Exception as e:
        logger.error(f"❌ Cannot check if database exists: {e}")
        return False

def get_database_info():
    """Get database information"""
    try:
        db = SessionLocal()
        from models import User, AttentionTarget, AttentionHistory, Portfolio, Trade
        info = {
            "database_url": re.sub(r'//.*@', "//***:***@", DATABASE_URL),
            "users": db.query(User).count(),
            "attention_targets": db.query(AttentionTarget).count(),
            "attention_history": db.query(AttentionHistory).count(),
            "portfolios": db.query(Portfolio).count(),
            "trades": db.query(Trade).count(),
            "connection_status": "connected"
        }
        db.close()
        return info
    except Exception as e:
        return {
            "database_url": re.sub(r'//.*@', "//***:***@", DATABASE_URL),
            "connection_status": "error",
            "error": str(e)
        }

def reset_database():
    """Reset database - drop and recreate all tables with initial data"""
    try:
        logger.info("🔄 Resetting database...")
        drop_tables()
        create_tables()
        seed_initial_data()
        logger.info("✅ Database reset completed successfully")
    except Exception as e:
        logger.error(f"❌ Database reset failed: {e}")
        raise