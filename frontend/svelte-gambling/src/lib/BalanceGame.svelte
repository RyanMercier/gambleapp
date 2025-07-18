<script>
  import { onMount } from "svelte";
  
  export let gameRoom;
  export let onBack;
  
  let game;
  let gameInfo = null;
  let gamePhase = "waiting";
  let countdown = 0;
  let playerReady = false;
  let playerCount = 0;
  let readyCount = 0;
  let gameMessage = "";
  let winner = null;

  onMount(async () => {
    if (!gameRoom) {
      console.error("No game room provided");
      return;
    }

    const Phaser = await import("phaser");
    
    console.log("Setting up Balance Game with room:", gameRoom.sessionId);
    
    setupRoomHandlers();
    setupPhaserGame(Phaser);
  });

  function setupRoomHandlers() {
    console.log("Setting up room handlers");
    
    // UI State management
    gameRoom.onMessage("game_info", (data) => {
      gameInfo = data;
      gameMessage = data.message;
      console.log("Game info received:", data);
    });

    gameRoom.onMessage("game_countdown", (data) => {
      countdown = data.countdown;
      gamePhase = "ready";
      console.log("Game countdown:", data.countdown);
    });

    gameRoom.onMessage("game_started", (data) => {
      gamePhase = "playing";
      gameMessage = data.message;
      countdown = 0;
      console.log("Game started");
    });

    gameRoom.onMessage("game_ended", (data) => {
      gamePhase = "finished";
      gameMessage = data.message;
      winner = data.winner;
      console.log("Game ended:", data);
    });

    gameRoom.onMessage("game_reset", (data) => {
      gamePhase = "waiting";
      gameMessage = data.message;
      playerReady = false;
      winner = null;
      countdown = 0;
      console.log("Game reset");
    });

    gameRoom.onMessage("game_cancelled", (data) => {
      gamePhase = "waiting";
      gameMessage = data.message;
      countdown = 0;
      console.log("Game cancelled");
    });

    // Handle initial state and state changes
    gameRoom.onStateChange.once((state) => {
      console.log("Initial state received:", state);
      updateUIFromState(state);
    });

    gameRoom.onStateChange((state) => {
      console.log("State changed - gamePhase:", state.gamePhase, "players:", state.players?.size);
      updateUIFromState(state);
    });
  }

  function updateUIFromState(state) {
    gamePhase = state.gamePhase || "waiting";
    
    // Add safety checks for players
    playerCount = state.players?.size || 0;
    readyCount = state.players 
      ? Array.from(state.players.values()).filter(p => p.ready).length
      : 0;

    // Update own ready state
    if (state.players && gameRoom.sessionId) {
      const ownPlayer = state.players.get(gameRoom.sessionId);
      if (ownPlayer) {
        playerReady = ownPlayer.ready;
      }
    }

    console.log("UI updated - Phase:", gamePhase, "Players:", playerCount, "Ready:", readyCount);
  }

  function setupPhaserGame(Phaser) {
    const config = {
      type: Phaser.AUTO,
      parent: "phaser-container",
      backgroundColor: "#222",
      physics: {
        default: "matter",
        matter: {
          gravity: { y: 1 },
          debug: false,
        },
      },
      scale: {
        mode: Phaser.Scale.RESIZE,
        autoCenter: Phaser.Scale.CENTER_BOTH,
        width: "100%",
        height: "100%",
      },
      scene: {
        preload() {
          console.log("Phaser preload");
        },

        create() {
          console.log("Phaser create");
          const scene = this;
          
          // Create ground
          const ground = scene.matter.add.rectangle(400, 580, 800, 40, { isStatic: true });
          scene.add.rectangle(400, 580, 800, 40, 0x2D3748);

          // Create player's stick
          const stick = scene.matter.add.rectangle(400, 500, 20, 120, {
            chamfer: { radius: 5 },
            inertia: Infinity,
            friction: 0.9,
            frictionAir: 0.1,
          });
          
          // Visual representation of player's stick
          const stickSprite = scene.add.rectangle(400, 500, 20, 120, 0x4A5568);

          const plates = [];
          const otherPlayers = {};

          // Input handling - only when game is playing
          scene.input.on("pointermove", (pointer) => {
            if (gamePhase === "playing") {
              const targetX = Phaser.Math.Clamp(pointer.x, 50, 750);
              scene.matter.body.setPosition(stick, { x: targetX, y: 500 });
              scene.matter.body.setVelocity(stick, { x: 0, y: 0 });
              stickSprite.setPosition(targetX, 500);
            }
          });

          // Send position updates
          scene.time.addEvent({
            delay: 50,
            loop: true,
            callback: () => {
              if (gamePhase === "playing") {
                gameRoom.send("update", { x: stick.position.x, y: stick.position.y });
              }
            },
          });

          // Handle plate spawning
          gameRoom.onMessage("spawn_plate", (data) => {
            console.log("Spawning plate at:", data.x);
            if (gamePhase === "playing") {
              const plate = scene.matter.add.rectangle(data.x, 0, 80, 10, {
                chamfer: { radius: 2 },
                friction: 0.5,
                frictionAir: 0.3,
                restitution: 0.1,
              });
              
              const plateSprite = scene.add.rectangle(data.x, 0, 80, 10, 0x8B4513);
              
              plates.push({ body: plate, sprite: plateSprite });
            }
          });

          // Handle other players
          gameRoom.onStateChange.once((state) => {
            console.log("Setting up player handlers");

            const waitForPlayers = () => {
              if (state.players && state.players.size > 0) {
                console.log("Players available, setting up handlers");
                
                // Handle new players joining
                state.players.onAdd = (player, sessionId) => {
                  console.log(`Player joined: ${sessionId}, current session: ${gameRoom.sessionId}`);
                  
                  if (sessionId === gameRoom.sessionId) {
                    console.log("Skipping own player");
                    return;
                  }

                  console.log(`Creating visual for other player: ${sessionId}`);
                  
                  const otherStickSprite = scene.add.rectangle(player.x, player.y, 20, 120, 0x999999);
                  otherStickSprite.setAlpha(0.6);
                  
                  otherPlayers[sessionId] = otherStickSprite;

                  player.onChange = (changes) => {
                    if (otherPlayers[sessionId]) {
                      otherPlayers[sessionId].setPosition(player.x, player.y);
                      
                      if (!player.alive) {
                        otherPlayers[sessionId].setAlpha(0.3);
                      } else {
                        otherPlayers[sessionId].setAlpha(0.6);
                      }
                    }
                  };
                };

                // Handle players leaving
                state.players.onRemove = (player, sessionId) => {
                  console.log(`Player left: ${sessionId}`);
                  if (otherPlayers[sessionId]) {
                    otherPlayers[sessionId].destroy();
                    delete otherPlayers[sessionId];
                  }
                };

                // Add visuals for existing players
                state.players.forEach((player, sessionId) => {
                  if (sessionId !== gameRoom.sessionId) {
                    console.log(`Creating visual for existing player: ${sessionId}`);
                    
                    const otherStickSprite = scene.add.rectangle(player.x, player.y, 20, 120, 0x999999);
                    otherStickSprite.setAlpha(0.6);
                    
                    otherPlayers[sessionId] = otherStickSprite;

                    player.onChange = (changes) => {
                      if (otherPlayers[sessionId]) {
                        otherPlayers[sessionId].setPosition(player.x, player.y);
                        
                        if (!player.alive) {
                          otherPlayers[sessionId].setAlpha(0.3);
                        } else {
                          otherPlayers[sessionId].setAlpha(0.6);
                        }
                      }
                    };
                  }
                });
              } else {
                setTimeout(waitForPlayers, 100);
              }
            };

            waitForPlayers();
          });

          // Death detection
          scene.matter.world.on("afterupdate", () => {
            if (gamePhase === "playing") {
              if (stick.position.y > 700) {
                gameRoom.send("dead");
              }
              
              plates.forEach((plateObj, index) => {
                if (plateObj.body.position.y > 700) {
                  scene.matter.world.remove(plateObj.body);
                  plateObj.sprite.destroy();
                  plates.splice(index, 1);
                }
              });
            }
          });

          // Update plate sprite positions
          scene.events.on('postupdate', () => {
            plates.forEach(plateObj => {
              if (plateObj.sprite && plateObj.body) {
                plateObj.sprite.setPosition(plateObj.body.position.x, plateObj.body.position.y);
                plateObj.sprite.setRotation(plateObj.body.angle);
              }
            });
          });
        },

        update() {
          // Game loop updates if needed
        },
      },
    };

    game = new Phaser.Game(config);
  }

  function toggleReady() {
    if (gamePhase === "waiting" && gameRoom) {
      console.log("Toggling ready state");
      gameRoom.send("ready");
    }
  }

  function restartGame() {
    if (gamePhase === "finished" && gameRoom) {
      console.log("Restarting game");
      gameRoom.send("restart");
    }
  }

  function handleBack() {
    if (game) {
      game.destroy();
    }
    if (gameRoom) {
      gameRoom.leave();
    }
    onBack();
  }
</script>

<!-- Game UI -->
<div class="game-container">
  <!-- Header with back button -->
  <div class="game-header">
    <button class="back-button" on:click={handleBack}>
      ← Back to Lobby
    </button>
    <h2>Balance Game</h2>
  </div>

  <!-- Game Status Bar -->
  <div class="status-bar">
    <div class="game-info">
      <span class="game-phase">Phase: {gamePhase}</span>
      <span class="player-count">Players: {playerCount}</span>
      <span class="ready-count">Ready: {readyCount}/{playerCount}</span>
    </div>
    
    {#if gamePhase === "waiting"}
      <button 
        class="ready-button" 
        class:ready={playerReady}
        on:click={toggleReady}
        disabled={playerCount < 2}
      >
        {playerReady ? "Unready" : "Ready"}
      </button>
    {:else if gamePhase === "ready"}
      <div class="countdown">Starting in {countdown}...</div>
    {:else if gamePhase === "finished"}
      <button class="restart-button" on:click={restartGame}>
        Play Again
      </button>
    {/if}
  </div>

  <!-- Game Message -->
  {#if gameMessage}
    <div class="game-message">
      {gameMessage}
    </div>
  {/if}

  <!-- Game Rules (shown while waiting) -->
  {#if gamePhase === "waiting" && gameInfo}
    <div class="game-rules">
      <h3>How to Play:</h3>
      <ul>
        {#each gameInfo.gameRules as rule}
          <li>{rule}</li>
        {/each}
      </ul>
      <p class="min-players">Minimum {gameInfo.minPlayers} players required</p>
    </div>
  {/if}

  <!-- Phaser Game Container -->
  <div id="phaser-container" class="phaser-wrapper"></div>
</div>

<style>
  .game-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
    position: relative;
  }

  .game-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
    background: rgba(0, 0, 0, 0.5);
    border-radius: 8px;
    margin-bottom: 1rem;
  }

  .back-button {
    padding: 0.5rem 1rem;
    background: #374151;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-weight: 500;
    transition: all 0.2s;
  }

  .back-button:hover {
    background: #4B5563;
  }

  .game-header h2 {
    margin: 0;
    color: #A78BFA;
  }

  .status-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    background: rgba(0, 0, 0, 0.7);
    color: white;
    font-size: 0.9rem;
    border-radius: 8px;
    margin-bottom: 1rem;
  }

  .game-info {
    display: flex;
    gap: 1rem;
  }

  .game-phase {
    font-weight: bold;
    color: #A78BFA;
  }

  .ready-button {
    padding: 0.5rem 1rem;
    background: #4C1D95;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-weight: bold;
    transition: all 0.2s;
  }

  .ready-button:hover {
    background: #5B21B6;
  }

  .ready-button:disabled {
    background: #6B7280;
    cursor: not-allowed;
  }

  .ready-button.ready {
    background: #059669;
  }

  .ready-button.ready:hover {
    background: #047857;
  }

  .countdown {
    font-size: 1.2rem;
    font-weight: bold;
    color: #F59E0B;
    animation: pulse 1s infinite;
  }

  .restart-button {
    padding: 0.5rem 1rem;
    background: #DC2626;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-weight: bold;
    transition: all 0.2s;
  }

  .restart-button:hover {
    background: #B91C1C;
  }

  .game-message {
    padding: 0.75rem;
    background: rgba(59, 130, 246, 0.1);
    border: 1px solid rgba(59, 130, 246, 0.3);
    border-radius: 4px;
    color: #3B82F6;
    text-align: center;
    margin-bottom: 1rem;
  }

  .game-rules {
    background: rgba(0, 0, 0, 0.5);
    padding: 1rem;
    border-radius: 8px;
    margin-bottom: 1rem;
    color: white;
  }

  .game-rules h3 {
    margin: 0 0 0.5rem 0;
    color: #A78BFA;
  }

  .game-rules ul {
    margin: 0;
    padding-left: 1.5rem;
  }

  .game-rules li {
    margin-bottom: 0.25rem;
  }

  .min-players {
    margin: 0.5rem 0 0 0;
    font-size: 0.9rem;
    color: #9CA3AF;
  }

  .phaser-wrapper {
    flex: 1;
    border-radius: 8px;
    overflow: hidden;
    border: 2px solid #374151;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
</style>