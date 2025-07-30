# Create/update this file: backend/background_updater.py

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from database import SessionLocal
from models import AttentionTarget, AttentionHistory
from google_trends_service import GoogleTrendsService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptimizedBackgroundUpdater:
    """
    Production-ready background updater with smart target management
    - Updates every 5 minutes
    - Maximum 50 targets per cycle
    - Priority-based target selection
    - Proper error handling and recovery
    """
    
    def __init__(self, max_targets_per_cycle=50, update_interval_minutes=5):
        self.max_targets_per_cycle = max_targets_per_cycle
        self.update_interval_seconds = update_interval_minutes * 60
        self.last_update_time = None
        self.cycle_count = 0
        
    async def get_priority_targets(self, db: Session) -> list:
        """
        Get up to max_targets_per_cycle targets, prioritized by:
        1. Newly created targets (less than 1 day old)
        2. Popular targets (high activity)
        3. Targets that haven't been updated recently
        4. Round-robin for the rest
        """
        
        # Get all active targets
        all_targets = db.query(AttentionTarget).filter(
            AttentionTarget.is_active == True
        ).all()
        
        if len(all_targets) <= self.max_targets_per_cycle:
            logger.info(f"📊 Will update all {len(all_targets)} targets")
            return all_targets
        
        # Priority 1: New targets (created in last 24 hours)
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        new_targets = [t for t in all_targets if t.created_at > one_day_ago]
        
        # Priority 2: Targets not updated in last hour (stale data)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        stale_targets = [t for t in all_targets 
                        if not t.last_updated or t.last_updated < one_hour_ago]
        
        # Priority 3: Round-robin through remaining targets
        remaining_targets = [t for t in all_targets 
                           if t not in new_targets and t not in stale_targets]
        
        # Rotate through remaining targets based on cycle count
        if remaining_targets:
            start_idx = (self.cycle_count * 10) % len(remaining_targets)
            rotated_targets = remaining_targets[start_idx:] + remaining_targets[:start_idx]
        else:
            rotated_targets = []
        
        # Combine priorities
        priority_targets = new_targets + stale_targets + rotated_targets
        
        # Take only the max we can handle
        selected_targets = priority_targets[:self.max_targets_per_cycle]
        
        logger.info(f"📊 Selected {len(selected_targets)} targets: "
                   f"{len(new_targets)} new, {len(stale_targets)} stale, "
                   f"{len(selected_targets) - len(new_targets) - len(stale_targets)} rotated")
        
        return selected_targets
    
    async def update_target_batch(self, targets: list, db: Session) -> dict:
        """Update a batch of targets with proper error recovery"""
        
        results = {
            "successful": 0,
            "failed": 0,
            "errors": []
        }
        
        async with GoogleTrendsService() as service:
            for i, target in enumerate(targets):
                try:
                    logger.info(f"📈 [{i+1}/{len(targets)}] Updating {target.name}...")
                    
                    # Get fresh attention data
                    trends_data = await service.get_google_trends_data(target.search_term)
                    new_score = trends_data["attention_score"]
                    
                    # Update target
                    old_score = float(target.current_attention_score) if target.current_attention_score else 50.0
                    target.current_attention_score = Decimal(str(new_score))
                    target.last_updated = datetime.utcnow()
                    
                    # Create historical entry
                    history_entry = AttentionHistory(
                        target_id=target.id,
                        attention_score=Decimal(str(new_score)),
                        timestamp=datetime.utcnow()
                    )
                    db.add(history_entry)
                    
                    # Log the update
                    change = new_score - old_score
                    change_str = f"({change:+.1f})" if change != 0 else "(no change)"
                    logger.info(f"✅ {target.name}: {old_score:.1f} → {new_score:.1f} {change_str}")
                    
                    results["successful"] += 1
                    
                    # Rate limiting delay
                    await asyncio.sleep(3)  # 3 seconds between requests
                    
                except Exception as e:
                    error_msg = f"Failed to update {target.name}: {str(e)}"
                    logger.error(f"❌ {error_msg}")
                    results["failed"] += 1
                    results["errors"].append(error_msg)
                    
                    # Continue with next target on error
                    continue
        
        return results
    
    async def run_update_cycle(self):
        """Run a single update cycle"""
        cycle_start = datetime.utcnow()
        self.cycle_count += 1
        
        logger.info(f"🔄 Starting update cycle #{self.cycle_count}")
        
        db = SessionLocal()
        try:
            # Get priority targets for this cycle
            targets = await self.get_priority_targets(db)
            
            if not targets:
                logger.info("📭 No targets to update")
                return
            
            # Update the selected targets
            results = await self.update_target_batch(targets, db)
            
            # Commit all changes
            db.commit()
            
            # Log cycle summary
            cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
            logger.info(f"✅ Cycle #{self.cycle_count} completed in {cycle_duration:.1f}s: "
                       f"{results['successful']} updated, {results['failed']} failed")
            
            if results["errors"]:
                logger.warning(f"⚠️ Errors in cycle #{self.cycle_count}: {len(results['errors'])} targets failed")
            
        except Exception as e:
            logger.error(f"❌ Update cycle #{self.cycle_count} failed: {e}")
            db.rollback()
        finally:
            db.close()
            self.last_update_time = datetime.utcnow()
    
    async def run_continuous_updates(self):
        """Main loop for continuous background updates"""
        logger.info(f"🚀 Starting continuous updates: {self.max_targets_per_cycle} targets every {self.update_interval_seconds//60} minutes")
        
        # Run initial update immediately
        await self.run_update_cycle()
        
        # Continue with scheduled updates
        while True:
            try:
                logger.info(f"⏰ Waiting {self.update_interval_seconds//60} minutes until next update...")
                await asyncio.sleep(self.update_interval_seconds)
                
                await self.run_update_cycle()
                
            except KeyboardInterrupt:
                logger.info("🛑 Background updater stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Error in update loop: {e}")
                # Wait before retrying on error
                await asyncio.sleep(60)  # 1 minute retry delay

# Global updater instance
updater = OptimizedBackgroundUpdater(max_targets_per_cycle=50, update_interval_minutes=5)

# Main functions for external use
async def start_background_updates():
    """Start the optimized background update system"""
    await updater.run_continuous_updates()

def get_updater_status():
    """Get current status of the background updater"""
    return {
        "max_targets_per_cycle": updater.max_targets_per_cycle,
        "update_interval_minutes": updater.update_interval_seconds // 60,
        "cycle_count": updater.cycle_count,
        "last_update_time": updater.last_update_time.isoformat() if updater.last_update_time else None,
        "status": "running"
    }

if __name__ == "__main__":
    # Run the background updater directly
    asyncio.run(start_background_updates())