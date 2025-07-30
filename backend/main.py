from fastapi import FastAPI, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional
import asyncio
import logging
from typing import List
import json
import numpy as np

from database import SessionLocal, engine
from models import (
    Base, User, AttentionTarget, Portfolio, Trade, Tournament, 
    TournamentEntry, AttentionHistory, TargetType, TournamentDuration
)
from auth import (
    create_user, authenticate_user, create_access_token, 
    decode_access_token, get_current_user
)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="TrendBet Attention Trading API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
logger = logging.getLogger(__name__)

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

class TradeRequest(BaseModel):
    target_id: int
    trade_type: str  # 'buy' or 'sell'
    shares: float

class SearchRequest(BaseModel):
    query: str
    target_type: str = "politician"

class TournamentEntryRequest(BaseModel):
    tournament_id: int

# Google Trends integration
from google_trends_service import GoogleTrendsService

# Auth endpoints
@app.post("/auth/register")
def register(user_data: UserRegister, db: Session = Depends(get_db)):
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
            "created_at": user.created_at
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
    
    return {
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "balance": float(user.balance),
            "created_at": user.created_at
        }
    }

@app.get("/auth/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "balance": float(current_user.balance),
        "created_at": current_user.created_at
    }

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.target_subscribers: Dict[int, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, target_id: int = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        if target_id:
            if target_id not in self.target_subscribers:
                self.target_subscribers[target_id] = []
            self.target_subscribers[target_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, target_id: int = None):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        if target_id and target_id in self.target_subscribers:
            if websocket in self.target_subscribers[target_id]:
                self.target_subscribers[target_id].remove(websocket)
    
    async def send_target_update(self, target_id: int, data: dict):
        """Send updates to all clients subscribed to a specific target"""
        if target_id in self.target_subscribers:
            disconnected = []
            for connection in self.target_subscribers[target_id]:
                try:
                    await connection.send_text(json.dumps(data))
                except:
                    disconnected.append(connection)
            
            # Clean up disconnected clients
            for conn in disconnected:
                self.target_subscribers[target_id].remove(conn)

manager = ConnectionManager()

# WebSocket endpoint for real-time chart updates  
@app.websocket("/ws/targets/{target_id}")
async def websocket_endpoint(websocket: WebSocket, target_id: int):
    await manager.connect(websocket, target_id)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, target_id)

# Attention targets endpoints
# Update targets endpoint to remove share price references
@app.get("/targets")
def get_targets(
    target_type: Optional[str] = None,
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db)
):
    """Get all attention targets (attention scores only)"""
    query = db.query(AttentionTarget).filter(AttentionTarget.is_active == True)
    
    if target_type:
        try:
            target_type_enum = TargetType(target_type)
            query = query.filter(AttentionTarget.type == target_type_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid target type")
    
    targets = query.order_by(AttentionTarget.current_attention_score.desc()).limit(limit).all()
    
    result = []
    for target in targets:
        result.append({
            "id": target.id,
            "name": target.name,
            "type": target.type.value,
            "description": target.description,
            "attention_score": float(target.current_attention_score),
            "search_term": target.search_term,
            "last_updated": target.last_updated
        })
    
    return result

@app.get("/targets/{target_id}")
def get_target(target_id: int, db: Session = Depends(get_db)):
    """Get specific target details (attention score only)"""
    target = db.query(AttentionTarget).filter(AttentionTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    return {
        "id": target.id,
        "name": target.name,
        "type": target.type.value,
        "description": target.description,
        "attention_score": float(target.current_attention_score),
        "search_term": target.search_term,
        "last_updated": target.last_updated
    }

@app.get("/targets/{target_id}/chart")
def get_target_chart(target_id: int, days: int = Query(30, le=1825), db: Session = Depends(get_db)):
    """Get historical attention data for charts (real Google Trends data only)"""
    target = db.query(AttentionTarget).filter(AttentionTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    # Get historical data
    start_date = datetime.utcnow() - timedelta(days=days)
    history = db.query(AttentionHistory).filter(
        AttentionHistory.target_id == target_id,
        AttentionHistory.timestamp >= start_date
    ).order_by(AttentionHistory.timestamp.asc()).all()
    
    chart_data = {
        "target": {
            "id": target.id,
            "name": target.name,
            "type": target.type.value,
            "search_term": target.search_term
        },
        "timeframe": {
            "days": days,
            "start_date": start_date.isoformat(),
            "end_date": datetime.utcnow().isoformat(),
            "data_source": "google_trends_api"
        },
        "data": []
    }
    
    # Add real attention score data
    for entry in history:
        chart_data["data"].append({
            "timestamp": entry.timestamp.isoformat(),
            "attention_score": float(entry.attention_score),
            "data_source": entry.data_source or "google_trends_api"
        })
    
    # Add summary statistics
    if chart_data["data"]:
        scores = [point["attention_score"] for point in chart_data["data"]]
        chart_data["summary"] = {
            "average": round(sum(scores) / len(scores), 2),
            "max": max(scores),
            "min": min(scores),
            "latest": scores[-1] if scores else 0,
            "change_percent": round(((scores[-1] - scores[0]) / scores[0] * 100), 2) if len(scores) > 1 and scores[0] != 0 else 0,
            "volatility": round(np.std(scores), 2) if len(scores) > 1 else 0,
            "data_points": len(scores)
        }
        
        # Add baseline comparison if available
        if target.baseline_average:
            current_vs_baseline = ((scores[-1] - float(target.baseline_average)) / float(target.baseline_average)) * 100
            chart_data["summary"]["vs_baseline_percent"] = round(current_vs_baseline, 2)
    
    return chart_data

# Update search endpoint to use 5-year baseline
@app.post("/search")
async def search_trends(search_data: SearchRequest, db: Session = Depends(get_db)):
    """Search for any term and get real 5-year Google Trends data"""
    
    try:
        logger.info(f"🔍 Searching for: {search_data.query}")
        
        # Check if target already exists
        existing_target = db.query(AttentionTarget).filter(
            AttentionTarget.search_term.ilike(f"%{search_data.query}%")
        ).first()
        
        if existing_target:
            logger.info(f"📊 Target exists: {existing_target.name}")
            
            # Get fresh data from Google Trends
            try:
                async with GoogleTrendsService() as service:
                    trends_data = await service.get_google_trends_data(existing_target.search_term, 'now 7-d')
                    attention_score = trends_data.get("attention_score", 0.0)
                
                # Update existing target
                existing_target.current_attention_score = Decimal(str(attention_score))
                existing_target.last_updated = datetime.utcnow()
                
                # Save history entry
                history = AttentionHistory(
                    target_id=existing_target.id,
                    attention_score=Decimal(str(attention_score)),
                    data_source='google_trends_api',
                    timeframe_used='7_day'
                )
                db.add(history)
                db.commit()
                
                # Send real-time update to connected clients
                await manager.send_target_update(existing_target.id, {
                    "type": "attention_update",
                    "target_id": existing_target.id,
                    "attention_score": attention_score,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                target_id = existing_target.id
                
            except Exception as e:
                logger.error(f"Failed to update existing target: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to get current trends data: {str(e)}")
        
        else:
            # Create new target with real 5-year data
            logger.info(f"🆕 Creating new target for: {search_data.query}")
            
            try:
                async with GoogleTrendsService() as service:
                    # Get current attention score first
                    trends_data = await service.get_google_trends_data(search_data.query, 'now 7-d')
                    attention_score = trends_data.get("attention_score", 0.0)
            except Exception as e:
                logger.error(f"Failed to get initial trends data: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to fetch Google Trends data: {str(e)}")
            
            # Create target type
            try:
                target_type_enum = TargetType(search_data.target_type)
            except ValueError:
                target_type_enum = TargetType.POLITICIAN
            
            # Create new target
            new_target = AttentionTarget(
                name=search_data.query.title(),
                type=target_type_enum,
                search_term=search_data.query,
                current_attention_score=Decimal(str(attention_score)),
                description=f"Real-time attention tracking for {search_data.query}",
                baseline_period="5_year"
            )
            
            db.add(new_target)
            db.commit()
            db.refresh(new_target)
            
            # Initial history entry
            history = AttentionHistory(
                target_id=new_target.id,
                attention_score=Decimal(str(attention_score)),
                data_source='google_trends_api',
                timeframe_used='7_day'
            )
            db.add(history)
            db.commit()
            
            # Seed 5-year historical data in background (real Google Trends data)
            async def seed_background():
                try:
                    async with GoogleTrendsService() as service:
                        await service.seed_historical_data(new_target, days=1825)
                    logger.info(f"✅ Seeded 5-year historical data for {new_target.name}")
                except Exception as e:
                    logger.error(f"❌ Failed to seed historical data: {e}")
            
            asyncio.create_task(seed_background())
            
            target_id = new_target.id
        
        return {
            "target_id": target_id,
            "query": search_data.query,
            "current_attention_score": float(attention_score),
            "baseline": "5_year_real_data",
            "data_source": "google_trends_api",
            "update_interval": "3_minutes",
            "message": "Target data updated with real Google Trends data"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Search failed for '{search_data.query}': {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

# Add new endpoint for attention score analytics
@app.get("/targets/{target_id}/analytics")
def get_target_analytics(target_id: int, db: Session = Depends(get_db)):
    """Get detailed analytics for attention trends"""
    target = db.query(AttentionTarget).filter(AttentionTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    # Get different timeframe analyses
    timeframes = {
        "week": 7,
        "month": 30,
        "quarter": 90,
        "year": 365,
        "five_year": 1825
    }
    
    analytics = {
        "target": {
            "id": target.id,
            "name": target.name,
            "type": target.type.value
        },
        "timeframe_analysis": {}
    }
    
    for period, days in timeframes.items():
        start_date = datetime.utcnow() - timedelta(days=days)
        history = db.query(AttentionHistory).filter(
            AttentionHistory.target_id == target_id,
            AttentionHistory.timestamp >= start_date
        ).all()
        
        if history:
            scores = [float(h.attention_score) for h in history]
            analytics["timeframe_analysis"][period] = {
                "average": round(sum(scores) / len(scores), 2),
                "max": max(scores),
                "min": min(scores),
                "volatility": round(np.std(scores), 2) if len(scores) > 1 else 0,
                "trend": "increasing" if scores[-1] > scores[0] else "decreasing" if scores[-1] < scores[0] else "stable",
                "data_points": len(scores)
            }
    
    return analytics

# Trading endpoints
@app.post("/trade")
def execute_trade(
    trade_data: TradeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Execute a buy or sell trade"""
    target = db.query(AttentionTarget).filter(AttentionTarget.id == trade_data.target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    if trade_data.shares <= 0:
        raise HTTPException(status_code=400, detail="Shares must be positive")
    
    current_price = float(target.current_share_price)
    total_cost = trade_data.shares * current_price
    
    if trade_data.trade_type == "buy":
        # Check if user has enough balance
        if current_user.balance < Decimal(str(total_cost)):
            raise HTTPException(status_code=400, detail="Insufficient balance")
        
        # Deduct from balance
        current_user.balance -= Decimal(str(total_cost))
        
        # Update or create portfolio entry
        portfolio = db.query(Portfolio).filter(
            Portfolio.user_id == current_user.id,
            Portfolio.target_id == trade_data.target_id
        ).first()
        
        if portfolio:
            # Update existing position
            total_shares = float(portfolio.shares_owned) + trade_data.shares
            total_cost_basis = (float(portfolio.shares_owned) * float(portfolio.average_price)) + total_cost
            portfolio.shares_owned = Decimal(str(total_shares))
            portfolio.average_price = Decimal(str(total_cost_basis / total_shares)) if total_shares > 0 else Decimal(str(current_price))
        else:
            # Create new position
            portfolio = Portfolio(
                user_id=current_user.id,
                target_id=trade_data.target_id,
                shares_owned=Decimal(str(trade_data.shares)),
                average_price=Decimal(str(current_price))
            )
            db.add(portfolio)
    
    elif trade_data.trade_type == "sell":
        # Check if user has enough shares
        portfolio = db.query(Portfolio).filter(
            Portfolio.user_id == current_user.id,
            Portfolio.target_id == trade_data.target_id
        ).first()
        
        if not portfolio or float(portfolio.shares_owned) < trade_data.shares:
            raise HTTPException(status_code=400, detail="Insufficient shares")
        
        # Update portfolio
        portfolio.shares_owned -= Decimal(str(trade_data.shares))
        
        # Add to balance
        current_user.balance += Decimal(str(total_cost))
    else:
        raise HTTPException(status_code=400, detail="Invalid trade type")
    
    # Record the trade
    trade = Trade(
        user_id=current_user.id,
        target_id=trade_data.target_id,
        trade_type=trade_data.trade_type,
        shares=Decimal(str(trade_data.shares)),
        price_per_share=Decimal(str(current_price)),
        total_amount=Decimal(str(total_cost))
    )
    db.add(trade)
    
    db.commit()
    
    return {
        "message": "Trade executed successfully",
        "trade_type": trade_data.trade_type,
        "shares": trade_data.shares,
        "price_per_share": current_price,
        "total_amount": total_cost,
        "new_balance": float(current_user.balance)
    }

@app.get("/portfolio")
def get_portfolio(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user's portfolio with current P&L"""
    portfolios = db.query(Portfolio).filter(
        Portfolio.user_id == current_user.id,
        Portfolio.shares_owned > 0
    ).all()
    
    total_value = 0
    total_cost = 0
    positions = []
    
    for portfolio in portfolios:
        target = portfolio.target
        current_price = float(target.current_share_price)
        shares_owned = float(portfolio.shares_owned)
        avg_price = float(portfolio.average_price)
        
        position_value = shares_owned * current_price
        position_cost = shares_owned * avg_price
        pnl = position_value - position_cost
        pnl_percent = (pnl / position_cost * 100) if position_cost > 0 else 0
        
        positions.append({
            "target_id": target.id,
            "target_name": target.name,
            "target_type": target.type.value,
            "shares_owned": shares_owned,
            "average_price": avg_price,
            "current_price": current_price,
            "position_value": position_value,
            "position_cost": position_cost,
            "pnl": pnl,
            "pnl_percent": pnl_percent
        })
        
        total_value += position_value
        total_cost += position_cost
    
    total_pnl = total_value - total_cost
    total_pnl_percent = (total_pnl / total_cost * 100) if total_cost > 0 else 0
    
    return {
        "cash_balance": float(current_user.balance),
        "portfolio_value": total_value,
        "total_value": float(current_user.balance) + total_value,
        "total_pnl": total_pnl,
        "total_pnl_percent": total_pnl_percent,
        "positions": positions
    }

@app.get("/trades/my")
def get_my_trades(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user's trade history"""
    trades = db.query(Trade).filter(
        Trade.user_id == current_user.id
    ).order_by(Trade.timestamp.desc()).limit(50).all()
    
    result = []
    for trade in trades:
        target = trade.target
        result.append({
            "id": trade.id,
            "target_id": target.id,
            "target_name": target.name,
            "target_type": target.type.value,
            "trade_type": trade.trade_type,
            "shares": float(trade.shares),
            "price_per_share": float(trade.price_per_share),
            "total_amount": float(trade.total_amount),
            "timestamp": trade.timestamp
        })
    
    return result

# Tournament endpoints
@app.get("/tournaments")
def get_tournaments(db: Session = Depends(get_db)):
    """Get active tournaments"""
    tournaments = db.query(Tournament).filter(
        Tournament.is_active == True,
        Tournament.end_date > datetime.utcnow()
    ).order_by(Tournament.start_date.asc()).all()
    
    result = []
    for tournament in tournaments:
        entry_count = db.query(TournamentEntry).filter(TournamentEntry.tournament_id == tournament.id).count()
        
        result.append({
            "id": tournament.id,
            "name": tournament.name,
            "target_type": tournament.target_type.value,
            "duration": tournament.duration.value,
            "entry_fee": float(tournament.entry_fee),
            "prize_pool": float(tournament.prize_pool),
            "start_date": tournament.start_date,
            "end_date": tournament.end_date,
            "participants": entry_count
        })
    
    return result

@app.post("/tournaments/join")
def join_tournament(
    entry_data: TournamentEntryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Join a tournament"""
    tournament = db.query(Tournament).filter(Tournament.id == entry_data.tournament_id).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    # Check if already joined
    existing_entry = db.query(TournamentEntry).filter(
        TournamentEntry.tournament_id == entry_data.tournament_id,
        TournamentEntry.user_id == current_user.id
    ).first()
    
    if existing_entry:
        raise HTTPException(status_code=400, detail="Already joined this tournament")
    
    # Check balance
    if current_user.balance < tournament.entry_fee:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Deduct entry fee (10% goes to platform)
    platform_fee = tournament.entry_fee * Decimal('0.10')
    prize_contribution = tournament.entry_fee - platform_fee
    
    current_user.balance -= tournament.entry_fee
    tournament.prize_pool += prize_contribution
    
    # Create tournament entry
    entry = TournamentEntry(
        tournament_id=entry_data.tournament_id,
        user_id=current_user.id,
        entry_fee_paid=tournament.entry_fee
    )
    db.add(entry)
    
    db.commit()
    
    return {"message": "Successfully joined tournament", "entry_fee": float(tournament.entry_fee)}

@app.get("/leaderboard")
def get_leaderboard(db: Session = Depends(get_db)):
    """Get platform leaderboard based on total portfolio value"""
    # This is a simplified leaderboard - could be enhanced with different metrics
    users = db.query(User).filter(User.is_active == True).all()
    
    leaderboard = []
    for user in users:
        # Calculate total portfolio value
        portfolios = db.query(Portfolio).filter(
            Portfolio.user_id == user.id,
            Portfolio.shares_owned > 0
        ).all()
        
        portfolio_value = 0
        for portfolio in portfolios:
            target = portfolio.target
            portfolio_value += float(portfolio.shares_owned) * float(target.current_share_price)
        
        total_value = float(user.balance) + portfolio_value
        
        leaderboard.append({
            "username": user.username,
            "total_value": total_value,
            "cash_balance": float(user.balance),
            "portfolio_value": portfolio_value
        })
    
    # Sort by total value
    leaderboard.sort(key=lambda x: x["total_value"], reverse=True)
    
    # Add ranks
    for i, entry in enumerate(leaderboard[:10]):  # Top 10
        entry["rank"] = i + 1
    
    return leaderboard[:10]

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "trendbet-attention-trading", "version": "2.0.0"}

# Background tasks
async def start_background_tasks():
    """Start background data update tasks"""
    from google_trends_service import run_data_updates
    from tournament_management import tournament_management_task
    
    # Start both tasks concurrently
    await asyncio.gather(
        run_data_updates(),
        tournament_management_task()
    )

@app.get("/trends")
def get_trends_legacy(limit: int = Query(50, le=100), db: Session = Depends(get_db)):
    """Legacy endpoint - redirects to /targets for frontend compatibility"""
    return get_targets(target_type=None, limit=limit, db=db)

@app.get("/trends/categories") 
def get_trend_categories():
    """Get available target categories for frontend dropdowns"""
    categories = []
    for target_type in TargetType:
        icon_map = {
            "politician": "🏛️",
            "billionaire": "💰", 
            "country": "🌍",
            "stock": "📈"
        }
        
        categories.append({
            "id": target_type.value,
            "name": target_type.value.title(),
            "icon": icon_map.get(target_type.value, "📊"),
            "description": f"{target_type.value.title()} attention tracking"
        })
    
    return categories

# Admin endpoints for managing real data
@app.get("/admin/cleanup-unused")
async def cleanup_unused_targets(current_user: User = Depends(get_current_user)):
    """Clean up targets that no one is holding positions in"""
    try:
        async with GoogleTrendsService() as service:
            await service.cleanup_unused_targets()
        return {"message": "Cleanup completed successfully", "status": "success"}
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

@app.get("/admin/force-update/{target_id}")
async def force_update_target(target_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Force update a specific target with fresh Google Trends data"""
    target = db.query(AttentionTarget).filter(AttentionTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    try:
        async with GoogleTrendsService() as service:
            success = await service.update_target_data(target, db)
        
        if success:
            # Send real-time update to connected clients
            await manager.send_target_update(target_id, {
                "type": "forced_update",
                "target_id": target_id,
                "attention_score": float(target.current_attention_score),
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return {
                "message": f"Target {target.name} updated successfully",
                "attention_score": float(target.current_attention_score),
                "status": "success"
            }
        else:
            raise HTTPException(status_code=500, detail="Update failed")
            
    except Exception as e:
        logger.error(f"Force update failed: {e}")
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")

# Background task startup with real data updates
async def start_background_tasks():
    """Start background tasks for real-time data updates"""
    try:
        from google_trends_service import run_data_updates
        # Start the real-time background data update task (3-minute intervals)
        asyncio.create_task(run_data_updates())
        logger.info("✅ Real-time background data updates started (3-minute intervals)")
    except ImportError as e:
        logger.error(f"❌ Failed to start background tasks: {e}")
        logger.info("📊 Real-time data updates are disabled")

@app.on_event("startup")
async def startup_event():
    """Initialize the application with real-time capabilities"""
    logger.info("🚀 TrendBet API starting up with real Google Trends data...")
    
    # Start background tasks for real-time updates
    await start_background_tasks()
    
    logger.info("✅ TrendBet API ready with real-time data updates!")

# Service status endpoint
@app.get("/admin/service-status")
async def get_service_status():
    """Get Google Trends service status"""
    try:
        from google_trends_service import get_service_status
        return get_service_status()
    except Exception as e:
        return {
            "error": str(e), 
            "status": "error",
            "timestamp": datetime.utcnow().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)