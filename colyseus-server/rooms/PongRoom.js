// PongRoom.js - Pong game implementation using the base framework
const { BaseGameRoom, BasePlayer, BaseGameState } = require("./BaseGameRoom");
const { Schema, MapSchema } = require("@colyseus/schema");

console.log("BaseGameRoom import:", typeof BaseGameRoom);
console.log("BasePlayer import:", typeof BasePlayer);
console.log("BaseGameState import:", typeof BaseGameState);

class PongPlayer extends BasePlayer {
  constructor() {
    super();
    this.paddleY = 300;
    this.paddleHeight = 80;
    this.paddleSpeed = 8;
    this.side = "left"; // "left" or "right"
  }
}
PongPlayer.schema = {
  ...BasePlayer.schema,
  paddleY: "number",
  paddleHeight: "number",
  paddleSpeed: "number",
  side: "string"
};

class Ball extends Schema {
  constructor() {
    super();
    this.x = 400;
    this.y = 300;
    this.velocityX = 0;
    this.velocityY = 0;
    this.speed = 5;
    this.radius = 8;
  }
}
Ball.schema = {
  x: "number",
  y: "number",
  velocityX: "number",
  velocityY: "number",
  speed: "number",
  radius: "number"
};

class PongGameState extends BaseGameState {
  constructor() {
    super();
    this.ball = new Ball();
    this.gameWidth = 800;
    this.gameHeight = 600;
    this.scoreLimit = 5;
  }
}
PongGameState.schema = {
  ...BaseGameState.schema,
  ball: Ball,
  gameWidth: "number",
  gameHeight: "number",
  scoreLimit: "number"
};

class PongRoom extends BaseGameRoom {
  constructor() {
    super();
    this.minPlayers = 2;
    this.maxClients = 2; // Pong is exactly 2 players
    this.gameUpdateInterval = null;
    this.ballResetTimer = null;
  }

  onCreate(options) {
    console.log("PongRoom onCreate called with options:", options);
    
    this.setState(new PongGameState());
    
    // Add players from lobby if provided
    if (options.players) {
      this.pendingPlayers = options.players;
      console.log("Pending players set:", this.pendingPlayers);
    }
    
    this.setupMessageHandlers();
    this.initializeGame();
    
    console.log("PongRoom created successfully with room ID:", this.roomId);
  }

  initializeGame() {
    console.log("Initializing Pong Game");
    
    // Handle paddle movement
    this.onMessage("paddle_move", (client, data) => {
      const player = this.state.players.get(client.sessionId);
      if (player && player.alive && this.state.gameStarted) {
        // Clamp paddle position to game bounds
        const minY = player.paddleHeight / 2;
        const maxY = this.state.gameHeight - player.paddleHeight / 2;
        player.paddleY = Math.max(minY, Math.min(maxY, data.paddleY));
      }
    });
    
    // Handle ready state
    this.onMessage("ready", (client) => {
      const player = this.state.players.get(client.sessionId);
      if (player && this.state.gamePhase === "waiting") {
        player.ready = !player.ready;
        this.checkReadyState();
      }
    });
  }

  createPlayer() {
    return new PongPlayer();
  }

  onJoin(client, options) {
    super.onJoin(client, options);
    
    const player = this.state.players.get(client.sessionId);
    if (player) {
      // Assign sides based on join order
      const playerCount = this.state.players.size;
      player.side = playerCount === 1 ? "left" : "right";
      player.x = player.side === "left" ? 50 : this.state.gameWidth - 50;
      player.paddleY = this.state.gameHeight / 2;
      
      client.send("game_info", {
        message: `Welcome to Pong! You are the ${player.side} player.`,
        gameRules: [
          "Use W/S keys or mouse to move your paddle",
          "Hit the ball to send it to your opponent", 
          "First to 5 points wins!",
          "Don't let the ball get past your paddle!"
        ],
        side: player.side,
        minPlayers: this.minPlayers,
        maxPlayers: this.maxClients
      });
    }
  }

  resetPlayerPosition(player) {
    player.paddleY = this.state.gameHeight / 2;
    player.x = player.side === "left" ? 50 : this.state.gameWidth - 50;
  }

  onGameStart() {
    console.log("Pong game started");
    
    // Reset ball to center
    this.resetBall();
    
    // Start game physics updates at 60fps
    this.gameUpdateInterval = setInterval(() => {
      this.updateGamePhysics();
    }, 1000 / 60);
  }
  
  resetBall() {
    this.state.ball.x = this.state.gameWidth / 2;
    this.state.ball.y = this.state.gameHeight / 2;
    
    // Random direction
    const angle = (Math.random() - 0.5) * Math.PI / 3; // ±30 degrees
    const direction = Math.random() < 0.5 ? 1 : -1;
    
    this.state.ball.velocityX = Math.cos(angle) * this.state.ball.speed * direction;
    this.state.ball.velocityY = Math.sin(angle) * this.state.ball.speed;
  }
  
  updateGamePhysics() {
    if (!this.state.gameStarted) return;
    
    const ball = this.state.ball;
    
    // Update ball position
    ball.x += ball.velocityX;
    ball.y += ball.velocityY;
    
    // Ball collision with top/bottom walls
    if (ball.y <= ball.radius || ball.y >= this.state.gameHeight - ball.radius) {
      ball.velocityY = -ball.velocityY;
      ball.y = Math.max(ball.radius, Math.min(this.state.gameHeight - ball.radius, ball.y));
    }
    
    // Ball collision with paddles
    this.checkPaddleCollisions();
    
    // Check for scoring
    if (ball.x <= 0) {
      this.playerScored("right");
    } else if (ball.x >= this.state.gameWidth) {
      this.playerScored("left");
    }
  }
  
  checkPaddleCollisions() {
    const ball = this.state.ball;
    
    this.state.players.forEach((player) => {
      if (!player.alive) return;
      
      const paddleLeft = player.x - 10;
      const paddleRight = player.x + 10;
      const paddleTop = player.paddleY - player.paddleHeight / 2;
      const paddleBottom = player.paddleY + player.paddleHeight / 2;
      
      // Check collision
      if (ball.x + ball.radius >= paddleLeft && 
          ball.x - ball.radius <= paddleRight &&
          ball.y + ball.radius >= paddleTop && 
          ball.y - ball.radius <= paddleBottom) {
        
        // Calculate hit position relative to paddle center (-1 to 1)
        const hitPos = (ball.y - player.paddleY) / (player.paddleHeight / 2);
        
        // Reverse X direction and add angle based on hit position
        ball.velocityX = -ball.velocityX;
        ball.velocityY = hitPos * ball.speed * 0.75;
        
        // Increase ball speed slightly
        const speedMultiplier = 1.05;
        ball.velocityX *= speedMultiplier;
        ball.velocityY *= speedMultiplier;
        
        // Clamp max speed
        const maxSpeed = ball.speed * 2;
        const currentSpeed = Math.sqrt(ball.velocityX * ball.velocityX + ball.velocityY * ball.velocityY);
        if (currentSpeed > maxSpeed) {
          ball.velocityX = (ball.velocityX / currentSpeed) * maxSpeed;
          ball.velocityY = (ball.velocityY / currentSpeed) * maxSpeed;
        }
        
        // Move ball out of paddle to prevent double hits
        if (player.side === "left") {
          ball.x = paddleRight + ball.radius;
        } else {
          ball.x = paddleLeft - ball.radius;
        }
        
        this.broadcast("paddle_hit", { 
          player: player.username,
          side: player.side,
          hitPosition: hitPos
        });
      }
    });
  }
  
  playerScored(scoringSide) {
    // Find the scoring player
    const scoringPlayer = Array.from(this.state.players.values())
      .find(p => p.side === scoringSide);
    
    if (scoringPlayer) {
      scoringPlayer.score++;
      
      this.broadcast("player_scored", {
        player: scoringPlayer.username,
        side: scoringSide,
        score: scoringPlayer.score
      });
      
      // Check for game end
      if (scoringPlayer.score >= this.state.scoreLimit) {
        this.endGame(scoringPlayer);
        return;
      }
    }
    
    // Reset ball after a short delay
    if (this.ballResetTimer) {
      clearTimeout(this.ballResetTimer);
    }
    
    this.ballResetTimer = setTimeout(() => {
      this.resetBall();
    }, 1500);
  }

  onGameEnd(winner) {
    console.log("Pong game ended");
    
    // Clean up intervals
    if (this.gameUpdateInterval) {
      clearInterval(this.gameUpdateInterval);
      this.gameUpdateInterval = null;
    }
    
    if (this.ballResetTimer) {
      clearTimeout(this.ballResetTimer);
      this.ballResetTimer = null;
    }
  }

  onGameReset() {
    console.log("Pong game reset");
    
    // Reset scores
    this.state.players.forEach(player => {
      player.score = 0;
    });
    
    // Reset ball
    this.state.ball.x = this.state.gameWidth / 2;
    this.state.ball.y = this.state.gameHeight / 2;
    this.state.ball.velocityX = 0;
    this.state.ball.velocityY = 0;
    
    if (this.gameUpdateInterval) {
      clearInterval(this.gameUpdateInterval);
      this.gameUpdateInterval = null;
    }
    
    if (this.ballResetTimer) {
      clearTimeout(this.ballResetTimer);
      this.ballResetTimer = null;
    }
  }

  onDispose() {
    if (this.gameUpdateInterval) {
      clearInterval(this.gameUpdateInterval);
    }
    
    if (this.ballResetTimer) {
      clearTimeout(this.ballResetTimer);
    }
    
    super.onDispose();
  }
}

module.exports = PongRoom;