import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from database import SessionLocal
from models import Tournament, TargetType, TournamentDuration

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TournamentSeeder:
    """Ensures there are always free tournaments available for users"""
    
    def __init__(self):
        self.min_free_tournaments = 3  # Always keep at least 3 free tournaments
        self.tournament_duration_hours = 24  # 24 hour tournaments
        
    async def seed_tournaments(self):
        """Main seeding function - ensures free tournaments are always available"""
        db = SessionLocal()
        
        try:
            await self._ensure_free_tournaments_exist(db)
            await self._cleanup_expired_tournaments(db)
            
        except Exception as e:
            logger.error(f"❌ Tournament seeding error: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def _ensure_free_tournaments_exist(self, db):
        """Ensure minimum number of free tournaments exist"""
        
        # Count active free tournaments
        active_free_count = db.query(Tournament).filter(
            Tournament.entry_fee == 0,
            Tournament.is_active == True,
            Tournament.is_finished == False,
            Tournament.end_date >= datetime.utcnow()
        ).count()
        
        logger.info(f"📊 Found {active_free_count} active free tournaments")
        
        # Create additional tournaments if needed
        tournaments_to_create = max(0, self.min_free_tournaments - active_free_count)
        
        if tournaments_to_create > 0:
            logger.info(f"🏗️ Creating {tournaments_to_create} new free tournaments")
            
            for i in range(tournaments_to_create):
                await self._create_free_tournament(db, i)
        else:
            logger.info("✅ Sufficient free tournaments already exist")
    
    async def _create_free_tournament(self, db, index):
        """Create a single free tournament"""
        
        # Stagger start times to avoid all tournaments ending simultaneously
        start_offset_minutes = index * 30  # 30 minutes apart
        start_time = datetime.utcnow() + timedelta(minutes=start_offset_minutes)
        end_time = start_time + timedelta(hours=self.tournament_duration_hours)
        
        # Rotate through target types for variety
        target_types = list(TargetType)
        target_type = target_types[index % len(target_types)]
        
        # Generate tournament name
        type_names = {
            TargetType.POLITICIAN: "Political Pulse",
            TargetType.CELEBRITY: "Celebrity Watch", 
            TargetType.COUNTRY: "Global Focus",
            TargetType.GAME: "Gaming Trends",
            TargetType.STOCK: "Market Movers",
            TargetType.CRYPTO: "Crypto Hype"
        }
        
        tournament_name = f"🆓 Free {type_names.get(target_type, 'Mixed')} Tournament"
        
        tournament = Tournament(
            name=tournament_name,
            target_type=target_type,
            duration=TournamentDuration.DAILY,
            entry_fee=Decimal('0.00'),
            prize_pool=Decimal('0.00'),
            participant_count=0,
            start_date=start_time,
            end_date=end_time,
            is_active=True,
            is_finished=False
        )
        
        db.add(tournament)
        db.commit()
        db.refresh(tournament)
        
        logger.info(f"✅ Created free tournament: {tournament.name}")
        logger.info(f"   ID: {tournament.id}, Type: {target_type.value}")
        logger.info(f"   Duration: {start_time} → {end_time}")
        
        return tournament
    
    async def _cleanup_expired_tournaments(self, db):
        """Mark expired tournaments as finished"""
        
        now = datetime.utcnow()
        
        # Find tournaments that have ended but aren't marked as finished
        expired_tournaments = db.query(Tournament).filter(
            Tournament.end_date < now,
            Tournament.is_finished == False
        ).all()
        
        if expired_tournaments:
            logger.info(f"🧹 Cleaning up {len(expired_tournaments)} expired tournaments")
            
            for tournament in expired_tournaments:
                tournament.is_finished = True
                tournament.is_active = False
                logger.info(f"   Marked tournament {tournament.id} as finished")
        
        db.commit()
    
    async def run_continuous_seeding(self, interval_minutes=30):
        """Run tournament seeding continuously"""
        logger.info(f"🚀 Starting continuous tournament seeding (every {interval_minutes} minutes)")
        
        while True:
            try:
                await self.seed_tournaments()
                await asyncio.sleep(interval_minutes * 60)  # Convert to seconds
                
            except Exception as e:
                logger.error(f"❌ Continuous seeding error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry

# Standalone seeding function for one-time use
async def seed_tournaments_once():
    """One-time tournament seeding"""
    seeder = TournamentSeeder()
    await seeder.seed_tournaments()

# Background task for continuous seeding
async def start_tournament_seeder():
    """Start background tournament seeding task"""
    seeder = TournamentSeeder()
    await seeder.run_continuous_seeding(interval_minutes=30)

if __name__ == "__main__":
    # Run seeding once when script is executed directly
    asyncio.run(seed_tournaments_once())