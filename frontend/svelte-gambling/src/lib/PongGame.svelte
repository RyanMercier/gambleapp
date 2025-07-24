<!-- PongGame.svelte -->
<script>
  import { onMount, onDestroy } from "svelte";
  import Chat from "./Chat.svelte";
  
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
  let chatMessages = [];
  
  // Game objects
  let gameScene = null;
  let leftPaddle = null;
  let rightPaddle = null;
  let ball = null;
  let scoreText = { left: null, right: null };
  let cursors = null;
  
  // Input state
  let keys = {};
  let mouseY = 300;

  onMount(async () => {
    if (!gameRoom) {
      console.error("No game room provided");
      return;
    }

    const Phaser = await import("phaser");
    
    console.log("🏓 Setting up Pong Game with room:", gameRoom.sessionId);
    
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
      winner = data.winnerName;
      gameMessage = data.message;
      console.log("🏁 Game ended:", data);
    });

    gameRoom.onMessage("game_reset", (data) => {
      gamePhase = "waiting";
      winner = null;
      gameMessage = data.message;
      console.log("🔄 Game reset:", data);
    });

    // Pong-specific messages
    gameRoom.onMessage("player_scored", (data) => {
      console.log(`⚽ ${data.player} scored! Score: ${data.score}`);
      updateScore();
    });

    gameRoom.onMessage("paddle_hit", (data) => {
      console.log(`🏓 Paddle hit by ${data.player} on ${data.side} side`);
      // Add visual/audio feedback here
    });

    // Chat messages
    gameRoom.onMessage("chat_message", (data) => {
      const message = {
        id: `${data.timestamp}_${Math.random()}`,
        username: data.username,
        message: data.message,
        timestamp: data.timestamp,
        isOwn: data.username === (ownPlayer?.username || "")
      };
      
      chatMessages = [...chatMessages, message];
    });

    // State synchronization
    gameRoom.onStateChange((state) => {
      updateFromState(state);
    });
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
        side: player.side,
        paddleY: player.paddleY,
        isOwn: sessionId === gameRoom.sessionId
      }));

      ownPlayer = players.find(p => p.isOwn) || null;
    }

    // Update game objects if scene exists
    if (gameScene && state.ball) {
      updateBallPosition(state.ball);
      updatePaddlePositions();
      updateScore();
    }
  }

  function setupPhaserGame(Phaser) {
    const config = {
      type: Phaser.AUTO,
      parent: "phaser-container",
      width: 800,
      height: 600,
      backgroundColor: "#0a0a1a",
      physics: {
        default: "arcade",
        arcade: {
          gravity: { y: 0 },
          debug: false
        }
      },
      scene: {
        preload() {
          gameScene = this;
          console.log("🎨 Preloading Pong assets");
        },

        create() {
          console.log("🎮 Creating Pong scene");
          
          // Create game area border
          const graphics = this.add.graphics();
          graphics.lineStyle(2, 0x7C3AED);
          graphics.strokeRect(0, 0, 800, 600);
          
          // Create center line
          graphics.setDefaultStyles({
            lineStyle: {
              width: 2,
              color: 0x7C3AED,
              alpha: 0.5
            }
          });
          for (let y = 0; y < 600; y += 20) {
            graphics.lineBetween(400, y, 400, y + 10);
          }
          
          // Create paddles
          leftPaddle = this.add.rectangle(50, 300, 20, 80, 0xA78BFA);
          rightPaddle = this.add.rectangle(750, 300, 20, 80, 0xA78BFA);
          
          // Create ball
          ball = this.add.circle(400, 300, 8, 0xFFFFFF);
          
          // Create score text
          scoreText.left = this.add.text(150, 50, "0", {
            fontSize: "48px",
            fill: "#A78BFA",
            fontFamily: "Arial"
          }).setOrigin(0.5);
          
          scoreText.right = this.add.text(650, 50, "0", {
            fontSize: "48px", 
            fill: "#A78BFA",
            fontFamily: "Arial"
          }).setOrigin(0.5);
          
          // Add labels
          this.add.text(150, 100, "Player 1", {
            fontSize: "16px",
            fill: "#9CA3AF",
            fontFamily: "Arial"
          }).setOrigin(0.5);
          
          this.add.text(650, 100, "Player 2", {
            fontSize: "16px",
            fill: "#9CA3AF", 
            fontFamily: "Arial"
          }).setOrigin(0.5);
          
          // Setup input
          cursors = this.input.keyboard.createCursorKeys();
          
          // W and S keys
          this.wKey = this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.W);
          this.sKey = this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.S);
          
          // Mouse movement
          this.input.on('pointermove', (pointer) => {
            mouseY = pointer.y;
          });
          
          console.log("🎮 Pong scene setup complete");
        },

        update() {
          handleInput();
        },
      },
    };

    game = new Phaser.Game(config);
  }

  function handleInput() {
    if (!ownPlayer || !gameRoom || gamePhase !== "playing") return;
    
    let targetY = ownPlayer.paddleY;
    let moved = false;
    
    // Keyboard input
    if (cursors.up.isDown || gameScene.wKey.isDown) {
      targetY -= 8;
      moved = true;
    } else if (cursors.down.isDown || gameScene.sKey.isDown) {
      targetY += 8;
      moved = true;
    }
    
    // Mouse input (override keyboard if mouse moved recently)
    if (Math.abs(mouseY - ownPlayer.paddleY) > 5) {
      targetY = mouseY;
      moved = true;
    }
    
    if (moved) {
      // Clamp to bounds
      targetY = Math.max(40, Math.min(560, targetY));
      
      gameRoom.send("paddle_move", { paddleY: targetY });
    }
  }

  function updateBallPosition(ballState) {
    if (ball) {
      ball.x = ballState.x;
      ball.y = ballState.y;
    }
  }

  function updatePaddlePositions() {
    players.forEach(player => {
      if (player.side === "left" && leftPaddle) {
        leftPaddle.y = player.paddleY;
      } else if (player.side === "right" && rightPaddle) {
        rightPaddle.y = player.paddleY;
      }
    });
  }

  function updateScore() {
    const leftPlayer = players.find(p => p.side === "left");
    const rightPlayer = players.find(p => p.side === "right");
    
    if (scoreText.left && leftPlayer) {
      scoreText.left.setText(leftPlayer.score.toString());
    }
    if (scoreText.right && rightPlayer) {
      scoreText.right.setText(rightPlayer.score.toString());
    }
  }

  function toggleReady() {
    if (gameRoom && gamePhase === "waiting") {
      gameRoom.send("ready");
    }
  }

  function restartGame() {
    if (gameRoom && gamePhase === "finished") {
      gameRoom.send("restart");
    }
  }

  function handleChatMessage(message) {
    if (gameRoom) {
      try {
        gameRoom.send("chat_message", { text: message });
      } catch (err) {
        console.error("Error sending chat message:", err);
      }
    }
  }

  function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }
</script>

<div class="game-container min-h-screen flex">
  <!-- Game Area -->
  <div class="flex-1 flex flex-col">
    <!-- Enhanced Game Header -->
    <div class="flex items-center justify-between p-4 bg-black/20 backdrop-blur-sm border-b border-white/10">
      <div class="flex items-center gap-6">
        <button class="btn btn-secondary flex items-center gap-2" on:click={onBack}>
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
          </svg>
          Back
        </button>
        
        <div>
          <h1 class="text-2xl font-bold flex items-center gap-2">
            <span class="text-3xl">🏓</span>
            Pong
          </h1>
          <p class="text-gray-400">Classic arcade action for two players</p>
        </div>
      </div>
      
      <div class="text-right">
        <div class="text-xl font-bold bg-gradient-to-r from-green-400 to-blue-400 bg-clip-text text-transparent">
          2/2 Players
        </div>
        <div class="text-sm text-gray-300">
          First to 5 wins!
        </div>
      </div>
    </div>

    <!-- Enhanced Game Status Bar -->
    <div class="flex items-center justify-between p-4 bg-black/20 backdrop-blur-sm border-b border-white/10">
      <div class="flex items-center gap-6">
        <!-- Player Status -->
        {#if ownPlayer}
          <div class="flex items-center gap-3 bg-white/5 rounded-lg p-3 border border-white/10">
            <div class="w-4 h-4 rounded-full {ownPlayer.alive ? 'bg-green-400 animate-pulse' : 'bg-red-400'}"></div>
            <div>
              <span class="font-bold text-white">{ownPlayer.username}</span>
              <div class="text-xs text-gray-300">
                {ownPlayer.side === "left" ? "Left Paddle" : "Right Paddle"} • Score: {ownPlayer.score}
              </div>
            </div>
          </div>
        {/if}
        
        <!-- Game Phase Info -->
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
            Game Active - Use W/S or mouse!
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

    <!-- Game Message -->
    {#if gameMessage}
      <div class="p-4 bg-gradient-to-r from-blue-500/10 to-purple-500/10 border-b border-blue-500/20 text-center backdrop-blur-sm">
        <div class="text-blue-300 font-medium">{gameMessage}</div>
      </div>
    {/if}

    <!-- Winner Announcement -->
    {#if winner && gamePhase === "finished"}
      <div class="p-6 bg-gradient-to-r from-green-500/20 to-yellow-500/20 border-b border-green-500/30 text-center backdrop-blur-sm">
        <div class="text-2xl font-bold text-transparent bg-gradient-to-r from-yellow-300 to-green-300 bg-clip-text animate-pulse">
          🏆 {winner} Wins! 🏆
        </div>
        <div class="text-sm text-gray-300 mt-2">Excellent game!</div>
      </div>
    {/if}

    <!-- Players Display -->
    <div class="flex items-center gap-2 p-4 bg-black/10 backdrop-blur-sm border-b border-white/5">
      {#each players as player}
        <div class="flex items-center gap-3 px-4 py-2 rounded-xl bg-gradient-to-r from-white/5 to-white/10 min-w-0 flex-shrink-0 border border-white/10 {player.isOwn ? 'ring-2 ring-purple-400/50' : ''}">
          
          <div class="w-8 h-8 rounded-full bg-gradient-to-br from-purple-400 to-blue-500 flex items-center justify-center text-sm text-white font-bold">
            {player.username.charAt(0).toUpperCase()}
          </div>
          
          <div class="min-w-0">
            <div class="text-sm font-bold truncate max-w-24 text-white">{player.username}</div>
            <div class="text-xs text-gray-300 flex items-center gap-1">
              <span>{player.side === "left" ? "Left" : "Right"} Player</span>
              <span>•</span>
              <span>Score: {player.score}</span>
            </div>
          </div>
        </div>
      {/each}
    </div>

    <!-- Game Rules (shown while waiting) -->
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
            <strong class="text-purple-300">🎮 Controls:</strong> 
            Use W/S keys or move your mouse to control your paddle. 
            <strong class="text-blue-300">Hit the ball past your opponent to score!</strong>
          </div>
        </div>
      </div>
    {/if}

    <!-- Phaser Game Container -->
    <div class="flex-1 p-6">
      <div id="phaser-container" class="phaser-container w-full h-full min-h-96 rounded-xl overflow-hidden border-2 border-purple-500/30 shadow-2xl shadow-purple-500/20"></div>
    </div>
  </div>

  <!-- Chat Panel -->
  <div class="w-80 border-l border-white/10 bg-black/10">
    <Chat 
      messages={chatMessages}
      onSendMessage={handleChatMessage}
      disabled={!gameRoom}
      placeholder="Chat with your opponent..."
    />
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