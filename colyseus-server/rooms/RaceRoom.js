// RaceRoom.js - Example of another game using the base framework
const { BaseGameRoom, BasePlayer, BaseGameState } = require("./BaseGameRoom");

class RacePlayer extends BasePlayer {
  constructor() {
    super();
    this.x = 100;
    this.y = 300;
    this.speed = 5;
    this.checkpoint = 0;
    this.finished = false;
  }
}
RacePlayer.schema = {
  ...BasePlayer.schema,
  speed: "number",
  checkpoint: "number",
  finished: "boolean"
};

class RaceGameState extends BaseGameState {
  constructor() {
    super();
    this.raceProgress = 0;
    this.finishLine = 1400;
  }
}
RaceGameState.schema = {
  ...BaseGameState.schema,
  raceProgress: "number",
  finishLine: "number"
};

class RaceRoom extends BaseGameRoom {
  constructor() {
    super();
    this.roomName = "Race Game";
    this.minPlayers = 2;
    this.maxClients = 6;
    this.obstacles = [];
    this.obstacleSpawnTimer = null;
  }

  onCreate() {
    this.setState(new RaceGameState());
    this.setupMessageHandlers();
    this.initializeGame();
  }

  initializeGame() {
    // Race-specific initialization
    this.obstacles = [];
    
    // Handle player input for racing
    this.onMessage("move", (client, data) => {
      if (this.state.gameStarted) {
        this.handlePlayerMove(client, data);
      }
    });

    this.onMessage("checkpoint", (client, data) => {
      const player = this.state.players.get(client.sessionId);
      if (player && this.state.gameStarted) {
        player.checkpoint = data.checkpoint;
        this.checkForWinner();
      }
    });
  }

  createPlayer() {
    return new RacePlayer();
  }

  getWelcomeMessage() {
    return "Welcome to Race Game! Navigate through obstacles to reach the finish line first!";
  }

  getGameRules() {
    return [
      "Use arrow keys to move your racer",
      "Avoid obstacles that slow you down",
      "First to reach the finish line wins!",
      "Collect power-ups for speed boosts"
    ];
  }

  resetPlayerPosition(player) {
    player.x = 100;
    player.y = 300;
    player.checkpoint = 0;
    player.finished = false;
    player.speed = 5;
  }

  handlePlayerMove(client, data) {
    const player = this.state.players.get(client.sessionId);
    if (player && player.alive && !player.finished) {
      // Apply movement with bounds checking
      const newX = Math.max(0, Math.min(this.state.finishLine, player.x + data.deltaX * player.speed));
      const newY = Math.max(50, Math.min(550, player.y + data.deltaY * player.speed));
      
      player.x = newX;
      player.y = newY;
      
      // Check if player reached finish line
      if (player.x >= this.state.finishLine && !player.finished) {
        player.finished = true;
        this.checkForWinner();
      }
    }
  }

  checkForWinner() {
    const finishedPlayers = Array.from(this.state.players.values()).filter(p => p.finished);
    if (finishedPlayers.length > 0) {
      // First finished player wins
      this.endGame(finishedPlayers[0]);
    }
  }

  checkGameEnd() {
    // Override to use race-specific win conditions
    this.checkForWinner();
  }

  onGameStart() {
    // Spawn obstacles periodically
    this.obstacleSpawnTimer = setInterval(() => {
      this.spawnObstacle();
    }, 3000);
  }

  spawnObstacle() {
    const obstacle = {
      id: `obstacle_${Date.now()}`,
      x: Math.random() * 1200 + 200,
      y: Math.random() * 400 + 100,
      type: "rock"
    };
    this.obstacles.push(obstacle);
    this.broadcast("spawn_obstacle", obstacle);
  }

  gameUpdate() {
    // Update race progress based on leading player
    const players = Array.from(this.state.players.values());
    if (players.length > 0) {
      const leadingPlayer = players.reduce((prev, current) => 
        (prev.x > current.x) ? prev : current
      );
      this.state.raceProgress = (leadingPlayer.x / this.state.finishLine) * 100;
    }
  }

  onGameEnd(winner) {
    if (this.obstacleSpawnTimer) {
      clearInterval(this.obstacleSpawnTimer);
      this.obstacleSpawnTimer = null;
    }
  }

  onGameReset() {
    this.obstacles = [];
    this.state.raceProgress = 0;
    if (this.obstacleSpawnTimer) {
      clearInterval(this.obstacleSpawnTimer);
      this.obstacleSpawnTimer = null;
    }
  }

  onGameDispose() {
    if (this.obstacleSpawnTimer) {
      clearInterval(this.obstacleSpawnTimer);
    }
  }
}

module.exports = RaceRoom;