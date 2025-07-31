from fastapi import FastAPI, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict
import asyncio
import logging
import json
from seed_data import store_timeframe_data_with_real_timestamps

from database import SessionLocal, engine
from models import (
    User, AttentionTarget, Portfolio, Trade, Tournament, 
    TournamentEntry, AttentionHistory, TargetType, TournamentDuration
)
from auth import (
    create_user, authenticate_user, create_access_token, 
    decode_access_token, get_current_user
)

app = FastAPI(title="TrendBet Attention Trading API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Setup logging
logging.basicConfig(level=logging.INFO)
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

# WebSocket Connection Manager
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
            detail="Invalid username or password"
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
        "email": current_user.email,
        "balance": float(current_user.balance),
        "created_at": current_user.created_at
    }

# Search and Target Management
# backend/main.py - Conservative search endpoint and seeding to prevent 429 errors

@app.post("/search")
async def search_attention_target(
    request: SearchRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Search for attention targets and create them with conservative seeding"""
    query = request.query.strip()
    target_type = request.target_type
    
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    logger.info(f"🔍 Search request: '{query}' (type: {target_type})")
    
    # Check if target already exists
    existing_target = db.query(AttentionTarget).filter(
        AttentionTarget.search_term.ilike(f"%{query}%")
    ).first()
    
    if existing_target:
        logger.info(f"✅ Found existing target: {existing_target.name}")
        return {
            "id": existing_target.id,
            "name": existing_target.name,
            "type": existing_target.type.value,
            "search_term": existing_target.search_term,
            "current_attention_score": float(existing_target.current_attention_score),
            "created": False,
            "message": f"Found existing target: {existing_target.name}"
        }
    
    try:
        # Create new target with Google Trends data
        async with GoogleTrendsService(websocket_manager=manager) as service:
            logger.info(f"🔍 Creating new target for: {query}")
            
            # FIX: Only get current score initially - don't seed all timeframes immediately
            current_data = await service.get_google_trends_data(query, timeframe="now 1-d")
            
            if not current_data.get('success'):
                error_msg = current_data.get('error', 'Unknown error')
                if 'Rate limited' in error_msg or 'Circuit breaker' in error_msg:
                    raise HTTPException(
                        status_code=429,
                        detail=f"Google Trends is rate limiting requests. Please try again in a few minutes."
                    )
                else:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"No Google Trends data found for '{query}'. Try a more popular search term."
                    )
            
            current_score = current_data["attention_score"]
            logger.info(f"✅ Got trend score for {query}: {current_score}")
            
            # Map target type
            type_mapping = {
                "politician": TargetType.POLITICIAN,
                "billionaire": TargetType.BILLIONAIRE,
                "stock": TargetType.STOCK,
                "country": TargetType.COUNTRY,
                "stock": TargetType.STOCK
            }
            
            # Create the target
            target = AttentionTarget(
                name=query.title(),
                type=type_mapping.get(target_type, TargetType.POLITICIAN),
                search_term=query,
                current_attention_score=Decimal(str(current_score)),
                description=f"Google Trends attention score for {query}"
            )
            
            db.add(target)
            db.commit()
            db.refresh(target)
            
            logger.info(f"✅ Created target {query} with current score: {current_score}")
            
            # FIX: Conservative seeding approach - spread out over time
            # Start with immediate seeding of just 1-day data (already have it)
            if current_data.get('timeline') and current_data.get('timeline_timestamps'):
                try:
                    from seed_data import store_timeframe_data_with_real_timestamps
                    await store_timeframe_data_with_real_timestamps(
                        target, current_data, "1d", "now 1-d", db
                    )
                    logger.info("✅ Stored initial 1-day data immediately")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to store initial 1d data: {e}")
            
            # FIX: Gradual background seeding - spread over 30+ minutes
            background_tasks.add_task(
                gradual_historical_seeding, 
                target.id, 
                query,
                start_delay_minutes=2  # Wait 2 minutes before starting
            )
            
            return {
                "id": target.id,
                "name": target.name,
                "type": target.type.value,
                "search_term": target.search_term,
                "current_attention_score": float(target.current_attention_score),
                "created": True,
                "message": f"Created {target.name}! More historical data will load gradually over the next 30 minutes to avoid rate limits."
            }
            
    except HTTPException:
        # Re-raise HTTP exceptions (429, 404)
        raise
    except Exception as e:
        logger.error(f"❌ Search failed for '{query}': {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


async def gradual_historical_seeding(target_id: int, search_term: str, start_delay_minutes: int = 2):
    """Gradual background seeding to avoid rate limits - spread over 30+ minutes"""
    
    # Initial delay before starting
    logger.info(f"📊 Gradual seeding for target {target_id} starting in {start_delay_minutes} minutes...")
    await asyncio.sleep(start_delay_minutes * 60)
    
    db = SessionLocal()
    try:
        target = db.query(AttentionTarget).filter(AttentionTarget.id == target_id).first()
        if not target:
            logger.error(f"❌ Target {target_id} not found for gradual seeding")
            return
            
        logger.info(f"📊 Starting gradual historical seeding for {target.name}")
        
        # FIX: Conservative timeframe seeding with long delays (no random)
        timeframes_with_delays = [
            ("now 7-d", "7d", 5),      # Wait 5 minutes, then seed 7-day
            ("today 1-m", "1m", 8),    # Wait 8 more minutes, then seed 1-month  
            ("today 3-m", "3m", 10),   # Wait 10 more minutes, then seed 3-month
            ("today 12-m", "1y", 12),  # Wait 12 more minutes, then seed 1-year
            ("today 5-y", "5y", 15),   # Wait 15 more minutes, then seed 5-year
        ]
        
        seeded_count = 1  # Already have 1d data
        
        async with GoogleTrendsService(websocket_manager=manager) as service:
            for timeframe_code, timeframe_name, delay_minutes in timeframes_with_delays:
                try:
                    # Wait before each request
                    logger.info(f"⏱️ Waiting {delay_minutes} minutes before seeding {timeframe_name} data for {target.name}")
                    await asyncio.sleep(delay_minutes * 60)
                    
                    logger.info(f"📅 Seeding {timeframe_name} data for {target.name}...")
                    data = await service.get_google_trends_data(
                        search_term, 
                        timeframe=timeframe_code,
                    )
                    
                    if data and data.get('success') and data.get('timeline'):
                        from seed_data import store_timeframe_data_with_real_timestamps
                        await store_timeframe_data_with_real_timestamps(
                            target, data, timeframe_name, timeframe_code, db
                        )
                        seeded_count += 1
                        logger.info(f"✅ Seeded {timeframe_name} data for {target.name}")
                    else:
                        error_msg = data.get('error', 'No timeline data') if data else 'Request failed'
                        logger.warning(f"⚠️ No {timeframe_name} data for {target.name}: {error_msg}")
                        
                        # If we hit rate limits, increase delays for remaining timeframes
                        if 'Rate limited' in error_msg or 'Circuit breaker' in error_msg:
                            logger.warning(f"🚫 Rate limited during {timeframe_name} seeding. Extending delays for remaining timeframes.")
                            # Double remaining delays
                            remaining_frames = timeframes_with_delays[timeframes_with_delays.index((timeframe_code, timeframe_name, delay_minutes)) + 1:]
                            for i, (tc, tn, dm) in enumerate(remaining_frames):
                                timeframes_with_delays[timeframes_with_delays.index((tc, tn, dm))] = (tc, tn, dm * 2)
                    
                except Exception as e:
                    logger.error(f"❌ Failed to seed {timeframe_name} data for {target.name}: {e}")
                    # Continue with next timeframe after brief pause
                    await asyncio.sleep(30)
            
            total_time = sum([delay for _, _, delay in timeframes_with_delays])
            logger.info(f"✅ Gradual seeding complete for {target.name}: {seeded_count}/6 timeframes over {total_time} minutes")
            
            # Update target to indicate seeding is complete
            target.last_updated = datetime.utcnow()
            db.commit()
            
    except Exception as e:
        logger.error(f"❌ Gradual seeding failed for target {target_id}: {e}")
        db.rollback()
    finally:
        db.close()

async def seed_historical_data_for_target(target_id: int, search_term: str):
    """Background task to seed historical data for a newly created target"""
    db = SessionLocal()
    try:
        target = db.query(AttentionTarget).filter(AttentionTarget.id == target_id).first()
        if not target:
            logger.error(f"❌ Target {target_id} not found for historical seeding")
            return
            
        logger.info(f"📊 Starting historical data seeding for {target.name}")
        
        async with GoogleTrendsService(websocket_manager=manager) as service:
            # Standard Google Trends timeframes
            timeframes = [
                ("now 1-d", "1d"),
                ("now 7-d", "7d"), 
                ("today 1-m", "1m"),
                ("today 3-m", "3m"),
                ("today 12-m", "1y"),
                ("today 5-y", "5y")
            ]
            
            seeded_count = 0
            
            for timeframe_code, timeframe_name in timeframes:
                try:
                    logger.info(f"📅 Seeding {timeframe_name} data for {target.name}...")
                    data = await service.get_google_trends_data(search_term, timeframe=timeframe_code)
                    
                    if data and data.get('success') and data.get('timeline'):
                        await store_timeframe_data_with_real_timestamps(
                            target, data, timeframe_name, timeframe_code, db
                        )
                        seeded_count += 1
                        logger.info(f"✅ Seeded {timeframe_name} data")
                    else:
                        logger.warning(f"⚠️ No {timeframe_name} data available for {target.name}")
                    
                    # Rate limit between requests
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"❌ Failed to seed {timeframe_name} data for {target.name}: {e}")
            
            logger.info(f"✅ Historical seeding complete for {target.name}: {seeded_count}/6 timeframes")
            
            # Update target to indicate seeding is complete
            target.last_updated = datetime.utcnow()
            db.commit()
            
    except Exception as e:
        logger.error(f"❌ Historical seeding failed for target {target_id}: {e}")
        db.rollback()
    finally:
        db.close()

@app.get("/targets")
def get_targets(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """Get all available attention targets"""
    targets = db.query(AttentionTarget).filter(
        AttentionTarget.is_active == True
    ).offset(skip).limit(limit).all()
    
    return [
        {
            "id": target.id,
            "name": target.name,
            "type": target.type.value,
            "search_term": target.search_term,
            "current_attention_score": float(target.current_attention_score),
            "last_updated": target.last_updated
        }
        for target in targets
    ]

@app.get("/targets/{target_id}")
def get_target_detail(target_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific target"""
    target = db.query(AttentionTarget).filter(AttentionTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    return {
        "id": target.id,
        "name": target.name,
        "type": target.type.value,
        "search_term": target.search_term,
        "description": target.description,
        "current_attention_score": float(target.current_attention_score),
        "last_updated": target.last_updated,
        "created_at": target.created_at
    }

@app.get("/targets/{target_id}/chart")
def get_target_chart_data(target_id: int, days: int = 30, db: Session = Depends(get_db)):
    """Get chart data"""
    
    target = db.query(AttentionTarget).filter(AttentionTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    # Simple timeframe mapping to data sources
    if days <= 1:
        data_source = "google_trends_1d"
    elif days <= 7:
        data_source = "google_trends_7d"
    elif days <= 30:
        data_source = "google_trends_1m"
    elif days <= 90:
        data_source = "google_trends_3m"
    elif days <= 365:
        data_source = "google_trends_1y"
    else:
        data_source = "google_trends_5y"
    
    logger.info(f"📊 Chart request: {days} days -> trying {data_source}")
    
    # Try primary data source first
    base_data = db.query(AttentionHistory).filter(
        AttentionHistory.target_id == target_id,
        AttentionHistory.data_source == data_source,
        AttentionHistory.timestamp >= start_time
    ).order_by(AttentionHistory.timestamp.asc()).all()
    
    all_data = list(base_data)
    actual_data_source = data_source
    
    # For 1-day charts, always try to add real-time data
    if days <= 1:
        logger.info("📊 Adding real-time data for 1-day chart")
        realtime_data = db.query(AttentionHistory).filter(
            AttentionHistory.target_id == target_id,
            AttentionHistory.data_source == "google_trends_realtime",
            AttentionHistory.timestamp >= start_time
        ).order_by(AttentionHistory.timestamp.asc()).all()
        
        if realtime_data:
            # Combine and sort
            all_data = list(all_data) + list(realtime_data)
            all_data.sort(key=lambda x: x.timestamp)
            logger.info(f"📊 Combined data: {len(base_data)} base + {len(realtime_data)} realtime = {len(all_data)} total")
    
    # FIX: If still no data, create a synthetic data point from current score
    if not all_data:
        logger.warning(f"No historical data found for target {target_id}. Creating synthetic data point.")
        
        # Create a single data point with current score
        synthetic_data_point = {
            "timestamp": datetime.utcnow().isoformat(),
            "attention_score": float(target.current_attention_score),
            "data_source": "current_score_synthetic"
        }
        
        return {
            "target": {
                "id": target.id,
                "name": target.name,
                "current_attention_score": float(target.current_attention_score)
            },
            "data": [synthetic_data_point],
            "data_count": 1,
            "data_source": "synthetic",
            "date_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "days": days
            },
            "sampling_info": {
                "granularity": "current_only",
                "total_points_available": 1,
                "is_synthetic": True
            },
            "message": "Historical data is being loaded in the background. Chart will update automatically when ready."
        }
    
    # Convert to response format
    data_points = [
        {
            "timestamp": point.timestamp.isoformat(),
            "attention_score": float(point.attention_score),
            "data_source": point.data_source
        }
        for point in all_data
    ]
    
    # Simple sampling if too many points
    original_count = len(data_points)
    if len(data_points) > 200:
        step = len(data_points) // 150
        data_points = [data_points[i] for i in range(0, len(data_points), step)]
        if data_points and all_data and data_points[-1]["timestamp"] != all_data[-1].timestamp.isoformat():
            data_points.append({
                "timestamp": all_data[-1].timestamp.isoformat(),
                "attention_score": float(all_data[-1].attention_score),
                "data_source": all_data[-1].data_source
            })
    
    # Determine granularity based on actual data source used
    granularity_map = {
        "google_trends_realtime": "real-time updates",
        "google_trends_1d": "hourly data",
        "google_trends_7d": "daily data", 
        "google_trends_1m": "daily data",
        "google_trends_3m": "weekly data",
        "google_trends_1y": "monthly data",
        "google_trends_5y": "monthly data"
    }
    
    logger.info(f"📊 Returning {len(data_points)} points for {target.name} ({days}d) using {actual_data_source}")
    
    return {
        "target": {
            "id": target.id,
            "name": target.name,
            "current_attention_score": float(target.current_attention_score)
        },
        "data": data_points,
        "data_count": len(data_points),
        "data_source": actual_data_source,
        "date_range": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "days": days
        },
        "sampling_info": {
            "granularity": granularity_map.get(actual_data_source, "optimized sampling"),
            "total_points_available": original_count,
            "sampled_points": len(data_points),
            "is_synthetic": False
        }
    }

# Trading endpoints
@app.post("/trade")
def execute_trade(trade: TradeRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Execute an attention trade"""
    target = db.query(AttentionTarget).filter(AttentionTarget.id == trade.target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    # For attention trading, we use a simplified model
    trade_amount = Decimal(str(abs(trade.shares) * 10))  # Simple pricing model
    
    if trade.trade_type == "buy":
        if current_user.balance < trade_amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        
        current_user.balance -= trade_amount
        
        # Update or create portfolio position
        portfolio = db.query(Portfolio).filter(
            Portfolio.user_id == current_user.id,
            Portfolio.target_id == target.id
        ).first()
        
        if portfolio:
            # Update existing position
            total_stakes = portfolio.attention_stakes + trade_amount
            portfolio.average_entry_score = (
                (portfolio.attention_stakes * portfolio.average_entry_score + 
                 trade_amount * target.current_attention_score) / total_stakes
            )
            portfolio.attention_stakes = total_stakes
        else:
            # Create new position
            portfolio = Portfolio(
                user_id=current_user.id,
                target_id=target.id,
                attention_stakes=trade_amount,
                average_entry_score=target.current_attention_score
            )
            db.add(portfolio)
    
    elif trade.trade_type == "sell":
        portfolio = db.query(Portfolio).filter(
            Portfolio.user_id == current_user.id,
            Portfolio.target_id == target.id
        ).first()
        
        if not portfolio or portfolio.attention_stakes < trade_amount:
            raise HTTPException(status_code=400, detail="Insufficient position")
        
        # Calculate P&L
        pnl = trade_amount * (target.current_attention_score - portfolio.average_entry_score) / 100
        current_user.balance += trade_amount + pnl
        
        portfolio.attention_stakes -= trade_amount
        if portfolio.attention_stakes <= 0:
            db.delete(portfolio)
    
    # Record the trade
    new_trade = Trade(
        user_id=current_user.id,
        target_id=target.id,
        trade_type=f"stake_{trade.trade_type}",
        stake_amount=trade_amount,
        attention_score_at_entry=target.current_attention_score
    )
    db.add(new_trade)
    
    db.commit()
    
    return {
        "message": "Trade executed successfully",
        "balance": float(current_user.balance)
    }

@app.get("/portfolio")
def get_portfolio(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user's current portfolio"""
    positions = db.query(Portfolio).filter(
        Portfolio.user_id == current_user.id
    ).all()
    
    portfolio_data = []
    total_value = 0
    
    for position in positions:
        target = position.target
        current_value = position.attention_stakes * (target.current_attention_score / position.average_entry_score)
        pnl = current_value - position.attention_stakes
        pnl_percent = (pnl / position.attention_stakes) * 100 if position.attention_stakes > 0 else 0
        
        portfolio_data.append({
            "target": {
                "id": target.id,
                "name": target.name,
                "current_attention_score": float(target.current_attention_score)
            },
            "attention_stakes": float(position.attention_stakes),
            "average_entry_score": float(position.average_entry_score),
            "current_value": float(current_value),
            "pnl": float(pnl),
            "pnl_percent": float(pnl_percent)
        })
        total_value += current_value
    
    return {
        "positions": portfolio_data,
        "total_value": float(total_value),
        "cash_balance": float(current_user.balance),
        "total_portfolio_value": float(total_value + current_user.balance)
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
            "stake_amount": float(trade.stake_amount),
            "attention_score_at_entry": float(trade.attention_score_at_entry),
            "timestamp": trade.timestamp
        })
    
    return result

# Tournament endpoints
@app.get("/tournaments")
def get_tournaments(db: Session = Depends(get_db)):
    """Get active tournaments"""
    tournaments = db.query(Tournament).filter(
        Tournament.status.in_(["upcoming", "active"])
    ).all()
    
    result = []
    for tournament in tournaments:
        entry_count = db.query(TournamentEntry).filter(
            TournamentEntry.tournament_id == tournament.id
        ).count()
        
        result.append({
            "id": tournament.id,
            "name": tournament.name,
            "description": tournament.description,
            "duration": tournament.duration.value,
            "entry_fee": float(tournament.entry_fee),
            "max_participants": tournament.max_participants,
            "current_participants": entry_count,
            "prize_pool": float(tournament.prize_pool),
            "start_date": tournament.start_date,
            "end_date": tournament.end_date,
            "status": tournament.status
        })
    
    return result

@app.post("/tournaments/join")
def join_tournament(entry: TournamentEntryRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Join a tournament"""
    tournament = db.query(Tournament).filter(Tournament.id == entry.tournament_id).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    
    if tournament.status not in ["upcoming", "active"]:
        raise HTTPException(status_code=400, detail="Tournament not available for entry")
    
    # Check if already joined
    existing = db.query(TournamentEntry).filter(
        TournamentEntry.user_id == current_user.id,
        TournamentEntry.tournament_id == tournament.id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Already joined this tournament")
    
    if current_user.balance < tournament.entry_fee:
        raise HTTPException(status_code=400, detail="Insufficient balance for entry fee")
    
    # Deduct entry fee
    current_user.balance -= tournament.entry_fee
    
    # Create tournament entry
    tournament_entry = TournamentEntry(
        user_id=current_user.id,
        tournament_id=tournament.id,
        entry_fee_paid=tournament.entry_fee
    )
    db.add(tournament_entry)
    
    # Update prize pool (90% goes to prize pool, 10% platform fee)
    tournament.prize_pool += tournament.entry_fee * Decimal("0.9")
    
    db.commit()
    
    return {"message": "Successfully joined tournament", "balance": float(current_user.balance)}

@app.get("/leaderboard")
def get_leaderboard(db: Session = Depends(get_db)):
    """Get platform leaderboard"""
    # Simple leaderboard based on account balance
    users = db.query(User).order_by(User.balance.desc()).limit(10).all()
    
    return [
        {
            "rank": i + 1,
            "username": user.username,
            "balance": float(user.balance)
        }
        for i, user in enumerate(users)
    ]

# Admin endpoints
@app.get("/admin/cleanup")
async def cleanup_database(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Admin endpoint to cleanup old data"""
    try:
        # Simple cleanup - remove old history entries (keep last 100 per target)
        targets = db.query(AttentionTarget).all()
        
        for target in targets:
            # Keep only the latest 100 history entries per target
            old_entries = db.query(AttentionHistory).filter(
                AttentionHistory.target_id == target.id
            ).order_by(AttentionHistory.timestamp.desc()).offset(100).all()
            
            for entry in old_entries:
                db.delete(entry)
        
        db.commit()
        logger.info("Database cleanup completed")
        return {"message": "Database cleanup completed", "status": "success"}
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
        async with GoogleTrendsService(websocket_manager=manager) as service:
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

# Health check endpoints
@app.get("/")
def read_root():
    return {"message": "TrendBet Attention Trading API", "version": "2.0.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/service-status")
def get_service_status():
    """Get status of various services"""
    return {
        "api": {"status": "healthy", "version": "2.0.0"},
        "database": {"status": "connected"},
        "google_trends": {"status": "running", "service": "GoogleTrendsService"},
        "timestamp": datetime.utcnow().isoformat()
    }

# WebSocket endpoints
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and send periodic updates
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({
                "type": "ping", 
                "timestamp": datetime.utcnow().isoformat()
            }))
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.websocket("/ws/{target_id}")
async def websocket_target_endpoint(websocket: WebSocket, target_id: int):
    await manager.connect(websocket, target_id)
    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({
                "type": "ping",
                "target_id": target_id,
                "timestamp": datetime.utcnow().isoformat()
            }))
    except WebSocketDisconnect:
        manager.disconnect(websocket, target_id)

# Background task startup - FIXED IMPORTS
async def start_background_tasks():
    """Start background tasks for real-time data updates with WebSocket support"""
    try:
        # FIX: Import the correct function and pass websocket manager
        from background_updater import start_background_updates
        
        # Pass the WebSocket manager to enable real-time updates
        asyncio.create_task(start_background_updates(websocket_manager=manager))
        logger.info("✅ Background data updates started with WebSocket support")
        
    except ImportError as e:
        logger.error(f"❌ Failed to import background_updater: {e}")
        # Fallback to service method with WebSocket manager
        try:
            from google_trends_service import run_background_updates
            asyncio.create_task(run_background_updates(websocket_manager=manager))
            logger.info("✅ Fallback background data updates started with WebSocket support")
        except ImportError:
            logger.error("❌ No background update system available")

@app.on_event("startup")
async def startup_event():
    """Initialize the application with real-time capabilities"""
    logger.info("🚀 TrendBet API starting up...")
    
    # Start background tasks for real-time updates
    await start_background_tasks()
    
    logger.info("✅ TrendBet API ready!")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 TrendBet API shutting down...")
    
    # Close all WebSocket connections
    for connection in manager.active_connections:
        try:
            await connection.close()
        except:
            pass
    
    logger.info("✅ TrendBet API shutdown complete!")