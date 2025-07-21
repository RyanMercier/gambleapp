<!-- src/lib/BalanceGame.svelte -->
<script>
  import { onMount, onDestroy } from "svelte";
  
  export let gameRoom;
  export let onBack;
  
  let game;
  let gameInfo = null;
  let gamePhase = "waiting";
  let countdown = 0;
  let gameMessage = "";
  let winner = null;
  let players = [];
  let ownPlayer = null;
  
  // Game objects
  let stick = null;
  let stickSprite = null;
  let otherPlayers = {};
  let plates = {};

  onMount(async () => {
    if (!gameRoom) {
      console.error("No game room provided");
      return;
    }

    const Phaser = await import("phaser");
    
    console.log("🎯 Setting up Balance Game with room:", gameRoom.sessionId);
    
    setupRoomHandlers();
    setupPhaserGame(Phaser);
  });

  onDestroy(() => {
    if (game) {
      game.destroy(true);
    }
  });

  function setupRoomHandlers() {
    console.log("🔗 Setting up room handlers");
    
    // Game info and UI messages
    gameRoom.onMessage("game_info", (data) => {
      gameInfo = data;
      gameMessage = data.message;
      console.log("📋 Game info received:", data);
    });

    gameRoom.onMessage("game_countdown", (data) => {
      countdown = data.countdown;
      gamePhase = "ready";
      console.log(`⏰ Game countdown: ${data.countdown}`);
    });

    gameRoom.onMessage("game_started", (data) => {
      gamePhase = "playing";
      gameMessage = data.message;
      countdown = 0;
      console.log("🚀 Game started!");
    });

    gameRoom.onMessage("game_ended", (data) => {
      gamePhase = "finished";
      gameMessage = data.message;
      winner = data.winnerName;
      console.log("🏁 Game ended:", data);
    });

    gameRoom.onMessage("game_reset", (data) => {
      gamePhase = "waiting";
      gameMessage = data.message;
      winner = null;
      countdown = 0;
      console.log("🔄 Game reset");
    });

    gameRoom.onMessage("game_cancelled", (data) => {
      gamePhase = "waiting";
      gameMessage = data.message;
      countdown = 0;
      console.log("❌ Game cancelled");
    });

    // Game events
    gameRoom.onMessage("player_hit", (data) => {
      console.log(`💥 Player ${data.playerName} hit by plate`);
      if (plates[data.plateId]) {
        // Create explosion effect
        createExplosion(plates[data.plateId].sprite);
        destroyPlate(data.plateId);
      }
    });

    gameRoom.onMessage("player_fell", (data) => {
      console.log(`💀 Player ${data.playerName} fell off screen`);
    });

    gameRoom.onMessage("player_died", (data) => {
      console.log(`☠️ Player ${data.username} died`);
    });

    // Handle initial state and state changes
    gameRoom.onStateChange.once((state) => {
      console.log("📊 Initial state received");
      updateFromState(state);
      setupPlayerHandlers(state);
    });

    gameRoom.onStateChange((state) => {
      updateFromState(state);
    });
  }

  function setupPlayerHandlers(state) {
    if (!state.players) return;

    // Handle new players joining
    state.players.onAdd = (player, sessionId) => {
      console.log(`👤 Player joined: ${player.username} (${sessionId})`);
      
      if (sessionId === gameRoom.sessionId) {
        console.log("👤 This is our player, skipping visual creation");
        return;
      }

      createOtherPlayerVisual(sessionId, player);

      // Listen for player changes
      player.onChange = () => {
        updateOtherPlayerVisual(sessionId, player);
      };
    };

    // Handle players leaving
    state.players.onRemove = (player, sessionId) => {
      console.log(`👋 Player left: ${sessionId}`);
      removeOtherPlayerVisual(sessionId);
    };

    // Setup existing players
    state.players.forEach((player, sessionId) => {
      if (sessionId !== gameRoom.sessionId) {
        createOtherPlayerVisual(sessionId, player);
        
        player.onChange = () => {
          updateOtherPlayerVisual(sessionId, player);
        };
      }
    });

    // Handle plates
    state.plates.onAdd = (plate, plateId) => {
      createPlateVisual(plateId, plate);
    };

    state.plates.onRemove = (plate, plateId) => {
      destroyPlate(plateId);
    };
  }

  function updateFromState(state) {
    gamePhase = state.gamePhase || "waiting";
    
    // Update players array
    if (state.players) {
      players = Array.from(state.players.entries()).map(([sessionId, player]) => ({
        sessionId,
        username: player.username,
        alive: player.alive,
        ready: player.ready,
        score: player.score,
        isOwn: sessionId === gameRoom.sessionId
      }));

      ownPlayer = players.find(p => p.isOwn) || null;
    }
  }

  function setupPhaserGame(Phaser) {
    const config = {
      type: Phaser.AUTO,
      parent: "phaser-container",
      backgroundColor: "#1a1a2e",
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
        width: 800,
        height: 600,
      },
      scene: {
        preload() {
          console.log("🎮 Phaser preload");
          
          // Create simple colored rectangles for game objects
          this.add.graphics()
            .fillStyle(0x4A5568)
            .fillRect(0, 0, 32, 32)
            .generateTexture('stick', 32, 32);
            
          this.add.graphics()
            .fillStyle(0x8B4513)
            .fillRect(0, 0, 64, 64)
            .generateTexture('plate', 64, 64);
        },

        create() {
          console.log("🎮 Phaser create");
          const scene = this;
          
          // Create ground
          const ground = scene.matter.add.rectangle(400, 580, 800, 40, { isStatic: true });
          scene.add.rectangle(400, 580, 800, 40, 0x2D3748);

          // Create player's stick
          stick = scene.matter.add.rectangle(400, 500, 20, 120, {
            chamfer: { radius: 5 },
            inertia: Infinity,
            friction: 0.9,
            frictionAir: 0.1,
          });
          
          // Visual representation of player's stick
          stickSprite = scene.add.rectangle(400, 500, 20, 120, 0x7C3AED);

          // Input handling - only when game is playing
          scene.input.on("pointermove", (pointer) => {
            if (gamePhase === "playing" && stick) {
              const targetX = Phaser.Math.Clamp(pointer.x, 50, 750);
              scene.matter.body.setPosition(stick, { x: targetX, y: stick.position.y });
              scene.matter.body.setVelocity(stick, { x: 0, y: 0 });
              
              if (stickSprite) {
                stickSprite.setPosition(targetX, stick.position.y);
                stickSprite.setRotation(stick.angle);
              }
            }
          });

          // Send position updates to server
          scene.time.addEvent({
            delay: 50,
            loop: true,
            callback: () => {
              if (gamePhase === "playing" && stick && gameRoom) {
                gameRoom.send("player_update", { 
                  x: stick.position.x, 
                  y: stick.position.y,
                  angle: stick.angle,
                  velocityX: stick.velocity.x,
                  velocityY: stick.velocity.y
                });
              }
            },
          });

          // Death detection
          scene.matter.world.on("afterupdate", () => {
            if (gamePhase === "playing" && stick && ownPlayer?.alive) {
              // Check if player fell off screen
              if (stick.position.y > 650 || stick.position.x < 0 || stick.position.x > 800) {
                console.log("💀 Player fell off screen, sending death message");
                gameRoom.send("player_died");
              }
            }
          });

          // Update sprite positions every frame
          scene.events.on('postupdate', () => {
            // Update own stick sprite
            if (stick && stickSprite) {
              stickSprite.setPosition(stick.position.x, stick.position.y);
              stickSprite.setRotation(stick.angle);
            }
            
            // Update plate sprites
            Object.values(plates).forEach(plateObj => {
              if (plateObj.sprite && plateObj.data) {
                plateObj.sprite.setPosition(plateObj.data.x, plateObj.data.y);
                plateObj.sprite.setRotation(plateObj.data.rotation);
              }
            });
          });

          // Store scene reference for helper functions
          window.gameScene = scene;
        },

        update() {
          // Game loop updates if needed
        },
      },
    };

    game = new Phaser.Game(config);
  }

  function createOtherPlayerVisual(sessionId, player) {
    if (!window.gameScene) return;
    
    console.log(`🎨 Creating visual for player: ${player.username}`);
    
    const otherStickSprite = window.gameScene.add.rectangle(
      player.x, 
      player.y, 
      20, 
      120, 
      0xA78BFA
    );
    otherStickSprite.setAlpha(0.8);
    
    // Add username label
    const nameLabel = window.gameScene.add.text(
      player.x, 
      player.y - 80, 
      player.username,
      {
        fontSize: '12px',
        fill: '#ffffff',
        backgroundColor: '#000000',
        padding: { x: 4, y: 2 }
      }
    );
    nameLabel.setOrigin(0.5);
    
    otherPlayers[sessionId] = {
      stick: otherStickSprite,
      nameLabel: nameLabel
    };
  }

  function updateOtherPlayerVisual(sessionId, player) {
    const playerVisual = otherPlayers[sessionId];
    if (!playerVisual) return;
    
    // Update position
    playerVisual.stick.setPosition(player.x, player.y);
    playerVisual.stick.setRotation(player.stickAngle);
    playerVisual.nameLabel.setPosition(player.x, player.y - 80);
    
    // Update visibility based on alive status
    const alpha = player.alive ? 0.8 : 0.3;
    playerVisual.stick.setAlpha(alpha);
    playerVisual.nameLabel.setAlpha(alpha);
  }

  function removeOtherPlayerVisual(sessionId) {
    const playerVisual = otherPlayers[sessionId];
    if (playerVisual) {
      playerVisual.stick.destroy();
      playerVisual.nameLabel.destroy();
      delete otherPlayers[sessionId];
    }
  }

  function createPlateVisual(plateId, plateData) {
    if (!window.gameScene) return;
    
    const plateSprite = window.gameScene.add.rectangle(
      plateData.x,
      plateData.y,
      plateData.size,
      10,
      0x8B4513
    );
    
    plates[plateId] = {
      sprite: plateSprite,
      data: plateData
    };
    
    console.log(`🍽️ Created plate visual: ${plateId}`);
  }

  function destroyPlate(plateId) {
    const plate = plates[plateId];
    if (plate && plate.sprite) {
      plate.sprite.destroy();
      delete plates[plateId];
    }
  }

  function createExplosion(sprite) {
    if (!window.gameScene || !sprite) return;
    
    // Simple explosion effect
    const particles = window.gameScene.add.particles(sprite.x, sprite.y, 'plate', {
      speed: { min: 50, max: 100 },
      scale: { start: 0.3, end: 0 },
      lifespan: 300,
      quantity: 8
    });
    
    setTimeout(() => {
      particles.destroy();
    }, 500);
  }

  function toggleReady() {
    if (gamePhase === "waiting" && gameRoom) {
      console.log("🎯 Toggling ready state");
      gameRoom.send("ready");
    }
  }

  function restartGame() {
    if (gamePhase === "finished" && gameRoom) {
      console.log("🔄 Restarting game");
      gameRoom.send("restart");
    }
  }

  function handleBack() {
    if (game) {
      game.destroy(true);
    }
    if (gameRoom) {
      gameRoom.leave();
    }
    onBack();
  }
</script>

<!-- Game UI -->
<div class="game-container min-h-screen flex flex-col">
  <!-- Header -->
  <div class="flex items-center justify-between p-6 bg-black/20 border-b border-white/10">
    <div class="flex items-center gap-4">
      <button class="btn btn-secondary flex items-center gap-2" on:click={handleBack}>
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
        </svg>
        Back to Lobby
      </button>
      
      <div>
        <h2 class="text-xl font-bold flex items-center gap-2">
          🎯 Balance Game
        </h2>
        <div class="text-sm text-gray-400">
          Phase: <span class="capitalize font-medium text-purple-400">{gamePhase}</span>
        </div>
      </div>
    </div>
    
    <div class="text-right">
      <div class="text-lg font-semibold">
        {players.length} Players
      </div>
      <div class="text-sm text-gray-400">
        {players.filter(p => p.alive).length} Alive
      </div>
    </div>
  </div>

  <!-- Game Status Bar -->
  <div class="flex items-center justify-between p-4 bg-black/10 border-b border-white/10">
    <div class="flex items-center gap-6">
      <!-- Player Status -->
      {#if ownPlayer}
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-full {ownPlayer.alive ? 'bg-green-400' : 'bg-red-400'}"></div>
          <span class="font-medium">{ownPlayer.username}</span>
          <span class="text-sm text-gray-400">
            {ownPlayer.alive ? "Alive" : "Dead"} • Score: {ownPlayer.score}
          </span>
        </div>
      {/if}
      
      <!-- Game Phase Info -->
      {#if gamePhase === "waiting"}
        <div class="text-sm text-gray-400">
          Waiting for players to ready up...
        </div>
      {:else if gamePhase === "ready"}
        <div class="flex items-center gap-2 text-yellow-400">
          <div class="w-2 h-2 bg-yellow-400 rounded-full animate-pulse"></div>
          Starting in {countdown}...
        </div>
      {:else if gamePhase === "playing"}
        <div class="flex items-center gap-2 text-green-400">
          <div class="w-2 h-2 bg-green-400 rounded-full"></div>
          Game in progress
        </div>
      {:else if gamePhase === "finished"}
        <div class="flex items-center gap-2 text-blue-400">
          <div class="w-2 h-2 bg-blue-400 rounded-full"></div>
          Game finished
        </div>
      {/if}
    </div>
    
    <!-- Action Buttons -->
    <div class="flex items-center gap-3">
      {#if gamePhase === "waiting"}
        <button 
          class="btn {ownPlayer?.ready ? 'btn-success' : 'btn-primary'}"
          on:click={toggleReady}
          disabled={!gameRoom}
        >
          {ownPlayer?.ready ? "✓ Ready" : "Ready Up"}
        </button>
      {:else if gamePhase === "finished"}
        <button class="btn btn-primary" on:click={restartGame}>
          🔄 Play Again
        </button>
      {/if}
    </div>
  </div>

  <!-- Game Message -->
  {#if gameMessage}
    <div class="p-4 bg-blue-500/10 border-b border-blue-500/20 text-center">
      <div class="text-blue-400">{gameMessage}</div>
    </div>
  {/if}

  <!-- Winner Announcement -->
  {#if winner && gamePhase === "finished"}
    <div class="p-4 bg-green-500/10 border-b border-green-500/20 text-center">
      <div class="text-green-400 text-lg font-bold">
        🏆 {winner} Wins!
      </div>
    </div>
  {/if}

  <!-- Players List (Compact) -->
  <div class="flex items-center gap-2 p-3 bg-black/5 border-b border-white/5 overflow-x-auto">
    {#each players as player}
      <div class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 min-w-0 flex-shrink-0 {player.alive ? 'bg-green-500/20' : 'bg-red-500/20'} {player.isOwn ? 'ring-2 ring-purple-400' : ''}">
        
        <div class="w-6 h-6 rounded-full bg-gradient-to-br from-purple-400 to-blue-500 flex items-center justify-center text-xs text-white font-bold">
          {player.username.charAt(0).toUpperCase()}
        </div>
        
        <span class="text-sm font-medium truncate max-w-20">{player.username}</span>
        
        <div class="text-xs">
          {player.alive ? "🟢" : "💀"}
        </div>
      </div>
    {/each}
  </div>

  <!-- Game Rules (shown while waiting) -->
  {#if gamePhase === "waiting" && gameInfo}
    <div class="p-6 bg-black/10">
      <h3 class="font-semibold mb-3 text-purple-400">How to Play:</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        {#each gameInfo.gameRules as rule, index}
          <div class="flex items-start gap-2 text-sm">
            <span class="w-6 h-6 rounded-full bg-purple-500 text-white flex items-center justify-center text-xs font-bold flex-shrink-0">
              {index + 1}
            </span>
            <span class="text-gray-300">{rule}</span>
          </div>
        {/each}
      </div>
      <div class="mt-4 text-sm text-gray-400">
        💡 <strong>Tip:</strong> Move your mouse to control your stick. The last player standing wins!
      </div>
    </div>
  {/if}

  <!-- Phaser Game Container -->
  <div class="flex-1 p-6">
    <div id="phaser-container" class="phaser-container w-full h-full min-h-96"></div>
  </div>
</div>

<style>
  .phaser-container {
    border-radius: 12px;
    overflow: hidden;
    border: 2px solid var(--border-color);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    background: #1a1a2e;
  }
</style>