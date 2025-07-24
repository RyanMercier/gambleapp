<script>
  import { onMount, onDestroy } from "svelte";
  
  export let gameType = "pong";
  export let onBack;
  export let onGameStart;
  export let onChatMessage; // Pass chat messages to parent
  export let onChatConnected; // Pass connection status to parent
  export let onChatHandlerReady; // Pass chat handler to parent
  
  let client = null;
  let lobbyRoom = null;
  
  // Lobby state
  let players = [];
  let ownPlayer = null;
  let gameStarting = false;
  let countdown = 0;
  let connecting = false;
  let error = null;
  
  // Game info
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
    console.log("🧹 Cleaning up lobby connection...");
    
    if (lobbyRoom) {
      try {
        lobbyRoom.leave();
      } catch (err) {
        console.warn("Error leaving lobby room:", err);
      }
      lobbyRoom = null;
    }
    
    if (client) {
      client = null;
    }
    
    // Notify parent of disconnection
    if (onChatConnected) {
      onChatConnected(false);
    }
  }
  
  async function connectToGameLobby() {
    try {
      connecting = true;
      error = null;
      
      const Colyseus = await import("colyseus.js");
      client = new Colyseus.Client("ws://localhost:2567");
      
      const user = JSON.parse(localStorage.getItem("user") || "{}");
      const username = user.username || `Player${Date.now().toString().slice(-4)}`;
      
      console.log(`🎮 Connecting to ${gameType}_lobby as ${username}...`);
      
      // Connect directly to the game-specific lobby
      lobbyRoom = await client.joinOrCreate(`${gameType}_lobby`, {
        gameType: gameType,
        username: username
      });
      
      setupLobbyHandlers();
      connecting = false;
      
      // Notify parent of successful connection
      if (onChatConnected) {
        onChatConnected(true);
      }
      
      // Pass chat handler to parent
      if (onChatHandlerReady) {
        onChatHandlerReady(handleChatInput);
      }
      
      console.log("✅ Connected to game lobby successfully");
      
    } catch (err) {
      console.error("❌ Failed to connect to game lobby:", err);
      error = `Failed to connect to ${gameType} lobby. Make sure the Colyseus server is running on port 2567.`;
      connecting = false;
      
      // Notify parent of connection failure
      if (onChatConnected) {
        onChatConnected(false);
      }
    }
  }
  
  function setupLobbyHandlers() {
    // Handle player joined message
    lobbyRoom.onMessage("player_joined", (data) => {
      console.log("👤 Player joined:", data);
      if (lobbyRoom.state) {
        updateFromState(lobbyRoom.state);
      }
    });
    
    // Handle lobby full message
    lobbyRoom.onMessage("lobby_full", (data) => {
      console.log("🏓 Lobby full:", data);
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
    
    // Handle chat messages - pass to parent
    lobbyRoom.onMessage("chat_message", (data) => {
      console.log("💬 Lobby chat message received:", data);
      
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
    
    // Handle state changes
    lobbyRoom.onStateChange((state) => {
      updateFromState(state);
    });
    
    // Handle room errors
    lobbyRoom.onError((code, message) => {
      console.error("❌ Lobby room error:", code, message);
      error = "Connection lost. Please try again.";
      
      // Notify parent of connection loss
      if (onChatConnected) {
        onChatConnected(false);
      }
      
      setTimeout(() => {
        connectToGameLobby();
      }, 1000);
    });
  }
  
  function updateFromState(state) {
    // Update players array
    if (state.players) {
      players = Array.from(state.players.entries()).map(([sessionId, player]) => ({
        sessionId,
        username: player.username,
        ready: player.ready,
        joinedAt: player.joinedAt,
        isOwn: sessionId === lobbyRoom.sessionId
      }));

      ownPlayer = players.find(p => p.isOwn) || null;
    }
  }
  
  async function joinGame(roomId) {
    try {
      console.log(`🎮 Joining game room: ${roomId}`);
      
      const gameRoom = await client.joinById(roomId);
      console.log("✅ Joined game room successfully");
      
      // Don't cleanup lobby yet - let parent handle transition
      // cleanup();
      
      // Pass the game room to parent component
      onGameStart(gameRoom);
      
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

  // Handle chat input from unified chat component
  function handleChatInput(message) {
    console.log("📤 Sending lobby chat message:", message);
    
    if (lobbyRoom && !connecting) {
      try {
        lobbyRoom.send("chat_message", { text: message });
      } catch (err) {
        console.error("❌ Error sending lobby chat message:", err);
      }
    } else {
      console.warn("⚠️ Cannot send message - not connected to lobby");
    }
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
           gameStarting ? `Starting in ${countdown}s...` : 
           players.length === currentGameInfo?.maxPlayers ? "Lobby Full" : "Waiting for players..."}
        </div>
      </div>
    </div>

    <!-- Main Content Area -->
    <div class="flex-1 p-6">
      <!-- Game Starting Countdown -->
      {#if gameStarting && countdown > 0}
        <div class="text-center mb-6">
          <div class="inline-flex items-center gap-3 px-6 py-4 bg-gradient-to-r from-green-500/20 to-blue-500/20 rounded-lg border border-green-500/30">
            <div class="text-2xl animate-pulse">🚀</div>
            <div>
              <div class="text-xl font-bold text-green-400">Game Starting!</div>
              <div class="text-lg">Get ready in {countdown} seconds...</div>
            </div>
          </div>
        </div>
      {/if}

      <!-- Players List -->
      <div class="space-y-4 mb-8">
        <h3 class="text-xl font-bold mb-4">Players in Lobby</h3>
        
        {#each players as player}
          <div class="flex items-center justify-between p-4 bg-white/5 rounded-lg border border-white/10">
            <div class="flex items-center gap-4">
              <div class="w-12 h-12 rounded-full bg-gradient-to-br from-purple-400 to-blue-500 flex items-center justify-center">
                <span class="text-xl font-bold text-white">
                  {player.username.charAt(0).toUpperCase()}
                </span>
              </div>
              
              <div>
                <div class="flex items-center gap-2">
                  <span class="font-bold text-white">{player.username}</span>
                  {#if player.isOwn}
                    <span class="text-xs px-2 py-1 bg-purple-500/30 text-purple-300 rounded-full">You</span>
                  {/if}
                </div>
                <div class="text-sm text-gray-400">
                  {gameType === "pong" ? 
                    player.sessionId === players[0]?.sessionId ? "Left Paddle" : "Right Paddle"
                    : "Player"}
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
      </div>

      <!-- Ready Button -->
      {#if ownPlayer && !gameStarting}
        <div class="text-center">
          <button 
            class="btn {ownPlayer.ready ? 'btn-secondary' : 'btn-primary'} text-lg px-8 py-3"
            on:click={toggleReady}
            disabled={connecting}
          >
            {ownPlayer.ready ? "❌ Not Ready" : "✅ Ready Up"}
          </button>
          
          <p class="text-sm text-gray-400 mt-3">
            {ownPlayer.ready 
              ? "Waiting for other players to ready up..." 
              : "Click ready when you're prepared to play!"}
          </p>
        </div>
      {/if}

      <!-- Game Rules -->
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
{/if}