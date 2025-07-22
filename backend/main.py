from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import SessionLocal, engine
from models import Base, User
from auth import (
    create_user, 
    authenticate_user, 
    create_access_token, 
    decode_access_token
)
import json
from typing import Dict, List, Optional

# Create tables
Base.metadata.create_all(bind=engine)

# FastAPI app setup
app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 config
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# Chat system - organized by rooms
chat_rooms: Dict[str, List[WebSocket]] = {}

@app.websocket("/ws/chat/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()
    
    # Add to room
    if room_id not in chat_rooms:
        chat_rooms[room_id] = []
    chat_rooms[room_id].append(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Broadcast to all clients in the same room
            for client in chat_rooms[room_id]:
                try:
                    await client.send_text(json.dumps(message))
                except:
                    # Remove broken connections
                    if client in chat_rooms[room_id]:
                        chat_rooms[room_id].remove(client)
                        
    except WebSocketDisconnect:
        if websocket in chat_rooms[room_id]:
            chat_rooms[room_id].remove(websocket)
        
        # Clean up empty rooms
        if len(chat_rooms[room_id]) == 0:
            del chat_rooms[room_id]

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Request models
class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class StatsUpdateRequest(BaseModel):
    user_id: int
    wins: int = 0
    losses: int = 0
    profit: float = 0.0

@app.get("/")
def root():
    return {"message": "Gamble Royale Backend API v2.0 - Enhanced Edition"}

@app.post("/register")
def register(user: RegisterRequest, db: Session = Depends(get_db)):
    # Check if user exists
    existing_user = db.query(User).filter(
        (User.username == user.username) | (User.email == user.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists"
        )
    
    user_obj = create_user(db, user.username, user.email, user.password)
    token = create_access_token(data={"sub": user_obj.username})
    
    return {
        "token": token,
        "id": user_obj.id, 
        "username": user_obj.username,
        "wins": user_obj.wins,
        "losses": user_obj.losses,
        "profit": float(user_obj.profit)
    }

@app.post("/login")
def login(user: LoginRequest, db: Session = Depends(get_db)):
    user_obj = authenticate_user(db, user.username, user.password)
    if not user_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid credentials"
        )

    token = create_access_token(data={"sub": user_obj.username})
    return {
        "token": token, 
        "id": user_obj.id, 
        "username": user_obj.username,
        "wins": user_obj.wins,
        "losses": user_obj.losses,
        "profit": float(user_obj.profit)
    }

# Get current authenticated user from token
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
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

@app.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id, 
        "username": current_user.username,
        "wins": current_user.wins,
        "losses": current_user.losses,
        "profit": float(current_user.profit)
    }

@app.post("/update-stats")
def update_player_stats(
    stats_update: StatsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update player statistics after a game"""
    try:
        # Verify the user is updating their own stats or has permission
        target_user = db.query(User).filter(User.id == stats_update.user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # For now, allow users to update their own stats
        # In production, this should be called by the game server with proper auth
        if target_user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update other user's stats"
            )
        
        # Update statistics
        target_user.wins += stats_update.wins
        target_user.losses += stats_update.losses
        target_user.profit += stats_update.profit
        
        db.commit()
        db.refresh(target_user)
        
        return {
            "success": True,
            "message": "Stats updated successfully",
            "updated_stats": {
                "wins": target_user.wins,
                "losses": target_user.losses,
                "profit": float(target_user.profit)
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update stats: {str(e)}"
        )

@app.post("/game-result")
def record_game_result(
    user_id: int,
    game_type: str,
    won: bool,
    score: float = 0.0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Record the result of a game for a specific user"""
    try:
        target_user = db.query(User).filter(User.id == user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update wins/losses
        if won:
            target_user.wins += 1
            # Winner bonus
            profit_change = score + 100  # Base win bonus
        else:
            target_user.losses += 1
            profit_change = score  # Points earned even in loss
        
        target_user.profit += profit_change
        
        db.commit()
        db.refresh(target_user)
        
        return {
            "success": True,
            "message": f"Game result recorded - {'Win' if won else 'Loss'}",
            "profit_change": profit_change,
            "new_stats": {
                "wins": target_user.wins,
                "losses": target_user.losses,
                "profit": float(target_user.profit),
                "win_rate": round((target_user.wins / max(target_user.wins + target_user.losses, 1)) * 100, 1)
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record game result: {str(e)}"
        )

@app.get("/leaderboard")
def get_leaderboard(db: Session = Depends(get_db), limit: int = 10):
    """Get the top players leaderboard"""
    try:
        # Get top players by wins, then by profit
        top_players = db.query(User).order_by(
            User.wins.desc(), 
            User.profit.desc()
        ).limit(limit).all()
        
        leaderboard = []
        for i, player in enumerate(top_players):
            total_games = player.wins + player.losses
            win_rate = (player.wins / total_games * 100) if total_games > 0 else 0
            
            leaderboard.append({
                "rank": i + 1,
                "username": player.username,
                "wins": player.wins,
                "losses": player.losses,
                "win_rate": round(win_rate, 1),
                "profit": float(player.profit),
                "total_games": total_games
            })
        
        return {
            "leaderboard": leaderboard,
            "total_players": db.query(User).count()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get leaderboard: {str(e)}"
        )

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "gamble-royale-backend", "version": "2.0"}

@app.get("/stats/summary")
def get_stats_summary(db: Session = Depends(get_db)):
    """Get overall platform statistics"""
    try:
        total_users = db.query(User).count()
        total_games = db.query(User.wins + User.losses).scalar() or 0
        top_player = db.query(User).order_by(User.wins.desc()).first()
        
        return {
            "total_users": total_users,
            "total_games_played": total_games,
            "top_player": {
                "username": top_player.username if top_player else None,
                "wins": top_player.wins if top_player else 0
            } if top_player else None,
            "platform_stats": {
                "active": True,
                "version": "2.0",
                "features": ["balance_game", "real_time_multiplayer", "statistics"]
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get platform stats: {str(e)}"
        )