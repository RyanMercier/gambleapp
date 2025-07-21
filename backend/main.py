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
from typing import Dict, List

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

@app.get("/")
def root():
    return {"message": "Gamble Royale Backend API v1.0"}

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
        "username": user_obj.username
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
        "username": user_obj.username
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

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "gamble-royale-backend"}
