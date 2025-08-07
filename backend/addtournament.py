#!/usr/bin/env python3
"""
Script to add a free tournament for testing
Run this from the backend directory: python add_free_tournament.py
"""

import sys
from datetime import datetime, timedelta
from decimal import Decimal
from database import SessionLocal
from models import Tournament, TargetType, TournamentDuration
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_free_tournament():
    """Add a free tournament for testing purposes"""
    db = SessionLocal()
    
    try:
        # Check if free tournament already exists
        existing_free = db.query(Tournament).filter(
            Tournament.entry_fee == 0,
            Tournament.name.like('%Free%')
        ).first()
        
        if existing_free:
            logger.info(f"✅ Free tournament already exists: {existing_free.name}")
            return existing_free
        
        # Create a free tournament that starts now and lasts 7 days
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(days=7)
        
        free_tournament = Tournament(
            name="🆓 Free Weekly Championship - Test Tournament",
            target_type=TargetType.POLITICIAN,  # Focus on politicians for testing
            duration=TournamentDuration.WEEKLY,
            entry_fee=Decimal('0.00'),  # Completely free
            prize_pool=Decimal('0.00'),  # No cash prizes, just for fun
            participant_count=0,
            start_date=start_time,
            end_date=end_time,
            is_active=True,
            is_finished=False
        )
        
        db.add(free_tournament)
        db.commit()
        db.refresh(free_tournament)
        
        logger.info(f"✅ Created free tournament: {free_tournament.name}")
        logger.info(f"   ID: {free_tournament.id}")
        logger.info(f"   Entry Fee: ${free_tournament.entry_fee}")
        logger.info(f"   Duration: {start_time} to {end_time}")
        logger.info(f"   Type: {free_tournament.target_type.value}")
        
        # Also create a paid tournament for comparison
        paid_tournament = Tournament(
            name="💰 Weekly Challenge - $10 Entry",
            target_type=TargetType.CELEBRITY,
            duration=TournamentDuration.WEEKLY,
            entry_fee=Decimal('10.00'),
            prize_pool=Decimal('0.00'),  # Will grow as people join
            participant_count=0,
            start_date=start_time,
            end_date=end_time,
            is_active=True,
            is_finished=False
        )
        
        db.add(paid_tournament)
        db.commit()
        db.refresh(paid_tournament)
        
        logger.info(f"✅ Also created paid tournament: {paid_tournament.name}")
        logger.info(f"   Entry Fee: ${paid_tournament.entry_fee}")
        
        return free_tournament, paid_tournament
        
    except Exception as e:
        logger.error(f"❌ Failed to create tournaments: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def show_all_tournaments():
    """Show all current tournaments"""
    db = SessionLocal()
    
    try:
        tournaments = db.query(Tournament).filter(Tournament.is_active == True).all()
        
        if not tournaments:
            logger.info("❌ No active tournaments found")
            return
        
        logger.info(f"📋 Found {len(tournaments)} active tournaments:")
        for t in tournaments:
            status = "🆓 FREE" if t.entry_fee == 0 else f"💰 ${t.entry_fee}"
            logger.info(f"   {t.id}: {t.name}")
            logger.info(f"       {status} | {t.participant_count} participants")
            logger.info(f"       {t.start_date} → {t.end_date}")
            logger.info(f"       Type: {t.target_type.value} | Duration: {t.duration.value}")
            logger.info("")
            
    except Exception as e:
        logger.error(f"❌ Failed to show tournaments: {e}")
    finally:
        db.close()

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == "show":
        show_all_tournaments()
    else:
        logger.info("🏆 Adding free tournament for testing...")
        add_free_tournament()
        logger.info("🏆 Showing all tournaments...")
        show_all_tournaments()
        logger.info("✅ Done! You can now test tournament features.")

if __name__ == "__main__":
    main()