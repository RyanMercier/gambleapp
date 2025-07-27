"""
Admin endpoints for managing trends and platform
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List, Optional

from database import get_db
from models import User, Trend, TrendCategory, Prediction
from auth import get_current_user
from utils.calculations import calculate_platform_stats

router = APIRouter(prefix="/admin", tags=["admin"])

def verify_admin(current_user: User = Depends(get_current_user)):
    """Verify user has admin privileges"""
    if current_user.username != "admin":  # Simple admin check
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

@router.get("/stats")
async def get_admin_stats(
    admin_user: User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """Get comprehensive platform statistics"""
    stats = calculate_platform_stats(db)
    
    # Additional admin-specific stats
    recent_users = db.query(User).filter(
        User.created_at >= datetime.utcnow() - timedelta(days=7)
    ).count()
    
    pending_trends = db.query(Trend).filter(
        Trend.is_active == True,
        Trend.deadline <= datetime.utcnow() + timedelta(days=1),
        Trend.is_resolved == False
    ).count()
    
    stats.update({
        'new_users_this_week': recent_users,
        'trends_ending_soon': pending_trends
    })
    
    return stats

@router.get("/trends/pending")
async def get_pending_trends(
    admin_user: User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """Get trends that need resolution"""
    trends = db.query(Trend).filter(
        Trend.is_active == True,
        Trend.deadline <= datetime.utcnow(),
        Trend.is_resolved == False
    ).order_by(Trend.deadline.desc()).all()
    
    return trends

@router.post("/trends/{trend_id}/resolve")
async def resolve_trend(
    trend_id: int,
    outcome: bool,
    admin_user: User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """Resolve a trend and calculate payouts"""
    trend = db.query(Trend).filter(Trend.id == trend_id).first()
    if not trend:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trend not found"
        )
    
    if trend.is_resolved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trend already resolved"
        )
    
    # Update trend
    trend.is_resolved = True
    trend.actual_outcome = outcome
    
    # Update predictions and calculate payouts
    predictions = db.query(Prediction).filter(
        Prediction.trend_id == trend_id,
        Prediction.is_resolved == False
    ).all()
    
    total_payout = 0
    correct_count = 0
    
    for prediction in predictions:
        prediction.is_resolved = True
        prediction.is_correct = (prediction.prediction == outcome)
        
        if prediction.is_correct:
            # Calculate payout (using potential_payout for now)
            payout = prediction.potential_payout
            prediction.payout_amount = payout
            
            # Add payout to user balance
            user = db.query(User).filter(User.id == prediction.user_id).first()
            if user:
                user.balance += payout
                user.correct_predictions += 1
                total_payout += float(payout)
                correct_count += 1
        
        # Update user total predictions count
        user = db.query(User).filter(User.id == prediction.user_id).first()
        if user:
            user.total_predictions += 1
    
    db.commit()
    
    return {
        "message": "Trend resolved successfully",
        "trend_id": trend_id,
        "outcome": outcome,
        "total_predictions": len(predictions),
        "correct_predictions": correct_count,
        "total_payout": total_payout
    }

@router.get("/users")
async def get_all_users(
    page: int = 1,
    limit: int = 50,
    admin_user: User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """Get paginated list of all users"""
    offset = (page - 1) * limit
    
    users = db.query(User).offset(offset).limit(limit).all()
    total_users = db.query(User).count()
    
    user_data = []
    for user in users:
        accuracy = (user.correct_predictions / user.total_predictions * 100) if user.total_predictions > 0 else 0
        user_data.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "balance": float(user.balance),
            "total_predictions": user.total_predictions,
            "correct_predictions": user.correct_predictions,
            "accuracy_rate": round(accuracy, 1),
            "created_at": user.created_at,
            "is_active": user.is_active
        })
    
    return {
        "users": user_data,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total_users,
            "pages": (total_users + limit - 1) // limit
        }
    }