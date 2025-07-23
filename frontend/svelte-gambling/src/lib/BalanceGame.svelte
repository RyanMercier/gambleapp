<script>
  import { onMount, onDestroy } from "svelte";
  
  export let gameRoom;
  export let onBack;
  
  let game;
  let gamePhase = "waiting";
  let countdown = 0;
  let winner = null;
  let players = [];
  let ownPlayer = null;
  
  // Chat system
  let chatMessages = [];
  let newMessage = "";
  let chatContainer;
  
  // Game objects
  let gameScene = null;
  let ownStick = null;
  let otherPlayerSticks = {};
  let plates = {};
  
  // Debug info
  let debugInfo = {
    platesInState: 0,
    gameStarted: false
  };

  onMount(async () => {
    if (!gameRoom) {
      console.error("No game room provided");
      return;
    }

    const Phaser = await import("phaser");
    
    console.log("🎯 Setting up Balance Game");
    
    setupRoomHandlers();
    setupPhaserGame(Phaser);
  });

  onDestroy(() => {
    if (game) {
      game.destroy(true);
    }
  });

  function setupRoomHandlers() {
    // Handle all message types properly
    gameRoom.onMessage("game_info", (data) => {
      console.log("📋 Game info received:", data);
    });

    gameRoom.onMessage("game_countdown", (data) => {
      countdown = data.countdown;
      gamePhase = "ready";
      console.log(`⏰ Game countdown: ${data.countdown}`);
    });

    gameRoom.onMessage("game_started", (data) => {
      gamePhase = "playing";
      countdown = 0;
      console.log("🚀 Game started!");
    });

    gameRoom.onMessage("game_ended", (data) => {
      gamePhase = "finished";
      winner = data.winnerName || data.winner;
      console.log("🏁 Game ended, winner:", winner);
    });
    
    gameRoom.onMessage("game_reset", (data) => {
      gamePhase = "waiting";
      winner = null;
      console.log("🔄 Game reset");
    });
    
    gameRoom.onMessage("player_hit", (data) => {
      console.log("💥 Player hit:", data);
    });
    
    gameRoom.onMessage("player_died", (data) => {
      console.log("💀 Player died:", data);
    });

    // Chat messages
    gameRoom.onMessage("chat_message", (data) => {
      addChatMessage(data.username, data.message, data.timestamp);
    });

    // Initial state setup
    gameRoom.onStateChange.once((state) => {
      console.log("📊 Initial game state received:", state);
      updateFromState(state);
      setupStateListeners(state);
    });

    // Continuous state updates
    gameRoom.onStateChange((state) => {
      updateFromState(state);
      debugInfo.gameStarted = state.gameStarted || false;
      debugInfo.platesInState = state.plates?.size || 0;
    });
  }

  function setupStateListeners(state) {
    // Handle players
    if (state.players) {
      state.players.onAdd = (player, sessionId) => {
        console.log(`👤 Player added: ${player.username} (${sessionId})`);
        
        if (sessionId !== gameRoom.sessionId) {
          createOtherPlayerVisual(sessionId, player);
        }

        player.onChange = () => {
          if (sessionId !== gameRoom.sessionId) {
            updateOtherPlayerVisual(sessionId, player);
          }
        };
      };

      state.players.onRemove = (player, sessionId) => {
        console.log(`👋 Player removed: ${sessionId}`);
        removeOtherPlayerVisual(sessionId);
      };
    }

    // Handle plates - check if plates exist first
    if (state.plates) {
      state.plates.onAdd = (plate, plateId) => {
        console.log(`🍽️ Plate added: ${plateId} at (${plate.x}, ${plate.y})`);
        createPlateVisual(plateId, plate);
        
        plate.onChange = () => {
          updatePlateVisual(plateId, plate);
        };
      };

      state.plates.onRemove = (plate, plateId) => {
        console.log(`🗑️ Plate removed: ${plateId}`);
        destroyPlate(plateId);
      };
    } else {
      console.log("⚠️ No plates collection in state yet");
    }
  }

  function updateFromState(state) {
    gamePhase = state.gamePhase || "waiting";
    
    if (state.players) {
      players = Array.from(state.players.entries()).map(([sessionId, player]) => ({
        sessionId,
        username: player.username,
        alive: player.alive,
        ready: player.ready,
        isOwn: sessionId === gameRoom.sessionId
      }));

      ownPlayer = players.find(p => p.isOwn) || null;
    }
  }

  function setupPhaserGame(Phaser) {
    const config = {
      type: Phaser.AUTO,
      parent: "phaser-container",
      width: 800,
      height: 600,
      backgroundColor: '#2a2a3e',
      scene: {
        preload: preload,
        create: create,
        update: update
      }
    };

    game = new Phaser.Game(config);
  }

  function preload() {
    // Nothing to preload
  }

  function create() {
    console.log("🎮 Phaser create");
    gameScene = this;
    
    // Background
    this.add.rectangle(400, 300, 800, 600, 0x1a1a2e);
    
    // Platform
    this.add.rectangle(400, 520, 700, 20, 0x4a5568);
    
    // Platform edges (danger zones)
    this.add.rectangle(25, 520, 50, 30, 0xef4444);
    this.add.rectangle(775, 520, 50, 30, 0xef4444);
    
    // Own player stick
    ownStick = this.add.rectangle(400, 480, 20, 80, 0x9333ea);
    
    // Mouse/touch input
    this.input.on('pointermove', (pointer) => {
      if (gamePhase === "playing" && ownPlayer?.alive && ownStick) {
        const targetX = Phaser.Math.Clamp(pointer.x, 50, 750);
        ownStick.x = targetX;
        
        // Send position update to server
        gameRoom.send("player_update", {
          x: targetX,
          y: ownStick.y,
          angle: 0
        });
      }
    });
  }

  function update() {
    // Game updates handled by server state
  }

  function createOtherPlayerVisual(sessionId, player) {
    if (!gameScene) return;
    
    const stick = gameScene.add.rectangle(player.x, player.y, 20, 80, 0x3b82f6);
    const label = gameScene.add.text(player.x, player.y - 50, player.username, {
      fontSize: '14px',
      color: '#ffffff',
      backgroundColor: '#000000',
      padding: { x: 4, y: 2 }
    });
    label.setOrigin(0.5);
    
    otherPlayerSticks[sessionId] = { stick, label };
  }

  function updateOtherPlayerVisual(sessionId, player) {
    const visual = otherPlayerSticks[sessionId];
    if (!visual || !gameScene) return;
    
    visual.stick.x = player.x;
    visual.stick.y = player.y;
    visual.label.x = player.x;
    visual.label.y = player.y - 50;
    
    const alpha = player.alive ? 1 : 0.3;
    visual.stick.alpha = alpha;
    visual.label.alpha = alpha;
  }

  function removeOtherPlayerVisual(sessionId) {
    const visual = otherPlayerSticks[sessionId];
    if (visual) {
      visual.stick.destroy();
      visual.label.destroy();
      delete otherPlayerSticks[sessionId];
    }
  }

  function createPlateVisual(plateId, plateData) {
    if (!gameScene) return;
    
    const plate = gameScene.add.rectangle(
      plateData.x, 
      plateData.y, 
      plateData.size, 
      plateData.size, 
      0xfbbf24
    );
    plate.rotation = plateData.rotation;
    plates[plateId] = plate;
  }

  function updatePlateVisual(plateId, plateData) {
    const plate = plates[plateId];
    if (plate && gameScene) {
      plate.x = plateData.x;
      plate.y = plateData.y;
      plate.rotation = plateData.rotation;
    }
  }

  function destroyPlate(plateId) {
    const plate = plates[plateId];
    if (plate) {
      plate.destroy();
      delete plates[plateId];
    }
  }

  function toggleReady() {
    if (gameRoom && gamePhase === "waiting") {
      gameRoom.send("toggle_ready");
    }
  }
  
  function addChatMessage(username, message, timestamp) {
    const msg = {
      id: `${timestamp}_${Math.random()}`,
      username: username,
      message: message,
      timestamp: timestamp,
      isOwn: username === (ownPlayer?.username || "")
    };
    
    chatMessages = [...chatMessages, msg];
    
    // Auto-scroll
    setTimeout(() => {
      if (chatContainer) {
        chatContainer.scrollTop = chatContainer.scrollHeight;
      }
    }, 10);
  }

  function sendChatMessage() {
    const message = newMessage.trim();
    if (message && gameRoom) {
      gameRoom.send("chat_message", { text: message });
      newMessage = "";
    }
  }

  function handleChatKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendChatMessage();
    }
  }
</script>

<div class="h-screen flex flex-col bg-gray-900">
  <!-- Game Header -->
  <div class="flex items-center justify-between p-4 bg-black/50 border-b border-white/10">
    <div class="flex items-center gap-4">
      <button class="btn btn-secondary" on:click={onBack}>
        ← Back
      </button>
      <h1 class="text-xl font-bold">🎯 Balance Game</h1>
    </div>

    <div class="flex items-center gap-4">
      {#if countdown > 0}
        <div class="text-xl font-bold text-yellow-400">
          Starting in {countdown}...
        </div>
      {/if}
      
      {#if gamePhase === "waiting" && ownPlayer}
        <button 
          class="btn {ownPlayer.ready ? 'bg-green-600' : 'btn-primary'}"
          on:click={toggleReady}
        >
          {ownPlayer.ready ? "✓ Ready" : "Ready Up"}
        </button>
      {/if}
    </div>
  </div>

  <!-- Winner announcement -->
  {#if winner && gamePhase === "finished"}
    <div class="p-4 bg-yellow-500/20 text-center">
      <div class="text-2xl font-bold text-yellow-400">
        🏆 {winner} Wins! 🏆
      </div>
    </div>
  {/if}

  <!-- Main game area -->
  <div class="flex-1 flex">
    <!-- Game area -->
    <div class="flex-1 flex flex-col">
      <!-- Players bar -->
      <div class="flex gap-2 p-3 bg-black/30 overflow-x-auto">
        {#each players as player}
          <div class="flex items-center gap-2 px-3 py-2 rounded bg-gray-800 min-w-fit {player.isOwn ? 'ring-2 ring-purple-400' : ''}">
            <div class="w-8 h-8 rounded-full bg-gradient-to-br from-purple-400 to-blue-500 flex items-center justify-center text-white font-bold text-sm">
              {player.username.charAt(0).toUpperCase()}
            </div>
            <div>
              <div class="text-sm font-medium">{player.username}</div>
              <div class="text-xs {player.alive ? 'text-green-400' : 'text-red-400'}">
                {player.alive ? 'Alive' : 'Dead'}
              </div>
            </div>
          </div>
        {/each}
      </div>

      <!-- Phaser container -->
      <div class="flex-1 p-4">
        <div id="phaser-container" class="w-full h-full rounded-lg overflow-hidden"></div>
      </div>
      
      <!-- Debug info -->
      {#if false}
        <div class="absolute top-20 left-4 bg-black/80 text-white p-2 rounded text-xs">
          <div>Phase: {gamePhase}</div>
          <div>Started: {debugInfo.gameStarted}</div>
          <div>Plates: {Object.keys(plates).length} / {debugInfo.platesInState}</div>
        </div>
      {/if}
    </div>

    <!-- Chat sidebar -->
    <div class="w-80 chat-container">
      <div class="chat-header">
        <h3 class="font-semibold">Game Chat</h3>
      </div>
      
      <div class="chat-messages" bind:this={chatContainer}>
        {#each chatMessages as message}
          <div class="chat-message {message.isOwn ? 'own' : ''}">
            <div class="chat-message-content">
              {#if !message.isOwn}
                <div class="chat-message-username">{message.username}</div>
              {/if}
              <div class="chat-message-bubble">
                <div class="chat-message-text">{message.message}</div>
                <div class="chat-message-time">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </div>
          </div>
        {/each}
        
        {#if chatMessages.length === 0}
          <div class="chat-empty">
            <div class="chat-empty-icon">💬</div>
            <div>No messages yet</div>
            <div class="text-sm">Be the first to chat!</div>
          </div>
        {/if}
      </div>
      
      <div class="chat-input-container">
        <div class="chat-input-group">
          <input
            type="text"
            placeholder="Type a message..."
            class="chat-input"
            bind:value={newMessage}
            on:keydown={handleChatKeyPress}
          />
          <button 
            class="chat-send-btn"
            on:click={sendChatMessage}
            disabled={!newMessage.trim()}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  </div>
</div>