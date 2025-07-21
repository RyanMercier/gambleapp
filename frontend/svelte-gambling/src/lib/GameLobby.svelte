<script>
  import { onMount, onDestroy } from "svelte";
  import BalanceGame from "./BalanceGame.svelte";
  
  export let gameType = "balance";
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
  
  // Chat state
  let chatMessages = [];
  let newMessage = "";
  let chatContainer;
  
  // Game info
  const gameInfo = {
    balance: {
      name: "Balance Game",
      description: "Keep your stick balanced while avoiding falling plates. Last player standing wins!",
      icon: "🎯",
      minPlayers: 2,
      maxPlayers: 8
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
      // Force refresh of current state
      if (lobbyRoom.state) {
        updateFromState(lobbyRoom.state);
      }
    });
    
    // Handle player ready state change
    lobbyRoom.onMessage("player_ready_changed", (data) => {
      console.log("🎯 Player ready changed:", data);
      // Force refresh of current state
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
    
    // Handle chat messages
    lobbyRoom.onMessage("chat_message", (data) => {
      const message = {
        id: `${data.timestamp}_${Math.random()}`,
        username: data.username,
        message: data.message,
        timestamp: data.timestamp,
        isOwn: data.username === (ownPlayer?.username || "")
      };
      
      chatMessages = [...chatMessages, message];
      
      // Auto-scroll to bottom
      setTimeout(() => {
        if (chatContainer) {
          chatContainer.scrollTop = chatContainer.scrollHeight;
        }
      }, 10);
    });
    
    // Handle room errors
    lobbyRoom.onError((code, message) => {
      console.error("Room error:", code, message);
      error = `Room error: ${message}`;
    });
    
    // Handle initial lobby state
    lobbyRoom.onStateChange.once((state) => {
      console.log("📊 Initial state received");
      console.log("Raw state object:", state);
      console.log("State players:", state.players);
      console.log("State players size:", state.players?.size);
      console.log("Direct state access test:");
      console.log("  state.gameType:", state.gameType);
      console.log("  state.maxPlayers:", state.maxPlayers);
      console.log("  state.minPlayers:", state.minPlayers);
      console.log("  state.gameStarting:", state.gameStarting);
      
      updateFromState(state);
      
      // Set up player change listeners
      if (state.players) {
        state.players.onAdd = (player, sessionId) => {
          console.log(`Player added: ${sessionId} - ${player.username}`);
          updateFromState(state);
        };
        
        state.players.onRemove = (player, sessionId) => {
          console.log(`Player removed: ${sessionId}`);
          updateFromState(state);
        };
      }
    });

    // Handle lobby state changes
    lobbyRoom.onStateChange((state) => {
      console.log("State changed, updating...");
      updateFromState(state);
    });
  }
  
  function updateFromState(state) {
    // Safely handle state updates
    console.log("Updating from state:", state);
    
    if (!state) {
      console.warn("Received empty state");
      return;
    }
    
    // Test direct property access
    console.log("Direct state property access:");
    console.log("  gameType:", state.gameType);
    console.log("  maxPlayers:", state.maxPlayers);
    console.log("  minPlayers:", state.minPlayers);
    console.log("  gameStarting:", state.gameStarting);
    console.log("  countdown:", state.countdown);
    console.log("  players:", state.players);
    
    // Update game state first (these should work)
    gameStarting = state.gameStarting || false;
    countdown = state.countdown || 0;
    
    // Update players array safely
    if (state.players) {
      try {
        console.log("Processing players state:", state.players);
        console.log("Players size:", state.players.size);
        console.log("Players type:", typeof state.players);
        console.log("Players constructor:", state.players.constructor?.name);
        
        // For Colyseus MapSchema, we need to use forEach or direct access
        let playersData = [];
        
        if (typeof state.players.forEach === 'function') {
          // Use forEach to iterate over MapSchema
          console.log("Using forEach method");
          state.players.forEach((player, sessionId) => {
            console.log(`Found player: ${sessionId} -> ${player.username}`);
            playersData.push([sessionId, player]);
          });
        } else if (typeof state.players.entries === 'function') {
          // Fallback to entries method
          console.log("Using entries method");
          playersData = Array.from(state.players.entries());
        } else if (state.players.size !== undefined) {
          // Try to access via keys if it has size
          console.log("Trying manual iteration with size:", state.players.size);
          for (let i = 0; i < state.players.size; i++) {
            // This might not work, but worth trying
            console.log("Index", i, ":", state.players[i]);
          }
        } else {
          // Last resort: treat as object
          console.log("Treating as plain object");
          playersData = Object.entries(state.players);
        }
          
        console.log("Players data extracted:", playersData);
          
        players = playersData.map(([sessionId, player]) => ({
          sessionId,
          username: player.username || `Player${sessionId.slice(0, 4)}`,
          ready: player.ready || false,
          joinedAt: player.joinedAt || Date.now(),
          isOwn: sessionId === lobbyRoom.sessionId
        }));
        
        // Find own player
        ownPlayer = players.find(p => p.isOwn) || null;
        
        console.log("Processed players:", players);
        console.log("Own player:", ownPlayer);
        
      } catch (err) {
        console.error("Error processing players state:", err);
        console.error("State.players type:", typeof state.players);
        console.error("State.players constructor:", state.players?.constructor?.name);
        console.error("Full error:", err);
        players = [];
        ownPlayer = null;
      }
    } else {
      console.log("No players in state");
      console.log("Available state properties:", Object.keys(state));
      console.log("State prototype:", Object.getPrototypeOf(state));
    }
    
    console.log(`👥 Lobby updated: ${players.length} players, ${players.filter(p => p.ready).length} ready`);
  }
  
  async function joinGame(roomId) {
    try {
      console.log(`🎯 Joining game room: ${roomId}`);
      
      const user = JSON.parse(localStorage.getItem("user") || "{}");
      
      // Join the actual game room
      gameRoom = await client.joinById(roomId, {
        username: user.username || `Player${Date.now().toString().slice(-4)}`
      });
      
      // Leave lobby
      if (lobbyRoom) {
        lobbyRoom.leave();
        lobbyRoom = null;
      }
      
      currentView = "game";
      console.log("🎮 Successfully joined game!");
      
    } catch (err) {
      console.error("❌ Failed to join game:", err);
      error = "Failed to join game. Please try again.";
      
      // Try to reconnect to lobby
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
  
  function sendChatMessage() {
    const message = newMessage.trim();
    if (message && lobbyRoom && !connecting) {
      try {
        lobbyRoom.send("chat_message", { text: message });
        newMessage = "";
      } catch (err) {
        console.error("Error sending chat message:", err);
      }
    }
  }
  
  function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendChatMessage();
    }
  }
  
  function handleBackFromGame() {
    currentView = "lobby";
    gameRoom = null;
    
    // Reconnect to lobby
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
  <BalanceGame {gameRoom} onBack={handleBackFromGame} />

{:else}
  <!-- Lobby View -->
  <div class="game-container">
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
          {connecting ? "Connecting..." : "In Lobby"}
        </div>
      </div>
    </div>

    <div class="flex h-full">
      <!-- Players Panel -->
      <div class="w-80 bg-black/20 border-r border-white/10 flex flex-col">
        <div class="p-4 border-b border-white/10">
          <div class="flex items-center justify-between mb-4">
            <h3 class="font-semibold">Players</h3>
            {#if gameStarting}
              <div class="flex items-center gap-2 text-yellow-400 animate-pulse">
                <div class="w-2 h-2 bg-yellow-400 rounded-full"></div>
                Starting in {countdown}...
              </div>
            {/if}
          </div>
          
          <button 
            class="btn w-full {ownPlayer?.ready ? 'btn-success' : 'btn-primary'}"
            on:click={toggleReady}
            disabled={connecting || gameStarting}
          >
            {#if connecting}
              <div class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            {:else if ownPlayer?.ready}
              ✓ Ready
            {:else}
              Ready Up
            {/if}
          </button>
          
          <div class="text-xs text-gray-400 mt-2 text-center">
            Minimum {currentGameInfo?.minPlayers} players needed
          </div>
        </div>
        
        <div class="flex-1 overflow-y-auto p-4">
          {#each players as player}
            <div class="flex items-center gap-3 p-3 rounded-lg mb-2 {player.ready ? 'bg-green-500/20' : 'bg-white/5'} {player.isOwn ? 'ring-2 ring-purple-400' : ''}">
              
              <div class="w-10 h-10 rounded-full bg-gradient-to-br from-purple-400 to-blue-500 flex items-center justify-center text-white font-bold">
                {player.username.charAt(0).toUpperCase()}
              </div>
              
              <div class="flex-1 min-w-0">
                <div class="font-medium truncate flex items-center gap-2">
                  {player.username}
                  {#if player.isOwn}
                    <span class="text-xs bg-purple-500 px-1.5 py-0.5 rounded text-white">You</span>
                  {/if}
                </div>
                <div class="text-xs {player.ready ? 'text-green-400' : 'text-gray-400'}">
                  {player.ready ? "Ready" : "Not Ready"}
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
      </div>

      <!-- Chat Panel -->
      <div class="flex-1 flex flex-col">
        <div class="p-4 border-b border-white/10">
          <h3 class="font-semibold">Lobby Chat</h3>
        </div>
        
        <div class="flex-1 overflow-y-auto p-4 space-y-3" bind:this={chatContainer}>
          {#each chatMessages as message}
            <div class="flex gap-3 {message.isOwn ? 'justify-end' : ''}">
              <div class="max-w-xs {message.isOwn ? 'order-last' : ''}">
                <div class="p-3 rounded-lg {message.isOwn ? 'bg-purple-600' : 'bg-white/10'}">
                  
                  {#if !message.isOwn}
                    <div class="text-xs text-purple-400 mb-1">{message.username}</div>
                  {/if}
                  
                  <div class="text-sm">{message.message}</div>
                  
                  <div class="text-xs opacity-60 mt-1">
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            </div>
          {/each}
          
          {#if chatMessages.length === 0}
            <div class="text-center text-gray-400 py-8">
              <div class="text-4xl mb-2">💬</div>
              <div>No messages yet</div>
              <div class="text-sm">Say hello to other players!</div>
            </div>
          {/if}
        </div>
        
        <div class="p-4 border-t border-white/10">
          <div class="flex gap-2">
            <input
              type="text"
              placeholder="Type a message..."
              class="input flex-1"
              bind:value={newMessage}
              on:keydown={handleKeyPress}
              disabled={!lobbyRoom || gameStarting || connecting}
            />
            <button 
              class="btn btn-primary px-6"
              on:click={sendChatMessage}
              disabled={!newMessage.trim() || !lobbyRoom || gameStarting || connecting}
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
{/if}