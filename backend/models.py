from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    balance = Column(Numeric(10, 2), default=1000.00)  # Starting balance
    total_predictions = Column(Integer, default=0)
    correct_predictions = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationship to predictions
    predictions = relationship("Prediction", back_populates="user")

class TrendCategory(Base):
    __tablename__ = 'trend_categories'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)
    icon = Column(String)  # Emoji or icon identifier
    is_active = Column(Boolean, default=True)
    
    # Relationship to trends
    trends = relationship("Trend", back_populates="category")

class Trend(Base):
    __tablename__ = 'trends'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category_id = Column(Integer, ForeignKey('trend_categories.id'))
    creator_id = Column(Integer, ForeignKey('users.id'))
    
    # Trend details
    current_value = Column(Numeric(15, 4))  # Current metric value
    target_value = Column(Numeric(15, 4))   # Target value for prediction
    deadline = Column(DateTime, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_resolved = Column(Boolean, default=False)
    actual_outcome = Column(Boolean)  # True if target was reached
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    category = relationship("TrendCategory", back_populates="trends")
    creator = relationship("User")
    predictions = relationship("Prediction", back_populates="trend")

class Prediction(Base):
    __tablename__ = 'predictions'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    trend_id = Column(Integer, ForeignKey('trends.id'))
    
    # Prediction details
    prediction = Column(Boolean, nullable=False)  # True = will reach target, False = won't
    confidence = Column(Integer)  # 1-10 confidence level
    stake_amount = Column(Numeric(10, 2), nullable=False)
    potential_payout = Column(Numeric(10, 2))
    
    # Status
    is_resolved = Column(Boolean, default=False)
    is_correct = Column(Boolean)
    payout_amount = Column(Numeric(10, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="predictions")
    trend = relationship("Trend", back_populates="predictions")