# backend/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum, Text, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class TargetType(enum.Enum):
    POLITICIAN = "politician"
    BILLIONAIRE = "billionaire"
    COUNTRY = "country"
    STOCK = "stock"

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
    balance = Column(Numeric(10, 2), default=1000.00)
    created_at = Column(DateTime, default=datetime.utcnow)
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
    last_updated = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
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
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    target = relationship("AttentionTarget", back_populates="history")

class Portfolio(Base):
    """
    Attention-based portfolio tracking (no traditional shares)
    """
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_id = Column(Integer, ForeignKey("attention_targets.id"), nullable=False)
    
    # Attention-based tracking
    attention_stakes = Column(Numeric(10, 2), nullable=False, default=0.0)
    average_entry_score = Column(Numeric(5, 2))  # Average attention score when invested
    
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="portfolios")
    target = relationship("AttentionTarget", back_populates="portfolios")

class Trade(Base):
    """
    Attention betting/staking instead of traditional trading
    """
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_id = Column(Integer, ForeignKey("attention_targets.id"), nullable=False)
    
    # Trade details - betting on attention direction/levels
    trade_type = Column(String(20), nullable=False)  # 'stake_up', 'stake_down', 'stake_stable'
    stake_amount = Column(Numeric(10, 2), nullable=False)  # Amount staked
    attention_score_at_entry = Column(Numeric(5, 2), nullable=False)  # Score when trade made
    
    # Prediction/outcome tracking
    predicted_direction = Column(String(20))  # 'up', 'down', 'stable'
    predicted_target_score = Column(Numeric(5, 2))  # What score they're betting on
    outcome = Column(String(20))  # 'win', 'loss', 'pending'
    pnl = Column(Numeric(10, 2), default=0.0)  # Profit/loss from this stake
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    settled_at = Column(DateTime)  # When the outcome was determined
    
    # Relationships
    user = relationship("User", back_populates="trades")
    target = relationship("AttentionTarget", back_populates="trades")

class Tournament(Base):
    __tablename__ = "tournaments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Tournament config
    duration = Column(Enum(TournamentDuration), nullable=False)
    entry_fee = Column(Numeric(10, 2), nullable=False)
    max_participants = Column(Integer, default=1000)
    prize_pool = Column(Numeric(12, 2), default=0.0)
    
    # Tournament timing
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    # Status
    status = Column(String(20), default="upcoming")  # upcoming, active, completed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    entries = relationship("TournamentEntry", back_populates="tournament")

class TournamentEntry(Base):
    __tablename__ = "tournament_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"), nullable=False)
    
    # Entry details
    entry_fee_paid = Column(Numeric(10, 2), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    # Performance tracking
    starting_score = Column(Numeric(10, 2), default=0.0)
    final_score = Column(Numeric(10, 2), default=0.0)
    rank = Column(Integer)
    prize_won = Column(Numeric(10, 2), default=0.0)
    
    # Relationships
    user = relationship("User", back_populates="tournament_entries")
    tournament = relationship("Tournament", back_populates="entries")