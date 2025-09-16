from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum, Text, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

Base = declarative_base()

class TargetType(enum.Enum):
    POLITICIAN = "politician"
    CELEBRITY = "celebrity"  # Combines billionaires + content creators + entertainers
    COUNTRY = "country"
    GAME = "game"  # New gaming category
    STOCK = "stock"  # Traditional stocks
    CRYPTO = "crypto"  # Cryptocurrencies

class TournamentDuration(enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    password_hash = Column(String(128))
    balance = Column(Numeric(10, 2), default=0.00)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    
    # Relationships
    portfolios = relationship("Portfolio", back_populates="user")
    trades = relationship("Trade", back_populates="user")
    tournament_entries = relationship("TournamentEntry", back_populates="user")

class AttentionTarget(Base):
    __tablename__ = "attention_targets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    type = Column(Enum(TargetType), nullable=False)
    search_term = Column(String(200), nullable=False, index=True)
    description = Column(Text)
    
    # ONLY attention score - no share price
    current_attention_score = Column(Numeric(5, 2), nullable=False, default=50.0)
    
    # Metadata
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    
    # 5-year baseline metadata
    baseline_period = Column(String(20), default="5_year")
    baseline_average = Column(Numeric(5, 2))
    baseline_max = Column(Numeric(5, 2))
    baseline_min = Column(Numeric(5, 2))
    
    # Relationships
    history = relationship("AttentionHistory", back_populates="target")
    portfolios = relationship("Portfolio", back_populates="target")
    trades = relationship("Trade", back_populates="target")

class AttentionHistory(Base):
    __tablename__ = "attention_history"
    
    id = Column(Integer, primary_key=True, index=True)
    target_id = Column(Integer, ForeignKey("attention_targets.id"), nullable=False)
    
    # ONLY attention score - no share price
    attention_score = Column(Numeric(5, 2), nullable=False)
    
    # Additional context fields
    data_source = Column(String(50), default="google_trends")
    timeframe_used = Column(String(20), default="5_year")
    confidence_score = Column(Numeric(3, 2))
    
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Relationship
    target = relationship("AttentionTarget", back_populates="history")

class Portfolio(Base):
    """
    Attention-based portfolio tracking with long/short positions
    """
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_id = Column(Integer, ForeignKey("attention_targets.id"), nullable=False)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"), nullable=True)  # NEW: Which tournament
    
    # Position type: long (bet score goes up) or short (bet score goes down)
    position_type = Column(String(10), nullable=False, default="long")  # NEW: "long" or "short"
    
    # Attention-based tracking
    attention_stakes = Column(Numeric(10, 2), nullable=False, default=0.0)
    average_entry_score = Column(Numeric(5, 2))  # Average attention score when invested
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = relationship("User", back_populates="portfolios")
    target = relationship("AttentionTarget", back_populates="portfolios")
    tournament = relationship("Tournament", back_populates="portfolios")

# Add relationship to Tournament model
class Tournament(Base):
    __tablename__ = "tournaments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    target_type = Column(Enum(TargetType), nullable=False)
    duration = Column(Enum(TournamentDuration), nullable=False)
    
    entry_fee = Column(Numeric(10, 2), nullable=False)
    prize_pool = Column(Numeric(10, 2), default=0.0)
    participant_count = Column(Integer, default=0)
    
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    is_finished = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    entries = relationship("TournamentEntry", back_populates="tournament")
    portfolios = relationship("Portfolio", back_populates="tournament")  # NEW

# Updated TournamentEntry with virtual balances
class TournamentEntry(Base):
    __tablename__ = "tournament_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"), nullable=False)
    
    entry_fee = Column(Numeric(10, 2), nullable=False)
    starting_balance = Column(Numeric(10, 2), default=10000.0)  # Everyone gets $10k
    current_balance = Column(Numeric(10, 2), default=10000.0)   # Updated as they trade
    final_balance = Column(Numeric(10, 2))
    final_pnl = Column(Numeric(10, 2), default=0.0)
    rank = Column(Integer)
    
    payout_amount = Column(Numeric(10, 2), default=0.0)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="tournament_entries")
    tournament = relationship("Tournament", back_populates="entries")

# Updated Trade model to include tournament context
class Trade(Base):
    """
    Attention betting/staking with tournament context
    """
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_id = Column(Integer, ForeignKey("attention_targets.id"), nullable=False)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"), nullable=True)  # NEW
    
    # Trade details
    trade_type = Column(String(20), nullable=False)  # 'stake_buy' (long), 'stake_sell' (short), 'close_long', 'close_short'
    position_type = Column(String(10), nullable=False, default="long")  # "long" or "short"
    stake_amount = Column(Numeric(10, 2), nullable=False)
    attention_score_at_entry = Column(Numeric(5, 2), nullable=False)
    
    # Outcome tracking
    pnl = Column(Numeric(10, 2), default=0.0)
    is_closed = Column(Boolean, default=False)
    
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    closed_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="trades")
    target = relationship("AttentionTarget", back_populates="trades")
    tournament = relationship("Tournament")  # NEW