from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status
from pydantic import BaseModel, validator

class TrendValidation(BaseModel):
    title: str
    description: str
    category_id: int
    target_value: Optional[float] = None
    deadline: datetime
    
    @validator('title')
    def validate_title(cls, v):
        if len(v.strip()) < 5:
            raise ValueError('Title must be at least 5 characters long')
        if len(v.strip()) > 200:
            raise ValueError('Title must be less than 200 characters')
        return v.strip()
    
    @validator('description')
    def validate_description(cls, v):
        if len(v.strip()) < 20:
            raise ValueError('Description must be at least 20 characters long')
        if len(v.strip()) > 1000:
            raise ValueError('Description must be less than 1000 characters')
        return v.strip()
    
    @validator('deadline')
    def validate_deadline(cls, v):
        if v <= datetime.utcnow():
            raise ValueError('Deadline must be in the future')
        if v > datetime.utcnow() + timedelta(days=365):
            raise ValueError('Deadline cannot be more than 1 year in the future')
        return v

class PredictionValidation(BaseModel):
    trend_id: int
    prediction: bool
    confidence: int
    stake_amount: float
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if v < 1 or v > 10:
            raise ValueError('Confidence must be between 1 and 10')
        return v
    
    @validator('stake_amount')
    def validate_stake_amount(cls, v):
        if v <= 0:
            raise ValueError('Stake amount must be positive')
        if v > 10000:
            raise ValueError('Stake amount cannot exceed $10,000')
        return v

def validate_user_balance(user_balance: float, stake_amount: float):
    """Check if user has sufficient balance"""
    if user_balance < stake_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient balance. Available: ${user_balance:.2f}, Required: ${stake_amount:.2f}"
        )

def validate_trend_active(trend):
    """Check if trend is active and accepting predictions"""
    if not trend:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trend not found"
        )
    
    if not trend.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trend is not active"
        )
    
    if trend.is_resolved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trend has already been resolved"
        )
    
    if trend.deadline <= datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trend deadline has passed"
        )