const { BaseGameRoom, BasePlayer, BaseGameState } = require("./BaseGameRoom");

class BalancePlayer extends BasePlayer {
  constructor() {
    super();
    this.x = 400;
    this.y = 500; // Balance game specific starting position
  }
}
BalancePlayer.schema = {
  ...BasePlayer.schema
};

class BalanceRoom extends BaseGameRoom {
  constructor() {
    super();
    this.minPlayers = 2;
    this.maxClients = 8;
    this.plateCount = 0;
    this.plateSpawnInterval = null;
  }

  initializeGame() {
    console.log("Initializing Balance Game");
    // Balance game specific initialization
    this.plateCount = 0;
    
    // Handle death messages
    this.onMessage("dead", (client) => {
      const player = this.state.players.get(client.sessionId);
      if (player && this.state.gameStarted) {
        player.alive = false;
        console.log(`Player ${client.sessionId} died`);
        this.checkGameEnd();
      }
    });
  }

  createPlayer() {
    return new BalancePlayer();
  }

  getWelcomeMessage() {
    return "Welcome to Balance Game! Keep your stick balanced while avoiding falling plates. Click 'Ready' when you're ready to play.";
  }

  getGameRules() {
    return [
      "Move your mouse to control the balance stick",
      "Avoid letting plates fall on you",
      "Don't let your stick fall off the screen",
      "Last player standing wins!"
    ];
  }

  resetPlayerPosition(player) {
    player.x = 400;
    player.y = 500;
  }

  handlePlayerUpdate(client, data) {
    const player = this.state.players.get(client.sessionId);
    if (player && player.alive) {
      player.x = data.x;
      player.y = data.y;
    }
  }

  onGameStart() {
    console.log("Balance game started - spawning plates");
    // Start spawning plates every 5 seconds
    this.plateSpawnInterval = setInterval(() => {
      const id = `plate_${this.plateCount++}`;
      const x = Math.floor(Math.random() * 700) + 50;
      console.log(`Spawning plate at x: ${x}`);
      this.broadcast("spawn_plate", { id, x });
    }, 5000);
  }

  onGameEnd(winner) {
    console.log("Balance game ended");
    // Clean up plate spawning
    if (this.plateSpawnInterval) {
      clearInterval(this.plateSpawnInterval);
      this.plateSpawnInterval = null;
    }
  }

  onGameReset() {
    console.log("Balance game reset");
    // Reset plate counter
    this.plateCount = 0;
    if (this.plateSpawnInterval) {
      clearInterval(this.plateSpawnInterval);
      this.plateSpawnInterval = null;
    }
  }

  onGameDispose() {
    if (this.plateSpawnInterval) {
      clearInterval(this.plateSpawnInterval);
    }
  }
}

module.exports = BalanceRoom;