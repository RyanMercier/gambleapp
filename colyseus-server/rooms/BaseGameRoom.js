// BaseGameRoom.js - Framework for all multiplayer games
const { Room } = require("colyseus");
const { Schema, MapSchema } = require("@colyseus/schema");

class BasePlayer extends Schema {
  constructor() {
    super();
    this.username = "";
    this.x = 400;
    this.y = 300;
    this.alive = true;
    this.ready = false;
    this.score = 0;
  }
}
BasePlayer.schema = {
  username: "string",
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
    this.pendingPlayers = null;
  }

  onCreate(options) {
    this.setState(new BaseGameState());
    
    if (options.players) {
      this.pendingPlayers = options.players;
    }
    
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

    this.onMessage("restart", (client) => {
      if (this.state.gamePhase === "finished") {
        this.resetGame();
      }
    });
  }

  onJoin(client, options) {
    const player = this.createPlayer();
    
    // Set username from pending players or options
    if (this.pendingPlayers) {
      const pendingPlayer = this.pendingPlayers.find(p => p.sessionId === client.sessionId);
      if (pendingPlayer) {
        player.username = pendingPlayer.username;
      }
    } else if (options.username) {
      player.username = options.username;
    } else {
      player.username = `Player${client.sessionId.slice(0, 4)}`;
    }
    
    this.state.players.set(client.sessionId, player);
    console.log(`Player ${player.username} (${client.sessionId}) joined game. Total: ${this.state.players.size}`);
    
    this.onPlayerJoin(client, player);
    
    // Auto-start if all pending players joined
    if (this.pendingPlayers && this.state.players.size === this.pendingPlayers.length) {
      setTimeout(() => {
        this.autoStartGame();
      }, 1000);
    }
  }

  onLeave(client) {
    const player = this.state.players.get(client.sessionId);
    const username = player ? player.username : client.sessionId;
    
    this.state.players.delete(client.sessionId);
    console.log(`Player ${username} left game. Total: ${this.state.players.size}`);
    
    if (this.state.gameStarted) {
      this.checkGameEnd();
    }
    
    if (this.state.players.size < this.minPlayers && this.state.gamePhase !== "waiting") {
      this.resetGame();
    }

    this.onPlayerLeave(client);
  }

  autoStartGame() {
    // Auto-ready all players and start
    this.state.players.forEach(player => {
      player.ready = true;
    });
    
    this.startGameCountdown();
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
      this.state.winner = winner.username;
      winner.score++;
      this.broadcast("game_ended", { 
        winner: true, 
        winnerName: winner.username,
        message: `🎉 ${winner.username} wins!`,
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
