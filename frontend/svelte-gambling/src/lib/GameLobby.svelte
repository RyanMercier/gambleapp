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
      
      console.log(`🎮 Connecting to ${gameType}_lobby as ${username}...`);
      
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
      error = `Failed to connect to ${gameType} lobby. Make sure the server is running.`;
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
      updateFromState(lobbyRoom.state);
    });
    
    // Handle player ready state change
    lobbyRoom.onMessage("player_ready_changed", (data) => {
      console.log("🎯 Player ready changed:", data);
      updateFromState(lobbyRoom.state);
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
    
    // Handle chat messages
    lobbyRoom.onMessage("chat_message", (data) => {
      addChatMessage(data.username, data.message, data.timestamp);
    });
    
    // Handle room errors
    lobbyRoom.onError((code, message) => {
      console.error("Room error:", code, message);
      error = `Room error: ${message}`;
    });
    
    // Handle initial lobby state
    lobbyRoom.onStateChange.once((state) => {
      console.log("📊 Initial state received");
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
      updateFromState(state);
    });
  }
  
  function updateFromState(state) {
    if (!state || !state.players) return;
    
    players = Array.from(state.players.entries()).map(([sessionId, player]) => ({
      sessionId,
      username: player.username,
      ready: player.ready,
      joinedAt: player.joinedAt,
      isOwn: sessionId === lobbyRoom.sessionId
    }));
    
    ownPlayer = players.find(p => p.isOwn) || null;
  }
  
  async function joinGame(roomId) {
    try {
      console.log(`🎮 Joining game room: ${roomId}`);
      
      gameRoom = await client.joinById(roomId);
      
      console.log("✅ Successfully joined game room");
      
      // Leave lobby room
      if (lobbyRoom) {
        lobbyRoom.leave();
        lobbyRoom = null;
      }
      
      // Switch to game view
      currentView = "game";
      
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
      lobbyRoom.send("toggle_ready");
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
    
    // Auto-scroll to bottom
    setTimeout(() => {
      if (chatContainer) {
        chatContainer.scrollTop = chatContainer.scrollHeight;
      }
    }, 10);
  }
  
  function sendChatMessage() {
    const message = newMessage.trim();
    if (message && lobbyRoom && !connecting) {
      lobbyRoom.send("chat_message", { text: message });
      newMessage = "";
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
  <div class="min-h-screen flex items-center justify-center p-6 bg-gradient-to-br from-gray-900 to-purple-900">
    <div class="card max-w-md w-full text-center bg-black/40 backdrop-blur-sm">
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
    </div>
  </div>

{:else if currentView === "game"}
  <!-- Game View -->
  <BalanceGame {gameRoom} onBack={handleBackFromGame} />

{:else}
  <!-- Lobby View -->
  <div class="min-h-screen flex flex-col bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900">
    <!-- Header -->
    <div class="flex items-center justify-between p-4 bg-black/40 backdrop-blur-sm border-b border-white/10">
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
            {currentGameInfo?.name} Lobby
          </h1>
          <p class="text-sm text-gray-400">{currentGameInfo?.description}</p>
        </div>
      </div>
      
      <div class="text-right">
        <div class="text-lg font-semibold">
          {players.length}/{currentGameInfo?.maxPlayers} Players
        </div>
        <div class="text-sm text-gray-400">
          {connecting ? 'Connecting...' : gameStarting ? `Starting in ${countdown}...` : 'Waiting for players...'}
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="flex-1 flex overflow-hidden">
      <!-- Players Panel -->
      <div class="flex-1 flex flex-col p-6">
        <h3 class="text-xl font-semibold mb-4">Players in Lobby</h3>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3 overflow-y-auto">
          {#each players as player}
            <div class="flex items-center justify-between p-4 rounded-lg bg-white/10 backdrop-blur-sm border {player.ready ? 'border-green-400/50' : 'border-white/20'} {player.isOwn ? 'ring-2 ring-purple-400' : ''}">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-full bg-gradient-to-br from-purple-400 to-blue-500 flex items-center justify-center text-white font-bold">
                  {player.username.charAt(0).toUpperCase()}
                </div>
                
                <div>
                  <div class="font-semibold flex items-center gap-2">
                    {player.username}
                    {#if player.isOwn}
                      <span class="text-xs bg-purple-500 px-2 py-1 rounded text-white">You</span>
                    {/if}
                  </div>
                  <div class="text-sm {player.ready ? 'text-green-400' : 'text-gray-400'}">
                    {player.ready ? "Ready" : "Not Ready"}
                  </div>
                </div>
              </div>
              
              <div class="text-2xl">
                {player.ready ? "✅" : "⏳"}
              </div>
            </div>
          {/each}
          
          {#if players.length === 0 && !connecting}
            <div class="col-span-2 text-center text-gray-400 py-12">
              <div class="text-6xl mb-4">👥</div>
              <div class="text-xl">Waiting for players to join...</div>
              <div class="text-sm mt-2">Be the first one here!</div>
            </div>
          {/if}
          
          {#if connecting}
            <div class="col-span-2 text-center text-gray-400 py-12">
              <div class="w-12 h-12 border-3 border-purple-400/30 border-t-purple-400 rounded-full animate-spin mx-auto mb-4"></div>
              <div>Connecting to lobby...</div>
            </div>
          {/if}
        </div>

        <!-- Ready Button -->
        <div class="mt-6 flex justify-center">
          {#if ownPlayer && !gameStarting}
            <button 
              class="btn btn-lg {ownPlayer.ready ? 'btn-success' : 'btn-primary'} px-8 py-3 text-lg"
              on:click={toggleReady}
              disabled={connecting}
            >
              {ownPlayer.ready ? "✓ Ready" : "Click to Ready Up"}
            </button>
          {:else if gameStarting}
            <div class="text-2xl font-bold text-yellow-400 animate-pulse">
              Game starting in {countdown}...
            </div>
          {/if}
        </div>
      </div>

      <!-- Chat Panel -->
      <div class="w-96 chat-container">
        <div class="chat-header">
          <h3 class="font-semibold text-lg">Lobby Chat</h3>
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
              <div class="text-sm">Say hello to other players!</div>
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
              on:keydown={handleKeyPress}
              disabled={!lobbyRoom || connecting}
            />
            <button 
              class="chat-send-btn"
              on:click={sendChatMessage}
              disabled={!newMessage.trim() || !lobbyRoom || connecting}
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  /* Custom scrollbar for chat */
  .overflow-y-auto::-webkit-scrollbar {
    width: 6px;
  }
  
  .overflow-y-auto::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.2);
  }
  
  .overflow-y-auto::-webkit-scrollbar-thumb {
    background: rgba(139, 92, 246, 0.5);
    border-radius: 3px;
  }
  
  .overflow-y-auto::-webkit-scrollbar-thumb:hover {
    background: rgba(139, 92, 246, 0.7);
  }
  
  .btn-lg {
    font-size: 1.125rem;
    padding: 0.75rem 2rem;
  }
</style>