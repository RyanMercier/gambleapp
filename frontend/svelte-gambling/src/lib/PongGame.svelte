<!-- PongGame.svelte - With Game Chat Integration -->
<script>
  import { onMount, onDestroy } from "svelte";
  
  export let gameRoom;
  export let onBack;
  export let onChatMessage; // Pass chat messages to parent
  export let onChatConnected; // Pass connection status to parent
  
  let game;
  let gameInfo = null;
  let gamePhase = "waiting";
  let countdown = 0;
  let gameMessage = "";
  let winner = null;
  let players = [];
  let ownPlayer = null;
  
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
    
    // Notify parent that chat is connected (game room is connected)
    if (onChatConnected) {
      onChatConnected(true);
    }
  });

  onDestroy(() => {
    if (game) {
      game.destroy(true);
    }
    
    // Notify parent that chat is disconnected
    if (onChatConnected) {
      onChatConnected(false);
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
    });

    // Handle chat messages - pass to parent
    gameRoom.onMessage("chat_message", (data) => {
      console.log("💬 Game chat message:", data);
      
      const user = JSON.parse(localStorage.getItem("user") || "{}");
      
      if (onChatMessage) {
        onChatMessage({
          username: data.username,
          message: data.message,
          timestamp: data.timestamp,
          isOwn: data.username === user.username
        });
      }
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
          console.log("🎨 Preloading Pong assets...");
        },
        
        create() {
          console.log("🎮 Creating Pong game scene");
          
          // Create paddles
          leftPaddle = this.add.rectangle(30, 300, 15, 80, 0x7C3AED);
          rightPaddle = this.add.rectangle(770, 300, 15, 80, 0x3B82F6);
          
          // Create ball
          ball = this.add.circle(400, 300, 8, 0xFFFFFF);
          
          // Create center line
          const centerLine = this.add.graphics();
          centerLine.lineStyle(2, 0x666666, 0.5);
          centerLine.beginPath();
          centerLine.moveTo(400, 0);
          centerLine.lineTo(400, 600);
          centerLine.strokePath();
          
          // Create score text
          scoreText.left = this.add.text(200, 50, '0', {
            fontSize: '48px',
            fill: '#7C3AED',
            fontFamily: 'Arial'
          }).setOrigin(0.5);
          
          scoreText.right = this.add.text(600, 50, '0', {
            fontSize: '48px', 
            fill: '#3B82F6',
            fontFamily: 'Arial'
          }).setOrigin(0.5);
          
          // Setup input
          cursors = this.input.keyboard.createCursorKeys();
          
          // WASD keys
          keys.W = this.input.keyboard.addKey('W');
          keys.S = this.input.keyboard.addKey('S');
          
          // Mouse input
          this.input.on('pointermove', (pointer) => {
            mouseY = pointer.y;
          });
          
          console.log("✅ Pong game scene created");
        },
        
        update() {
          handleInput();
        }
      }
    };

    game = new Phaser.Game(config);
  }

  function handleInput() {
    if (!gameRoom || !ownPlayer || gamePhase !== "playing") return;
    
    let targetY = ownPlayer.paddleY;
    let inputDetected = false;
    
    // Keyboard input
    if (keys.W.isDown || cursors.up.isDown) {
      targetY -= 8;
      inputDetected = true;
    } else if (keys.S.isDown || cursors.down.isDown) {
      targetY += 8;
      inputDetected = true;
    }
    
    // Mouse input (with deadzone)
    const mouseDiff = Math.abs(mouseY - ownPlayer.paddleY);
    if (mouseDiff > 5) {
      targetY = mouseY;
      inputDetected = true;
    }
    
    // Send input to server
    if (inputDetected) {
      gameRoom.send("player_input", { paddleY: targetY });
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

  // Handle chat input from unified chat component
  function handleChatInput(message) {
    if (gameRoom) {
      try {
        gameRoom.send("chat_message", { text: message });
      } catch (err) {
        console.error("Error sending game chat message:", err);
      }
    }
  }

  // Expose chat handler to parent via global function
  $: if (typeof window !== 'undefined') {
    window.sendGameChatMessage = handleChatInput;
  }

  function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }
</script>

<div class="game-container min-h-screen flex flex-col">
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
              {ownPlayer.side === "left" ? "Left Paddle" : "Right Paddle"}
            </div>
          </div>
        </div>
      {/if}
      
      <!-- Game Phase Status -->
      <div class="flex items-center gap-2">
        {#if gamePhase === "waiting"}
          <div class="w-3 h-3 bg-yellow-400 rounded-full animate-pulse"></div>
          <span class="text-yellow-400 font-semibold">Waiting for players...</span>
        {:else if gamePhase === "ready"}
          <div class="w-3 h-3 bg-orange-400 rounded-full animate-pulse"></div>
          <span class="text-orange-400 font-semibold">Get Ready! ({countdown})</span>
        {:else if gamePhase === "playing"}
          <div class="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
          <span class="text-green-400 font-semibold">Game In Progress</span>
        {:else if gamePhase === "finished"}
          <div class="w-3 h-3 bg-red-400 rounded-full"></div>
          <span class="text-red-400 font-semibold">Game Finished</span>
        {/if}
      </div>
    </div>
    
    <!-- Game Controls -->
    <div class="flex items-center gap-3">
      {#if gamePhase === "waiting"}
        <button class="btn btn-primary" on:click={toggleReady}>
          Ready Up
        </button>
      {:else if gamePhase === "finished"}
        <div class="text-right mr-4">
          <div class="text-lg font-bold text-purple-400">
            🏆 {winner} Wins!
          </div>
        </div>
        <button class="btn btn-primary" on:click={restartGame}>
          Play Again
        </button>
      {/if}
    </div>
  </div>

  <!-- Game Instructions (only when waiting) -->
  {#if gamePhase === "waiting"}
    <div class="flex items-center justify-center p-6 bg-gradient-to-r from-purple-500/10 to-blue-500/10 border-b border-purple-500/20">
      <div class="text-center">
        <h3 class="text-lg font-bold text-purple-300 mb-2">🎮 Game Controls</h3>
        <div class="flex items-center gap-8 text-sm text-gray-300">
          <div class="flex items-center gap-2">
            <span class="px-2 py-1 bg-white/10 rounded text-xs font-mono">W/S</span>
            <span>Move Paddle</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="px-2 py-1 bg-white/10 rounded text-xs font-mono">Mouse</span>
            <span>Move Paddle</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-blue-400">●</span>
            <strong class="text-blue-300">Hit the ball past your opponent to score!</strong>
          </div>
        </div>
      </div>
    </div>
  {/if}

  <!-- Phaser Game Container -->
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