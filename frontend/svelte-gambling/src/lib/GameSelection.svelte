<script>
  import { onMount, onDestroy } from "svelte";
  import GameLobby from "./GameLobby.svelte";
  
  let selectedGame = null;
  let connecting = false;
  let error = null;
  
  // Global chat state
  let globalChatClient = null;
  let globalChatRoom = null;
  let globalMessages = [];
  let newGlobalMessage = "";
  let globalChatContainer;
  let connectedToGlobalChat = false;

  const gameInfo = {
    balance: {
      name: "Balance Game",
      description: "Keep your stick balanced while avoiding falling plates. Last player standing wins!",
      icon: "🎯",
      minPlayers: 2,
      maxPlayers: 8,
      difficulty: "Medium",
      estimatedTime: "3-5 minutes"
    }
  };

  // Available games
  const availableGames = Object.keys(gameInfo);
  
  onMount(async () => {
    await connectToGlobalChat();
  });
  
  onDestroy(() => {
    if (globalChatRoom) {
      globalChatRoom.leave();
    }
    globalChatClient = null;
  });
  
  async function connectToGlobalChat() {
    try {
      const Colyseus = await import("colyseus.js");
      globalChatClient = new Colyseus.Client("ws://localhost:2567");
      
      const user = JSON.parse(localStorage.getItem("user") || "{}");
      const username = user.username || `Player${Date.now().toString().slice(-4)}`;
      
      // Connect to global chat room
      globalChatRoom = await globalChatClient.joinOrCreate("global_chat", {
        username: username
      });
      
      setupGlobalChatHandlers();
      connectedToGlobalChat = true;
      
      console.log("✅ Connected to global chat");
      
    } catch (err) {
      console.error("Failed to connect to global chat:", err);
      // Don't show error for global chat, it's optional
    }
  }
  
  function setupGlobalChatHandlers() {
    globalChatRoom.onMessage("chat_message", (data) => {
      addGlobalMessage(data.username, data.message, data.timestamp);
    });
    
    globalChatRoom.onMessage("user_joined", (data) => {
      addGlobalMessage("System", `${data.username} joined the lobby`, Date.now(), true);
    });
    
    globalChatRoom.onMessage("user_left", (data) => {
      addGlobalMessage("System", `${data.username} left the lobby`, Date.now(), true);
    });
  }
  
  function addGlobalMessage(username, message, timestamp, isSystem = false) {
    const user = JSON.parse(localStorage.getItem("user") || "{}");
    const msg = {
      id: `${timestamp}_${Math.random()}`,
      username: username,
      message: message,
      timestamp: timestamp,
      isOwn: username === user.username,
      isSystem: isSystem
    };
    
    globalMessages = [...globalMessages, msg];
    
    // Keep only last 100 messages
    if (globalMessages.length > 100) {
      globalMessages = globalMessages.slice(-100);
    }
    
    // Auto-scroll
    setTimeout(() => {
      if (globalChatContainer) {
        globalChatContainer.scrollTop = globalChatContainer.scrollHeight;
      }
    }, 10);
  }
  
  function sendGlobalMessage() {
    const message = newGlobalMessage.trim();
    if (message && globalChatRoom && connectedToGlobalChat) {
      globalChatRoom.send("chat_message", { text: message });
      newGlobalMessage = "";
    }
  }
  
  function handleGlobalChatKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendGlobalMessage();
    }
  }

  function selectGame(gameType) {
    if (connecting) return;
    console.log(`🎮 Selected game: ${gameType}`);
    selectedGame = gameType;
  }

  function backToSelection() {
    console.log("🔙 Back to game selection");
    selectedGame = null;
    error = null;
  }
</script>

{#if selectedGame}
  <GameLobby gameType={selectedGame} onBack={backToSelection} />
{:else}
  <!-- Game Selection Menu -->
  <div class="h-full flex">
    <!-- Main Content -->
    <div class="flex-1 flex flex-col">
      <!-- Header -->
      <div class="text-center py-8 px-6">
        <h1 class="text-4xl font-bold mb-4 text-white">
          🎮 Choose Your Game
        </h1>
        <p class="text-xl text-gray-300">
          Select a game to join and compete with players from around the world
        </p>
      </div>

      <!-- Game Grid -->
      <div class="flex-1 px-6 pb-8 overflow-y-auto">
        <div class="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-6">
          {#each availableGames as gameType}
            {@const game = gameInfo[gameType]}
            <button 
              class="card bg-gray-800 hover:bg-gray-700 border border-gray-700 hover:border-purple-500 transition-all p-6 text-left"
              on:click={() => selectGame(gameType)}
            >
              <!-- Game Icon -->
              <div class="text-5xl mb-4">{game.icon}</div>
              
              <!-- Game Info -->
              <h3 class="text-xl font-bold text-white mb-2">{game.name}</h3>
              <p class="text-gray-300 text-sm mb-4">{game.description}</p>
              
              <!-- Game Stats -->
              <div class="space-y-1 text-sm">
                <div class="flex justify-between">
                  <span class="text-gray-400">Players:</span>
                  <span class="text-blue-400">{game.minPlayers}-{game.maxPlayers}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-400">Duration:</span>
                  <span class="text-green-400">{game.estimatedTime}</span>
                </div>
                <div class="flex justify-between">
                  <span class="text-gray-400">Difficulty:</span>
                  <span class="{game.difficulty === 'Easy' ? 'text-green-400' : game.difficulty === 'Medium' ? 'text-yellow-400' : 'text-red-400'}">
                    {game.difficulty}
                  </span>
                </div>
              </div>
            </button>
          {/each}
        </div>
      </div>
    </div>

    <!-- Global Chat Sidebar -->
    <div class="w-80 chat-container">
      <div class="chat-header">
        <h3 class="font-semibold flex items-center gap-2">
          🌍 Global Chat
          {#if connectedToGlobalChat}
            <span class="w-2 h-2 bg-green-400 rounded-full"></span>
          {:else}
            <span class="w-2 h-2 bg-red-400 rounded-full"></span>
          {/if}
        </h3>
        <p class="text-xs text-gray-400 mt-1">Chat with players looking for games</p>
      </div>
      
      <div class="chat-messages" bind:this={globalChatContainer}>
        {#each globalMessages as message}
          {#if message.isSystem}
            <div class="chat-system-message">
              {message.message}
            </div>
          {:else}
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
          {/if}
        {/each}
        
        {#if globalMessages.length === 0}
          <div class="chat-empty">
            <div class="chat-empty-icon">🌍</div>
            <div>No messages yet</div>
            <div class="text-sm">Say hello!</div>
          </div>
        {/if}
      </div>
      
      <div class="chat-input-container">
        <div class="chat-input-group">
          <input
            type="text"
            placeholder={connectedToGlobalChat ? "Type a message..." : "Connecting..."}
            class="chat-input"
            bind:value={newGlobalMessage}
            on:keydown={handleGlobalChatKeyPress}
            disabled={!connectedToGlobalChat}
          />
          <button 
            class="chat-send-btn"
            on:click={sendGlobalMessage}
            disabled={!newGlobalMessage.trim() || !connectedToGlobalChat}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}