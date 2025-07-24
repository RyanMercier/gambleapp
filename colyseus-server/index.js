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
const PongRoom = require("./rooms/PongRoom"); // Make sure this file exists

console.log("PongRoom imported:", typeof PongRoom); // Debug log

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
    this.state.gameType = options.gameType || "pong"; // Default to pong now
    this.state.maxPlayers = options.maxPlayers || 2; // Pong max players
    this.state.minPlayers = options.minPlayers || 2; // Pong min players
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
    
    console.log(`Player ${player.username} added to lobby. Total players: ${this.state.players.size}/${this.state.maxPlayers}`);
    
    // Broadcast player joined
    this.broadcast("player_joined", {
      username: player.username,
      totalPlayers: this.state.players.size,
      maxPlayers: this.state.maxPlayers
    });
    
    // For Pong, just notify that lobby is full but don't auto-start
    // Players still need to ready up manually
    if (this.state.players.size === this.state.maxPlayers && this.state.gameType === "pong") {
      console.log("Pong lobby full! Both players can now ready up to start.");
      this.broadcast("lobby_full", {
        message: "Lobby is full! Both players ready up to start the game."
      });
    }
  }
  
  onLeave(client, consented) {
    const player = this.state.players.get(client.sessionId);
    const username = player ? player.username : "Unknown";
    
    this.state.players.delete(client.sessionId);
    console.log(`Player ${username} left ${this.state.gameType} lobby. Remaining: ${this.state.players.size}`);
    
    // Cancel game start if not enough players
    if (this.state.gameStarting && this.state.players.size < this.state.minPlayers) {
      this.cancelGameStart();
    }
    
    this.broadcast("player_left", {
      username: username,
      totalPlayers: this.state.players.size
    });
  }
  
  checkGameStart() {
    const totalPlayers = this.state.players.size;
    const readyPlayers = Array.from(this.state.players.values()).filter(p => p.ready).length;
    
    console.log(`Checking game start: ${readyPlayers}/${totalPlayers} ready, min: ${this.state.minPlayers}, max: ${this.state.maxPlayers}`);
    
    // For Pong: need exactly 2 players and both must be ready
    if (this.state.gameType === "pong") {
      if (totalPlayers === 2 && readyPlayers === 2 && !this.state.gameStarting) {
        console.log("Both Pong players ready, starting countdown!");
        this.startGameCountdown();
      }
    } else {
      // For other games: need minimum players and all must be ready
      if (totalPlayers >= this.state.minPlayers && readyPlayers === totalPlayers && !this.state.gameStarting) {
        this.startGameCountdown();
      }
    }
  }
  
  startGameCountdown() {
    if (this.state.gameStarting) return;
    
    this.state.gameStarting = true;
    this.state.countdown = 3;
    
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
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
      this.countdownTimer = null;
    }
    
    this.state.gameStarting = false;
    this.state.countdown = 0;
    
    console.log("Game start cancelled");
    this.broadcast("game_cancelled", { message: "Game start cancelled" });
  }
  
  async startGame() {
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
      this.countdownTimer = null;
    }
    
    console.log(`Starting ${this.state.gameType} game with ${this.state.players.size} players`);
    
    try {
      // Prepare player data for game room
      const playersForGame = Array.from(this.state.players.entries()).map(([sessionId, player]) => ({
        sessionId,
        username: player.username,
        userId: player.userId || null
      }));
      
      console.log("Players for game:", playersForGame);
      
      // Create game room based on game type
      let gameRoom;
      if (this.state.gameType === "pong") {
        console.log("Creating pong_game room...");
        
        // Use matchMaker.createRoom instead of create for better error handling
        gameRoom = await matchMaker.createRoom("pong_game", {
          players: playersForGame
        });
        
        console.log("Raw game room object:", gameRoom);
        console.log("Game room roomId:", gameRoom?.roomId);
        console.log("Game room id:", gameRoom?.id);
        
        // Some versions of Colyseus use 'id' instead of 'roomId'
        const roomId = gameRoom?.roomId || gameRoom?.id;
        
        if (!roomId) {
          console.error("No room ID found in:", gameRoom);
          throw new Error("Failed to create game room - no room ID returned");
        }
        
        console.log("Using room ID:", roomId);
        
        // Send redirect message to all players
        this.broadcast("redirect_to_game", {
          roomId: roomId,
          gameType: this.state.gameType
        });
        
      } else {
        throw new Error(`Unknown game type: ${this.state.gameType}`);
      }
      
      // Close lobby after short delay
      setTimeout(() => {
        this.disconnect();
      }, 2000);
      
    } catch (error) {
      console.error("Error creating game room:", error);
      console.error("Error stack:", error.stack);
      this.broadcast("game_error", {
        message: "Failed to create game room. Please try again."
      });
      this.cancelGameStart();
    }
  }
  
  onDispose() {
    if (this.countdownTimer) {
      clearInterval(this.countdownTimer);
    }
    console.log(`${this.state.gameType} lobby disposed`);
  }
}

// Global Chat Room
class GlobalChatRoom extends Room {
  onCreate() {
    console.log("🌍 Global chat room created");
    this.maxClients = 100;
    
    // Store usernames for each client
    this.usernames = new Map();
    
    // Set up message handlers in onCreate
    this.setupMessageHandlers();
  }
  
  setupMessageHandlers() {
    console.log("🔧 Setting up global chat message handlers");
    
    // This is the missing handler that's causing the error!
    this.onMessage("chat_message", (client, message) => {
      console.log("💬 Received chat_message in GlobalChatRoom:", message);
      
      if (message && message.text && message.text.trim()) {
        const username = this.usernames.get(client.sessionId) || `Player${client.sessionId.slice(0, 4)}`;
        
        console.log(`📤 Broadcasting global chat message from ${username}: ${message.text}`);
        
        this.broadcast("chat_message", {
          username: username,
          message: message.text.trim(),
          timestamp: Date.now()
        });
      } else {
        console.log("❌ Invalid chat message format:", message);
      }
    });
    
    console.log("✅ Global chat message handlers set up successfully");
  }
  
  onJoin(client, options) {
    const username = options.username || `Player${client.sessionId.slice(0, 4)}`;
    
    // Store username for this client
    this.usernames.set(client.sessionId, username);
    
    console.log(`👤 ${username} joined global chat (${client.sessionId})`);
    
    // Notify others that user joined
    this.broadcast("user_joined", { username }, { except: client });
  }
  
  onLeave(client, consented) {
    const username = this.usernames.get(client.sessionId) || "Unknown Player";
    
    console.log(`👋 ${username} left global chat (${client.sessionId})`);
    
    // Notify others that user left
    this.broadcast("user_left", { username });
    
    // Clean up stored username
    this.usernames.delete(client.sessionId);
  }
}

// Register rooms
try {
  console.log("Registering Pong rooms...");
  gameServer.define("pong_lobby", GameLobbyRoom); // Pong lobby
  gameServer.define("pong_game", PongRoom); // Pong game room
  gameServer.define("global_chat", GlobalChatRoom); // Global chat
  console.log("✅ Pong rooms registered successfully");
} catch (error) {
  console.error("❌ Failed to register rooms:", error);
}

// Start the server
const PORT = process.env.PORT || 2567;
gameServer.listen(PORT);
console.log(`🎮 Colyseus server listening on port ${PORT}`);
console.log(`🏓 Pong game server ready!`);
console.log(`💬 Global chat available`);

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully');
  gameServer.gracefullyShutdown();
});

process.on('SIGINT', () => {
  console.log('SIGINT received, shutting down gracefully');
  gameServer.gracefullyShutdown();
});