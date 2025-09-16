"""
Database configuration and management for TrendBet Attention Trading API

This module provides:
- SQLAlchemy database configuration and session management
- Database connection utilities and health checks
- Table creation and migration utilities
- Initial data seeding functionality
- Database reset and cleanup operations
"""

import logging
import os
import re
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, text, Engine
from sqlalchemy.orm import sessionmaker, Session

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/trendbet"
)

# SQLAlchemy engine configuration
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections after 1 hour
)

# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)


def get_db() -> Session:
    """
    FastAPI dependency to get database session.

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """
    Context manager for database sessions.

    Yields:
        Session: SQLAlchemy database session with automatic cleanup
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_database_connection() -> bool:
    """
    Check if database connection is working.

    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def check_database_exists() -> bool:
    """
    Check if the target database exists.

    Returns:
        bool: True if database exists, False otherwise
    """
    try:
        # Extract database name from URL
        db_match = re.search(r'/([^/]+)$', DATABASE_URL)
        if not db_match:
            logger.error("Cannot extract database name from URL")
            return False

        db_name = db_match.group(1)

        # Connect to postgres database to check if target database exists
        postgres_url = DATABASE_URL.rsplit('/', 1)[0] + '/postgres'
        postgres_engine = create_engine(postgres_url)

        with postgres_engine.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": db_name}
            )
            exists = result.fetchone() is not None

        postgres_engine.dispose()

        if exists:
            logger.info(f"Database '{db_name}' exists")
            return True
        else:
            logger.error(f"Database '{db_name}' does not exist")
            return False

    except Exception as e:
        logger.error(f"Cannot check if database exists: {e}")
        return False


def create_tables() -> None:
    """
    Create all database tables based on SQLAlchemy models.

    Raises:
        Exception: If table creation fails
    """
    try:
        # Import models to ensure they're registered with Base
        from models import Base

        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")

    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        raise


def drop_tables() -> None:
    """
    Drop all database tables and enum types.

    Raises:
        Exception: If table dropping fails
    """
    try:
        # Import Base from models
        from models import Base

        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        logger.info("All tables dropped")

        # Drop enum types to prevent conflicts
        with engine.connect() as conn:
            conn.execute(text("DROP TYPE IF EXISTS targettype CASCADE;"))
            conn.execute(text("DROP TYPE IF EXISTS tournamentduration CASCADE;"))
            conn.commit()
        logger.info("Enum types dropped")

    except Exception as e:
        logger.error(f"Failed to drop tables: {e}")
        raise


def create_database_indices() -> None:
    """
    Create database indices for optimal query performance.
    """
    indices = [
        # Attention history composite index for chart queries
        """
        CREATE INDEX IF NOT EXISTS idx_attention_history_target_source_time
        ON attention_history (target_id, data_source, timestamp);
        """,

        # Portfolio performance index
        """
        CREATE INDEX IF NOT EXISTS idx_portfolio_user_tournament
        ON portfolios (user_id, tournament_id);
        """,

        # Trade history index
        """
        CREATE INDEX IF NOT EXISTS idx_trades_user_timestamp
        ON trades (user_id, timestamp DESC);
        """,

        # Tournament entries index
        """
        CREATE INDEX IF NOT EXISTS idx_tournament_entries_user_tournament
        ON tournament_entries (user_id, tournament_id);
        """,

        # Active tournaments index
        """
        CREATE INDEX IF NOT EXISTS idx_tournaments_active_type
        ON tournaments (is_active, target_type) WHERE is_active = true;
        """
    ]

    try:
        with engine.connect() as conn:
            for index_sql in indices:
                conn.execute(text(index_sql))
            conn.commit()
        logger.info("Database indices created successfully")

    except Exception as e:
        logger.error(f"Failed to create indices: {e}")
        raise


def seed_initial_data() -> None:
    """
    Seed database with initial required data including users and tournaments.

    Raises:
        Exception: If seeding fails
    """
    try:
        from models import (
            User, Tournament, TournamentDuration, TargetType
        )
        from auth import hash_password

        with get_db_session() as db:
            # Create admin user if not exists
            admin_user = db.query(User).filter(User.username == "admin").first()
            if not admin_user:
                admin_user = User(
                    username="admin",
                    email="admin@trendbet.com",
                    password_hash=hash_password("admin123"),
                    balance=Decimal("0.00")  # Tournament-based system
                )
                db.add(admin_user)
                logger.info("Admin user created (username: admin, password: admin123)")

            # Create test user if not exists
            test_user = db.query(User).filter(User.username == "testuser").first()
            if not test_user:
                test_user = User(
                    username="testuser",
                    email="test@trendbet.com",
                    password_hash=hash_password("password123"),
                    balance=Decimal("0.00")  # Tournament-based system
                )
                db.add(test_user)
                logger.info("Test user created (username: testuser, password: password123)")

            # Create sample tournaments if none exist
            if db.query(Tournament).count() == 0:
                tournaments = _create_sample_tournaments()
                db.add_all(tournaments)
                logger.info(f"Created {len(tournaments)} sample tournaments")

            # Log final counts
            tournament_count = db.query(Tournament).count()
            user_count = db.query(User).count()
            logger.info(f"Database summary: {user_count} users, {tournament_count} tournaments")

    except Exception as e:
        logger.error(f"Failed to seed initial data: {e}")
        raise


def _create_sample_tournaments() -> list:
    """
    Create sample tournaments for all target types.

    Returns:
        list: List of Tournament objects
    """
    from models import Tournament, TournamentDuration, TargetType

    tournaments = []
    start_time = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ) + timedelta(days=1)

    # Tournament templates
    tournament_templates = [
        {
            "duration": TournamentDuration.DAILY,
            "name_suffix": "Daily Challenge",
            "entry_fee": Decimal("0.00"),  # Free tournaments
            "duration_days": 1
        },
        {
            "duration": TournamentDuration.WEEKLY,
            "name_suffix": "Weekly Wars",
            "entry_fee": Decimal("10.00"),
            "duration_days": 7
        },
        {
            "duration": TournamentDuration.MONTHLY,
            "name_suffix": "Monthly Championship",
            "entry_fee": Decimal("25.00"),
            "duration_days": 30
        }
    ]

    # Create tournaments for each target type
    for target_type in TargetType:
        for template in tournament_templates:
            tournament = Tournament(
                name=f"{template['name_suffix']} - {target_type.value.title()}",
                target_type=target_type,
                duration=template["duration"],
                entry_fee=template["entry_fee"],
                prize_pool=Decimal("0.00"),
                participant_count=0,
                start_date=start_time,
                end_date=start_time + timedelta(days=template["duration_days"]),
                is_active=True,
                is_finished=False
            )
            tournaments.append(tournament)

    return tournaments


def get_database_info() -> Dict[str, Any]:
    """
    Get comprehensive database information and statistics.

    Returns:
        Dict[str, Any]: Database information including table counts and connection status
    """
    try:
        from models import (
            User, AttentionTarget, AttentionHistory,
            Portfolio, Trade, Tournament, TournamentEntry
        )

        with get_db_session() as db:
            info = {
                "database_url": re.sub(r'//.*@', "//***:***@", DATABASE_URL),
                "connection_status": "connected",
                "tables": {
                    "users": db.query(User).count(),
                    "attention_targets": db.query(AttentionTarget).count(),
                    "attention_history": db.query(AttentionHistory).count(),
                    "portfolios": db.query(Portfolio).count(),
                    "trades": db.query(Trade).count(),
                    "tournaments": db.query(Tournament).count(),
                    "tournament_entries": db.query(TournamentEntry).count(),
                },
                "active_tournaments": db.query(Tournament).filter(
                    Tournament.is_active == True
                ).count()
            }

        return info

    except Exception as e:
        return {
            "database_url": re.sub(r'//.*@', "//***:***@", DATABASE_URL),
            "connection_status": "error",
            "error": str(e)
        }


def get_category_stats() -> Dict[str, Dict[str, int]]:
    """
    Get statistics for each target type category.

    Returns:
        Dict[str, Dict[str, int]]: Statistics by category
    """
    try:
        from models import AttentionTarget, TargetType, Tournament

        stats = {}

        with get_db_session() as db:
            for target_type in TargetType:
                try:
                    target_count = db.query(AttentionTarget).filter(
                        AttentionTarget.type == target_type
                    ).count()

                    tournament_count = db.query(Tournament).filter(
                        Tournament.target_type == target_type
                    ).count()

                    active_tournament_count = db.query(Tournament).filter(
                        Tournament.target_type == target_type,
                        Tournament.is_active == True
                    ).count()

                    stats[target_type.value] = {
                        "targets": target_count,
                        "tournaments": tournament_count,
                        "active_tournaments": active_tournament_count
                    }

                except Exception as e:
                    logger.warning(f"Could not get stats for {target_type.value}: {e}")
                    stats[target_type.value] = {"targets": 0, "tournaments": 0, "active_tournaments": 0}

        return stats

    except Exception as e:
        logger.error(f"Error getting category stats: {e}")
        return {}


def reset_database() -> None:
    """
    Complete database reset: drop tables, recreate, seed data, and create indices.

    Raises:
        Exception: If reset fails
    """
    try:
        logger.info("Starting database reset...")

        # Step 1: Drop existing tables and enums
        drop_tables()

        # Step 2: Create fresh tables
        create_tables()

        # Step 3: Create performance indices
        create_database_indices()

        # Step 4: Seed initial data
        seed_initial_data()

        logger.info("Database reset completed successfully")

        # Show final statistics
        stats = get_category_stats()
        if stats:
            logger.info("Category breakdown:")
            for category, data in stats.items():
                logger.info(
                    f"  {category}: {data['targets']} targets, "
                    f"{data['active_tournaments']}/{data['tournaments']} active tournaments"
                )

        # Show database info
        db_info = get_database_info()
        if "tables" in db_info:
            total_records = sum(db_info["tables"].values())
            logger.info(f"Total database records: {total_records}")

    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        raise


def optimize_database() -> None:
    """
    Run database optimization operations including VACUUM and ANALYZE.
    """
    try:
        with engine.connect() as conn:
            # VACUUM ANALYZE to update statistics and reclaim space
            conn.execute(text("VACUUM ANALYZE;"))
            logger.info("Database optimization completed")

    except Exception as e:
        logger.error(f"Database optimization failed: {e}")
        raise


def backup_database(backup_path: Optional[str] = None) -> str:
    """
    Create a database backup using pg_dump.

    Args:
        backup_path: Optional custom backup file path

    Returns:
        str: Path to the backup file

    Raises:
        Exception: If backup fails
    """
    import subprocess
    from urllib.parse import urlparse

    try:
        # Parse database URL
        parsed = urlparse(DATABASE_URL)

        # Generate backup filename if not provided
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"trendbet_backup_{timestamp}.sql"

        # Build pg_dump command
        cmd = [
            "pg_dump",
            f"--host={parsed.hostname}",
            f"--port={parsed.port or 5432}",
            f"--username={parsed.username}",
            f"--dbname={parsed.path[1:]}",  # Remove leading slash
            "--no-password",
            "--verbose",
            "--clean",
            "--if-exists",
            f"--file={backup_path}"
        ]

        # Set password via environment variable
        env = os.environ.copy()
        env["PGPASSWORD"] = parsed.password

        # Run backup
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)

        if result.returncode == 0:
            logger.info(f"Database backup created: {backup_path}")
            return backup_path
        else:
            raise Exception(f"pg_dump failed: {result.stderr}")

    except Exception as e:
        logger.error(f"Database backup failed: {e}")
        raise


if __name__ == "__main__":
    """
    Command-line interface for database operations.
    Usage: python database.py [reset|info|optimize|backup]
    """
    import sys

    if not check_database_connection():
        logger.error("Cannot connect to database. Please check your DATABASE_URL.")
        sys.exit(1)

    command = sys.argv[1] if len(sys.argv) > 1 else "reset"

    try:
        if command == "reset":
            logger.info("Running database reset...")
            reset_database()

        elif command == "info":
            info = get_database_info()
            print(f"Database URL: {info['database_url']}")
            print(f"Status: {info['connection_status']}")
            if "tables" in info:
                print("Table counts:")
                for table, count in info["tables"].items():
                    print(f"  {table}: {count}")

        elif command == "optimize":
            logger.info("Running database optimization...")
            optimize_database()

        elif command == "backup":
            backup_file = backup_database()
            print(f"Backup created: {backup_file}")

        else:
            print("Usage: python database.py [reset|info|optimize|backup]")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Command '{command}' failed: {e}")
        sys.exit(1)