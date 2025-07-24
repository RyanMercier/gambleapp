<script>
  import { onMount, onDestroy } from "svelte";
  import GameLobby from "./GameLobby.svelte";
  import Chat from "./Chat.svelte";
  
  let selectedGame = null;
  let connecting = false;
  let error = null;
  
  // Global chat state - simplified for unified chat
  let globalChatClient = null;
  let globalChatRoom = null;
  let globalMessages = [];
  let connectedToGlobalChat = false;

  const gameInfo = {
    pong: {
      name: "Pong",
      description: "Classic arcade action! Control your paddle and score against your opponent.",
      icon: "🏓",
      minPlayers: 2,
      maxPlayers: 2, // Exactly 2 players for Pong
      difficulty: "Easy",
      estimatedTime: "2-5 minutes"
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
  }
  
  // Chat handler for unified chat component
  function handleGlobalChatMessage(message) {
    if (globalChatRoom && connectedToGlobalChat) {
      try {
        globalChatRoom.send("chat_message", { text: message });
      } catch (err) {
        console.error("Error sending global chat message:", err);
      }
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
  <div class="min-h-screen flex">
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
              class="card bg-gray-800 hover:bg-gray-700 border border-gray-700 hover:border-purple-500 transition-all p-6 text-left group hover:scale-105 transform"
              on:click={() => selectGame(gameType)}
            >
              <!-- Game Icon -->
              <div class="text-5xl mb-4 group-hover:animate-bounce">{game.icon}</div>
              
              <!-- Game Info -->
              <h3 class="text-xl font-bold text-white mb-2">{game.name}</h3>
              <p class="text-gray-300 text-sm mb-4">{game.description}</p>
              
              <!-- Game Stats -->
              <div class="space-y-1 text-sm">
                <div class="flex justify-between">
                  <span class="text-gray-400">Players:</span>
                  <span class="text-blue-400">
                    {#if game.minPlayers === game.maxPlayers}
                      {game.maxPlayers}
                    {:else}
                      {game.minPlayers}-{game.maxPlayers}
                    {/if}
                  </span>
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
              
              <!-- Special badge for 2-player games -->
              {#if game.maxPlayers === 2}
                <div class="mt-3 inline-flex items-center px-2 py-1 rounded-full text-xs bg-purple-500/20 text-purple-300 border border-purple-500/30">
                  👥 1v1 Duel
                </div>
              {/if}
            </button>
          {/each}
          
          <!-- Coming Soon Card -->
          <div class="card bg-gray-900 border border-gray-600 p-6 text-left opacity-60">
            <div class="text-5xl mb-4">🚧</div>
            <h3 class="text-xl font-bold text-gray-400 mb-2">More Games Coming Soon!</h3>
            <p class="text-gray-500 text-sm mb-4">We're working on exciting new games. Stay tuned!</p>
            <div class="space-y-1 text-sm">
              <div class="flex justify-between">
                <span class="text-gray-600">Status:</span>
                <span class="text-yellow-500">In Development</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Global Chat Panel -->
    <div class="w-1/3 border-l border-white/10 bg-black/10 flex flex-col max-h-screen">
      <div class="p-3 border-b border-white/10 bg-black/20 flex-shrink-0">
        <h3 class="font-semibold text-sm flex items-center gap-2">
          🌍 Global Chat
          {#if connectedToGlobalChat}
            <span class="w-2 h-2 bg-green-400 rounded-full"></span>
          {:else}
            <span class="w-2 h-2 bg-red-400 rounded-full"></span>
          {/if}
        </h3>
        <p class="text-xs text-gray-400 mt-1">
          Chat with players from all games
        </p>
      </div>
      
      <div class="flex-1 min-h-0">
        <Chat 
          messages={globalMessages}
          onSendMessage={handleGlobalChatMessage}
          disabled={!connectedToGlobalChat}
          placeholder="Chat with everyone..."
        />
      </div>
    </div>
  </div>
{/if}