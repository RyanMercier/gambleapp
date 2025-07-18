// BaseGameRoom.js - Framework for all multiplayer games
const { Room } = require("colyseus");
const { Schema, MapSchema } = require("@colyseus/schema");

class BasePlayer extends Schema {
  constructor() {
    super();
    this.x = 400;
    this.y = 300;
    this.alive = true;
    this.ready = false;
    this.score = 0;
  }
}
BasePlayer.schema = {
  x: "number",
  y: "number",
  alive: "boolean",
  ready: "boolean",
  score: "number"
};

class BaseGameState extends Schema {
  constructor() {
    super();
    this.players = new MapSchema();
    this.gameStarted = false;
    this.gamePhase = "waiting"; // waiting, ready, playing, finished
    this.winner = null;
    this.gameTimer = 0;
  }
}
BaseGameState.schema = {
  players: { map: BasePlayer },
  gameStarted: "boolean",
  gamePhase: "string",
  winner: "string",
  gameTimer: "number"
};

class BaseGameRoom extends Room {
  constructor() {
    super();
    this.maxClients = 8;
    this.minPlayers = 2;
    this.gameStartTimer = null;
    this.gameInterval = null;
  }

  onCreate() {
    this.setState(new BaseGameState());
    this.setupMessageHandlers();
    this.initializeGame();
  }

  setupMessageHandlers() {
    this.onMessage("ready", (client) => {
      const player = this.state.players.get(client.sessionId);
      if (player && this.state.gamePhase === "waiting") {
        player.ready = !player.ready;
        this.checkReadyState();
      }
    });

    this.onMessage("update", (client, data) => {
      if (this.state.gameStarted) {
        this.handlePlayerUpdate(client, data);
      }
    });

    this.onMessage("restart", (client) => {
      if (this.state.gamePhase === "finished") {
        this.resetGame();
      }
    });
  }

  onJoin(client) {
    const player = this.createPlayer();
    this.state.players.set(client.sessionId, player);
    console.log(`Player ${client.sessionId} joined ${this.roomName}. Total: ${this.state.players.size}`);
    
    client.send("game_info", {
      message: this.getWelcomeMessage(),
      minPlayers: this.minPlayers,
      gameRules: this.getGameRules()
    });

    this.onPlayerJoin(client, player);
  }

  onLeave(client) {
    this.state.players.delete(client.sessionId);
    console.log(`Player ${client.sessionId} left ${this.roomName}. Total: ${this.state.players.size}`);
    
    if (this.state.gameStarted) {
      this.checkGameEnd();
    }
    
    if (this.state.players.size < this.minPlayers && this.state.gamePhase !== "waiting") {
      this.resetGame();
    }

    this.onPlayerLeave(client);
  }

  checkReadyState() {
    const playerCount = this.state.players.size;
    const readyCount = Array.from(this.state.players.values()).filter(p => p.ready).length;
    
    if (playerCount >= this.minPlayers && readyCount === playerCount) {
      this.startGameCountdown();
    } else if (this.state.gamePhase === "ready") {
      this.cancelGameStart();
    }
  }

  startGameCountdown() {
    this.state.gamePhase = "ready";
    this.broadcast("game_countdown", { countdown: 3 });
    
    let countdown = 3;
    this.gameStartTimer = setInterval(() => {
      countdown--;
      if (countdown > 0) {
        this.broadcast("game_countdown", { countdown });
      } else {
        this.startGame();
      }
    }, 1000);
  }

  cancelGameStart() {
    if (this.gameStartTimer) {
      clearInterval(this.gameStartTimer);
      this.gameStartTimer = null;
    }
    this.state.gamePhase = "waiting";
    this.broadcast("game_cancelled", { message: "Game start cancelled - not all players ready" });
  }

  startGame() {
    if (this.gameStartTimer) {
      clearInterval(this.gameStartTimer);
      this.gameStartTimer = null;
    }
    
    this.state.gameStarted = true;
    this.state.gamePhase = "playing";
    this.state.gameTimer = 0;
    
    this.resetPlayersForNewGame();
    this.broadcast("game_started", { message: "Game started!" });
    
    // Start game loop
    this.gameInterval = setInterval(() => {
      this.state.gameTimer++;
      this.gameUpdate();
    }, 1000 / 60); // 60 FPS
    
    this.onGameStart();
  }

  resetPlayersForNewGame() {
    this.state.players.forEach(player => {
      player.alive = true;
      this.resetPlayerPosition(player);
    });
  }

  resetPlayerPosition(player) {
    player.x = 400;
    player.y = 300;
  }

  checkGameEnd() {
    const alivePlayers = Array.from(this.state.players.values()).filter(p => p.alive);
    
    if (alivePlayers.length <= 1) {
      this.endGame(alivePlayers[0]);
    }
  }

  endGame(winner = null) {
    this.state.gameStarted = false;
    this.state.gamePhase = "finished";
    
    if (this.gameInterval) {
      clearInterval(this.gameInterval);
      this.gameInterval = null;
    }
    
    if (winner) {
      this.state.winner = winner;
      winner.score++;
      this.broadcast("game_ended", { 
        winner: true, 
        message: `Game Over! Winner decided!`,
        winnerScore: winner.score
      });
    } else {
      this.broadcast("game_ended", { 
        winner: false, 
        message: "Game Over! No winner." 
      });
    }
    
    this.onGameEnd(winner);
    
    // Auto-reset after 10 seconds
    setTimeout(() => {
      this.resetGame();
    }, 10000);
  }

  resetGame() {
    this.state.gameStarted = false;
    this.state.gamePhase = "waiting";
    this.state.winner = null;
    this.state.gameTimer = 0;
    
    this.state.players.forEach(player => {
      player.ready = false;
      player.alive = true;
      this.resetPlayerPosition(player);
    });
    
    if (this.gameInterval) {
      clearInterval(this.gameInterval);
      this.gameInterval = null;
    }
    
    if (this.gameStartTimer) {
      clearInterval(this.gameStartTimer);
      this.gameStartTimer = null;
    }
    
    this.broadcast("game_reset", { message: "Game reset! Get ready for the next round." });
    this.onGameReset();
  }

  onDispose() {
    if (this.gameInterval) {
      clearInterval(this.gameInterval);
    }
    if (this.gameStartTimer) {
      clearInterval(this.gameStartTimer);
    }
    this.onGameDispose();
  }

  // Abstract methods to be implemented by subclasses
  initializeGame() {
    // Override in subclass
  }

  createPlayer() {
    return new BasePlayer();
  }

  getWelcomeMessage() {
    return "Welcome to the game! Click 'Ready' when you're ready to play.";
  }

  getGameRules() {
    return ["Be the last player standing!", "Use mouse/keyboard to control your character"];
  }

  handlePlayerUpdate(client, data) {
    const player = this.state.players.get(client.sessionId);
    if (player) {
      player.x = data.x;
      player.y = data.y;
    }
  }

  gameUpdate() {
    // Called every frame during game - override in subclass
  }

  onGameStart() {
    // Called when game starts - override in subclass
  }

  onGameEnd(winner) {
    // Called when game ends - override in subclass
  }

  onGameReset() {
    // Called when game resets - override in subclass
  }

  onPlayerJoin(client, player) {
    // Called when player joins - override in subclass
  }

  onPlayerLeave(client) {
    // Called when player leaves - override in subclass
  }

  onGameDispose() {
    // Called when room is disposed - override in subclass
  }
}

module.exports = { BaseGameRoom, BasePlayer, BaseGameState };