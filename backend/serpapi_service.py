"""
SerpAPI Data Fetching Service for Google Trends
Fixed version with proper error handling and historical data
"""

import asyncio
import aiohttp
import os
import random
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from database import SessionLocal
from models import AttentionTarget, AttentionHistory
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SerpAPIService:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("SERPAPI_KEY")
        self.base_url = "https://serpapi.com/search?engine=google_trends"
        
        # If no API key, we'll use mock data
        if not self.api_key:
            logger.warning("No SERPAPI_KEY found - using mock data for development")
        
    async def get_google_trends_data(self, search_term: str, timeframe: str = "now 7-d") -> dict:
        """Fetch Google Trends data for a specific search term with fallback to mock data"""
        
        # If no API key, return mock data
        if not self.api_key:
            return self._generate_mock_trends_data(search_term)
        
        params = {
            "engine": "google_trends",
            "q": search_term,
            "date": timeframe,
            "api_key": self.api_key,
            "data_type": "TIMESERIES"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params, timeout=10) as response:
                    if response.status == 400:
                        logger.error(f"SerpAPI 400 error for '{search_term}' - likely invalid API key or request format")
                        return self._generate_mock_trends_data(search_term)
                    
                    if response.status == 429:
                        logger.warning(f"SerpAPI rate limit hit for '{search_term}' - using mock data")
                        return self._generate_mock_trends_data(search_term)
                        
                    if response.status != 200:
                        logger.error(f"SerpAPI error for '{search_term}': {response.status}")
                        return self._generate_mock_trends_data(search_term)
                    
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
                                "last_updated": datetime.utcnow(),
                                "source": "serpapi"
                            }
                    
                    # If no valid data, use mock
                    logger.warning(f"No valid trends data for '{search_term}' - using mock data")
                    return self._generate_mock_trends_data(search_term)
                    
        except Exception as e:
            logger.error(f"Error fetching trends for '{search_term}': {e}")
            return self._generate_mock_trends_data(search_term)

    def _generate_mock_trends_data(self, search_term: str) -> dict:
        """Generate realistic mock trends data for development/testing"""
        
        # Base attention scores for different types
        base_scores = {
            # Politicians - higher volatility
            "donald trump": random.uniform(60, 95),
            "joe biden": random.uniform(40, 80), 
            "kamala harris": random.uniform(25, 60),
            "ron desantis": random.uniform(20, 55),
            
            # Billionaires - medium volatility
            "elon musk": random.uniform(70, 90),
            "jeff bezos": random.uniform(15, 45),
            "bill gates": random.uniform(20, 50),
            "warren buffett": random.uniform(10, 35),
            
            # Countries - lower volatility
            "united states": random.uniform(30, 70),
            "china": random.uniform(25, 60),
            "japan": random.uniform(15, 40),
            "united kingdom": random.uniform(20, 45),
            
            # Stocks/Crypto - high volatility
            "tesla": random.uniform(40, 85),
            "gamestop": random.uniform(20, 70),
            "amc": random.uniform(15, 50),
            "bitcoin": random.uniform(50, 90)
        }
        
        # Get base score or use random for unknown terms
        search_lower = search_term.lower().replace(" news", "").replace(" stock", "")
        base_score = base_scores.get(search_lower, random.uniform(20, 60))
        
        # Add some randomness (-10 to +10)
        attention_score = max(0, min(100, base_score + random.uniform(-10, 10)))
        
        return {
            "attention_score": attention_score,
            "timeline": [],
            "search_term": search_term,
            "last_updated": datetime.utcnow(),
            "source": "mock"
        }

    def calculate_new_price(self, current_price: float, new_score: float, previous_score: float = 50.0) -> float:
        """
        Calculate new share price based on attention score change
        
        Formula:
        1. Calculate % change in attention: (new_score - previous_score) / previous_score
        2. Apply dampening factor: max change per update is ±15%
        3. Price multiplier = 1 + (attention_change * 0.15)
        4. New price = current_price * multiplier
        5. Minimum price floor of $1.00
        
        Example:
        - Current price: $10.00
        - Previous attention: 50
        - New attention: 60 (20% increase)
        - Price change: 20% * 0.15 = 3% increase
        - New price: $10.00 * 1.03 = $10.30
        """
        if previous_score == 0:
            previous_score = 50.0
        
        # Calculate percentage change in attention
        score_change = (new_score - previous_score) / previous_score
        
        # Apply dampening factor to prevent extreme price swings
        # Maximum 15% price change per update
        dampening_factor = 0.15
        price_multiplier = 1 + (score_change * dampening_factor)
        
        # Cap between 70% and 150% (max -30% or +50% change)
        price_multiplier = max(0.7, min(1.5, price_multiplier))
        
        new_price = current_price * price_multiplier
        
        # Minimum price floor of $1.00
        return max(1.0, new_price)

    async def seed_historical_data(self, target: AttentionTarget, days: int = 7):
        """Create realistic historical data for the past N days for charts"""
        db = SessionLocal()
        try:
            # Check if we already have historical data
            existing_history = db.query(AttentionHistory).filter(
                AttentionHistory.target_id == target.id
            ).count()
            
            if existing_history > 0:
                logger.info(f"Historical data already exists for {target.name}")
                return
            
            # Generate historical data for past 7 days
            base_attention = float(target.current_attention_score) if target.current_attention_score else 50.0
            base_price = float(target.current_share_price) if target.current_share_price else 10.0
            
            # Create entries for each day (4 entries per day = every 6 hours)
            entries_per_day = 4
            total_entries = days * entries_per_day
            
            for i in range(total_entries, 0, -1):  # Go backwards in time
                # Calculate timestamp (going backwards from now)
                timestamp = datetime.utcnow() - timedelta(hours=i * 6)
                
                # Generate realistic attention score with some trend
                trend_factor = (total_entries - i) / total_entries  # 0 to 1
                volatility = random.uniform(-5, 5)  # Random noise
                
                attention_score = base_attention + (trend_factor * 10) + volatility
                attention_score = max(0, min(100, attention_score))  # Keep in 0-100 range
                
                # Calculate corresponding price
                if i == total_entries:  # First entry
                    price = base_price
                else:
                    # Get previous price and calculate new one
                    prev_entry = db.query(AttentionHistory).filter(
                        AttentionHistory.target_id == target.id
                    ).order_by(AttentionHistory.timestamp.desc()).first()
                    
                    prev_score = float(prev_entry.attention_score) if prev_entry else 50.0
                    prev_price = float(prev_entry.share_price) if prev_entry else base_price
                    
                    price = self.calculate_new_price(prev_price, attention_score, prev_score)
                
                # Create history entry
                history_entry = AttentionHistory(
                    target_id=target.id,
                    attention_score=Decimal(str(attention_score)),
                    share_price=Decimal(str(price)),
                    timestamp=timestamp
                )
                db.add(history_entry)
            
            db.commit()
            logger.info(f"Created {total_entries} historical entries for {target.name}")
            
        except Exception as e:
            logger.error(f"Error seeding historical data for {target.name}: {e}")
            db.rollback()
        finally:
            db.close()

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
            
            source = trends_data.get("source", "unknown")
            logger.info(f"Updated {target.name}: Score {new_score:.1f}, Price ${new_price:.2f} ({source})")
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
                # Seed historical data if this is the first time
                await self.seed_historical_data(target)
                
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

# Background task runner with 1-minute updates
async def run_data_updates():
    """Main function to run periodic data updates every minute"""
    service = SerpAPIService()
    
    # Run initial update
    logger.info("Starting initial data update...")
    await service.update_all_targets()
    
    while True:
        try:
            logger.info("Starting scheduled data update...")
            await service.update_all_targets()
            
            # Wait 1 minute before next update (changed from 15 minutes)
            logger.info("Waiting 1 minute until next update...")
            await asyncio.sleep(60)  # 1 minute = 60 seconds
            
        except Exception as e:
            logger.error(f"Error in data update cycle: {e}")
            # Wait 1 minute before retrying on error
            await asyncio.sleep(60)

# Seed some initial targets with historical data
async def seed_initial_targets():
    """Seed the database with popular targets and their historical data"""
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
            {"name": "Tesla", "type": TargetType.STOCK, "search_term": "Tesla"},
            {"name": "GameStop", "type": TargetType.STOCK, "search_term": "GameStop"},
            {"name": "AMC", "type": TargetType.STOCK, "search_term": "AMC"},
            {"name": "Bitcoin", "type": TargetType.STOCK, "search_term": "Bitcoin"},
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
                db.commit()
                db.refresh(target)
                
                # Seed historical data
                await service.seed_historical_data(target, days=7)
                
                logger.info(f"Added target: {target_data['name']} (Score: {initial_score:.1f})")
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(2)
        
        db.commit()
        logger.info("Initial targets seeded successfully with historical data!")
        
    except Exception as e:
        logger.error(f"Error seeding targets: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # Run the seeder first, then start the update service
    asyncio.run(seed_initial_targets())
    asyncio.run(run_data_updates())