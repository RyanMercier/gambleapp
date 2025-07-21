const { BaseGameRoom, BasePlayer, BaseGameState } = require("./BaseGameRoom");
const { Schema, MapSchema } = require("@colyseus/schema");

class BalancePlayer extends BasePlayer {
  constructor() {
    super();
    this.x = 400;
    this.y = 500;
    this.stickAngle = 0;
    this.velocityX = 0;
    this.velocityY = 0;
  }
}
BalancePlayer.schema = {
  ...BasePlayer.schema,
  stickAngle: "number",
  velocityX: "number",
  velocityY: "number"
};

class Plate extends Schema {
  constructor() {
    super();
    this.id = "";
    this.x = 0;
    this.y = 0;
    this.velocityY = 0;
    this.rotation = 0;
    this.size = 60;
    this.active = true;
  }
}
Plate.schema = {
  id: "string",
  x: "number",
  y: "number",
  velocityY: "number",
  rotation: "number",
  size: "number",
  active: "boolean"
};

class BalanceGameState extends BaseGameState {
  constructor() {
    super();
    this.plates = new MapSchema();
    this.plateCount = 0;
  }
}
BalanceGameState.schema = {
  ...BaseGameState.schema,
  plates: { map: Plate },
  plateCount: "number"
};

class BalanceRoom extends BaseGameRoom {
  constructor() {
    super();
    this.minPlayers = 2;
    this.maxClients = 8;
    this.plateSpawnInterval = null;
    this.gameUpdateInterval = null;
  }

  onCreate(options) {
    this.setState(new BalanceGameState());
    
    // Add players from lobby if provided
    if (options.players) {
      this.pendingPlayers = options.players;
    }
    
    this.setupMessageHandlers();
    this.initializeGame();
  }

  initializeGame() {
    console.log("Initializing Balance Game");
    
    // Handle player position updates
    this.onMessage("player_update", (client, data) => {
      const player = this.state.players.get(client.sessionId);
      if (player && player.alive && this.state.gameStarted) {
        player.x = Math.max(50, Math.min(750, data.x));
        player.y = Math.max(450, Math.min(550, data.y));
        player.stickAngle = data.angle || 0;
        player.velocityX = data.velocityX || 0;
        player.velocityY = data.velocityY || 0;
      }
    });
    
    // Handle death messages
    this.onMessage("player_died", (client) => {
      const player = this.state.players.get(client.sessionId);
      if (player && this.state.gameStarted && player.alive) {
        player.alive = false;
        console.log(`Player ${player.username} died`);
        this.broadcast("player_died", { username: player.username });
        this.checkGameEnd();
      }
    });
  }

  createPlayer() {
    return new BalancePlayer();
  }

  onJoin(client, options) {
    super.onJoin(client, options);
    
    const player = this.state.players.get(client.sessionId);
    if (player) {
      client.send("game_info", {
        message: "Welcome to Balance Game! Keep your stick balanced while avoiding falling plates.",
        gameRules: [
          "Move your mouse to control the balance stick",
          "Avoid letting plates fall on you", 
          "Don't let your stick fall off the screen",
          "Last player standing wins!"
        ],
        minPlayers: this.minPlayers,
        maxPlayers: this.maxClients
      });
    }
  }

  resetPlayerPosition(player) {
    // Spread players out initially
    const players = Array.from(this.state.players.values());
    const playerIndex = players.indexOf(player);
    const spacing = 600 / Math.max(players.length, 1);
    
    player.x = 100 + (playerIndex * spacing);
    player.y = 500;
    player.stickAngle = 0;
    player.velocityX = 0;
    player.velocityY = 0;
  }

  onGameStart() {
    console.log("Balance game started - spawning plates");
    
    // Start spawning plates every 2-4 seconds
    this.plateSpawnInterval = setInterval(() => {
      this.spawnPlate();
    }, 2000 + Math.random() * 2000);
    
    // Start game physics updates at 30fps
    this.gameUpdateInterval = setInterval(() => {
      this.updateGamePhysics();
    }, 1000 / 30);
  }
  
  spawnPlate() {
    if (!this.state.gameStarted) return;
    
    const plateId = `plate_${this.state.plateCount++}`;
    const x = Math.floor(Math.random() * 700) + 50;
    
    const plate = new Plate();
    plate.id = plateId;
    plate.x = x;
    plate.y = -50;
    plate.velocityY = 2 + Math.random() * 2;
    plate.size = 50 + Math.random() * 30;
    plate.rotation = Math.random() * Math.PI * 2;
    
    this.state.plates.set(plateId, plate);
    
    console.log(`Spawned plate ${plateId} at x: ${x}`);
  }
  
  updateGamePhysics() {
    if (!this.state.gameStarted) return;
    
    // Update plate physics
    const platesToRemove = [];
    
    this.state.plates.forEach((plate, plateId) => {
      if (!plate.active) return;
      
      // Apply gravity and movement
      plate.velocityY += 0.2; // Gravity
      plate.y += plate.velocityY;
      plate.rotation += 0.05;
      
      // Remove plates that fell off screen
      if (plate.y > 650) {
        platesToRemove.push(plateId);
      }
    });
    
    // Clean up fallen plates
    platesToRemove.forEach(plateId => {
      this.state.plates.delete(plateId);
    });
    
    // Check collisions
    this.checkCollisions();
  }
  
  checkCollisions() {
    this.state.players.forEach((player, sessionId) => {
      if (!player.alive) return;
      
      // Check plate collisions
      this.state.plates.forEach((plate, plateId) => {
        if (!plate.active) return;
        
        const dx = player.x - plate.x;
        const dy = player.y - plate.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        // Simple collision detection
        if (distance < (plate.size / 2 + 15)) {
          console.log(`Player ${player.username} hit by plate ${plateId}`);
          player.alive = false;
          plate.active = false;
          
          this.broadcast("player_hit", { 
            playerId: sessionId,
            playerName: player.username,
            plateId: plateId 
          });
          
          this.checkGameEnd();
        }
      });
      
      // Check if player fell off screen
      if (player.y > 600 || player.x < 0 || player.x > 800) {
        console.log(`Player ${player.username} fell off screen`);
        player.alive = false;
        this.broadcast("player_fell", { 
          playerId: sessionId,
          playerName: player.username 
        });
        this.checkGameEnd();
      }
    });
  }

  onGameEnd(winner) {
    console.log("Balance game ended");
    
    // Clean up intervals
    if (this.plateSpawnInterval) {
      clearInterval(this.plateSpawnInterval);
      this.plateSpawnInterval = null;
    }
    
    if (this.gameUpdateInterval) {
      clearInterval(this.gameUpdateInterval);
      this.gameUpdateInterval = null;
    }
    
    // Clear plates
    this.state.plates.clear();
  }

  onGameReset() {
    console.log("Balance game reset");
    
    this.state.plateCount = 0;
    this.state.plates.clear();
    
    if (this.plateSpawnInterval) {
      clearInterval(this.plateSpawnInterval);
      this.plateSpawnInterval = null;
    }
    
    if (this.gameUpdateInterval) {
      clearInterval(this.gameUpdateInterval);
      this.gameUpdateInterval = null;
    }
  }

  onDispose() {
    if (this.plateSpawnInterval) {
      clearInterval(this.plateSpawnInterval);
    }
    
    if (this.gameUpdateInterval) {
      clearInterval(this.gameUpdateInterval);
    }
    
    super.onDispose();
  }
}

module.exports = BalanceRoom;