import asyncio
import uvicorn
import logging
import sys

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_tor_flag():
    """Check if --torify flag was passed"""
    use_tor = "--torify" in sys.argv or "--tor" in sys.argv
    if use_tor:
        logger.info("🧅 Tor proxy mode enabled")
    return use_tor

async def initialize_database():
    """Initialize database with proper async handling"""
    try:
        from database import create_tables, seed_initial_data, check_database_connection
        
        print("🔍 Checking database connection...")
        
        # Simple database connection check
        if not check_database_connection():
            print("\n❌ Cannot connect to database!")
            print("Please run: python test_database.py")
            print("This will help diagnose and fix the issue.")
            raise Exception("Cannot connect to database")
        
        print("Initializing database...")
        create_tables()
        print("✅ Database tables created")
        
        # Check if database needs seeding
        from database import SessionLocal
        from models import AttentionTarget
        
        db = SessionLocal()
        try:
            target_count = db.query(AttentionTarget).count()
            if target_count == 0:
                print("Database is empty, seeding initial data...")
                
                # Seed basic data (users, tournaments)
                seed_initial_data()
                
                # Seed sample targets with real Google Trends data
                try:
                    from seed_data import seed_sample_targets
                    await seed_sample_targets()
                    print("✅ Database seeded with real Google Trends data")
                except ImportError:
                    print("⚠️ seed_data module not found, skipping sample targets")
                except Exception as e:
                    print(f"⚠️ Failed to seed sample targets: {e}")
                    print("✅ Basic data seeded, you can add targets manually")
            else:
                print(f"Database has {target_count} targets, skipping seed")
                
        except Exception as e:
            print(f"Error checking/seeding database: {e}")
            raise
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise

def main():
    """Main server startup function"""
    print("🚀 Starting TrendBet API server...")

    use_tor = check_tor_flag()
    
    # Set environment variable for main.py
    import os
    if use_tor:
        os.environ['USE_TOR'] = 'true'
    
    try:
        # Run database initialization with proper async handling
        asyncio.run(initialize_database())
        
        print("🌐 Starting web server...")
        
        # Start the server
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
        
    except KeyboardInterrupt:
        print("\n⚠️ Server stopped by user")
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()