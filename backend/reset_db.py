#!/usr/bin/env python3
"""
Simple database reset script for TrendBet

This script provides a quick way to reset the database without
complex user creation or seeding that might fail due to dependencies.
Useful for development and testing.
"""

import logging
from database import engine, drop_tables, create_tables, create_database_indices
from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def simple_reset():
    """
    Perform a simple database reset operation.

    This function:
    1. Drops all existing tables and enum types
    2. Creates fresh tables based on current models
    3. Creates performance indices
    4. Lists the created tables for verification

    Does not create users or seed data to avoid dependency issues.

    Raises:
        Exception: If any step of the reset process fails
    """
    try:
        logger.info("Starting simple database reset...")

        # Step 1: Drop all existing tables and enum types
        logger.info("Dropping existing tables...")
        drop_tables()

        # Step 2: Create fresh tables from models
        logger.info("Creating fresh tables...")
        create_tables()

        # Step 3: Create performance indices (handle errors gracefully)
        logger.info("Creating database indices...")
        try:
            create_database_indices()
        except Exception as e:
            logger.warning("Some indices may have failed: %s", e)

        logger.info("Database reset completed successfully")

        # Step 4: Verify what was created
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            logger.info("Created tables: %s", tables)

    except Exception as e:
        logger.error("Reset failed: %s", e)
        raise

if __name__ == "__main__":
    simple_reset()