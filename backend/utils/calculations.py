"""
Business logic calculations
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any
from models import User, Prediction, Trend

def calculate_payout_ratio(trend_id: int, prediction: bool, predictions_count: Dict[str, int]) -> float:
    """
    Calculate dynamic payout ratio based on prediction distribution
    More balanced = higher payout, more one-sided = lower payout
    """
    total_predictions = predictions_count.get('total', 0)
    if total_predictions == 0:
        return 2.0  # Default 2:1 ratio
    
    yes_count = predictions_count.get('yes', 0)
    no_count = predictions_count.get('no', 0)
    
    # Calculate ratio based on minority prediction
    if prediction:  # Predicting YES
        minority_ratio = no_count / total_predictions if total_predictions > 0 else 0.5
    else:  # Predicting NO
        minority_ratio = yes_count / total_predictions if total_predictions > 0 else 0.5
    
    # Base ratio + bonus for minority prediction
    base_ratio = 1.5
    bonus_ratio = 1.0 + (0.5 - minority_ratio) * 2  # Max bonus of 1.0
    
    return max(1.1, min(5.0, base_ratio + bonus_ratio))

def calculate_accuracy_metrics(user: User) -> Dict[str, Any]:
    """Calculate various accuracy metrics for a user"""
    total_predictions = user.total_predictions
    correct_predictions = user.correct_predictions
    
    if total_predictions == 0:
        return {
            'accuracy_rate': 0.0,
            'confidence_rating': 'Newcomer',
            'skill_level': 'Beginner',
            'trend': 'stable'
        }
    
    accuracy_rate = (correct_predictions / total_predictions) * 100
    
    # Determine confidence rating
    if accuracy_rate >= 80:
        confidence_rating = 'Expert'
    elif accuracy_rate >= 70:
        confidence_rating = 'Advanced'
    elif accuracy_rate >= 60:
        confidence_rating = 'Intermediate'
    elif accuracy_rate >= 50:
        confidence_rating = 'Novice'
    else:
        confidence_rating = 'Learning'
    
    # Determine skill level based on both accuracy and volume
    if total_predictions >= 100 and accuracy_rate >= 75:
        skill_level = 'Master'
    elif total_predictions >= 50 and accuracy_rate >= 65:
        skill_level = 'Expert'
    elif total_predictions >= 20 and accuracy_rate >= 55:
        skill_level = 'Intermediate'
    else:
        skill_level = 'Beginner'
    
    return {
        'accuracy_rate': round(accuracy_rate, 1),
        'confidence_rating': confidence_rating,
        'skill_level': skill_level,
        'total_predictions': total_predictions,
        'correct_predictions': correct_predictions
    }

def calculate_platform_stats(db_session) -> Dict[str, Any]:
    """Calculate overall platform statistics"""
    from sqlalchemy import func
    
    # Total users
    total_users = db_session.query(User).count()
    
    # Active users (made prediction in last 30 days)
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    active_users = db_session.query(User).join(Prediction).filter(
        Prediction.created_at >= thirty_days_ago
    ).distinct().count()
    
    # Total predictions
    total_predictions = db_session.query(Prediction).count()
    
    # Total resolved predictions
    resolved_predictions = db_session.query(Prediction).filter(
        Prediction.is_resolved == True
    ).count()
    
    # Average accuracy
    if resolved_predictions > 0:
        correct_predictions = db_session.query(Prediction).filter(
            Prediction.is_resolved == True,
            Prediction.is_correct == True
        ).count()
        platform_accuracy = (correct_predictions / resolved_predictions) * 100
    else:
        platform_accuracy = 0.0
    
    # Active trends
    active_trends = db_session.query(Trend).filter(
        Trend.is_active == True,
        Trend.is_resolved == False
    ).count()
    
    return {
        'total_users': total_users,
        'active_users': active_users,
        'total_predictions': total_predictions,
        'resolved_predictions': resolved_predictions,
        'platform_accuracy': round(platform_accuracy, 1),
        'active_trends': active_trends
    }

def round_currency(amount: float) -> Decimal:
    """Round currency to 2 decimal places"""
    return Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)