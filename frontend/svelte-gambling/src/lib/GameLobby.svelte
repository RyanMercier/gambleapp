<script>
  import { onMount, onDestroy } from "svelte";
  import PongGame from "./PongGame.svelte"; // Import PongGame instead of BalanceGame
  import Chat from "./Chat.svelte";
  
  export let gameType = "pong"; // Default to pong now
  export let onBack;
  
  let client = null;
  let lobbyRoom = null;
  let gameRoom = null;
  let currentView = "lobby"; // "lobby" | "game"
  
  // Lobby state
  let players = [];
  let ownPlayer = null;
  let gameStarting = false;
  let countdown = 0;
  let connecting = false;
  let error = null;
  
  // Chat state - simplified for unified chat
  let chatMessages = [];
  
  // Game info - updated for Pong
  const gameInfo = {
    pong: {
      name: "Pong",
      description: "Classic arcade action! Control your paddle and score against your opponent.",
      icon: "🏓",
      minPlayers: 2,
      maxPlayers: 2
    }
  };
  
  const currentGameInfo = gameInfo[gameType];
  
  onMount(async () => {
    await connectToGameLobby();
  });
  
  onDestroy(() => {
    cleanup();
  });
  
  function cleanup() {
    if (gameRoom) {
      gameRoom.leave();
      gameRoom = null;
    }
    
    if (lobbyRoom) {
      lobbyRoom.leave();
      lobbyRoom = null;
    }
    
    client = null;
  }
  
  async function connectToGameLobby() {
    try {
      connecting = true;
      error = null;
      
      const Colyseus = await import("colyseus.js");
      client = new Colyseus.Client("ws://localhost:2567");
      
      const user = JSON.parse(localStorage.getItem("user") || "{}");
      const username = user.username || `Player${Date.now().toString().slice(-4)}`;
      
      console.log(`🎮 Connecting directly to ${gameType}_lobby as ${username}...`);
      
      // Connect directly to the game-specific lobby
      lobbyRoom = await client.joinOrCreate(`${gameType}_lobby`, {
        gameType: gameType,
        username: username
      });
      
      setupLobbyHandlers();
      connecting = false;
      
      console.log("✅ Connected to game lobby successfully");
      
    } catch (err) {
      console.error("❌ Failed to connect to game lobby:", err);
      error = `Failed to connect to ${gameType} lobby. Make sure the Colyseus server is running on port 2567.`;
      connecting = false;
    }
  }
  
  function setupLobbyHandlers() {
    // Handle lobby info
    lobbyRoom.onMessage("lobby_info", (data) => {
      console.log("📋 Lobby info:", data);
    });
    
    // Handle player joined message
    lobbyRoom.onMessage("player_joined", (data) => {
      console.log("👤 Player joined:", data);
      if (lobbyRoom.state) {
        updateFromState(lobbyRoom.state);
      }
    });
    
    // Handle lobby full message (for Pong)
    lobbyRoom.onMessage("lobby_full", (data) => {
      console.log("🏓 Lobby full:", data);
      // Could show a notification here if desired
    });
    
    // Handle player ready state change
    lobbyRoom.onMessage("player_ready_changed", (data) => {
      console.log("🎯 Player ready changed:", data);
      if (lobbyRoom.state) {
        updateFromState(lobbyRoom.state);
      }
    });
    
    // Handle game starting countdown
    lobbyRoom.onMessage("game_starting", (data) => {
      gameStarting = true;
      countdown = data.countdown;
      console.log(`⏰ Game starting in ${countdown}...`);
    });
    
    // Handle game start cancelled
    lobbyRoom.onMessage("game_cancelled", () => {
      gameStarting = false;
      countdown = 0;
      console.log("❌ Game start cancelled");
    });
    
    // Handle redirect to actual game
    lobbyRoom.onMessage("redirect_to_game", async (data) => {
      console.log("🚀 Redirecting to game:", data);
      await joinGame(data.roomId);
    });
    
    // Handle game creation error
    lobbyRoom.onMessage("game_error", (data) => {
      error = data.message;
      gameStarting = false;
      countdown = 0;
    });
    
    // Handle chat messages - simplified for unified chat
    lobbyRoom.onMessage("chat_message", (data) => {
      const message = {
        id: `${data.timestamp}_${Math.random()}`,
        username: data.username,
        message: data.message,
        timestamp: data.timestamp,
        isOwn: data.username === (ownPlayer?.username || "")
      };
      
      chatMessages = [...chatMessages, message];
      console.log("💬 Chat message:", message);
    });
    
    // Handle state changes
    lobbyRoom.onStateChange((state) => {
      updateFromState(state);
    });
    
    // Handle room errors
    lobbyRoom.onError((code, message) => {
      console.error("❌ Room error:", code, message);
      error = `Room error: ${message}`;
    });
    
    // Handle disconnection
    lobbyRoom.onLeave((code) => {
      console.log("👋 Left lobby room with code:", code);
    });
  }
  
  function updateFromState(state) {
    if (!state || !state.players) return;
    
    const user = JSON.parse(localStorage.getItem("user") || "{}");
    const username = user.username || `Player${Date.now().toString().slice(-4)}`;
    
    players = Array.from(state.players.values()).map(player => ({
      username: player.username,
      ready: player.ready,
      joinedAt: player.joinedAt,
      isOwn: player.username === username
    }));
    
    ownPlayer = players.find(p => p.isOwn) || null;
    
    console.log("🔄 Updated state:", {
      playersCount: players.length,
      ownPlayer: ownPlayer?.username,
      gameStarting
    });
  }
  
  async function joinGame(roomId) {
    try {
      console.log("🎮 Joining game room:", roomId);
      gameRoom = await client.joinById(roomId);
      currentView = "game";
      
    } catch (err) {
      console.error("❌ Failed to join game:", err);
      error = "Failed to join game. Please try again.";
      
      setTimeout(() => {
        connectToGameLobby();
      }, 1000);
    }
  }
  
  function toggleReady() {
    if (lobbyRoom && !gameStarting && !connecting) {
      try {
        lobbyRoom.send("toggle_ready");
        console.log(`🎯 ${ownPlayer?.ready ? 'Unreadying' : 'Readying'} up...`);
      } catch (err) {
        console.error("Error sending ready toggle:", err);
      }
    }
  }
  
  // Chat handler for unified chat component
  function handleChatMessage(message) {
    if (lobbyRoom && !connecting) {
      try {
        lobbyRoom.send("chat_message", { text: message });
      } catch (err) {
        console.error("Error sending chat message:", err);
      }
    }
  }
  
  function handleBackFromGame() {
    currentView = "lobby";
    gameRoom = null;
    
    setTimeout(() => {
      connectToGameLobby();
    }, 500);
  }
  
  function handleBack() {
    cleanup();
    onBack();
  }
</script>

{#if error}
  <!-- Error State -->
  <div class="min-h-screen flex items-center justify-center p-6">
    <div class="card max-w-md w-full text-center">
      <div class="text-4xl mb-4">⚠️</div>
      <h2 class="text-xl font-bold mb-4 text-red-400">Connection Error</h2>
      <p class="text-gray-300 mb-6">{error}</p>
      <div class="flex gap-3 justify-center">
        <button class="btn btn-primary" on:click={connectToGameLobby}>
          Try Again
        </button>
        <button class="btn btn-secondary" on:click={handleBack}>
          Back to Menu
        </button>
      </div>
      
      <div class="mt-6 text-sm text-gray-400">
        <p><strong>Make sure the Colyseus server is running:</strong></p>
        <p class="font-mono text-xs mt-2">cd colyseus-server && node index.js</p>
      </div>
    </div>
  </div>

{:else if currentView === "game"}
  <!-- Game View -->
  <PongGame {gameRoom} onBack={handleBackFromGame} />

{:else}
  <!-- Lobby View -->
  <div class="game-container min-h-screen flex flex-col">
    <!-- Header -->
    <div class="flex items-center justify-between p-6 bg-black/20 border-b border-white/10">
      <div class="flex items-center gap-4">
        <button class="btn btn-secondary flex items-center gap-2" on:click={handleBack}>
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"/>
          </svg>
          Back
        </button>
        
        <div>
          <h1 class="text-2xl font-bold flex items-center gap-2">
            <span class="text-3xl">{currentGameInfo?.icon}</span>
            {currentGameInfo?.name}
          </h1>
          <p class="text-gray-400">{currentGameInfo?.description}</p>
        </div>
      </div>
      
      <div class="text-right">
        <div class="text-lg font-semibold">
          {players.length}/{currentGameInfo?.maxPlayers} Players
        </div>
        <div class="text-sm text-gray-400">
          {connecting ? "Connecting..." : 
           gameStarting ? `Starting in ${countdown}s` :
           players.length < (currentGameInfo?.minPlayers || 2) ? 
           `Need ${(currentGameInfo?.minPlayers || 2) - players.length} more player${(currentGameInfo?.minPlayers || 2) - players.length === 1 ? '' : 's'}` :
           players.filter(p => p.ready).length < players.length ? 
           "Waiting for players to ready up" :
           "Ready to start!"}
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="flex flex-1 min-h-0">
      <!-- Players Panel -->
      <div class="w-2/3 flex flex-col">
        <div class="p-4 border-b border-white/10 bg-black/10">
          <div class="flex items-center justify-between">
            <h3 class="font-semibold">Players</h3>
            <div class="text-sm text-gray-400">
              {players.filter(p => p.ready).length}/{players.length} Ready
            </div>
          </div>
        </div>
        
        <div class="flex-1 overflow-y-auto p-4">
          <!-- Ready Button -->
          {#if ownPlayer && !gameStarting}
            <div class="mb-6 text-center">
              <button 
                class="btn {ownPlayer.ready ? 'btn-success' : 'btn-primary'} text-lg px-8 py-3 hover:scale-105 transition-transform"
                on:click={toggleReady}
                disabled={connecting}
              >
                {ownPlayer.ready ? "✓ Ready" : "🚀 Ready Up"}
              </button>
            </div>
          {/if}
          
          <!-- Game Starting Countdown -->
          {#if gameStarting}
            <div class="mb-6 text-center">
              <div class="text-4xl font-bold text-green-400 animate-pulse">
                {countdown}
              </div>
              <div class="text-lg text-green-300">Game Starting...</div>
            </div>
          {/if}
          
          <!-- Special message for Pong 2-player requirement -->
          {#if players.length === 1 && !connecting}
            <div class="text-center text-blue-400 py-8 mb-4">
              <div class="text-4xl mb-4">🏓</div>
              <div class="text-lg font-semibold mb-2">Waiting for Opponent</div>
              <div class="text-sm text-gray-400">Pong requires exactly 2 players</div>
              <div class="text-xs text-gray-500 mt-2">Share this lobby with a friend!</div>
            </div>
          {/if}
          
          <!-- Players List -->
          {#each players as player, index}
            <div class="flex items-center justify-between p-3 mb-2 rounded-lg bg-white/5 border border-white/10 {player.isOwn ? 'ring-2 ring-purple-400/50' : ''}">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-full bg-gradient-to-br from-purple-400 to-blue-500 flex items-center justify-center text-white font-bold">
                  {player.username.charAt(0).toUpperCase()}
                </div>
                
                <div>
                  <div class="font-semibold flex items-center gap-2">
                    {player.username}
                    {#if player.isOwn}
                      <span class="text-xs bg-purple-500/20 text-purple-300 px-2 py-1 rounded">You</span>
                    {/if}
                    <span class="text-xs bg-blue-500/20 text-blue-300 px-2 py-1 rounded">
                      {index === 0 ? "Left Paddle" : "Right Paddle"}
                    </span>
                  </div>
                  <div class="text-sm {player.ready ? 'text-green-400' : 'text-gray-400'}">
                    {player.ready ? "Ready" : "Not Ready"}
                  </div>
                </div>
              </div>
              
              <div class="text-lg">
                {player.ready ? "✅" : "⏳"}
              </div>
            </div>
          {/each}
          
          {#if players.length === 0 && !connecting}
            <div class="text-center text-gray-400 py-8">
              <div class="text-4xl mb-2">👥</div>
              <div>Waiting for players...</div>
            </div>
          {/if}
          
          {#if connecting}
            <div class="text-center text-gray-400 py-8">
              <div class="w-8 h-8 border-2 border-purple-400/30 border-t-purple-400 rounded-full animate-spin mx-auto mb-2"></div>
              <div>Connecting to lobby...</div>
            </div>
          {/if}
          
          <!-- Pong Game Rules -->
          {#if players.length > 0 && !gameStarting}
            <div class="mt-6 p-4 bg-gradient-to-r from-purple-500/10 to-blue-500/10 rounded-lg border border-purple-500/20">
              <h4 class="font-bold text-purple-300 mb-3">🏓 How to Play Pong:</h4>
              <div class="space-y-2 text-sm text-gray-300">
                <div class="flex items-start gap-2">
                  <span class="text-purple-400">•</span>
                  <span>Use W/S keys or mouse to move your paddle</span>
                </div>
                <div class="flex items-start gap-2">
                  <span class="text-purple-400">•</span>
                  <span>Hit the ball to send it to your opponent</span>
                </div>
                <div class="flex items-start gap-2">
                  <span class="text-purple-400">•</span>
                  <span>First player to 5 points wins!</span>
                </div>
                <div class="flex items-start gap-2">
                  <span class="text-purple-400">•</span>
                  <span>Don't let the ball get past your paddle</span>
                </div>
              </div>
            </div>
          {/if}
        </div>
      </div>

      <!-- Chat Panel -->
      <div class="w-1/3 border-l border-white/10 bg-black/10">
        <Chat 
          messages={chatMessages}
          onSendMessage={handleChatMessage}
          disabled={!lobbyRoom || gameStarting || connecting}
          placeholder="Chat with your opponent..."
        />
      </div>
    </div>
  </div>
{/if}