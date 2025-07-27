"""
Tournament Management System
Creates tournaments, calculates rankings, distributes prizes
"""

from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database import SessionLocal
from models import Tournament, TournamentEntry, User, TargetType, TournamentDuration
import logging
import asyncio

logger = logging.getLogger(__name__)

class TournamentManager:
    def __init__(self):
        self.platform_fee_rate = Decimal('0.10')  # 10% platform fee
    
    def create_daily_tournaments(self, db: Session):
        """Create daily tournaments for each target type"""
        tomorrow = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end_time = tomorrow + timedelta(days=1)
        
        for target_type in TargetType:
            # Check if tournament already exists for tomorrow
            existing = db.query(Tournament).filter(
                Tournament.target_type == target_type,
                Tournament.duration == TournamentDuration.DAILY,
                Tournament.start_date == tomorrow
            ).first()
            
            if not existing:
                tournament = Tournament(
                    name=f"Daily {target_type.value.title()} Challenge",
                    target_type=target_type,
                    duration=TournamentDuration.DAILY,
                    entry_fee=Decimal('10.00'),
                    start_date=tomorrow,
                    end_date=end_time
                )
                db.add(tournament)
                logger.info(f"Created daily tournament for {target_type.value}")
    
    def create_weekly_tournaments(self, db: Session):
        """Create weekly tournaments (Mondays)"""
        now = datetime.utcnow()
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0:  # Today is Monday
            days_until_monday = 7
        
        next_monday = (now + timedelta(days=days_until_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = next_monday + timedelta(days=7)
        
        for target_type in TargetType:
            existing = db.query(Tournament).filter(
                Tournament.target_type == target_type,
                Tournament.duration == TournamentDuration.WEEKLY,
                Tournament.start_date == next_monday
            ).first()
            
            if not existing:
                tournament = Tournament(
                    name=f"Weekly {target_type.value.title()} Championship",
                    target_type=target_type,
                    duration=TournamentDuration.WEEKLY,
                    entry_fee=Decimal('25.00'),
                    start_date=next_monday,
                    end_date=end_time
                )
                db.add(tournament)
                logger.info(f"Created weekly tournament for {target_type.value}")
    
    def create_monthly_tournaments(self, db: Session):
        """Create monthly tournaments (1st of each month)"""
        now = datetime.utcnow()
        
        # Calculate next month's 1st day
        if now.month == 12:
            next_month = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            next_month = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # End time is last day of that month
        if next_month.month == 12:
            end_time = next_month.replace(year=next_month.year + 1, month=1) - timedelta(days=1)
        else:
            end_time = next_month.replace(month=next_month.month + 1) - timedelta(days=1)
        end_time = end_time.replace(hour=23, minute=59, second=59)
        
        for target_type in TargetType:
            existing = db.query(Tournament).filter(
                Tournament.target_type == target_type,
                Tournament.duration == TournamentDuration.MONTHLY,
                Tournament.start_date == next_month
            ).first()
            
            if not existing:
                tournament = Tournament(
                    name=f"Monthly {target_type.value.title()} Major",
                    target_type=target_type,
                    duration=TournamentDuration.MONTHLY,
                    entry_fee=Decimal('50.00'),
                    start_date=next_month,
                    end_date=end_time
                )
                db.add(tournament)
                logger.info(f"Created monthly tournament for {target_type.value}")
    
    def calculate_tournament_pnl(self, entry: TournamentEntry, db: Session) -> Decimal:
        """Calculate P&L for a tournament entry based on their virtual trades"""
        # This would track virtual portfolio performance during tournament
        # For now, simulate with random performance
        import random
        
        # Simulate realistic P&L distribution
        # 60% lose money, 30% small gains, 10% big gains
        rand = random.random()
        if rand < 0.6:
            # Lose between 5-30%
            loss_percent = random.uniform(0.05, 0.30)
            return entry.starting_balance * (Decimal('1.0') - Decimal(str(loss_percent)))
        elif rand < 0.9:
            # Gain between 5-25%
            gain_percent = random.uniform(0.05, 0.25)
            return entry.starting_balance * (Decimal('1.0') + Decimal(str(gain_percent)))
        else:
            # Big gains 30-100%
            gain_percent = random.uniform(0.30, 1.00)
            return entry.starting_balance * (Decimal('1.0') + Decimal(str(gain_percent)))
    
    def end_tournament(self, tournament: Tournament, db: Session):
        """End tournament and calculate final rankings and prizes"""
        # Get all entries
        entries = db.query(TournamentEntry).filter(
            TournamentEntry.tournament_id == tournament.id
        ).all()
        
        if not entries:
            logger.info(f"No entries for tournament {tournament.id}")
            return
        
        # Calculate final P&L for each entry
        for entry in entries:
            final_balance = self.calculate_tournament_pnl(entry, db)
            entry.current_balance = final_balance
            entry.final_pnl = final_balance - entry.starting_balance
        
        # Sort by P&L (highest first)
        entries.sort(key=lambda x: x.final_pnl, reverse=True)
        
        # Assign ranks and calculate prizes
        total_prize_pool = tournament.prize_pool
        
        # Prize distribution: 50% to 1st, 30% to 2nd, 20% to 3rd
        prize_percentages = [0.50, 0.30, 0.20]
        
        for i, entry in enumerate(entries):
            entry.rank = i + 1
            
            # Award prizes to top 3
            if i < 3 and i < len(prize_percentages):
                prize = total_prize_pool * Decimal(str(prize_percentages[i]))
                entry.prize_won = prize
                
                # Add prize to user's real balance
                user = db.query(User).filter(User.id == entry.user_id).first()
                if user:
                    user.balance += prize
                    logger.info(f"Awarded ${prize} to {user.username} (Rank {entry.rank})")
        
        # Mark tournament as completed
        tournament.is_completed = True
        tournament.is_active = False
        
        db.commit()
        logger.info(f"Tournament {tournament.id} completed with {len(entries)} participants")
    
    def check_and_end_tournaments(self, db: Session):
        """Check for tournaments that should end and process them"""
        now = datetime.utcnow()
        
        # Find tournaments that have ended but aren't completed
        ended_tournaments = db.query(Tournament).filter(
            Tournament.end_date <= now,
            Tournament.is_completed == False,
            Tournament.is_active == True
        ).all()
        
        for tournament in ended_tournaments:
            logger.info(f"Ending tournament: {tournament.name}")
            self.end_tournament(tournament, db)
    
    def create_all_tournaments(self):
        """Create all necessary tournaments"""
        db = SessionLocal()
        try:
            self.create_daily_tournaments(db)
            self.create_weekly_tournaments(db)
            self.create_monthly_tournaments(db)
            db.commit()
            logger.info("All tournaments created successfully")
        except Exception as e:
            logger.error(f"Error creating tournaments: {e}")
            db.rollback()
        finally:
            db.close()
    
    def process_tournament_endings(self):
        """Process tournament endings"""
        db = SessionLocal()
        try:
            self.check_and_end_tournaments(db)
        except Exception as e:
            logger.error(f"Error processing tournament endings: {e}")
        finally:
            db.close()

# Background task to manage tournaments
async def tournament_management_task():
    """Background task to create and manage tournaments"""
    manager = TournamentManager()
    
    while True:
        try:
            # Create new tournaments
            manager.create_all_tournaments()
            
            # Process tournament endings
            manager.process_tournament_endings()
            
            # Run every hour
            await asyncio.sleep(60 * 60)
            
        except Exception as e:
            logger.error(f"Error in tournament management: {e}")
            await asyncio.sleep(60 * 5)  # Wait 5 minutes on error

if __name__ == "__main__":
    import asyncio
    asyncio.run(tournament_management_task())