const http = require("http");
const express = require("express");
const { Server } = require("colyseus");
const { matchMaker } = require("colyseus");
const { WebSocketTransport } = require("@colyseus/ws-transport");
const { Room } = require("colyseus");
const { Schema, MapSchema, type } = require("@colyseus/schema");

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

// Lobby schemas using decorators
class LobbyPlayer extends Schema {}
type("string")(LobbyPlayer.prototype, "username");
type("boolean")(LobbyPlayer.prototype, "ready");
type("number")(LobbyPlayer.prototype, "joinedAt");

class LobbyState extends Schema {}
type({ map: LobbyPlayer })(LobbyState.prototype, "players");
type("string")(LobbyState.prototype, "gameType");
type("number")(LobbyState.prototype, "maxPlayers");
type("number")(LobbyState.prototype, "minPlayers");
type("boolean")(LobbyState.prototype, "gameStarting");
type("number")(LobbyState.prototype, "countdown");

// Game Lobby Room
class GameLobbyRoom extends Room {
  onCreate(options) {
    console.log("Creating lobby with options:", options);
    
    // Initialize state first
    this.setState(new LobbyState());
    
    // Initialize all properties with defaults
    this.state.players = new MapSchema();
    this.state.gameType = options.gameType || "balance";
    this.state.maxPlayers = options.maxPlayers || 8;
    this.state.minPlayers = options.minPlayers || 2;
    this.state.gameStarting = false;
    this.state.countdown = 0;
    
    this.countdownTimer = null;
    this.maxClients = this.state.maxPlayers;
    
    console.log(`${this.state.gameType} lobby created with state:`, {
      gameType: this.state.gameType,
      maxPlayers: this.state.maxPlayers,
      minPlayers: this.state.minPlayers,
      playersSize: this.state.players.size
    });

    // Set up message handlers immediately after state initialization
    this.setupMessageHandlers();
  }

  setupMessageHandlers() {
    console.log("Setting up message handlers for lobby");

    this.onMessage("toggle_ready", (client) => {
      console.log(`Received toggle_ready from client ${client.sessionId}`);
      
      const player = this.state.players.get(client.sessionId);
      if (!player) {
        console.log(`Player not found for session ${client.sessionId}`);
        return;
      }
      
      const wasReady = player.ready;
      player.ready = !player.ready;
      console.log(`Player ${player.username} toggled ready: ${wasReady} -> ${player.ready}`);
      
      // Broadcast ready state change
      this.broadcast("player_ready_changed", {
        sessionId: client.sessionId,
        username: player.username,
        ready: player.ready
      });
      
      this.checkGameStart();
    });

    this.onMessage("chat_message", (client, message) => {
      const player = this.state.players.get(client.sessionId);
      if (!player) {
        console.log(`Player not found for chat message from ${client.sessionId}`);
        return;
      }

      if (message && message.text) {
        console.log(`Chat message from ${player.username}: ${message.text}`);
        this.broadcast("chat_message", {
          username: player.username,
          message: message.text,
          timestamp: Date.now()
        });
      } else {
        console.log(`Invalid chat message from ${player.username}:`, message);
      }
    });

    this.onMessage("ready", (client) => {
      // Alternative ready message handler for compatibility
      console.log(`Received ready message from client ${client.sessionId}`);
      
      const player = this.state.players.get(client.sessionId);
      if (!player) {
        console.log(`Player not found for session ${client.sessionId}`);
        return;
      }
      
      const wasReady = player.ready;
      player.ready = !player.ready;
      console.log(`Player ${player.username} toggled ready: ${wasReady} -> ${player.ready}`);
      
      this.broadcast("player_ready_changed", {
        sessionId: client.sessionId,
        username: player.username,
        ready: player.ready
      });
      
      this.checkGameStart();
    });

    console.log("Message handlers set up successfully");
  }
  
  onJoin(client, options) {
    console.log(`Player ${client.sessionId} joined ${this.state.gameType} lobby with options:`, options);
    
    const player = new LobbyPlayer();
    player.username = options.username || `Player${client.sessionId.slice(0, 4)}`;
    player.ready = false;
    player.joinedAt = Date.now();
    
    // Add player to state
    this.state.players.set(client.sessionId, player);
    
    console.log(`Player ${player.username} added to lobby. Total players: ${this.state.players.size}`);
    
    // Force state synchronization
    this.broadcast("player_joined", {
      sessionId: client.sessionId,
      username: player.username,
      totalPlayers: this.state.players.size
    });
    
    // Send lobby info to the joining player
    client.send("lobby_info", {
      gameType: this.state.gameType,
      maxPlayers: this.state.maxPlayers,
      minPlayers: this.state.minPlayers
    });
    
    // Debug: Log current state
    console.log("Current lobby state after join:", {
      playersCount: this.state.players.size,
      gameType: this.state.gameType,
      gameStarting: this.state.gameStarting,
      playersKeys: Array.from(this.state.players.keys())
    });
  }
  
  onMessage(type, callback) {
    // Override to add logging
    console.log(`Registering message handler for: ${type}`);
    return super.onMessage(type, callback);
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
      const gameRoom = await matchMaker.createRoom(this.state.gameType, {
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