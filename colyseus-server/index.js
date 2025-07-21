const http = require("http");
const express = require("express");
const { Server } = require("colyseus");
const { WebSocketTransport } = require("@colyseus/ws-transport");
const { Room } = require("colyseus");
const { Schema, MapSchema } = require("@colyseus/schema");

const app = express();
const server = http.createServer(app);

const gameServer = new Server({
  transport: new WebSocketTransport({
    server,
    pingInterval: 6000,
    pingMaxRetries: 3
  }),
});

// Import game rooms
const BalanceRoom = require("./rooms/BalanceRoom");

// Lobby schemas
class LobbyPlayer extends Schema {
  constructor() {
    super();
    this.username = "";
    this.ready = false;
    this.joinedAt = Date.now();
  }
}
LobbyPlayer.schema = {
  username: "string",
  ready: "boolean",
  joinedAt: "number"
};

class LobbyState extends Schema {
  constructor() {
    super();
    this.players = new MapSchema();
    this.gameType = "";
    this.maxPlayers = 8;
    this.minPlayers = 2;
    this.gameStarting = false;
    this.countdown = 0;
  }
}
LobbyState.schema = {
  players: { map: LobbyPlayer },
  gameType: "string",
  maxPlayers: "number",
  minPlayers: "number",
  gameStarting: "boolean",
  countdown: "number"
};

// Game Lobby Room
class GameLobbyRoom extends Room {
  onCreate(options) {
    this.setState(new LobbyState());
    this.state.gameType = options.gameType || "balance";
    this.state.maxPlayers = options.maxPlayers || 8;
    this.state.minPlayers = options.minPlayers || 2;
    
    this.countdownTimer = null;
    this.maxClients = this.state.maxPlayers;
    
    console.log(`${this.state.gameType} lobby created`);
  }
  
  onJoin(client, options) {
    console.log(`Player ${client.sessionId} joined ${this.state.gameType} lobby`);
    
    const player = new LobbyPlayer();
    player.username = options.username || `Player${client.sessionId.slice(0, 4)}`;
    this.state.players.set(client.sessionId, player);
    
    // Send lobby info
    client.send("lobby_info", {
      gameType: this.state.gameType,
      maxPlayers: this.state.maxPlayers,
      minPlayers: this.state.minPlayers
    });
  }
  
  onMessage(client, type, message) {
    const player = this.state.players.get(client.sessionId);
    if (!player) return;
    
    switch(type) {
      case "toggle_ready":
        player.ready = !player.ready;
        console.log(`Player ${player.username} is now ${player.ready ? 'ready' : 'not ready'}`);
        this.checkGameStart();
        break;
        
      case "chat_message":
        this.broadcast("chat_message", {
          username: player.username,
          message: message.text,
          timestamp: Date.now()
        });
        break;
    }
  }
  
  onLeave(client) {
    console.log(`Player ${client.sessionId} left ${this.state.gameType} lobby`);
    this.state.players.delete(client.sessionId);
    
    if (this.state.gameStarting) {
      this.cancelGameStart();
    }
  }
  
  checkGameStart() {
    const players = Array.from(this.state.players.values());
    const readyPlayers = players.filter(p => p.ready);
    
    console.log(`Ready check: ${readyPlayers.length}/${players.length} ready, min: ${this.state.minPlayers}`);
    
    if (players.length >= this.state.minPlayers && 
        readyPlayers.length === players.length && 
        !this.state.gameStarting) {
      this.startGameCountdown();
    } else if (this.state.gameStarting && 
               (readyPlayers.length !== players.length || players.length < this.state.minPlayers)) {
      this.cancelGameStart();
    }
  }
  
  startGameCountdown() {
    this.state.gameStarting = true;
    this.state.countdown = 5;
    
    console.log("Starting game countdown...");
    this.broadcast("game_starting", { countdown: this.state.countdown });
    
    this.countdownTimer = setInterval(() => {
      this.state.countdown--;
      
      if (this.state.countdown > 0) {
        this.broadcast("game_starting", { countdown: this.state.countdown });
      } else {
        this.startGame();
      }
    }, 1000);
  }
  
  cancelGameStart() {
    console.log("Game start cancelled");
    
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
      this.countdownTimer = null;
    }
    
    this.state.gameStarting = false;
    this.state.countdown = 0;
    this.broadcast("game_cancelled");
  }
  
  async startGame() {
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
      this.countdownTimer = null;
    }
    
    console.log("Starting game...");
    
    // Create actual game room
    try {
      const gameRoom = await this.presence.create(this.state.gameType, {
        players: Array.from(this.state.players.entries()).map(([sessionId, player]) => ({
          sessionId,
          username: player.username
        }))
      });
      
      console.log(`Created game room: ${gameRoom.roomId}`);
      
      // Send all players to the game room
      this.broadcast("redirect_to_game", { 
        roomId: gameRoom.roomId,
        gameType: this.state.gameType
      });
      
      // Close this lobby after a delay
      setTimeout(() => {
        this.disconnect();
      }, 3000);
      
    } catch (error) {
      console.error("Failed to create game room:", error);
      this.broadcast("game_error", { message: "Failed to start game" });
      this.cancelGameStart();
    }
  }
  
  onDispose() {
    console.log(`${this.state.gameType} lobby disposed`);
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
    }
  }
}

// Register rooms
gameServer.define("balance_lobby", GameLobbyRoom)
  .filterBy(['gameType']);

gameServer.define("balance", BalanceRoom);

const PORT = 2567;
server.listen(PORT, () => {
  console.log(`🎮 Colyseus Game Server running on ws://localhost:${PORT}`);
  console.log(`📋 Registered rooms:`);
  console.log(`   ⏳ balance_lobby - Game lobby for Balance Game`);
  console.log(`   🎯 balance - Balance Game room`);
  console.log(`🚀 Ready for connections!`);
});

module.exports = { gameServer, server };