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
  let gameStats = { gameTime: 0, difficulty: 1 };
  
  // Game objects
  let gameScene = null;
  let ownStick = null;
  let otherPlayerSticks = {};
  let plates = {};
  let particles = null;
  let cursors = null;
  
  // Input state
  let mouseX = 400;
  let targetX = 400;

  onMount(async () => {
    if (!gameRoom) {
      console.error("No game room provided");
      return;
    }

    const Phaser = await import("phaser");
    
    console.log("🎯 Setting up Enhanced Balance Game with room:", gameRoom.sessionId);
    
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

    gameRoom.onMessage("game_ended", async (data) => {
      gamePhase = "finished";
      gameMessage = data.message;
      winner = data.winnerName;
      console.log("🏁 Game ended:", data);
      
      if (data.finalStats) {
        console.log("📊 Final stats:", data.finalStats);
      }
      
      // Update user stats in backend
      await updatePlayerStats(data);
    });

    gameRoom.onMessage("game_reset", (data) => {
      gamePhase = "waiting";
      gameMessage = data.message;
      winner = null;
      countdown = 0;
      gameStats = { gameTime: 0, difficulty: 1 };
      console.log("🔄 Game reset");
    });

    gameRoom.onMessage("game_cancelled", (data) => {
      gamePhase = "waiting";
      gameMessage = data.message;
      countdown = 0;
      console.log("❌ Game cancelled");
    });

    // Handle stats updates from server
    gameRoom.onMessage("stats_updated", (data) => {
      console.log("📊 Stats updated:", data);
      if (data.username === ownPlayer?.username) {
        // Update local user data
        updateLocalUserStats(data);
      }
    });

    // Game events
    gameRoom.onMessage("player_hit", (data) => {
      console.log(`💥 Player ${data.playerName} hit by ${data.plateType} plate`);
      if (plates[data.plateId]) {
        createExplosion(data.plateX, data.plateY, data.plateType);
        destroyPlate(data.plateId);
      }
    });

    gameRoom.onMessage("player_died", (data) => {
      console.log(`☠️ Player ${data.username} died: ${data.reason}`);
      showPlayerDeath(data);
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
        console.log("👤 This is our player");
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
      
      // Listen for plate changes
      plate.onChange = () => {
        updatePlateVisual(plateId, plate);
      };
    };

    state.plates.onRemove = (plate, plateId) => {
      destroyPlate(plateId);
    };
  }

  function updateFromState(state) {
    gamePhase = state.gamePhase || "waiting";
    
    // Update game stats
    if (state.gameTime !== undefined) {
      gameStats.gameTime = state.gameTime;
    }
    if (state.difficulty !== undefined) {
      gameStats.difficulty = state.difficulty;
    }
    
    // Update players array
    if (state.players) {
      players = Array.from(state.players.entries()).map(([sessionId, player]) => ({
        sessionId,
        username: player.username,
        alive: player.alive,
        ready: player.ready,
        score: player.score,
        balancePoints: player.balancePoints || 0,
        timeAlive: player.timeAlive || 0,
        isOwn: sessionId === gameRoom.sessionId
      }));

      ownPlayer = players.find(p => p.isOwn) || null;
    }
  }

  function setupPhaserGame(Phaser) {
    const config = {
      type: Phaser.AUTO,
      parent: "phaser-container",
      backgroundColor: "#0a0a1a",
      physics: {
        default: "arcade",
        arcade: {
          gravity: { y: 0 },
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
          
          // Create gradient backgrounds and textures
          this.add.graphics()
            .fillGradientStyle(0x7C3AED, 0x7C3AED, 0x3B82F6, 0x3B82F6)
            .fillRect(0, 0, 30, 100)
            .generateTexture('player_stick', 30, 100);
            
          this.add.graphics()
            .fillGradientStyle(0xA78BFA, 0xA78BFA, 0x60A5FA, 0x60A5FA)
            .fillRect(0, 0, 25, 80)
            .generateTexture('other_stick', 25, 80);
            
          // Different plate types
          this.add.graphics()
            .fillStyle(0x8B4513)
            .fillCircle(32, 32, 30)
            .lineStyle(2, 0xCD853F)
            .strokeCircle(32, 32, 30)
            .generateTexture('plate_normal', 64, 64);
            
          this.add.graphics()
            .fillStyle(0x4A5568)
            .fillCircle(40, 40, 35)
            .lineStyle(3, 0x718096)
            .strokeCircle(40, 40, 35)
            .generateTexture('plate_heavy', 80, 80);
            
          this.add.graphics()
            .fillStyle(0x10B981)
            .fillCircle(30, 30, 25)
            .lineStyle(2, 0x34D399)
            .strokeCircle(30, 30, 25)
            .generateTexture('plate_bouncy', 60, 60);
            
          // Particle texture
          this.add.graphics()
            .fillStyle(0xFBBF24)
            .fillCircle(4, 4, 3)
            .generateTexture('spark', 8, 8);
        },

        create() {
          console.log("🎮 Phaser create");
          gameScene = this;
          
          // Create beautiful gradient background
          const bg = this.add.graphics();
          bg.fillGradientStyle(0x0a0a1a, 0x1a1a2e, 0x16213e, 0x0f0f23);
          bg.fillRect(0, 0, 800, 600);
          
          // Create animated starfield
          for (let i = 0; i < 50; i++) {
            const star = this.add.circle(
              Math.random() * 800, 
              Math.random() * 600, 
              Math.random() * 2 + 1, 
              0xffffff, 
              Math.random() * 0.8 + 0.2
            );
            
            this.tweens.add({
              targets: star,
              alpha: Math.random() * 0.5 + 0.3,
              duration: Math.random() * 2000 + 1000,
              yoyo: true,
              repeat: -1
            });
          }
          
          // Create elegant platform
          const platformGradient = this.add.graphics();
          platformGradient.fillGradientStyle(0x4A5568, 0x4A5568, 0x2D3748, 0x2D3748);
          platformGradient.fillRoundedRect(50, 520, 700, 20, 10);
          
          // Platform edges with glow
          const leftEdge = this.add.graphics();
          leftEdge.fillGradientStyle(0xEF4444, 0xEF4444, 0xDC2626, 0xDC2626);
          leftEdge.fillRect(45, 515, 10, 30);
          
          const rightEdge = this.add.graphics();
          rightEdge.fillGradientStyle(0xEF4444, 0xEF4444, 0xDC2626, 0xDC2626);
          rightEdge.fillRect(745, 515, 10, 30);
          
          // Add glow effect to danger zones
          this.tweens.add({
            targets: [leftEdge, rightEdge],
            alpha: 0.6,
            duration: 1000,
            yoyo: true,
            repeat: -1
          });

          // Create own player stick
          ownStick = this.add.image(400, 480, 'player_stick');
          ownStick.setOrigin(0.5, 0.9);
          
          // Add glow effect to own stick
          const glowFx = ownStick.preFX.addGlow(0x7C3AED, 4, 0, false, 0.1, 8);

          // Mouse input handling
          this.input.on("pointermove", (pointer) => {
            if (gamePhase === "playing") {
              mouseX = pointer.x;
              targetX = Phaser.Math.Clamp(pointer.x, 75, 725);
            }
          });

          // Touch input for mobile
          this.input.on("pointerdown", (pointer) => {
            if (gamePhase === "playing") {
              targetX = Phaser.Math.Clamp(pointer.x, 75, 725);
            }
          });

          // Keyboard controls (WASD/Arrow keys)
          cursors = this.input.keyboard.createCursorKeys();
          const wasd = this.input.keyboard.addKeys('W,S,A,D');
          
          // Smooth movement update
          this.time.addEvent({
            delay: 16, // ~60fps
            loop: true,
            callback: () => {
              if (gamePhase === "playing" && ownStick) {
                // Keyboard input
                if (cursors.left.isDown || wasd.A.isDown) {
                  targetX = Math.max(75, targetX - 5);
                }
                if (cursors.right.isDown || wasd.D.isDown) {
                  targetX = Math.min(725, targetX + 5);
                }
                
                // Smooth movement towards target
                const currentX = ownStick.x;
                const diff = targetX - currentX;
                const moveSpeed = 4;
                
                if (Math.abs(diff) > 1) {
                  const newX = currentX + Math.sign(diff) * Math.min(moveSpeed, Math.abs(diff));
                  ownStick.setX(newX);
                  
                  // Tilt stick based on movement
                  const tiltAngle = diff * 0.003;
                  ownStick.setRotation(Phaser.Math.Clamp(tiltAngle, -0.3, 0.3));
                  
                  // Send position update to server
                  if (gameRoom) {
                    gameRoom.send("player_input", { 
                      targetX: newX
                    });
                  }
                }
                
                // Death detection
                if (ownStick.x < 60 || ownStick.x > 740) {
                  if (ownPlayer?.alive) {
                    console.log("💀 Player fell off platform");
                    gameRoom.send("player_died", { reason: "fell off platform" });
                  }
                }
              }
            },
          });

          // Create particle system for effects
          particles = this.add.particles(0, 0, 'spark', {
            scale: { start: 0.5, end: 0 },
            alpha: { start: 1, end: 0 },
            lifespan: 600,
            speed: { min: 50, max: 150 },
            emitting: false
          });

          console.log("🎮 Phaser scene setup complete");
        },

        update() {
          // Continuous updates handled in timed events
        },
      },
    };

    game = new Phaser.Game(config);
  }

  function createOtherPlayerVisual(sessionId, player) {
    if (!gameScene) return;
    
    console.log(`🎨 Creating visual for player: ${player.username}`);
    
    const otherStick = gameScene.add.image(player.x, player.y, 'other_stick');
    otherStick.setOrigin(0.5, 0.9);
    otherStick.setAlpha(0.8);
    
    // Add subtle glow
    const glowFx = otherStick.preFX.addGlow(0xA78BFA, 2, 0, false, 0.1, 4);
    
    // Add username label with better styling
    const nameLabel = gameScene.add.text(
      player.x, 
      player.y - 70, 
      player.username,
      {
        fontSize: '14px',
        fill: '#ffffff',
        backgroundColor: 'rgba(0,0,0,0.7)',
        padding: { x: 8, y: 4 },
        borderRadius: 4
      }
    );
    nameLabel.setOrigin(0.5);
    
    // Add status indicator
    const statusIndicator = gameScene.add.circle(player.x + 25, player.y - 70, 4, 0x10B981);
    
    otherPlayerSticks[sessionId] = {
      stick: otherStick,
      nameLabel: nameLabel,
      statusIndicator: statusIndicator
    };
  }

  function updateOtherPlayerVisual(sessionId, player) {
    const playerVisual = otherPlayerSticks[sessionId];
    if (!playerVisual) return;
    
    // Smooth movement for other players
    gameScene.tweens.add({
      targets: [playerVisual.stick, playerVisual.nameLabel],
      x: player.x,
      duration: 100,
      ease: 'Power2'
    });
    
    gameScene.tweens.add({
      targets: playerVisual.statusIndicator,
      x: player.x + 25,
      duration: 100,
      ease: 'Power2'
    });
    
    // Update stick rotation
    playerVisual.stick.setRotation(player.stickAngle);
    
    // Update visibility and status based on alive status
    const alpha = player.alive ? 0.8 : 0.3;
    playerVisual.stick.setAlpha(alpha);
    playerVisual.nameLabel.setAlpha(player.alive ? 1 : 0.5);
    
    // Update status indicator color
    const statusColor = player.alive ? 0x10B981 : 0xEF4444;
    playerVisual.statusIndicator.setFillStyle(statusColor);
  }

  function removeOtherPlayerVisual(sessionId) {
    const playerVisual = otherPlayerSticks[sessionId];
    if (playerVisual) {
      playerVisual.stick.destroy();
      playerVisual.nameLabel.destroy();
      playerVisual.statusIndicator.destroy();
      delete otherPlayerSticks[sessionId];
    }
  }

  function createPlateVisual(plateId, plateData) {
    if (!gameScene) return;
    
    let textureKey = 'plate_normal';
    let glowColor = 0x8B4513;
    
    switch (plateData.type) {
      case 'heavy':
        textureKey = 'plate_heavy';
        glowColor = 0x4A5568;
        break;
      case 'bouncy':
        textureKey = 'plate_bouncy';
        glowColor = 0x10B981;
        break;
      default:
        textureKey = 'plate_normal';
        glowColor = 0x8B4513;
    }
    
    const plateSprite = gameScene.add.image(plateData.x, plateData.y, textureKey);
    plateSprite.setRotation(plateData.rotation);
    
    // Add glow effect based on plate type
    const glowFx = plateSprite.preFX.addGlow(glowColor, 2, 0, false, 0.1, 4);
    
    // Add entrance animation
    plateSprite.setScale(0);
    gameScene.tweens.add({
      targets: plateSprite,
      scale: 1,
      duration: 200,
      ease: 'Back.Out'
    });
    
    plates[plateId] = {
      sprite: plateSprite,
      data: plateData
    };
    
    console.log(`🍽️ Created ${plateData.type} plate visual: ${plateId}`);
  }

  function updatePlateVisual(plateId, plateData) {
    const plate = plates[plateId];
    if (plate && plate.sprite) {
      plate.sprite.setPosition(plateData.x, plateData.y);
      plate.sprite.setRotation(plateData.rotation);
      plate.data = plateData;
    }
  }

  function destroyPlate(plateId) {
    const plate = plates[plateId];
    if (plate && plate.sprite) {
      // Add destruction animation
      gameScene.tweens.add({
        targets: plate.sprite,
        scale: 0,
        alpha: 0,
        duration: 200,
        ease: 'Power2.In',
        onComplete: () => {
          plate.sprite.destroy();
        }
      });
      delete plates[plateId];
    }
  }

  function createExplosion(x, y, plateType) {
    if (!gameScene || !particles) return;
    
    // Different colors for different plate types
    let color = 0xFBBF24;
    switch (plateType) {
      case 'heavy':
        color = 0x9CA3AF;
        break;
      case 'bouncy':
        color = 0x34D399;
        break;
      default:
        color = 0xFBBF24;
    }
    
    // Create particle explosion
    particles.setTint(color);
    particles.setPosition(x, y);
    particles.explode(15);
    
    // Add screen shake for impact
    gameScene.cameras.main.shake(200, 0.01);
    
    // Add sound effect placeholder (could add actual sound later)
    console.log(`💥 ${plateType} plate explosion at (${x}, ${y})`);
  }

  function showPlayerDeath(data) {
    if (!gameScene) return;
    
    // Create death message
    const deathText = gameScene.add.text(400, 300, 
      `${data.username} ${data.reason}!`, 
      {
        fontSize: '24px',
        fill: '#EF4444',
        backgroundColor: 'rgba(0,0,0,0.8)',
        padding: { x: 16, y: 8 },
        borderRadius: 8
      }
    );
    deathText.setOrigin(0.5);
    deathText.setAlpha(0);
    
    // Animate death message
    gameScene.tweens.add({
      targets: deathText,
      alpha: 1,
      y: 280,
      duration: 300,
      ease: 'Power2.Out'
    });
    
    gameScene.tweens.add({
      targets: deathText,
      alpha: 0,
      y: 260,
      duration: 300,
      delay: 2000,
      ease: 'Power2.In',
      onComplete: () => deathText.destroy()
    });
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

  // Helper function to format time
  function formatTime(ms) {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  }

  // Update player stats in backend
  async function updatePlayerStats(gameData) {
    try {
      const user = JSON.parse(localStorage.getItem("user") || "{}");
      if (!user.id) return;

      const isWinner = gameData.winnerName === ownPlayer?.username;
      const playerScore = ownPlayer?.score || ownPlayer?.balancePoints || 0;

      const response = await fetch("http://localhost:8000/game-result", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("token")}`
        },
        body: JSON.stringify({
          user_id: user.id,
          game_type: "balance",
          won: isWinner,
          score: playerScore
        })
      });

      if (response.ok) {
        const result = await response.json();
        console.log("✅ Stats updated successfully:", result);
        
        // Update local storage with new stats
        const updatedUser = {
          ...user,
          ...result.new_stats
        };
        localStorage.setItem("user", JSON.stringify(updatedUser));
        
        // Show stats update notification
        if (gameScene) {
          const statsText = gameScene.add.text(400, 200, 
            `Stats Updated!\n${isWinner ? 'Win' : 'Loss'} • +${result.profit_change} points\nWin Rate: ${result.new_stats.win_rate}%`, 
            {
              fontSize: '18px',
              fill: isWinner ? '#10B981' : '#F59E0B',
              backgroundColor: 'rgba(0,0,0,0.8)',
              padding: { x: 16, y: 12 },
              borderRadius: 8,
              align: 'center'
            }
          );
          statsText.setOrigin(0.5);
          
          gameScene.tweens.add({
            targets: statsText,
            alpha: 0,
            y: 150,
            duration: 3000,
            ease: 'Power2.Out',
            onComplete: () => statsText.destroy()
          });
        }
        
      } else {
        console.error("❌ Failed to update stats:", await response.text());
      }
    } catch (error) {
      console.error("❌ Error updating player stats:", error);
    }
  }

  function updateLocalUserStats(data) {
    const user = JSON.parse(localStorage.getItem("user") || "{}");
    if (user.id === data.playerId) {
      const updatedUser = {
        ...user,
        wins: user.wins + data.statsUpdate.wins,
        losses: user.losses + data.statsUpdate.losses,
        profit: user.profit + data.statsUpdate.profit
      };
      localStorage.setItem("user", JSON.stringify(updatedUser));
    }
  }
</script>

<!-- Enhanced Game UI -->
<div class="game-container min-h-screen flex flex-col bg-gradient-to-br from-gray-900 via-purple-900 to-blue-900">
  <!-- Header with enhanced styling -->
  <div class="flex items-center justify-between p-6 bg-black/30 backdrop-blur-md border-b border-white/20">
    <div class="flex items-center gap-4">
      <button class="btn btn-secondary flex items-center gap-2 hover:scale-105 transition-transform" on:click={handleBack}>
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
        </svg>
        Back to Lobby
      </button>
      
      <div>
        <h2 class="text-2xl font-bold flex items-center gap-2 bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
          🎯 Enhanced Balance Game
        </h2>
        <div class="text-sm text-gray-300 flex items-center gap-4">
          <span class="capitalize font-medium text-purple-300">Phase: {gamePhase}</span>
          {#if gameStats.gameTime > 0}
            <span class="text-blue-300">Time: {formatTime(gameStats.gameTime)}</span>
          {/if}
          {#if gameStats.difficulty > 1}
            <span class="text-yellow-300">Difficulty: {gameStats.difficulty.toFixed(1)}x</span>
          {/if}
        </div>
      </div>
    </div>
    
    <div class="text-right">
      <div class="text-xl font-bold bg-gradient-to-r from-green-400 to-blue-400 bg-clip-text text-transparent">
        {players.length} Players
      </div>
      <div class="text-sm text-gray-300">
        {players.filter(p => p.alive).length} Alive
      </div>
    </div>
  </div>

  <!-- Enhanced Game Status Bar -->
  <div class="flex items-center justify-between p-4 bg-black/20 backdrop-blur-sm border-b border-white/10">
    <div class="flex items-center gap-6">
      <!-- Player Status with enhanced info -->
      {#if ownPlayer}
        <div class="flex items-center gap-3 bg-white/5 rounded-lg p-3 border border-white/10">
          <div class="w-4 h-4 rounded-full {ownPlayer.alive ? 'bg-green-400 animate-pulse' : 'bg-red-400'}"></div>
          <div>
            <span class="font-bold text-white">{ownPlayer.username}</span>
            <div class="text-xs text-gray-300">
              {ownPlayer.alive ? "🟢 Alive" : "💀 Eliminated"} • 
              Balance: {ownPlayer.balancePoints} • 
              Time: {formatTime(ownPlayer.timeAlive)}
            </div>
          </div>
        </div>
      {/if}
      
      <!-- Game Phase Info with better styling -->
      {#if gamePhase === "waiting"}
        <div class="flex items-center gap-2 text-gray-300">
          <div class="w-3 h-3 bg-gray-400 rounded-full animate-pulse"></div>
          Waiting for players to ready up...
        </div>
      {:else if gamePhase === "ready"}
        <div class="flex items-center gap-2 text-yellow-300 bg-yellow-500/10 px-3 py-2 rounded-lg border border-yellow-500/20">
          <div class="w-3 h-3 bg-yellow-400 rounded-full animate-bounce"></div>
          Starting in {countdown}...
        </div>
      {:else if gamePhase === "playing"}
        <div class="flex items-center gap-2 text-green-300 bg-green-500/10 px-3 py-2 rounded-lg border border-green-500/20">
          <div class="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
          Game Active - Stay Balanced!
        </div>
      {:else if gamePhase === "finished"}
        <div class="flex items-center gap-2 text-blue-300 bg-blue-500/10 px-3 py-2 rounded-lg border border-blue-500/20">
          <div class="w-3 h-3 bg-blue-400 rounded-full"></div>
          Game Finished
        </div>
      {/if}
    </div>
    
    <!-- Action Buttons -->
    <div class="flex items-center gap-3">
      {#if gamePhase === "waiting"}
        <button 
          class="btn {ownPlayer?.ready ? 'btn-success' : 'btn-primary'} hover:scale-105 transition-transform"
          on:click={toggleReady}
          disabled={!gameRoom}
        >
          {ownPlayer?.ready ? "✓ Ready" : "🚀 Ready Up"}
        </button>
      {:else if gamePhase === "finished"}
        <button class="btn btn-primary hover:scale-105 transition-transform" on:click={restartGame}>
          🔄 Play Again
        </button>
      {/if}
    </div>
  </div>

  <!-- Game Message with enhanced styling -->
  {#if gameMessage}
    <div class="p-4 bg-gradient-to-r from-blue-500/10 to-purple-500/10 border-b border-blue-500/20 text-center backdrop-blur-sm">
      <div class="text-blue-300 font-medium">{gameMessage}</div>
    </div>
  {/if}

  <!-- Winner Announcement with celebration -->
  {#if winner && gamePhase === "finished"}
    <div class="p-6 bg-gradient-to-r from-green-500/20 to-yellow-500/20 border-b border-green-500/30 text-center backdrop-blur-sm">
      <div class="text-2xl font-bold text-transparent bg-gradient-to-r from-yellow-300 to-green-300 bg-clip-text animate-pulse">
        🏆 {winner} Wins! 🏆
      </div>
      <div class="text-sm text-gray-300 mt-2">Congratulations on your victory!</div>
    </div>
  {/if}

  <!-- Enhanced Players List -->
  <div class="flex items-center gap-2 p-4 bg-black/10 backdrop-blur-sm border-b border-white/5 overflow-x-auto">
    {#each players as player, index}
      <div class="flex items-center gap-3 px-4 py-2 rounded-xl bg-gradient-to-r from-white/5 to-white/10 min-w-0 flex-shrink-0 border border-white/10 {player.alive ? 'border-green-400/30' : 'border-red-400/30'} {player.isOwn ? 'ring-2 ring-purple-400/50' : ''} hover:scale-105 transition-transform">
        
        <div class="w-8 h-8 rounded-full bg-gradient-to-br from-purple-400 to-blue-500 flex items-center justify-center text-sm text-white font-bold relative">
          {player.username.charAt(0).toUpperCase()}
          {#if !player.alive}
            <div class="absolute inset-0 bg-red-500/70 rounded-full flex items-center justify-center">
              💀
            </div>
          {/if}
        </div>
        
        <div class="min-w-0">
          <div class="text-sm font-bold truncate max-w-24 text-white">{player.username}</div>
          <div class="text-xs text-gray-300 flex items-center gap-1">
            <span class="{player.alive ? 'text-green-400' : 'text-red-400'}">
              {player.alive ? "🟢" : "💀"}
            </span>
            {#if player.balancePoints > 0}
              <span>Pts: {player.balancePoints}</span>
            {/if}
          </div>
        </div>
        
        {#if player.isOwn}
          <div class="text-xs bg-purple-500/80 px-2 py-1 rounded-full text-white font-medium">
            You
          </div>
        {/if}
      </div>
    {/each}
  </div>

  <!-- Enhanced Game Rules (shown while waiting) -->
  {#if gamePhase === "waiting" && gameInfo}
    <div class="p-6 bg-gradient-to-r from-black/10 to-black/20 backdrop-blur-sm">
      <h3 class="font-bold mb-4 text-xl text-transparent bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text">How to Play:</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {#each gameInfo.gameRules as rule, index}
          <div class="flex items-start gap-3 text-sm bg-white/5 p-4 rounded-lg border border-white/10">
            <span class="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 text-white flex items-center justify-center text-sm font-bold flex-shrink-0">
              {index + 1}
            </span>
            <span class="text-gray-200">{rule}</span>
          </div>
        {/each}
      </div>
      <div class="bg-gradient-to-r from-purple-500/10 to-blue-500/10 p-4 rounded-lg border border-purple-500/20">
        <div class="text-sm text-gray-200">
          <strong class="text-purple-300">💡 Controls:</strong> 
          Move your mouse or use WASD/Arrow keys to control your stick. 
          <strong class="text-blue-300">Stay balanced and avoid the danger zones!</strong>
        </div>
      </div>
    </div>
  {/if}

  <!-- Enhanced Phaser Game Container -->
  <div class="flex-1 p-6">
    <div id="phaser-container" class="phaser-container w-full h-full min-h-96 rounded-xl overflow-hidden border-2 border-purple-500/30 shadow-2xl shadow-purple-500/20"></div>
  </div>
</div>

<style>
  .phaser-container {
    background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 50%, #16213e 100%);
    position: relative;
  }
  
  .phaser-container::before {
    content: '';
    position: absolute;
    inset: 0;
    padding: 2px;
    background: linear-gradient(45deg, #7C3AED, #3B82F6, #10B981, #F59E0B);
    border-radius: inherit;
    mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    mask-composite: subtract;
    animation: borderGlow 3s ease-in-out infinite alternate;
  }
  
  @keyframes borderGlow {
    from { opacity: 0.5; }
    to { opacity: 1; }
  }
</style>