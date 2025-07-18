const http = require("http");
const express = require("express");
const { Server } = require("colyseus");
const { Room } = require("colyseus");
const { Schema, MapSchema } = require("@colyseus/schema");

const app = express();
const server = http.createServer(app);

const gameServer = new Server({
  server,
});

// Import your game rooms
const BalanceRoom = require("./rooms/BalanceRoom");

// Define lobby schemas
class LobbyPlayer extends Schema {
  constructor() {
    super();
    this.username = "";
    this.selectedGame = "";
  }
}
LobbyPlayer.schema = {
  username: "string",
  selectedGame: "string"
};

class LobbyState extends Schema {
  constructor() {
    super();
    this.players = new MapSchema();
    this.availableGames = ["balance"];
  }
}
LobbyState.schema = {
  players: { map: LobbyPlayer },
  availableGames: ["string"]
};

// Lobby room class
class LobbyRoom extends Room {
  onCreate() {
    console.log("Lobby room created");
    this.setState(new LobbyState());
  }
  
  onJoin(client, options) {
    console.log(`Player ${client.sessionId} joined lobby`);
    const player = new LobbyPlayer();
    if (options && options.username) {
      player.username = options.username;
    }
    this.state.players.set(client.sessionId, player);
    
    // Send available games immediately
    client.send("available_games", { 
      games: this.state.availableGames 
    });
    
    console.log(`Sent available games to ${client.sessionId}: [${this.state.availableGames.join(', ')}]`);
  }
  
  onLeave(client) {
    console.log(`Player ${client.sessionId} left lobby`);
    this.state.players.delete(client.sessionId);
  }
}

// Register rooms
gameServer.define("lobby", LobbyRoom);
gameServer.define("balance", BalanceRoom);

const PORT = 2567;
server.listen(PORT, () => {
  console.log(`Colyseus server running on ws://localhost:${PORT}`);
  console.log(`Registered rooms:`);
  console.log(`   - lobby (game selection)`);
  console.log(`   - balance (balance game)`);
  console.log(`Connect at: ws://localhost:${PORT}`);
});

module.exports = { gameServer, server };