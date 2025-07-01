const { Room } = require("colyseus");
const { Schema, MapSchema } = require("@colyseus/schema");

class Player extends Schema {
  constructor() {
    super();
    this.x = 400;
    this.y = 300;
    this.alive = true;
  }
}
Player.schema = {
  x: "number",
  y: "number",
  alive: "boolean"
};

class State extends Schema {
  constructor() {
    super();
    this.players = new MapSchema();
  }
}
State.schema = {
  players: { map: Player }
};

class BalanceRoom extends Room {
  maxClients = 8;

  onCreate() {
    this.setState(new State());

    this.plateCount = 0;

    this.setSimulationInterval(() => {
      const id = `plate_${this.plateCount++}`;
      const x = Math.floor(Math.random() * 700) + 50;
      this.broadcast("spawn_plate", { id, x });
    }, 5000);

    this.onMessage("update", (client, data) => {
      const player = this.state.players.get(client.sessionId);
      if (player) {
        player.x = data.x;
        player.y = data.y;
      }
    });

    this.onMessage("dead", (client) => {
      const player = this.state.players.get(client.sessionId);
      if (player) {
        player.alive = false;
      }
      this.checkWinner();
    });
  }

  onJoin(client) {
    const player = new Player();
    this.state.players.set(client.sessionId, player);
    console.log(`Player ${client.sessionId} joined.`);
  }

  onLeave(client) {
    this.state.players.delete(client.sessionId);
    this.checkWinner();
  }

  checkWinner() {
    const alive = Array.from(this.state.players.values()).filter(p => p.alive);
    if (alive.length === 1) {
      console.log(`Winner:`, alive[0]);
      this.broadcast("winner", { winner: true });
    }
  }
}

module.exports = BalanceRoom;
