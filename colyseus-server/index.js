const http = require("http");
const express = require("express");
const { Server } = require("colyseus");
const BalanceRoom = require("./rooms/BalanceRoom");

const app = express();
const server = http.createServer(app);

const gameServer = new Server({
  server,
});

// Create a basic room handler
const { Room } = require("colyseus");

gameServer.define("balance", BalanceRoom);

const PORT = 2567;
server.listen(PORT, () => {
  console.log(`Colyseus server running on ws://localhost:${PORT}`);
});
