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

def drop_enum_types():
    """Drop existing enum types to allow for new values"""
    try:
        with engine.connect() as conn:
            # Drop enum types if they exist
            conn.execute(text("DROP TYPE IF EXISTS targettype CASCADE;"))
            conn.execute(text("DROP TYPE IF EXISTS tournamentduration CASCADE;"))
            conn.commit()
        logger.info("✅ Dropped existing enum types")
    except Exception as e:
        logger.error(f"❌ Failed to drop enum types: {e}")
        raise

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
    """Drop all database tables AND enum types"""
    try:
        # Import Base from models
        from models import Base
        Base.metadata.drop_all(bind=engine)
        logger.info("🗑️ All tables dropped")
        
        # Also drop enum types
        drop_enum_types()
        
    except Exception as e:
        logger.error(f"❌ Failed to drop tables: {e}")
        raise

def seed_initial_data():
    """Seed database with initial required data"""
    try:
        from models import User, Tournament, TournamentDuration, TargetType
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
                logger.info("✅ Admin user created! (username: admin, password: admin123)")

            # Create test user if not exists
            test_user = db.query(User).filter(User.username == "testuser").first()
            if not test_user:
                test_user = User(
                    username="testuser",
                    email="test@trendbet.com",
                    password_hash=hash_password("password123"),
                    balance=Decimal("1000.00")
                )
                db.add(test_user)
                logger.info("✅ Test user created! (username: testuser, password: password123)")

            # Create sample tournaments for each category if none exist
            if db.query(Tournament).count() == 0:
                tournaments = []
                
                # Get tomorrow's date for tournament start
                tomorrow = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                
                # Only create tournaments for existing enum values to avoid errors
                safe_target_types = [TargetType.POLITICIAN, TargetType.COUNTRY, TargetType.STOCK]
                
                # Daily tournaments for safe categories first
                for target_type in safe_target_types:
                    tournaments.extend([
                        # Daily tournament
                        Tournament(
                            name=f"Daily {target_type.value.title()} Challenge",
                            target_type=target_type,
                            duration=TournamentDuration.DAILY,
                            entry_fee=Decimal("10.00"),
                            prize_pool=Decimal("0.00"),
                            participant_count=0,
                            start_date=tomorrow,
                            end_date=tomorrow + timedelta(days=1),
                            is_active=True,
                            is_finished=False
                        ),
                        # Weekly tournament
                        Tournament(
                            name=f"Weekly {target_type.value.title()} Wars",
                            target_type=target_type,
                            duration=TournamentDuration.WEEKLY,
                            entry_fee=Decimal("25.00"),
                            prize_pool=Decimal("0.00"),
                            participant_count=0,
                            start_date=tomorrow,
                            end_date=tomorrow + timedelta(days=7),
                            is_active=True,
                            is_finished=False
                        ),
                        # Monthly tournament
                        Tournament(
                            name=f"Monthly {target_type.value.title()} Championship",
                            target_type=target_type,
                            duration=TournamentDuration.MONTHLY,
                            entry_fee=Decimal("50.00"),
                            prize_pool=Decimal("0.00"),
                            participant_count=0,
                            start_date=tomorrow,
                            end_date=tomorrow + timedelta(days=30),
                            is_active=True,
                            is_finished=False
                        )
                    ])
                
                db.add_all(tournaments)
                logger.info(f"✅ Created {len(tournaments)} sample tournaments for safe categories")

            db.commit()
            logger.info("✅ Initial data seeded successfully")
            
            # Log summary
            tournament_count = db.query(Tournament).count()
            user_count = db.query(User).count()
            logger.info(f"📊 Database summary: {user_count} users, {tournament_count} tournaments")
            
        except Exception as e:
            logger.error(f"❌ Failed to seed initial data: {e}")
            db.rollback()
            raise
        finally:
            db.close()
    except Exception as e:
        logger.error(f"❌ Error in seed_initial_data: {e}")
        raise

def create_remaining_tournaments():
    """Create tournaments for new categories after confirming enum is updated"""
    try:
        from models import Tournament, TournamentDuration, TargetType
        from datetime import datetime, timedelta
        from decimal import Decimal
        
        db = SessionLocal()
        try:
            # Check if we can use new enum values
            tomorrow = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            
            new_target_types = [TargetType.CELEBRITY, TargetType.GAME, TargetType.CRYPTO]
            tournaments = []
            
            for target_type in new_target_types:
                # Check if tournaments for this type already exist
                existing = db.query(Tournament).filter(Tournament.target_type == target_type).first()
                if not existing:
                    tournaments.extend([
                        Tournament(
                            name=f"Daily {target_type.value.title()} Challenge",
                            target_type=target_type,
                            duration=TournamentDuration.DAILY,
                            entry_fee=Decimal("10.00"),
                            prize_pool=Decimal("0.00"),
                            participant_count=0,
                            start_date=tomorrow,
                            end_date=tomorrow + timedelta(days=1),
                            is_active=True,
                            is_finished=False
                        ),
                        Tournament(
                            name=f"Weekly {target_type.value.title()} Wars",
                            target_type=target_type,
                            duration=TournamentDuration.WEEKLY,
                            entry_fee=Decimal("25.00"),
                            prize_pool=Decimal("0.00"),
                            participant_count=0,
                            start_date=tomorrow,
                            end_date=tomorrow + timedelta(days=7),
                            is_active=True,
                            is_finished=False
                        ),
                        Tournament(
                            name=f"Monthly {target_type.value.title()} Championship",
                            target_type=target_type,
                            duration=TournamentDuration.MONTHLY,
                            entry_fee=Decimal("50.00"),
                            prize_pool=Decimal("0.00"),
                            participant_count=0,
                            start_date=tomorrow,
                            end_date=tomorrow + timedelta(days=30),
                            is_active=True,
                            is_finished=False
                        )
                    ])
            
            if tournaments:
                db.add_all(tournaments)
                db.commit()
                logger.info(f"✅ Created {len(tournaments)} tournaments for new categories")
            else:
                logger.info("✅ All category tournaments already exist")
                
        except Exception as e:
            logger.error(f"❌ Failed to create remaining tournaments: {e}")
            db.rollback()
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Error in create_remaining_tournaments: {e}")

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
        from models import User, AttentionTarget, AttentionHistory, Portfolio, Trade, Tournament, TournamentEntry
        info = {
            "database_url": re.sub(r'//.*@', "//***:***@", DATABASE_URL),
            "users": db.query(User).count(),
            "attention_targets": db.query(AttentionTarget).count(),
            "attention_history": db.query(AttentionHistory).count(),
            "portfolios": db.query(Portfolio).count(),
            "trades": db.query(Trade).count(),
            "tournaments": db.query(Tournament).count(),
            "tournament_entries": db.query(TournamentEntry).count(),
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

def get_category_stats():
    """Get statistics for each category"""
    try:
        db = SessionLocal()
        from models import AttentionTarget, TargetType, Tournament
        
        stats = {}
        for target_type in TargetType:
            try:
                target_count = db.query(AttentionTarget).filter(AttentionTarget.type == target_type).count()
                tournament_count = db.query(Tournament).filter(Tournament.target_type == target_type).count()
                
                stats[target_type.value] = {
                    "targets": target_count,
                    "tournaments": tournament_count
                }
            except Exception as e:
                logger.warning(f"⚠️ Could not get stats for {target_type.value}: {e}")
        
        db.close()
        return stats
    except Exception as e:
        logger.error(f"❌ Error getting category stats: {e}")
        return {}

def reset_database():
    """Reset database - drop and recreate all tables with initial data"""
    try:
        logger.info("🔄 Resetting database...")
        drop_tables()  # This now also drops enum types
        create_tables()
        seed_initial_data()
        
        # Try to create remaining tournaments (might need enum migration first)
        try:
            create_remaining_tournaments()
        except Exception as e:
            logger.warning(f"⚠️ Could not create all tournaments yet: {e}")
            logger.info("💡 You may need to restart the app to create tournaments for new categories")
        
        logger.info("✅ Database reset completed successfully")
        
        # Show final stats
        stats = get_category_stats()
        if stats:
            logger.info("📊 Category breakdown:")
            for category, data in stats.items():
                logger.info(f"  {category}: {data['targets']} targets, {data['tournaments']} tournaments")
            
    except Exception as e:
        logger.error(f"❌ Database reset failed: {e}")
        raise

if __name__ == "__main__":
    # Quick database setup script
    if check_database_connection():
        logger.info("Running database setup...")
        reset_database()