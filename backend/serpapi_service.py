"""
SerpAPI Data Fetching Service for Google Trends
This service fetches real-time attention data and updates share prices
"""

import asyncio
import aiohttp
import os
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from database import SessionLocal
from models import AttentionTarget, AttentionHistory
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SerpAPIService:
    def __init__(self):
        self.api_key = os.getenv("SERPAPI_KEY")
        if not self.api_key:
            raise ValueError("SERPAPI_KEY environment variable is required")
        
        self.base_url = "https://serpapi.com/search"
        
    async def get_google_trends_data(self, search_term: str, timeframe: str = "today 7-d") -> dict:
        """Fetch Google Trends data for a specific search term"""
        params = {
            "engine": "google_trends",
            "q": search_term,
            "date": timeframe,
            "api_key": self.api_key,
            "data_type": "TIMESERIES"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"SerpAPI error for {search_term}: {response.status}")
                        return {"attention_score": 0.0, "timeline": []}
                    
                    data = await response.json()
                    
                    # Extract attention score and timeline
                    if "interest_over_time" in data:
                        timeline = data["interest_over_time"].get("timeline_data", [])
                        if timeline:
                            # Get latest score (0-100 from Google Trends)
                            latest_entry = timeline[-1]
                            latest_score = latest_entry.get("values", [{}])[0].get("value", 0)
                            
                            return {
                                "attention_score": float(latest_score),
                                "timeline": timeline,
                                "search_term": search_term,
                                "last_updated": datetime.utcnow()
                            }
                    
                    return {"attention_score": 0.0, "timeline": []}
                    
        except Exception as e:
            logger.error(f"Error fetching trends for {search_term}: {e}")
            return {"attention_score": 0.0, "timeline": []}

    def calculate_new_price(self, current_price: float, new_score: float, previous_score: float = 50.0) -> float:
        """Calculate new share price based on attention score change"""
        if previous_score == 0:
            previous_score = 50.0
        
        # Calculate percentage change in attention
        score_change = (new_score - previous_score) / previous_score
        
        # Apply dampening factor to prevent extreme price swings
        # Maximum 15% price change per update
        price_multiplier = 1 + (score_change * 0.15)
        price_multiplier = max(0.7, min(1.5, price_multiplier))  # Cap between 70% and 150%
        
        new_price = current_price * price_multiplier
        return max(1.0, new_price)  # Minimum price of $1

    async def update_target_data(self, target: AttentionTarget, db: Session) -> bool:
        """Update a single target's attention data"""
        try:
            # Get current trends data
            trends_data = await self.get_google_trends_data(target.search_term)
            new_score = trends_data["attention_score"]
            
            # Calculate new price
            previous_score = float(target.current_attention_score) if target.current_attention_score else 50.0
            new_price = self.calculate_new_price(
                float(target.current_share_price),
                new_score,
                previous_score
            )
            
            # Update target
            target.current_attention_score = Decimal(str(new_score))
            target.current_share_price = Decimal(str(new_price))
            target.last_updated = datetime.utcnow()
            
            # Save historical data
            history_entry = AttentionHistory(
                target_id=target.id,
                attention_score=Decimal(str(new_score)),
                share_price=Decimal(str(new_price))
            )
            db.add(history_entry)
            
            logger.info(f"Updated {target.name}: Score {new_score}, Price ${new_price:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating {target.name}: {e}")
            return False

    async def update_all_targets(self):
        """Update all active targets with fresh attention data"""
        db = SessionLocal()
        try:
            # Get all active targets
            targets = db.query(AttentionTarget).filter(
                AttentionTarget.is_active == True
            ).all()
            
            logger.info(f"Updating {len(targets)} targets...")
            
            updated_count = 0
            for target in targets:
                # Add small delay to avoid rate limiting
                await asyncio.sleep(1)
                
                if await self.update_target_data(target, db):
                    updated_count += 1
            
            db.commit()
            logger.info(f"Successfully updated {updated_count}/{len(targets)} targets")
            
        except Exception as e:
            logger.error(f"Error in update_all_targets: {e}")
            db.rollback()
        finally:
            db.close()

# Background task runner
async def run_data_updates():
    """Main function to run periodic data updates"""
    service = SerpAPIService()
    
    while True:
        try:
            logger.info("Starting scheduled data update...")
            await service.update_all_targets()
            
            # Wait 15 minutes before next update
            logger.info("Waiting 15 minutes until next update...")
            await asyncio.sleep(15 * 60)
            
        except Exception as e:
            logger.error(f"Error in data update cycle: {e}")
            # Wait 5 minutes before retrying on error
            await asyncio.sleep(5 * 60)

# Seed some initial targets
async def seed_initial_targets():
    """Seed the database with popular targets for each category"""
    db = SessionLocal()
    try:
        from models import TargetType
        
        initial_targets = [
            # Politicians
            {"name": "Donald Trump", "type": TargetType.POLITICIAN, "search_term": "Donald Trump"},
            {"name": "Joe Biden", "type": TargetType.POLITICIAN, "search_term": "Joe Biden"},
            {"name": "Kamala Harris", "type": TargetType.POLITICIAN, "search_term": "Kamala Harris"},
            {"name": "Ron DeSantis", "type": TargetType.POLITICIAN, "search_term": "Ron DeSantis"},
            
            # Billionaires
            {"name": "Elon Musk", "type": TargetType.BILLIONAIRE, "search_term": "Elon Musk"},
            {"name": "Jeff Bezos", "type": TargetType.BILLIONAIRE, "search_term": "Jeff Bezos"},
            {"name": "Bill Gates", "type": TargetType.BILLIONAIRE, "search_term": "Bill Gates"},
            {"name": "Warren Buffett", "type": TargetType.BILLIONAIRE, "search_term": "Warren Buffett"},
            
            # Countries
            {"name": "United States", "type": TargetType.COUNTRY, "search_term": "United States"},
            {"name": "China", "type": TargetType.COUNTRY, "search_term": "China"},
            {"name": "Japan", "type": TargetType.COUNTRY, "search_term": "Japan"},
            {"name": "United Kingdom", "type": TargetType.COUNTRY, "search_term": "United Kingdom"},
            
            # Stocks (meme potential)
            {"name": "Tesla", "type": TargetType.STOCK, "search_term": "Tesla stock meme"},
            {"name": "GameStop", "type": TargetType.STOCK, "search_term": "GameStop stock"},
            {"name": "AMC", "type": TargetType.STOCK, "search_term": "AMC stock"},
            {"name": "Bitcoin", "type": TargetType.STOCK, "search_term": "Bitcoin meme"},
        ]
        
        service = SerpAPIService()
        
        for target_data in initial_targets:
            # Check if target already exists
            existing = db.query(AttentionTarget).filter(
                AttentionTarget.name == target_data["name"]
            ).first()
            
            if not existing:
                # Get initial attention score
                trends_data = await service.get_google_trends_data(target_data["search_term"])
                initial_score = trends_data["attention_score"]
                
                target = AttentionTarget(
                    name=target_data["name"],
                    type=target_data["type"],
                    search_term=target_data["search_term"],
                    current_attention_score=Decimal(str(initial_score)),
                    current_share_price=Decimal("10.00"),  # Starting price
                    description=f"Attention score for {target_data['name']}"
                )
                
                db.add(target)
                logger.info(f"Added target: {target_data['name']} (Score: {initial_score})")
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(2)
        
        db.commit()
        logger.info("Initial targets seeded successfully!")
        
    except Exception as e:
        logger.error(f"Error seeding targets: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # Run the seeder first, then start the update service
    asyncio.run(seed_initial_targets())
    asyncio.run(run_data_updates())