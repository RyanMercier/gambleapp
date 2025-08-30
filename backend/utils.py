# backend/utils.py
# FIX 6: Technical debt cleanup - Centralized utility functions

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class CalculationUtils:
    """Centralized calculation utilities to avoid code duplication"""
    
    @staticmethod
    def calculate_position_value(
        stakes: Decimal,
        entry_score: Decimal,
        current_score: Decimal,
        position_type: str = "long"
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate position value and P&L consistently across the app
        
        Returns:
            tuple: (current_value, unrealized_pnl)
        """
        if not entry_score or entry_score <= 0:
            return stakes, Decimal('0.0')
        
        score_ratio = current_score / entry_score
        
        if position_type.lower() == "long":
            # Long position: profit when score increases
            current_value = stakes * score_ratio
            unrealized_pnl = current_value - stakes
        elif position_type.lower() == "short":
            # Short position: profit when score decreases  
            current_value = stakes * (Decimal('2.0') - score_ratio)
            unrealized_pnl = current_value - stakes
        else:
            logger.warning(f"Unknown position type: {position_type}")
            return stakes, Decimal('0.0')
        
        return current_value, unrealized_pnl
    
    @staticmethod
    def calculate_weighted_average(
        existing_stakes: Decimal,
        existing_score: Decimal,
        new_stakes: Decimal,
        new_score: Decimal
    ) -> Decimal:
        """Calculate weighted average entry score for position updates"""
        total_stakes = existing_stakes + new_stakes
        
        if total_stakes <= 0:
            return new_score
            
        weighted_avg = (
            (existing_stakes * existing_score) + (new_stakes * new_score)
        ) / total_stakes
        
        return weighted_avg.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @staticmethod
    def safe_decimal(value, default: Decimal = Decimal('0.0')) -> Decimal:
        """Safely convert various types to Decimal"""
        if value is None:
            return default
            
        try:
            if isinstance(value, Decimal):
                return value
            return Decimal(str(value))
        except (ValueError, TypeError):
            logger.warning(f"Failed to convert {value} to Decimal, using default {default}")
            return default

class ValidationUtils:
    """Input validation utilities"""
    
    @staticmethod
    def validate_trade_amount(amount: float, max_amount: float) -> bool:
        """Validate trade amount is within limits"""
        return 0 < amount <= max_amount
    
    @staticmethod
    def validate_position_type(position_type: str) -> bool:
        """Validate position type is valid"""
        return position_type.lower() in ['long', 'short']
    
    @staticmethod
    def validate_target_id(target_id: int) -> bool:
        """Validate target ID is positive integer"""
        return isinstance(target_id, int) and target_id > 0

class TournamentUtils:
    """Tournament-related utilities"""
    
    @staticmethod
    def is_tournament_active(tournament) -> bool:
        """Check if tournament is currently active"""
        from datetime import datetime
        
        now = datetime.utcnow()
        return (
            tournament.is_active and
            not tournament.is_finished and
            tournament.start_date <= now <= tournament.end_date
        )
    
    @staticmethod
    def get_tournament_status(tournament) -> str:
        """Get human-readable tournament status"""
        from datetime import datetime
        
        now = datetime.utcnow()
        
        if now < tournament.start_date:
            return "upcoming"
        elif now > tournament.end_date:
            return "finished"
        elif tournament.is_finished:
            return "completed"
        else:
            return "active"

# FIX 6: Cleaned up database query helpers
class DatabaseUtils:
    """Database query helpers to reduce code duplication"""
    
    @staticmethod
    def get_user_active_tournament_entry(user_id: int, db):
        """Get user's active tournament entry"""
        from models import TournamentEntry, Tournament
        from datetime import datetime
        
        return db.query(TournamentEntry).filter(
            TournamentEntry.user_id == user_id
        ).join(Tournament).filter(
            Tournament.is_active == True,
            Tournament.is_finished == False,
            Tournament.start_date <= datetime.utcnow(),
            Tournament.end_date >= datetime.utcnow()
        ).first()
    
    @staticmethod
    def get_user_position(user_id: int, target_id: int, tournament_id: int, position_type: str, db):
        """Get specific user position"""
        from models import Portfolio
        
        return db.query(Portfolio).filter(
            Portfolio.user_id == user_id,
            Portfolio.target_id == target_id,
            Portfolio.tournament_id == tournament_id,
            Portfolio.position_type == position_type
        ).first()
    
    @staticmethod
    def get_user_positions_in_tournament(user_id: int, tournament_id: int, db):
        """Get all user positions in a tournament"""
        from models import Portfolio
        
        return db.query(Portfolio).filter(
            Portfolio.user_id == user_id,
            Portfolio.tournament_id == tournament_id
        ).all()
    
    @staticmethod
    def get_daily_trades(user_id: int, db, date=None):
        """Get user's trades for a specific date (default: today)"""
        from models import Trade
        from datetime import datetime, timedelta
        
        if date is None:
            date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        next_day = date + timedelta(days=1)
        
        return db.query(Trade).filter(
            Trade.user_id == user_id,
            Trade.timestamp >= date,
            Trade.timestamp < next_day
        ).all()

# FIX 6: Error handling utilities
class ErrorHandlingUtils:
    """Centralized error handling"""
    
    @staticmethod
    def log_and_raise_http_error(status_code: int, detail: str, logger_instance=None):
        """Log error and raise HTTPException"""
        from fastapi import HTTPException
        
        if logger_instance:
            logger_instance.error(f"HTTP {status_code}: {detail}")
        
        raise HTTPException(status_code=status_code, detail=detail)
    
    @staticmethod
    def handle_database_error(db, error, operation: str):
        """Handle database errors consistently"""
        logger.error(f"Database error during {operation}: {error}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"{operation} failed: Database error")

# FIX 6: Response formatting utilities  
class ResponseUtils:
    """Consistent API response formatting"""
    
    @staticmethod
    def format_portfolio_response(positions, total_position_value, total_unrealized_pnl, realized_daily_pnl, total_cash_balance):
        """Format portfolio response consistently"""
        return {
            "positions": positions,
            "total_position_value": float(total_position_value),
            "total_unrealized_pnl": float(total_unrealized_pnl),
            "realized_daily_pnl": float(realized_daily_pnl),
            "total_daily_pnl": float(realized_daily_pnl + total_unrealized_pnl),
            "total_cash_balance": float(total_cash_balance),
            "total_portfolio_value": float(total_position_value + total_cash_balance)
        }
    
    @staticmethod
    def format_trade_response(message: str, pnl: Decimal, balance: Decimal, trade_id: int, **kwargs):
        """Format trade response consistently"""
        response = {
            "message": message,
            "pnl": float(pnl),
            "balance": float(balance),
            "trade_id": trade_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        response.update(kwargs)
        return response
    
    @staticmethod
    def format_tournament_response(tournament, participant_count=0):
        """Format tournament response consistently"""
        return {
            "id": tournament.id,
            "name": tournament.name,
            "target_type": tournament.target_type.value,
            "duration": tournament.duration.value,
            "entry_fee": float(tournament.entry_fee),
            "current_participants": participant_count,
            "prize_pool": float(tournament.prize_pool),
            "start_date": tournament.start_date.isoformat(),
            "end_date": tournament.end_date.isoformat(),
            "status": TournamentUtils.get_tournament_status(tournament),
            "is_active": tournament.is_active,
            "is_finished": tournament.is_finished
        }

# FIX 6: Caching utilities for performance
class CacheUtils:
    """Simple in-memory caching to reduce database hits"""
    
    _cache = {}
    _cache_timestamps = {}
    
    @classmethod
    def get(cls, key: str, max_age_seconds: int = 300):
        """Get cached value if not expired"""
        from datetime import datetime, timedelta
        
        if key not in cls._cache:
            return None
            
        timestamp = cls._cache_timestamps.get(key)
        if not timestamp:
            return None
            
        if datetime.utcnow() - timestamp > timedelta(seconds=max_age_seconds):
            # Expired, remove from cache
            cls._cache.pop(key, None)
            cls._cache_timestamps.pop(key, None)
            return None
            
        return cls._cache[key]
    
    @classmethod
    def set(cls, key: str, value):
        """Set cached value with timestamp"""
        from datetime import datetime
        
        cls._cache[key] = value
        cls._cache_timestamps[key] = datetime.utcnow()
    
    @classmethod
    def clear(cls):
        """Clear all cached values"""
        cls._cache.clear()
        cls._cache_timestamps.clear()

# FIX 6: Configuration management
class Config:
    """Centralized configuration"""
    
    # Trading limits
    MIN_TRADE_AMOUNT = Decimal('10.0')  # $10 minimum trade
    MAX_TRADE_AMOUNT = Decimal('1000.0')  # $1000 maximum trade
    STARTING_BALANCE = Decimal('10000.0')  # $10k starting balance
    
    # Tournament settings
    MIN_FREE_TOURNAMENTS = 3
    TOURNAMENT_DURATION_HOURS = 24
    PLATFORM_FEE_RATE = Decimal('0.10')  # 10% platform fee
    
    # Update intervals (seconds)
    CHART_UPDATE_INTERVAL = 60  # 1 minute
    POSITION_UPDATE_INTERVAL = 30  # 30 seconds
    NAV_UPDATE_INTERVAL = 45  # 45 seconds
    
    # Prize distribution
    PRIZE_PERCENTAGES = [
        Decimal('0.50'),  # 1st place: 50%
        Decimal('0.30'),  # 2nd place: 30%
        Decimal('0.20'),  # 3rd place: 20%
    ]