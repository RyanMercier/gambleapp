# backend/setup_database.py - Database setup and verification script

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/trendbet")

def parse_database_url(url):
    """Parse database URL into components"""
    try:
        # Example: postgresql://postgres:postgres@localhost:5432/trendbet
        if not url.startswith('postgresql://'):
            logger.error(f"URL must start with postgresql://")
            return None
        
        # Remove the protocol
        url_without_protocol = url.replace('postgresql://', '')
        
        # Split by @ to separate credentials from host/db
        if '@' not in url_without_protocol:
            logger.error("URL must contain @ to separate credentials from host")
            return None
            
        credentials_part, host_db_part = url_without_protocol.split('@', 1)
        
        # Parse credentials
        if ':' not in credentials_part:
            logger.error("Credentials must be in format user:password")
            return None
            
        user, password = credentials_part.split(':', 1)
        
        # Parse host, port, and database
        if '/' not in host_db_part:
            logger.error("URL must contain database name after /")
            return None
            
        host_port_part, database = host_db_part.rsplit('/', 1)
        
        # Remove any query parameters from database name
        database = database.split('?')[0]
        
        # Parse host and port
        if ':' in host_port_part:
            host, port = host_port_part.rsplit(':', 1)
        else:
            host = host_port_part
            port = '5432'  # Default PostgreSQL port
        
        return {
            'user': user,
            'password': password,
            'host': host,
            'port': port,
            'database': database
        }
        
    except Exception as e:
        logger.error(f"Error parsing database URL: {e}")
        return None

def check_postgresql_running():
    """Check if PostgreSQL is running"""
    try:
        db_info = parse_database_url(DATABASE_URL)
        if not db_info:
            return False
        
        # Try to connect to postgres database (default database)
        postgres_url = f"postgresql://{db_info['user']}:{db_info['password']}@{db_info['host']}:{db_info['port']}/postgres"
        engine = create_engine(postgres_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"✅ PostgreSQL is running: {version}")
            
        engine.dispose()
        return True
        
    except Exception as e:
        logger.error(f"❌ PostgreSQL is not running or not accessible: {e}")
        return False

def check_database_exists():
    """Check if the target database exists"""
    try:
        db_info = parse_database_url(DATABASE_URL)
        if not db_info:
            return False
        
        # Connect to postgres database to check if our database exists
        postgres_url = f"postgresql://{db_info['user']}:{db_info['password']}@{db_info['host']}:{db_info['port']}/postgres"
        engine = create_engine(postgres_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :db_name"), {"db_name": db_info['database']})
            exists = result.fetchone() is not None
            
        engine.dispose()
        
        if exists:
            logger.info(f"✅ Database '{db_info['database']}' exists")
        else:
            logger.error(f"❌ Database '{db_info['database']}' does not exist")
            
        return exists
        
    except Exception as e:
        logger.error(f"❌ Cannot check if database exists: {e}")
        return False

def create_database():
    """Create the target database"""
    try:
        db_info = parse_database_url(DATABASE_URL)
        if not db_info:
            return False
        
        logger.info(f"Creating database '{db_info['database']}'...")
        
        # Connect to postgres database to create our database
        postgres_url = f"postgresql://{db_info['user']}:{db_info['password']}@{db_info['host']}:{db_info['port']}/postgres"
        engine = create_engine(postgres_url)
        
        # Need to use autocommit for CREATE DATABASE
        with engine.connect() as conn:
            conn.execute(text("COMMIT"))  # End any existing transaction
            conn.execute(text(f"CREATE DATABASE {db_info['database']}"))
            
        engine.dispose()
        
        logger.info(f"✅ Database '{db_info['database']}' created successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create database: {e}")
        return False

def test_database_connection():
    """Test connection to the target database"""
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
            
        engine.dispose()
        
        logger.info("✅ Database connection successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🔧 TrendBet Database Setup")
    print("=" * 40)
    
    db_info = parse_database_url(DATABASE_URL)
    if not db_info:
        print("❌ Invalid database URL format!")
        sys.exit(1)
    
    print(f"Database: {db_info['database']}")
    print(f"Host: {db_info['host']}:{db_info['port']}")
    print(f"User: {db_info['user']}")
    print()
    
    # Step 1: Check if PostgreSQL is running
    print("🔍 Step 1: Checking PostgreSQL...")
    if not check_postgresql_running():
        print("\n💡 To fix this:")
        print("   - Make sure PostgreSQL is installed and running")
        print("   - Check if the host and port are correct")
        print("   - Verify username and password")
        sys.exit(1)
    
    # Step 2: Check if database exists
    print("\n🔍 Step 2: Checking database...")
    if not check_database_exists():
        print(f"\n🔧 Creating database '{db_info['database']}'...")
        if not create_database():
            print(f"\n💡 Manual creation needed:")
            print(f"   psql -U {db_info['user']} -h {db_info['host']} -p {db_info['port']} -c \"CREATE DATABASE {db_info['database']};\"")
            sys.exit(1)
    
    # Step 3: Test connection
    print("\n🔍 Step 3: Testing connection...")
    if not test_database_connection():
        print("\n❌ Connection test failed!")
        sys.exit(1)
    
    print("\n🎉 Database setup completed successfully!")
    print("You can now run: python run_server.py")

if __name__ == "__main__":
    main()