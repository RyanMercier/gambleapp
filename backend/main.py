"""
TrendBet Attention Trading API

A FastAPI application for attention-based trading using Google Trends data.
Provides endpoints for user authentication, attention target management,
tournament creation, trading execution, and real-time data updates.
"""

# Standard library imports
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional

# Third-party imports
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

# Local imports
from auth import authenticate_user, create_access_token, create_user, decode_access_token, get_current_user
from csv_loader import csv_loader
from database import SessionLocal, engine
from google_trends_service import GoogleTrendsService
from models import (
    AttentionHistory,
    AttentionTarget,
    ChatMessage,
    Portfolio,
    TargetType,
    Tournament,
    TournamentDuration,
    TournamentEntry,
    Trade,
    User,
)
from seed_data import store_timeframe_data_with_real_timestamps

# Configuration
USE_TOR = "--torify" in sys.argv or os.getenv('USE_TOR', 'false').lower() == 'true'


app = FastAPI(
    title="TrendBet Attention Trading API",
    version="2.0.0",
    description="A real-time attention trading platform using Google Trends data"
)

# CORS middleware configuration for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"  # For development only - remove in production
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# OAuth2 configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database dependency
def get_db():
    """
    Dependency function that provides database session.
    Ensures proper cleanup of database connections.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Pydantic request/response models
class UserRegister(BaseModel):
    """User registration request model."""
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    """User login request model."""
    username: str
    password: str


class TradeRequest(BaseModel):
    """Trade execution request model."""
    target_id: int
    trade_type: str  # 'buy' for long positions, 'sell' for short positions
    shares: float
    tournament_id: int


class SearchRequest(BaseModel):
    """Search request for finding attention targets."""
    query: str
    target_type: str = "politician"  # Default to politician search


class TournamentEntryRequest(BaseModel):
    """Tournament entry request model."""
    tournament_id: int

class ChatMessageRequest(BaseModel):
    """Chat message request model."""
    content: str

# WebSocket Connection Manager
class ConnectionManager:
    """
    Manages WebSocket connections for real-time data updates.
    Handles both global connections and target-specific subscriptions.
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.target_subscribers: Dict[int, List[WebSocket]] = {}
        self.chat_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, target_id: int = None):
        """Accept WebSocket connection and optionally subscribe to target updates."""
        await websocket.accept()
        self.active_connections.append(websocket)

        if target_id:
            if target_id not in self.target_subscribers:
                self.target_subscribers[target_id] = []
            self.target_subscribers[target_id].append(websocket)

    def disconnect(self, websocket: WebSocket, target_id: int = None):
        """Remove WebSocket connection from active connections and subscriptions."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        if target_id and target_id in self.target_subscribers:
            if websocket in self.target_subscribers[target_id]:
                self.target_subscribers[target_id].remove(websocket)

    async def send_target_update(self, target_id: int, data: dict):
        """Send updates to all clients subscribed to a specific target."""
        if target_id in self.target_subscribers:
            disconnected = []
            for connection in self.target_subscribers[target_id]:
                try:
                    await connection.send_text(json.dumps(data))
                except (ConnectionError, RuntimeError) as e:
                    logger.warning(f"Failed to send update to client: {e}")
                    disconnected.append(connection)

            # Clean up disconnected clients
            for conn in disconnected:
                self.target_subscribers[target_id].remove(conn)

    async def connect_chat(self, websocket: WebSocket):
        """Accept WebSocket connection for chat."""
        await websocket.accept()
        self.chat_connections.append(websocket)

    def disconnect_chat(self, websocket: WebSocket):
        """Remove WebSocket connection from chat connections."""
        if websocket in self.chat_connections:
            self.chat_connections.remove(websocket)

    async def broadcast_to_chat(self, data: dict):
        """Send updates to all chat WebSocket clients."""
        disconnected = []
        for connection in self.chat_connections:
            try:
                await connection.send_text(json.dumps(data))
            except (ConnectionError, RuntimeError) as e:
                logger.warning(f"Failed to send chat message to client: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.chat_connections.remove(conn)

manager = ConnectionManager()


# CORS preflight handler
@app.options("/{full_path:path}")
async def options_handler():
    """Handle CORS preflight requests."""
    return {"message": "OK"}


# Authentication endpoints
@app.post("/auth/register")
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user account.

    Args:
        user_data: User registration information
        db: Database session

    Returns:
        Authentication token and user information

    Raises:
        HTTPException: If username or email already exists
    """
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
    """
    Authenticate user and return access token.

    Args:
        user_data: User login credentials
        db: Database session

    Returns:
        Authentication token and user information

    Raises:
        HTTPException: If credentials are invalid
    """
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
    """
    Get current user information.

    Args:
        current_user: Authenticated user from token

    Returns:
        Current user profile information
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "balance": float(current_user.balance),
        "created_at": current_user.created_at
    }

# Search and Target Management
@app.get("/api/autocomplete/{category}")
async def get_autocomplete_suggestions(
    category: str, 
    q: str = Query("", min_length=0), 
    limit: int = Query(10, ge=1, le=50)
):
    """Get autocomplete suggestions for a specific category"""
    valid_categories = ['politicians', 'celebrities', 'countries', 'games', 'stocks', 'crypto']
    
    if category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {valid_categories}")
    
    # Return empty if query too short
    if len(q.strip()) < 2:
        return {
            "success": True,
            "category": category,
            "query": q,
            "suggestions": [],
            "total": 0,
            "message": "Query too short (minimum 2 characters)"
        }
    
    suggestions = csv_loader.search_in_category(category, q, limit)
    
    return {
        "success": True,
        "category": category,
        "query": q,
        "suggestions": suggestions,
        "total": len(suggestions)
    }

@app.get("/api/autocomplete")  
async def search_all_categories(
    q: str = Query("", min_length=0), 
    limit: int = Query(20, ge=1, le=100)
):
    """Search across all categories"""
    if len(q.strip()) < 2:
        return {
            "success": False, 
            "message": "Query too short (minimum 2 characters)",
            "query": q,
            "results": {}
        }
    
    results = csv_loader.search_all_categories(q, limit)
    
    return {
        "success": True,
        "query": q,
        "results": results,
        "total_categories": len(results),
        "total_results": sum(len(items) for items in results.values())
    }

@app.get("/api/categories/{category}")
async def get_category_list(
    category: str, 
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Get full list of items in a category"""
    valid_categories = ['politicians', 'celebrities', 'countries', 'games', 'stocks', 'crypto']
    
    if category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {valid_categories}")
    
    all_data = csv_loader.get_category_data(category)
    total = len(all_data)
    
    # Apply pagination
    data = all_data[offset:offset + limit]
    
    return {
        "success": True,
        "category": category,
        "data": data,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total
    }

@app.get("/api/categories")
async def get_all_categories():
    """Get list of all categories with their counts"""
    stats = csv_loader.get_category_stats()
    categories = []
    
    category_info = {
        'politicians': {'label': '🏛️ Politicians', 'icon': '🏛️'},
        'celebrities': {'label': '🌟 Celebrities', 'icon': '🌟'},
        'countries': {'label': '🌍 Countries', 'icon': '🌍'},
        'games': {'label': '🎮 Games', 'icon': '🎮'},
        'stocks': {'label': '📈 Stocks', 'icon': '📈'},
        'crypto': {'label': '₿ Crypto', 'icon': '₿'}
    }
    
    for category, count in stats.items():
        info = category_info.get(category, {'label': category.title(), 'icon': '📊'})
        categories.append({
            'value': category,
            'label': info['label'],
            'icon': info['icon'],
            'count': count
        })
    
    return {
        "success": True,
        "categories": categories,
        "total_categories": len(categories)
    }

@app.get("/api/suggestions/{category}")
async def get_random_suggestions(
    category: str,
    count: int = Query(10, ge=1, le=50)
):
    """Get random suggestions from a category for discovery"""
    valid_categories = ['politicians', 'celebrities', 'countries', 'games', 'stocks', 'crypto']
    
    if category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {valid_categories}")
    
    suggestions = csv_loader.get_random_suggestions(category, count)
    
    return {
        "success": True,
        "category": category,
        "suggestions": suggestions,
        "count": len(suggestions)
    }

@app.post("/admin/reload-csv-data")
async def reload_csv_data(current_user: User = Depends(get_current_user)):
    """Reload CSV data from files (admin only)"""
    # You might want to add admin role checking here
    try:
        csv_loader.reload_data()
        stats = csv_loader.get_category_stats()
        
        return {
            "success": True,
            "message": "CSV data reloaded successfully",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Failed to reload CSV data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reload CSV data: {str(e)}")

# Update your existing search endpoint to use CSV validation
@app.post("/api/search")
async def search_attention_target(
    search: SearchRequest, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search for attention targets - now validates against CSV data"""
    
    # Validate that the search term exists in our CSV data
    category_map = {
        'politician': 'politicians',
        'celebrity': 'celebrities', 
        'country': 'countries',
        'game': 'games',
        'stock': 'stocks',
        'crypto': 'crypto'
    }
    
    csv_category = category_map.get(search.target_type)
    if not csv_category:
        raise HTTPException(status_code=400, detail="Invalid target type")
    
    # Search in CSV to validate the target exists
    csv_matches = csv_loader.search_in_category(csv_category, search.query, limit=5)
    
    if not csv_matches:
        raise HTTPException(
            status_code=404, 
            detail=f"'{search.query}' not found in {search.target_type} list. Only pre-approved targets can be traded."
        )
    
    # Find the best match
    best_match = None
    for match in csv_matches:
        if match['name'].lower() == search.query.lower():
            best_match = match
            break
    
    if not best_match:
        best_match = csv_matches[0]  # Use first match if no exact match
    
    # Check if target already exists in database
    existing_target = db.query(AttentionTarget).filter(
        AttentionTarget.search_term.ilike(f"%{best_match['search_term']}%")
    ).first()
    
    if existing_target:
        return {
            "success": True,
            "message": f"Found existing target: {existing_target.name}",
            "target": {
                "id": existing_target.id,
                "name": existing_target.name,
                "type": existing_target.type.value,
                "search_term": existing_target.search_term,
                "current_attention_score": float(existing_target.current_attention_score)
            },
            "csv_match": best_match
        }
    
    # Create new target using CSV data
    try:
        async with GoogleTrendsService(websocket_manager=manager, use_tor=USE_TOR) as service:
            trends_data = await service.get_google_trends_data(best_match['search_term'])
            
            if not trends_data.get('success'):
                raise HTTPException(status_code=500, detail="Failed to get Google Trends data")
            
            # Map CSV category back to enum
            type_map = {
                'politicians': TargetType.POLITICIAN,
                'celebrities': TargetType.CELEBRITY,
                'countries': TargetType.COUNTRY,
                'games': TargetType.GAME,
                'stocks': TargetType.STOCK,
                'crypto': TargetType.CRYPTO
            }
            
            new_target = AttentionTarget(
                name=best_match['name'],
                type=type_map[csv_category],
                search_term=best_match['search_term'],
                current_attention_score=Decimal(str(trends_data['attention_score']))
            )
            
            db.add(new_target)
            db.commit()
            db.refresh(new_target)
            
            # Store initial history point with immediate 1-day data
            if trends_data.get('timeline') and trends_data.get('timeline_timestamps'):
                try:
                    from seed_data import store_timeframe_data_with_real_timestamps
                    await store_timeframe_data_with_real_timestamps(
                        new_target, trends_data, "1d", "now 1-d", db
                    )
                    logger.info("Successfully stored initial 1-day data immediately")
                except Exception as e:
                    logger.warning(f"Failed to store initial 1d data: {e}")
            else:
                # Store single point if no timeline data
                history = AttentionHistory(
                    target_id=new_target.id,
                    attention_score=new_target.current_attention_score,
                    data_source="google_trends",
                    timeframe_used="now 1-d"
                )
                db.add(history)
                db.commit()
            
            # Start gradual background seeding for remaining timeframes
            # This spreads the seeding over 30+ minutes to avoid rate limits
            asyncio.create_task(
                gradual_historical_seeding(
                    new_target.id, 
                    best_match['search_term'],
                    start_delay_minutes=2  # Wait 2 minutes before starting
                )
            )
            
            return {
                "success": True,
                "message": f"Created new target: {new_target.name}. More historical data will load gradually over the next 30 minutes to avoid rate limits.",
                "target": {
                    "id": new_target.id,
                    "name": new_target.name,
                    "type": new_target.type.value,
                    "search_term": new_target.search_term,
                    "current_attention_score": float(new_target.current_attention_score),
                },
                "csv_match": best_match,
                "trends_data": trends_data
            }
            
    except Exception as e:
        logger.error(f"Error creating target from CSV match: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create target: {str(e)}")

async def gradual_historical_seeding(target_id: int, search_term: str, start_delay_minutes: int = 2):
    """Gradual background seeding to avoid rate limits - spread over 30+ minutes"""
    
    # Initial delay before starting
    logger.info(f"Chart: Gradual seeding for target {target_id} starting in {start_delay_minutes} minutes...")
    await asyncio.sleep(start_delay_minutes * 60)
    
    db = SessionLocal()
    try:
        target = db.query(AttentionTarget).filter(AttentionTarget.id == target_id).first()
        if not target:
            logger.error(f"Failed: Target {target_id} not found for gradual seeding")
            return
            
        logger.info(f"Chart: Starting gradual historical seeding for {target.name}")
        
        # FIX: Conservative timeframe seeding with long delays (no random)
        timeframes_with_delays = [
            ("now 7-d", "7d", 5),      # Wait 5 minutes, then seed 7-day
            ("today 1-m", "1m", 8),    # Wait 8 more minutes, then seed 1-month  
            ("today 3-m", "3m", 10),   # Wait 10 more minutes, then seed 3-month
            ("today 12-m", "1y", 12),  # Wait 12 more minutes, then seed 1-year
            ("today 5-y", "5y", 15),   # Wait 15 more minutes, then seed 5-year
        ]
        
        seeded_count = 1  # Already have 1d data
        
        async with GoogleTrendsService(websocket_manager=manager, use_tor=USE_TOR) as service:
            for timeframe_code, timeframe_name, delay_minutes in timeframes_with_delays:
                try:
                    # Wait before each request
                    logger.info(f"Timing: Waiting {delay_minutes} minutes before seeding {timeframe_name} data for {target.name}")
                    await asyncio.sleep(delay_minutes * 60)
                    
                    logger.info(f"Data: Seeding {timeframe_name} data for {target.name}...")
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
                        logger.info(f"Successfully Seeded {timeframe_name} data for {target.name}")
                    else:
                        error_msg = data.get('error', 'No timeline data') if data else 'Request failed'
                        logger.warning(f"Warning: No {timeframe_name} data for {target.name}: {error_msg}")
                        
                        # If we hit rate limits, increase delays for remaining timeframes
                        if 'Rate limited' in error_msg or 'Circuit breaker' in error_msg:
                            logger.warning(f"Blocked: Rate limited during {timeframe_name} seeding. Extending delays for remaining timeframes.")
                            # Double remaining delays
                            remaining_frames = timeframes_with_delays[timeframes_with_delays.index((timeframe_code, timeframe_name, delay_minutes)) + 1:]
                            for tc, tn, dm in remaining_frames:
                                timeframes_with_delays[timeframes_with_delays.index((tc, tn, dm))] = (tc, tn, dm * 2)
                    
                except Exception as e:
                    logger.error(f"Failed: Failed to seed {timeframe_name} data for {target.name}: {e}")
                    # Continue with next timeframe after brief pause
                    await asyncio.sleep(30)
            
            total_time = sum([delay for _, _, delay in timeframes_with_delays])
            logger.info(f"Successfully Gradual seeding complete for {target.name}: {seeded_count}/6 timeframes over {total_time} minutes")
            
            # Update target to indicate seeding is complete
            target.last_updated = datetime.now(timezone.utc)
            db.commit()
            
    except Exception as e:
        logger.error(f"Failed: Gradual seeding failed for target {target_id}: {e}")
        db.rollback()
    finally:
        db.close()

async def seed_historical_data_for_target(target_id: int, search_term: str):
    """Background task to seed historical data for a newly created target"""
    db = SessionLocal()
    try:
        target = db.query(AttentionTarget).filter(AttentionTarget.id == target_id).first()
        if not target:
            logger.error(f"Failed: Target {target_id} not found for historical seeding")
            return
            
        logger.info(f"Chart: Starting historical data seeding for {target.name}")
        
        async with GoogleTrendsService(websocket_manager=manager, use_tor=USE_TOR) as service:
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
                    logger.info(f"Data: Seeding {timeframe_name} data for {target.name}...")
                    data = await service.get_google_trends_data(search_term, timeframe=timeframe_code)
                    
                    if data and data.get('success') and data.get('timeline'):
                        await store_timeframe_data_with_real_timestamps(
                            target, data, timeframe_name, timeframe_code, db
                        )
                        seeded_count += 1
                        logger.info(f"Successfully Seeded {timeframe_name} data")
                    else:
                        logger.warning(f"Warning: No {timeframe_name} data available for {target.name}")
                    
                    # Rate limit between requests
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Failed: Failed to seed {timeframe_name} data for {target.name}: {e}")
            
            logger.info(f"Successfully Historical seeding complete for {target.name}: {seeded_count}/6 timeframes")
            
            # Update target to indicate seeding is complete
            target.last_updated = datetime.now(timezone.utc)
            db.commit()
            
    except Exception as e:
        logger.error(f"Failed: Historical seeding failed for target {target_id}: {e}")
        db.rollback()
    finally:
        db.close()

@app.get("/targets")
def get_targets(
    target_type: Optional[str] = Query(None),
    limit: Optional[int] = Query(50),
    db: Session = Depends(get_db)
):
    """Get attention targets with frontend-compatible format"""
    query = db.query(AttentionTarget).filter(AttentionTarget.is_active == True)
    
    if target_type:
        try:
            target_type_enum = TargetType(target_type.lower())
            query = query.filter(AttentionTarget.type == target_type_enum)
        except ValueError:
            pass  # Invalid target type, ignore filter
    
    targets = query.order_by(AttentionTarget.current_attention_score.desc()).limit(limit).all()
    
    result = []
    for target in targets:
        result.append({
            "id": target.id,
            "name": target.name,
            "type": target.type.value,
            "search_term": target.search_term,
            "description": target.description,
            "current_attention_score": float(target.current_attention_score),
            "last_updated": target.last_updated.isoformat() if target.last_updated else None
        })
    
    return result

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
    
    end_time = datetime.now(timezone.utc)
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
    
    logger.info(f"Chart: Chart request: {days} days -> trying {data_source}")
    
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
        logger.info("Chart: Adding real-time data for 1-day chart")
        realtime_data = db.query(AttentionHistory).filter(
            AttentionHistory.target_id == target_id,
            AttentionHistory.data_source == "google_trends_realtime",
            AttentionHistory.timestamp >= start_time
        ).order_by(AttentionHistory.timestamp.asc()).all()
        
        if realtime_data:
            # Combine and sort
            all_data = list(all_data) + list(realtime_data)
            all_data.sort(key=lambda x: x.timestamp)
            logger.info(f"Chart: Combined data: {len(base_data)} base + {len(realtime_data)} realtime = {len(all_data)} total")
    
    # FIX: If still no data, create a synthetic data point from current score
    if not all_data:
        logger.warning(f"No historical data found for target {target_id}. Creating synthetic data point.")
        
        # Create a single data point with current score
        synthetic_data_point = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
    
    logger.info(f"Chart: Returning {len(data_points)} points for {target.name} ({days}d) using {actual_data_source}")
    
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
    """
    Execute a trade (buy/sell) for an attention target in a tournament.
    Validates tournament membership, target type compatibility, and balance requirements.

    Args:
        trade: Trade request containing target_id, trade_type, shares, and tournament_id
        current_user: Authenticated user executing the trade
        db: Database session

    Returns:
        Trade confirmation with updated balance and position information

    Raises:
        HTTPException: If target not found, tournament not found, insufficient balance,
                      or target type doesn't match tournament
    """
    try:
        target = db.query(AttentionTarget).filter(AttentionTarget.id == trade.target_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="Target not found")

        # Validate tournament exists and user is in it
        tournament = db.query(Tournament).filter(Tournament.id == trade.tournament_id).first()
        if not tournament:
            raise HTTPException(status_code=404, detail="Tournament not found")

        # Check if user is in this tournament
        tournament_entry = db.query(TournamentEntry).filter(
            TournamentEntry.tournament_id == trade.tournament_id,
            TournamentEntry.user_id == current_user.id
        ).first()
        if not tournament_entry:
            raise HTTPException(status_code=400, detail="You must join this tournament before trading")

        # CRITICAL: Validate target type matches tournament type
        if target.type != tournament.target_type:
            raise HTTPException(
                status_code=400,
                detail=f"Target type mismatch: {target.name} is a {target.type.value} target, but this is a {tournament.target_type.value} tournament"
            )
        
        # Convert to Decimal for precise calculations
        from decimal import Decimal
        trade_amount = Decimal(str(abs(trade.shares) * 10))
        current_score = Decimal(str(target.current_attention_score))
        pnl = Decimal('0.0')
        
        logger.info(f"Trade execution: {trade.trade_type} {trade.shares} units of {target.name} (${trade_amount}) for user {current_user.username}")

        # Validate tournament balance for the trade

        if trade.trade_type == "buy":  # LONG position
            if tournament_entry.current_balance < trade_amount:
                raise HTTPException(status_code=400, detail=f"Insufficient tournament balance. Need ${trade_amount}, have ${tournament_entry.current_balance}")

            tournament_entry.current_balance -= trade_amount
            
            # Update or create LONG portfolio position
            portfolio = db.query(Portfolio).filter(
                Portfolio.user_id == current_user.id,
                Portfolio.target_id == target.id,
                Portfolio.tournament_id == trade.tournament_id,
                Portfolio.position_type == "long"
            ).first()
            
            if portfolio:
                # Update existing position - all Decimal math
                total_stakes = portfolio.attention_stakes + trade_amount
                weighted_avg = (portfolio.attention_stakes * portfolio.average_entry_score + trade_amount * current_score) / total_stakes
                portfolio.average_entry_score = weighted_avg
                portfolio.attention_stakes = total_stakes
            else:
                # Create new LONG position
                portfolio = Portfolio(
                    user_id=current_user.id,
                    target_id=target.id,
                    tournament_id=trade.tournament_id,
                    attention_stakes=trade_amount,
                    average_entry_score=current_score,
                    position_type="long"
                )
                db.add(portfolio)
        
        elif trade.trade_type == "sell":  # SHORT position
            if tournament_entry.current_balance < trade_amount:
                raise HTTPException(status_code=400, detail=f"Insufficient tournament balance. Need ${trade_amount}, have ${tournament_entry.current_balance}")

            tournament_entry.current_balance -= trade_amount
            
            # Create or update SHORT position
            short_portfolio = db.query(Portfolio).filter(
                Portfolio.user_id == current_user.id,
                Portfolio.target_id == target.id,
                Portfolio.tournament_id == trade.tournament_id,
                Portfolio.position_type == "short"
            ).first()
            
            if short_portfolio:
                # Update existing short position - all Decimal math
                total_stakes = short_portfolio.attention_stakes + trade_amount
                weighted_avg = (short_portfolio.attention_stakes * short_portfolio.average_entry_score + trade_amount * current_score) / total_stakes
                short_portfolio.average_entry_score = weighted_avg
                short_portfolio.attention_stakes = total_stakes
            else:
                # Create new SHORT position
                short_portfolio = Portfolio(
                    user_id=current_user.id,
                    target_id=target.id,
                    tournament_id=trade.tournament_id,
                    attention_stakes=trade_amount,
                    average_entry_score=current_score,
                    position_type="short"
                )
                db.add(short_portfolio)
        
        # Record the trade
        new_trade = Trade(
            user_id=current_user.id,
            target_id=target.id,
            tournament_id=trade.tournament_id,
            trade_type=f"stake_{trade.trade_type}",
            position_type="long" if trade.trade_type == "buy" else "short",
            stake_amount=trade_amount,
            attention_score_at_entry=current_score,
            pnl=pnl
        )
        db.add(new_trade)
        
        db.commit()
        
        return {
            "message": f"{'Long' if trade.trade_type == 'buy' else 'Short'} position opened successfully",
            "balance": float(current_user.balance),
            "total_amount": float(trade_amount),
            "trade_id": new_trade.id,
            "position_type": "long" if trade.trade_type == "buy" else "short"
        }
        
    except Exception as e:
        logger.error(f"Trade execution failed for user {current_user.username}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Trade execution failed: {str(e)}")

@app.post("/trade/close/{target_id}")
def close_position(
    target_id: int,
    position_type: str,  # "long" or "short"
    tournament_id: Optional[int] = None,  # Tournament filter
    amount: Optional[float] = None,  # If None, close entire position
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Close a specific trading position (long or short) for a target.

    Args:
        target_id: ID of the attention target
        position_type: Type of position to close ("long" or "short")
        tournament_id: Optional tournament filter
        amount: Optional amount to close (if None, closes entire position)
        current_user: Authenticated user
        db: Database session

    Returns:
        Position close confirmation with P&L information

    Raises:
        HTTPException: If target or position not found, or insufficient position size
    """
    target = db.query(AttentionTarget).filter(AttentionTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    # Build query with optional tournament filter
    query = db.query(Portfolio).filter(
        Portfolio.user_id == current_user.id,
        Portfolio.target_id == target_id,
        Portfolio.position_type == position_type
    )

    if tournament_id:
        query = query.filter(Portfolio.tournament_id == tournament_id)

    portfolio = query.first()
    
    if not portfolio:
        raise HTTPException(status_code=404, detail=f"No {position_type} position found")
    
    # Determine close amount
    close_amount = Decimal(str((amount or portfolio.attention_stakes / 10) * 10))
    
    if close_amount > portfolio.attention_stakes:
        raise HTTPException(status_code=400, detail="Cannot close more than position size")
    
    # Calculate P&L
    score_ratio = target.current_attention_score / portfolio.average_entry_score if portfolio.average_entry_score > 0 else 1
    
    if position_type == "long":
        # Long profits when score goes up
        pnl = close_amount * (score_ratio - 1)
    else:
        # Short profits when score goes down
        pnl = close_amount * (1 - score_ratio)
    
    # Get tournament entry to update balance
    tournament_entry = db.query(TournamentEntry).filter(
        TournamentEntry.user_id == current_user.id,
        TournamentEntry.tournament_id == portfolio.tournament_id
    ).first()

    if tournament_entry:
        # Return money + P&L to tournament balance
        tournament_entry.current_balance += close_amount + pnl
    
    # Reduce or remove position
    portfolio.attention_stakes -= close_amount
    if portfolio.attention_stakes <= 0:
        db.delete(portfolio)
    
    # Record the close trade
    close_trade = Trade(
        user_id=current_user.id,
        target_id=target_id,
        tournament_id=portfolio.tournament_id,
        trade_type=f"close_{position_type}",
        stake_amount=close_amount,
        attention_score_at_entry=target.current_attention_score,
        pnl=pnl,
        is_closed=True
    )
    db.add(close_trade)
    
    db.commit()
    
    return {
        "message": f"{position_type.title()} position closed",
        "pnl": float(pnl),
        "balance": float(current_user.balance),
        "closed_amount": float(close_amount)
    }

# Add this function to handle "flatten" operations
@app.post("/trade/flatten/{target_id}")
def flatten_position(
    target_id: int, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Flatten (close) entire position in a target"""
    try:
        target = db.query(AttentionTarget).filter(AttentionTarget.id == target_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="Target not found")
        
        # Find all positions for this target
        positions = db.query(Portfolio).filter(
            Portfolio.user_id == current_user.id,
            Portfolio.target_id == target_id
        ).all()
        
        if not positions:
            raise HTTPException(status_code=404, detail="No positions found for this target")
        
        total_pnl = Decimal('0.0')
        total_closed = Decimal('0.0')
        closed_positions = []
        
        for portfolio in positions:
            position_type = portfolio.position_type or 'long'
            close_amount = portfolio.attention_stakes
            
            # Calculate P&L for this position
            score_ratio = target.current_attention_score / portfolio.average_entry_score if portfolio.average_entry_score > 0 else 1
            
            if position_type == "long":
                # Long profits when score goes up
                pnl = close_amount * (score_ratio - 1)
            else:
                # Short profits when score goes down
                pnl = close_amount * (1 - score_ratio)
            
            total_pnl += pnl
            total_closed += close_amount
            
            # Get tournament entry to update balance
            tournament_entry = db.query(TournamentEntry).filter(
                TournamentEntry.user_id == current_user.id,
                TournamentEntry.tournament_id == portfolio.tournament_id
            ).first()

            if tournament_entry:
                # Return money + P&L to tournament balance
                tournament_entry.current_balance += close_amount + pnl
            
            # Record the close trade
            close_trade = Trade(
                user_id=current_user.id,
                target_id=target_id,
                tournament_id=portfolio.tournament_id,
                trade_type=f"flatten_{position_type}",
                stake_amount=close_amount,
                attention_score_at_entry=target.current_attention_score,
                pnl=pnl,
                is_closed=True
            )
            db.add(close_trade)
            
            closed_positions.append({
                "position_type": position_type,
                "amount": float(close_amount),
                "pnl": float(pnl)
            })
            
            # Remove the position
            db.delete(portfolio)
        
        db.commit()
        
        return {
            "message": "All positions flattened successfully",
            "total_pnl": float(total_pnl),
            "total_closed": float(total_closed),
            "balance": float(current_user.balance),
            "closed_positions": closed_positions
        }
        
    except Exception as e:
        logger.error(f"Failed: Flatten position error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Flatten failed: {str(e)}")

@app.get("/portfolio")
def get_portfolio(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user's portfolio - FIXED for decimal/float mixing"""
    try:
        positions = db.query(Portfolio).filter(
            Portfolio.user_id == current_user.id
        ).all()
        
        portfolio_data = []
        total_value = 0.0
        daily_pnl = 0.0
        
        for position in positions:
            target = position.target
            
            # Convert ALL values to float immediately to avoid mixing
            attention_stakes = float(position.attention_stakes)
            average_entry_score = float(position.average_entry_score) if position.average_entry_score else 1.0
            current_attention_score = float(target.current_attention_score)
            
            # All calculations as float
            score_ratio = current_attention_score / average_entry_score if average_entry_score > 0 else 1.0
            
            # Get position type safely
            position_type = getattr(position, 'position_type', 'long')
            
            if position_type == "long":
                # Long profits when score goes up
                current_value = attention_stakes * score_ratio
                pnl = current_value - attention_stakes
            else:
                # Short profits when score goes down  
                current_value = attention_stakes * (2.0 - score_ratio)
                pnl = current_value - attention_stakes
            
            pnl_percent = (pnl / attention_stakes) * 100.0 if attention_stakes > 0 else 0.0
            
            portfolio_data.append({
                "target": {
                    "id": target.id,
                    "name": target.name,
                    "type": target.type.value,
                    "current_attention_score": current_attention_score
                },
                "target_id": target.id,
                "attention_stakes": attention_stakes,
                "average_entry_score": average_entry_score,
                "current_value": current_value,
                "pnl": pnl,
                "pnl_percent": pnl_percent,
                "position_type": position_type,
                # Legacy compatibility
                "shares_owned": attention_stakes / 10.0,
                "position_value": current_value
            })
            total_value += current_value
        
        # Calculate today's PnL from trades
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        today_trades = db.query(Trade).filter(
            Trade.user_id == current_user.id,
            Trade.timestamp >= today,
            Trade.timestamp < tomorrow
        ).all()
        
        daily_pnl = sum(float(trade.pnl or 0) for trade in today_trades)
        
        return {
            "positions": portfolio_data,
            "total_value": total_value,
            "daily_pnl": daily_pnl,
            "cash_balance": float(current_user.balance),
            "total_portfolio_value": total_value + float(current_user.balance)
        }
        
    except Exception as e:
        logger.error(f"Failed: Portfolio error: {e}")
        raise HTTPException(status_code=500, detail=f"Portfolio error: {str(e)}")

@app.get("/user/tournament-balances")
def get_tournament_balances(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user's balance in each active tournament - FIXED"""
    try:
        # Get all user's tournament entries for active tournaments
        entries = db.query(TournamentEntry).filter(
            TournamentEntry.user_id == current_user.id
        ).join(Tournament).filter(
            Tournament.is_active == True,
            Tournament.is_finished == False
        ).all()
        
        balances = []
        for entry in entries:
            tournament = entry.tournament
            
            # Calculate current tournament balance safely
            starting_balance = float(entry.starting_balance)
            
            # Use current_balance if it exists, otherwise calculate it
            try:
                current_balance = float(getattr(entry, 'current_balance', starting_balance))
            except (AttributeError, TypeError):
                # If current_balance doesn't exist, calculate from tournament trades
                tournament_trades = db.query(Trade).filter(
                    Trade.user_id == current_user.id,
                    Trade.tournament_id == tournament.id
                ).all()
                
                tournament_pnl = sum(float(trade.pnl or 0) for trade in tournament_trades)
                current_balance = starting_balance + tournament_pnl
            
            # Calculate P&L for this tournament
            pnl = current_balance - starting_balance

            balances.append({
                "tournament_id": tournament.id,
                "name": tournament.name,  # Changed from tournament_name to name
                "tournament_name": tournament.name,  # Keep both for compatibility
                "duration": tournament.duration.value,
                "starting_balance": starting_balance,
                "current_balance": current_balance,
                "pnl": pnl,
                "entry_fee": float(entry.entry_fee),
                "is_free": float(entry.entry_fee) == 0.0,
                "start_date": tournament.start_date.isoformat() if tournament.start_date else None,
                "end_date": tournament.end_date.isoformat() if tournament.end_date else None,
                "rank": entry.rank if hasattr(entry, 'rank') and entry.rank else None
            })
        
        return {
            "tournament_balances": balances,
            "active_tournaments": len(balances)
        }
        
    except Exception as e:
        logger.error(f"Failed: Tournament balances error: {e}")
        raise HTTPException(status_code=500, detail=f"Tournament balances error: {str(e)}")

@app.get("/user/daily-pnl")
def get_daily_pnl(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user's P&L for today across all tournaments"""
    try:
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        # Get today's trades
        today_trades = db.query(Trade).filter(
            Trade.user_id == current_user.id,
            Trade.timestamp >= today,
            Trade.timestamp < tomorrow
        ).all()
        
        daily_pnl = sum(float(trade.pnl or 0) for trade in today_trades)
        
        return {
            "daily_pnl": daily_pnl,
            "trades_today": len(today_trades),
            "date": today.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed: Daily P&L error: {e}")
        return {"daily_pnl": 0.0, "trades_today": 0}
    
@app.get("/user/stats")
def get_user_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get comprehensive user trading statistics"""
    try:
        # Get all user trades
        trades = db.query(Trade).filter(
            Trade.user_id == current_user.id
        ).all()
        
        # Get user's portfolio
        portfolio = db.query(Portfolio).filter(
            Portfolio.user_id == current_user.id
        ).all()
        
        # Calculate stats
        closed_trades = [t for t in trades if t.is_closed]
        winning_trades = [t for t in closed_trades if (t.pnl or 0) > 0]
        losing_trades = [t for t in closed_trades if (t.pnl or 0) < 0]
        
        total_pnl = sum(float(t.pnl or 0) for t in closed_trades)
        
        # Portfolio value calculation
        portfolio_value = 0.0
        for position in portfolio:
            target = position.target
            if target:
                attention_stakes = float(position.attention_stakes)
                average_entry_score = float(position.average_entry_score) if position.average_entry_score else 1.0
                current_attention_score = float(target.current_attention_score)
                score_ratio = current_attention_score / average_entry_score if average_entry_score > 0 else 1.0
                
                position_type = getattr(position, 'position_type', 'long')
                if position_type == "long":
                    current_value = attention_stakes * score_ratio
                else:
                    current_value = attention_stakes * (2.0 - score_ratio)
                portfolio_value += current_value
        
        # Tournament stats (placeholder)
        tournament_entries = db.query(TournamentEntry).filter(
            TournamentEntry.user_id == current_user.id
        ).all()
        
        tournaments_won = len([e for e in tournament_entries if getattr(e, 'rank', None) == 1])
        tournaments_top3 = len([e for e in tournament_entries if getattr(e, 'rank', None) and e.rank <= 3])
        
        return {
            "trading_stats": {
                "total_trades": len(trades),
                "closed_trades": len(closed_trades),
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "win_rate": len(winning_trades) / len(closed_trades) * 100 if closed_trades else 0,
                "total_pnl": total_pnl,
                "average_pnl": total_pnl / len(closed_trades) if closed_trades else 0,
                "best_trade": max([float(t.pnl or 0) for t in closed_trades], default=0),
                "worst_trade": min([float(t.pnl or 0) for t in closed_trades], default=0),
                "current_portfolio_value": portfolio_value,
                "total_value": portfolio_value + float(current_user.balance)
            },
            "tournament_stats": {
                "tournaments_entered": len(tournament_entries),
                "tournaments_won": tournaments_won,
                "tournaments_top3": tournaments_top3,
                "total_winnings": sum(float(getattr(e, 'prize_won', 0) or 0) for e in tournament_entries)
            },
            "account_info": {
                "username": current_user.username,
                "balance": float(current_user.balance),
                "member_since": current_user.created_at.isoformat() if hasattr(current_user, 'created_at') else None
            }
        }
        
    except Exception as e:
        logger.error(f"Failed: User stats error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user stats: {str(e)}")

@app.get("/trades/my")
def get_my_trades(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user's trade history with frontend-compatible format - FIXED"""
    try:
        trades = db.query(Trade).filter(
            Trade.user_id == current_user.id
        ).order_by(Trade.timestamp.desc()).limit(50).all()
        
        result = []
        for trade in trades:
            target = trade.target
            
            # Calculate outcome from PnL (since outcome field doesn't exist)
            pnl_value = float(trade.pnl) if trade.pnl else 0.0
            if trade.is_closed:
                if pnl_value > 0:
                    outcome = "profit"
                elif pnl_value < 0:
                    outcome = "loss"
                else:
                    outcome = "break_even"
            else:
                outcome = "open"
            
            result.append({
                "id": trade.id,
                "target_id": target.id,
                "target_name": target.name,
                "target_type": target.type.value,
                "trade_type": trade.trade_type.replace("stake_", ""),  # Convert "stake_buy" to "buy"
                "position_type": getattr(trade, 'position_type', 'long'),
                "stake_amount": float(trade.stake_amount),
                "attention_score_at_entry": float(trade.attention_score_at_entry),
                "timestamp": trade.timestamp.isoformat(),
                "outcome": outcome,  # Calculated instead of accessing nonexistent field
                "pnl": pnl_value,
                "is_closed": trade.is_closed
            })
        
        return {"trades": result}
        
    except Exception as e:
        logger.error(f"Failed: Get trades error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get trades: {str(e)}")

# Tournament endpoints
@app.get("/tournaments")
def get_tournaments(db: Session = Depends(get_db)):
    try:
        # FIX: Use is_active and is_finished fields that actually exist
        tournaments = db.query(Tournament).filter(
            Tournament.is_active == True,
            Tournament.is_finished == False
        ).all()
        
        result = []
        for tournament in tournaments:
            try:
                entry_count = db.query(TournamentEntry).filter(
                    TournamentEntry.tournament_id == tournament.id
                ).count()
                
                # Calculate status from dates with timezone handling
                now = datetime.now(timezone.utc)

                # Handle timezone-naive dates by assuming UTC
                start_date = tournament.start_date
                end_date = tournament.end_date

                if start_date and start_date.tzinfo is None:
                    start_date = start_date.replace(tzinfo=timezone.utc)
                if end_date and end_date.tzinfo is None:
                    end_date = end_date.replace(tzinfo=timezone.utc)

                if start_date and now < start_date:
                    status = "upcoming"
                elif end_date and now > end_date:
                    status = "finished"
                else:
                    status = "active"
                
                result.append({
                    "id": tournament.id,
                    "name": tournament.name,
                    "target_type": tournament.target_type.value,
                    "duration": tournament.duration.value,
                    "entry_fee": float(tournament.entry_fee),
                    "starting_balance": 10000.0,  # Standard starting balance for all tournaments
                    "current_participants": entry_count,
                    "prize_pool": float(tournament.prize_pool),
                    "start_date": tournament.start_date.isoformat(),
                    "end_date": tournament.end_date.isoformat(),
                    "status": status,  # Calculated, not from model
                    "is_active": tournament.is_active,
                    "is_finished": tournament.is_finished
                })
                
            except Exception as e:
                logger.error(f"Failed: Error processing tournament {tournament.id}: {e}")
                continue
        
        logger.info(f"List: Returning {len(result)} tournaments")
        return result
        
    except Exception as e:
        logger.error(f"Failed: Tournaments endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Tournament error: {str(e)}")

# Add tournament join endpoint
@app.post("/tournaments/join")
def join_tournament(
    entry_request: TournamentEntryRequest, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Join a tournament"""
    tournament = db.query(Tournament).filter(
        Tournament.id == entry_request.tournament_id,
        Tournament.is_active == True,
        Tournament.is_finished == False
    ).first()
    
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found or not active")
    
    # Check if user already joined
    existing_entry = db.query(TournamentEntry).filter(
        TournamentEntry.user_id == current_user.id,
        TournamentEntry.tournament_id == tournament.id
    ).first()
    
    if existing_entry:
        raise HTTPException(status_code=400, detail="Already joined this tournament")
    
    # Check if user has enough balance for entry fee
    if current_user.balance < tournament.entry_fee:
        raise HTTPException(
            status_code=400, 
            detail=f"Insufficient balance for entry fee: ${tournament.entry_fee}"
        )
    
    # Deduct entry fee (only if not free)
    if tournament.entry_fee > 0:
        current_user.balance -= tournament.entry_fee
        tournament.prize_pool += tournament.entry_fee * Decimal('0.9')  # 90% to prize pool
    
    # Create tournament entry
    entry = TournamentEntry(
        user_id=current_user.id,
        tournament_id=tournament.id,
        entry_fee=tournament.entry_fee,
        starting_balance=Decimal('10000.00')  # Everyone starts with same virtual balance
    )
    
    db.add(entry)
    tournament.participant_count += 1
    
    db.commit()
    
    logger.info(f"Tournament: {current_user.username} joined tournament: {tournament.name}")
    
    return {
        "message": f"Successfully joined {tournament.name}",
        "tournament_id": tournament.id,
        "entry_fee": float(tournament.entry_fee),
        "starting_balance": float(entry.starting_balance),
        "participants": tournament.participant_count
    }

@app.get("/tournaments/{tournament_id}")
def get_tournament_detail(tournament_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific tournament.

    Args:
        tournament_id: ID of the tournament to retrieve
        db: Database session

    Returns:
        Detailed tournament information including stats and metadata

    Raises:
        HTTPException: If tournament not found
    """
    tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()

    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    try:
        entry_count = db.query(TournamentEntry).filter(
            TournamentEntry.tournament_id == tournament.id
        ).count()

        # Calculate status from dates with timezone handling
        now = datetime.now(timezone.utc)

        # Handle timezone-naive dates by assuming UTC
        start_date = tournament.start_date
        end_date = tournament.end_date

        if start_date and start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date and end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)

        if start_date and now < start_date:
            status = "upcoming"
        elif end_date and now > end_date:
            status = "finished"
        else:
            status = "active"

        return {
            "id": tournament.id,
            "name": tournament.name,
            "target_type": tournament.target_type.value,
            "duration": tournament.duration.value,
            "entry_fee": float(tournament.entry_fee),
            "starting_balance": 10000.0,
            "current_participants": entry_count,
            "prize_pool": float(tournament.prize_pool),
            "start_date": tournament.start_date.isoformat(),
            "end_date": tournament.end_date.isoformat(),
            "status": status,
            "created_at": tournament.created_at.isoformat(),
            "max_participants": getattr(tournament, 'max_participants', None)
        }

    except Exception as e:
        logger.error(f"Error getting tournament detail: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get tournament details: {str(e)}")

@app.get("/tournaments/{tournament_id}/leaderboard")
def get_tournament_leaderboard(tournament_id: int, db: Session = Depends(get_db)):
    """
    Get the leaderboard for a specific tournament.

    Args:
        tournament_id: ID of the tournament
        db: Database session

    Returns:
        Ranked list of tournament participants with their current standings

    Raises:
        HTTPException: If tournament not found
    """
    tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()

    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    try:
        # Get all tournament entries with user information
        entries = db.query(TournamentEntry, User).join(
            User, TournamentEntry.user_id == User.id
        ).filter(
            TournamentEntry.tournament_id == tournament_id
        ).all()

        leaderboard = []
        for entry, user in entries:
            # Calculate current P&L: current_balance - starting_balance
            current_balance = float(entry.current_balance)
            starting_balance = float(entry.starting_balance)
            current_pnl = current_balance - starting_balance

            # Count trades for this user in this tournament
            trades_count = db.query(Trade).filter(
                Trade.user_id == user.id,
                Trade.tournament_id == tournament_id
            ).count()

            leaderboard.append({
                "user_id": user.id,
                "username": user.username,
                "current_balance": current_balance,
                "pnl": current_pnl,
                "trades_count": trades_count,
                "entry_date": entry.created_at.isoformat() if entry.created_at else None
            })

        # Sort by current balance (highest first) and assign ranks
        leaderboard.sort(key=lambda x: x["current_balance"], reverse=True)

        for i, entry in enumerate(leaderboard):
            entry["rank"] = i + 1

        logger.info(f"Tournament leaderboard: Retrieved {len(leaderboard)} entries for tournament {tournament_id}")
        return leaderboard

    except Exception as e:
        logger.error(f"Error getting tournament leaderboard: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get tournament leaderboard: {str(e)}")

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
async def cleanup_database(_current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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
async def force_update_target(target_id: int, _current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Force update a specific target with fresh Google Trends data"""
    target = db.query(AttentionTarget).filter(AttentionTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    try:
        async with GoogleTrendsService(websocket_manager=manager, use_tor=USE_TOR) as service:
            success = await service.update_target_data(target, db)
        
        if success:
            # Send real-time update to connected clients
            await manager.send_target_update(target_id, {
                "type": "forced_update",
                "target_id": target_id,
                "attention_score": float(target.current_attention_score),
                "timestamp": datetime.now(timezone.utc).isoformat()
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
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}

@app.get("/service-status")
def get_service_status():
    """Get status of various services"""
    return {
        "api": {"status": "healthy", "version": "2.0.0"},
        "database": {"status": "connected"},
        "google_trends": {"status": "running", "service": "GoogleTrendsService"},
        "timestamp": datetime.now(timezone.utc).isoformat()
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
                "timestamp": datetime.now(timezone.utc).isoformat()
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
                "timestamp": datetime.now(timezone.utc).isoformat()
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
        asyncio.create_task(start_background_updates(websocket_manager=manager, use_tor=USE_TOR))
        logger.info("Successfully Background data updates started with WebSocket support")
        
    except ImportError as e:
        logger.error(f"Failed: Failed to import background_updater: {e}")
        # Fallback to service method with WebSocket manager
        try:
            from google_trends_service import run_background_updates
            asyncio.create_task(run_background_updates(websocket_manager=manager, use_tor=USE_TOR))
            logger.info("Successfully Fallback background data updates started with WebSocket support")
        except ImportError:
            logger.error("Failed: No background update system available")

@app.on_event("startup")
async def startup_event():
    """Initialize the application with real-time capabilities"""
    logger.info("Starting: TrendBet API starting up...")
    if USE_TOR:
        logger.info("Tor proxy enabled for Google Trends requests")
    else:
        logger.info("Direct connections enabled for Google Trends requests")
    
    # Start background tasks for real-time updates
    await start_background_tasks()
    
    logger.info("Successfully TrendBet API ready!")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Stopping: TrendBet API shutting down...")
    
    # Close all WebSocket connections
    for connection in manager.active_connections:
        try:
            await connection.close()
        except:
            pass
    
    logger.info("Successfully TrendBet API shutdown complete!")

# Chat endpoints
@app.get("/chat/messages")
async def get_chat_messages(
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recent chat messages for the global chat."""
    messages = db.query(ChatMessage).order_by(ChatMessage.timestamp.desc()).limit(limit).all()
    messages.reverse()  # Reverse to show oldest first

    return {
        "messages": [
            {
                "id": msg.id,
                "username": msg.user.username,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "user_id": msg.user_id
            }
            for msg in messages
        ]
    }

@app.post("/chat/send")
async def send_chat_message(
    message: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message to the global chat."""
    # Create new chat message
    new_message = ChatMessage(
        user_id=current_user.id,
        content=message.content.strip()
    )

    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    # Broadcast message to all connected chat WebSocket clients
    message_data = {
        "type": "chat_message",
        "message": {
            "id": new_message.id,
            "username": current_user.username,
            "content": new_message.content,
            "timestamp": new_message.timestamp.isoformat(),
            "user_id": current_user.id
        }
    }

    await manager.broadcast_to_chat(message_data)

    return {"status": "success", "message": "Message sent"}

# WebSocket endpoint for chat
@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat functionality."""
    await manager.connect_chat(websocket)

    try:
        while True:
            # Keep connection alive, actual messaging is handled via REST API
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_chat(websocket)