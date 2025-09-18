"""
Database seeding module for TrendBet application.

This module populates the database with sample attention targets and their historical data
from Google Trends. It creates targets with multiple timeframe data points using real
timestamps from the Google Trends API.

Usage:
    python seed_data.py [--torify]

Features:
    - Creates attention targets (politicians, celebrities, crypto, etc.)
    - Fetches historical data for multiple timeframes
    - Uses real Google Trends timestamps for accurate charting
    - Includes proper rate limiting and error handling
    - Validates data integrity and timestamp alignment
"""

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from database import SessionLocal
from models import AttentionTarget, AttentionHistory, TargetType
from google_trends_service import GoogleTrendsService
import os
import sys

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

USE_TOR = "--torify" in sys.argv or os.getenv('USE_TOR', 'false').lower() == 'true'

# Updated sample targets with new category names
SAMPLE_TARGETS = [
    {"name": "Donald Trump", "type": "politician", "search_term": "donald trump"},
    {"name": "Elon Musk", "type": "celebrity", "search_term": "elon musk"},  # Changed from billionaire to celebrity
    {"name": "Bitcoin", "type": "crypto", "search_term": "bitcoin"},  # Changed from stock to crypto
    # {"name": "Tesla", "type": "stock", "search_term": "tesla"},
    # {"name": "Joe Biden", "type": "politician", "search_term": "joe biden"},
    # {"name": "Apple", "type": "stock", "search_term": "apple stock"},
    # {"name": "United States", "type": "country", "search_term": "united states"},
    # {"name": "Fortnite", "type": "game", "search_term": "fortnite"},
]

async def create_target_with_data(target_data: dict, service: GoogleTrendsService, db: SessionLocal) -> bool:
    """
    Create an attention target with historical data from Google Trends.

    Args:
        target_data: Dictionary containing name, type, and search_term
        service: GoogleTrendsService instance for API calls
        db: Database session for data persistence

    Returns:
        bool: True if target was successfully created, False otherwise
    """
    try:
        name = target_data["name"]
        search_term = target_data["search_term"]
        target_type = target_data["type"]
        
        # Check if target already exists
        existing = db.query(AttentionTarget).filter(AttentionTarget.name == name).first()
        if existing:
            logger.info(f"Target {name} already exists in database")
            return False
        
        # Get current attention score
        current_data = await service.get_google_trends_data(search_term, timeframe="now 1-d")
        if not current_data or not current_data.get('success'):
            logger.error(f"Failed to get current data for {name}")
            return False
        
        current_score = current_data.get("attention_score", 50.0)
        
        # Updated type mapping to match new enum values
        type_mapping = {
            "politician": TargetType.POLITICIAN,
            "celebrity": TargetType.CELEBRITY,  # Updated from billionaire
            "country": TargetType.COUNTRY,
            "game": TargetType.GAME,  # New
            "stock": TargetType.STOCK,
            "crypto": TargetType.CRYPTO  # New
        }
        
        if target_type not in type_mapping:
            logger.error(f"Invalid target type: {target_type}")
            return False
        
        target = AttentionTarget(
            name=name,
            type=type_mapping[target_type],
            search_term=search_term,
            current_attention_score=Decimal(str(current_score)),
            description=f"Google Trends attention score for {name}"
        )
        
        db.add(target)
        db.commit()
        db.refresh(target)
        
        logger.info(f"Created target: {name} (Score: {current_score:.1f}, Type: {target_type})")
        
        # Standard Google Trends timeframes with proper data source names
        timeframes = [
            ("now 1-d", "1d"),
            ("now 7-d", "7d"), 
            ("today 1-m", "1m"),
            ("today 3-m", "3m"),
            ("today 12-m", "1y"),
            ("today 5-y", "5y")
        ]
        
        # Get data for each timeframe using real timestamps
        for timeframe_code, timeframe_name in timeframes:
            try:
                logger.info(f"Fetching {timeframe_name} data for {name}")
                data = await service.get_google_trends_data(search_term, timeframe=timeframe_code)
                
                if data and data.get('success') and data.get('timeline'):
                    await store_timeframe_data_with_real_timestamps(target, data, timeframe_name, timeframe_code, db)
                else:
                    logger.error(f"No {timeframe_name} data available for {name}")
                
                # Rate limit
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.error(f"Failed to get {timeframe_name} data for {name}: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to create target {target_data['name']}: {e}")
        db.rollback()
        return False


async def store_timeframe_data_with_real_timestamps(
    target: AttentionTarget,
    data: dict,
    timeframe_name: str,
    timeframe_code: str,
    db: SessionLocal
) -> None:
    """
    Store historical attention data using real Google Trends timestamps.

    Args:
        target: The attention target to store data for
        data: Google Trends response containing timeline data
        timeframe_name: Human-readable timeframe (e.g., '1d', '7d')
        timeframe_code: Google Trends timeframe code (e.g., 'now 1-d')
        db: Database session for data persistence
    """
    try:
        timeline_values = data.get('timeline', [])
        timeline_timestamps = data.get('timeline_timestamps', [])
        
        if not timeline_values:
            logger.error(f"No timeline values for {target.name} ({timeframe_name})")
            return
        
        # Validate timestamp data
        if not timeline_timestamps or len(timeline_timestamps) != len(timeline_values):
            logger.error(f"Timestamp count mismatch for {target.name} ({timeframe_name}): {len(timeline_timestamps)} vs {len(timeline_values)}")
            return
        
        logger.info(f"Storing {timeframe_name}: {len(timeline_values)} data points for {target.name}")
        
        entries = []
        stored_count = 0
        
        for i, (timestamp_dt, value) in enumerate(zip(timeline_timestamps, timeline_values)):
            try:
                # Validate timestamp is datetime object
                if not isinstance(timestamp_dt, datetime):
                    logger.error(f"Expected datetime object, got {type(timestamp_dt)}: {timestamp_dt}")
                    continue

                # Ensure timestamp is timezone-aware (convert naive timestamps to UTC)
                if timestamp_dt.tzinfo is None:
                    logger.warning(f"Converting naive timestamp to UTC: {timestamp_dt}")
                    timestamp_dt = timestamp_dt.replace(tzinfo=timezone.utc)

                # Log sample timestamps for verification
                if i < 3:
                    logger.debug(f"Sample timestamp {i}: {timestamp_dt} (tzinfo: {timestamp_dt.tzinfo})")
                
                # Calculate normalized score if baseline is available
                normalized_score = None
                if target.normalization_baseline:
                    # Find peak score in current timeframe data for normalization
                    timeframe_peak = max(trends_data['timeline']) if trends_data['timeline'] else 100
                    normalization_factor = float(target.normalization_baseline) / timeframe_peak
                    normalized_score = Decimal(str(round(value * normalization_factor, 2)))

                entry = AttentionHistory(
                    target_id=target.id,
                    attention_score=Decimal(str(value)),
                    normalized_score=normalized_score,
                    timestamp=timestamp_dt,
                    data_source=f"google_trends_{timeframe_name}",
                    timeframe_used=timeframe_code,
                    confidence_score=Decimal("1.0")
                )
                entries.append(entry)
                stored_count += 1
                
            except Exception as e:
                logger.error(f"Failed to process timestamp {timestamp_dt}: {e}")
        
        if not entries:
            logger.error(f"No valid entries created for {target.name} ({timeframe_name})")
            return
        
        # Insert in batches
        batch_size = 1000
        for i in range(0, len(entries), batch_size):
            batch = entries[i:i+batch_size]
            db.add_all(batch)
            db.commit()
        
        # Show timestamp range for verification
        first_ts = entries[0].timestamp
        last_ts = entries[-1].timestamp
        logger.info(f"Stored {stored_count} {timeframe_name} points: {first_ts} to {last_ts}")
        
        # Verify timestamp alignment and timezone correctness
        current_utc = datetime.now(timezone.utc)
        logger.debug(f"Current UTC time: {current_utc}")
        logger.debug(f"Last data timestamp: {last_ts}")
        logger.debug(f"Last timestamp timezone: {last_ts.tzinfo}")

        # Check for timezone issues (allow small future variance for real-time data)
        if last_ts > current_utc:
            time_diff = (last_ts - current_utc).total_seconds() / 3600
            if time_diff > 1.0:  # More than 1 hour in future is concerning
                logger.warning(f"Last timestamp is {time_diff:.1f} hours in the future - possible timezone issue")
            else:
                logger.debug(f"Last timestamp is {time_diff:.1f} hours in future (acceptable for real-time data)")

        # Ensure timestamp is timezone-aware
        if last_ts.tzinfo is None:
            logger.error(f"Stored timestamp is timezone-naive: {last_ts}")
        
    except Exception as e:
        logger.error(f"Error storing {timeframe_name} data for {target.name}: {e}")
        db.rollback()


async def seed_sample_targets() -> None:
    """
    Seed database with sample attention targets and historical data.

    This function creates sample targets with real Google Trends data across
    multiple timeframes. It includes proper error handling, rate limiting,
    and data validation.
    """
    logger.info("Starting target seeding process with Google Trends data")
    
    db = SessionLocal()
    created_count = 0
    
    try:
        async with GoogleTrendsService(use_tor=USE_TOR) as service:
            for i, target_data in enumerate(SAMPLE_TARGETS):
                try:
                    logger.info(f"Processing target [{i+1}/{len(SAMPLE_TARGETS)}]: {target_data['name']} ({target_data['type']})")
                    
                    success = await create_target_with_data(target_data, service, db)
                    if success:
                        created_count += 1
                    
                    # Rate limiting between targets
                    if i < len(SAMPLE_TARGETS) - 1:
                        logger.info("Waiting 30 seconds to respect API rate limits")
                        await asyncio.sleep(30)
                        
                except Exception as e:
                    logger.error(f"Error processing {target_data['name']}: {e}")
        
        logger.info(f"Seeding completed successfully: {created_count} targets created")
        
        # Verify timestamp ranges
        logger.info("Verifying timestamp ranges for created targets")
        targets = db.query(AttentionTarget).all()
        current_utc = datetime.now(timezone.utc)
        
        for target in targets[:2]:  # Check first 2
            latest_point = db.query(AttentionHistory).filter(
                AttentionHistory.target_id == target.id
            ).order_by(AttentionHistory.timestamp.desc()).first()
            
            if latest_point:
                time_diff = (latest_point.timestamp - current_utc).total_seconds() / 3600
                tzinfo_status = "timezone-aware" if latest_point.timestamp.tzinfo else "timezone-naive"
                logger.info(f"{target.name}: Latest timestamp {latest_point.timestamp} ({time_diff:+.1f}h from now, {tzinfo_status})")
        
    except Exception as e:
        logger.error(f"Seeding process failed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(seed_sample_targets())