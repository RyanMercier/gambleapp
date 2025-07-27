from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import enum

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
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    balance = Column(Numeric(10, 2), default=1000.00)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    portfolios = relationship("Portfolio", back_populates="user")
    trades = relationship("Trade", back_populates="user")
    tournament_entries = relationship("TournamentEntry", back_populates="user")

class AttentionTarget(Base):
    __tablename__ = 'attention_targets'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    type = Column(Enum(TargetType), nullable=False)
    description = Column(Text)
    current_attention_score = Column(Numeric(10, 4), default=0)
    current_share_price = Column(Numeric(10, 2), default=10.00)  # Starting price
    search_term = Column(String, nullable=False)  # For Google Trends API
    last_updated = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    trades = relationship("Trade", back_populates="target")
    portfolios = relationship("Portfolio", back_populates="target")
    attention_history = relationship("AttentionHistory", back_populates="target")

class AttentionHistory(Base):
    __tablename__ = 'attention_history'
    
    id = Column(Integer, primary_key=True, index=True)
    target_id = Column(Integer, ForeignKey('attention_targets.id'))
    attention_score = Column(Numeric(10, 4), nullable=False)
    share_price = Column(Numeric(10, 2), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    target = relationship("AttentionTarget", back_populates="attention_history")

class Portfolio(Base):
    __tablename__ = 'portfolios'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    target_id = Column(Integer, ForeignKey('attention_targets.id'))
    shares_owned = Column(Numeric(15, 6), default=0)
    average_price = Column(Numeric(10, 2), default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="portfolios")
    target = relationship("AttentionTarget", back_populates="portfolios")

class Trade(Base):
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    target_id = Column(Integer, ForeignKey('attention_targets.id'))
    trade_type = Column(String, nullable=False)  # 'buy' or 'sell'
    shares = Column(Numeric(15, 6), nullable=False)
    price_per_share = Column(Numeric(10, 2), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="trades")
    target = relationship("AttentionTarget", back_populates="trades")

class Tournament(Base):
    __tablename__ = 'tournaments'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    target_type = Column(Enum(TargetType), nullable=False)
    duration = Column(Enum(TournamentDuration), nullable=False)
    entry_fee = Column(Numeric(10, 2), nullable=False)
    prize_pool = Column(Numeric(10, 2), default=0)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    entries = relationship("TournamentEntry", back_populates="tournament")

class TournamentEntry(Base):
    __tablename__ = 'tournament_entries'
    
    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(Integer, ForeignKey('tournaments.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    entry_fee_paid = Column(Numeric(10, 2), nullable=False)
    starting_balance = Column(Numeric(10, 2), default=1000.00)  # Virtual tournament balance
    current_balance = Column(Numeric(10, 2), default=1000.00)
    final_pnl = Column(Numeric(10, 2), default=0)
    rank = Column(Integer)
    prize_won = Column(Numeric(10, 2), default=0)
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tournament = relationship("Tournament", back_populates="entries")
    user = relationship("User", back_populates="tournament_entries")