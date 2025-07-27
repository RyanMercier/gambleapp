from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from database import SessionLocal, engine
from models import Base, User, TrendCategory, Trend, Prediction
from auth import (
    create_user, 
    authenticate_user, 
    create_access_token, 
    decode_access_token
)

# Create tables
Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI(title="TrendBet API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models
class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class TrendCreate(BaseModel):
    title: str
    description: str
    category_id: int
    target_value: float
    deadline: datetime

class PredictionCreate(BaseModel):
    trend_id: int
    prediction: bool
    confidence: int
    stake_amount: float

class UserResponse(BaseModel):
    id: int
    username: str
    balance: float
    total_predictions: int
    correct_predictions: int
    accuracy_rate: float

    class Config:
        from_attributes = True

# Auth endpoints
@app.post("/auth/register")
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    # Check if user exists
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists"
        )
    
    user = create_user(db, user_data.username, user_data.email, user_data.password)
    token = create_access_token(data={"sub": user.username})
    
    return {
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "balance": float(user.balance),
            "total_predictions": user.total_predictions,
            "correct_predictions": user.correct_predictions,
            "accuracy_rate": 0.0
        }
    }

@app.post("/auth/login")
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    token = create_access_token(data={"sub": user.username})
    accuracy_rate = (user.correct_predictions / user.total_predictions * 100) if user.total_predictions > 0 else 0
    
    return {
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "balance": float(user.balance),
            "total_predictions": user.total_predictions,
            "correct_predictions": user.correct_predictions,
            "accuracy_rate": round(accuracy_rate, 1)
        }
    }

# Get current user
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = decode_access_token(token)
    username = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user

@app.get("/auth/me")
def get_me(current_user: User = Depends(get_current_user)):
    accuracy_rate = (current_user.correct_predictions / current_user.total_predictions * 100) if current_user.total_predictions > 0 else 0
    return {
        "id": current_user.id,
        "username": current_user.username,
        "balance": float(current_user.balance),
        "total_predictions": current_user.total_predictions,
        "correct_predictions": current_user.correct_predictions,
        "accuracy_rate": round(accuracy_rate, 1)
    }

# Trend endpoints
@app.get("/trends/categories")
def get_categories(db: Session = Depends(get_db)):
    categories = db.query(TrendCategory).filter(TrendCategory.is_active == True).all()
    return categories

@app.get("/trends")
def get_trends(
    category_id: Optional[int] = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    query = db.query(Trend)
    
    if active_only:
        query = query.filter(Trend.is_active == True, Trend.is_resolved == False)
    
    if category_id:
        query = query.filter(Trend.category_id == category_id)
    
    trends = query.order_by(Trend.deadline.asc()).all()
    return trends

@app.post("/trends")
def create_trend(
    trend_data: TrendCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    trend = Trend(
        title=trend_data.title,
        description=trend_data.description,
        category_id=trend_data.category_id,
        target_value=trend_data.target_value,
        deadline=trend_data.deadline,
        creator_id=current_user.id
    )
    
    db.add(trend)
    db.commit()
    db.refresh(trend)
    return trend

@app.post("/predictions")
def create_prediction(
    prediction_data: PredictionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if user has sufficient balance
    if current_user.balance < prediction_data.stake_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient balance"
        )
    
    # Check if trend exists and is active
    trend = db.query(Trend).filter(
        Trend.id == prediction_data.trend_id,
        Trend.is_active == True,
        Trend.is_resolved == False
    ).first()
    
    if not trend:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trend not found or inactive"
        )
    
    # Calculate potential payout (simple 2:1 for now)
    potential_payout = prediction_data.stake_amount * 2
    
    prediction = Prediction(
        user_id=current_user.id,
        trend_id=prediction_data.trend_id,
        prediction=prediction_data.prediction,
        confidence=prediction_data.confidence,
        stake_amount=prediction_data.stake_amount,
        potential_payout=potential_payout
    )
    
    # Deduct stake from user balance
    current_user.balance -= Decimal(str(prediction_data.stake_amount))
    
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    
    return {"message": "Prediction created successfully", "prediction": prediction}

@app.get("/predictions/my")
def get_my_predictions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    predictions = db.query(Prediction).filter(
        Prediction.user_id == current_user.id
    ).order_by(Prediction.created_at.desc()).all()
    
    return predictions

@app.get("/leaderboard")
def get_leaderboard(db: Session = Depends(get_db)):
    users = db.query(User).filter(
        User.total_predictions > 0
    ).order_by(
        (User.correct_predictions / User.total_predictions).desc(),
        User.total_predictions.desc()
    ).limit(10).all()
    
    leaderboard = []
    for i, user in enumerate(users):
        accuracy = (user.correct_predictions / user.total_predictions * 100) if user.total_predictions > 0 else 0
        leaderboard.append({
            "rank": i + 1,
            "username": user.username,
            "accuracy_rate": round(accuracy, 1),
            "total_predictions": user.total_predictions,
            "correct_predictions": user.correct_predictions
        })
    
    return leaderboard

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "trendbet-api", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)