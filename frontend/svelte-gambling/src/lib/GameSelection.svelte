<script>
  import { onMount, onDestroy } from "svelte";
  
  export let onGameSelect;
  export let onChatMessage; // Pass chat messages to parent
  export let onChatConnected; // Pass connection status to parent
  export let onChatHandlerReady; // Pass chat handler to parent
  
  let connecting = false;
  
  // Global chat state
  let globalChatClient = null;
  let globalChatRoom = null;
  let connectedToGlobalChat = false;

  const gameInfo = {
    pong: {
      name: "Pong",
      description: "Classic arcade action! Control your paddle and score against your opponent.",
      icon: "🏓",
      minPlayers: 2,
      maxPlayers: 2,
      difficulty: "Easy",
      estimatedTime: "2-5 minutes"
    }
  };

  // Available games (only pong for now, balance game was removed)
  const availableGames = Object.keys(gameInfo);

  onMount(async () => {
    await connectToGlobalChat();
  });
  
  onDestroy(() => {
    disconnectFromGlobalChat();
  });

  async function connectToGlobalChat() {
    try {
      const Colyseus = await import("colyseus.js");
      globalChatClient = new Colyseus.Client("ws://localhost:2567");
      
      const user = JSON.parse(localStorage.getItem("user") || "{}");
      const username = user.username || `Player${Date.now().toString().slice(-4)}`;
      
      console.log("💬 Connecting to global chat...");
      
      // Connect to global chat room
      globalChatRoom = await globalChatClient.joinOrCreate("global_chat", {
        username: username
      });
      
      setupGlobalChatHandlers();
      connectedToGlobalChat = true;
      
      // Notify parent of connection status
      if (onChatConnected) {
        onChatConnected(true);
      }
      
      // Pass chat handler to parent
      if (onChatHandlerReady) {
        onChatHandlerReady(handleChatInput);
      }
      
      console.log("✅ Connected to global chat");
      
    } catch (err) {
      console.error("❌ Failed to connect to global chat:", err);
      connectedToGlobalChat = false;
      
      // Notify parent of connection failure
      if (onChatConnected) {
        onChatConnected(false);
      }
    }
  }
  
  function setupGlobalChatHandlers() {
    if (!globalChatRoom) return;

    globalChatRoom.onMessage("chat_message", (data) => {
      console.log("💬 Global chat message received:", data);
      
      const user = JSON.parse(localStorage.getItem("user") || "{}");
      
      // Pass message to parent
      if (onChatMessage) {
        onChatMessage({
          username: data.username,
          message: data.message,
          timestamp: data.timestamp,
          isOwn: data.username === user.username
        });
      }
    });
    
    globalChatRoom.onMessage("user_joined", (data) => {
      console.log("👤 User joined global chat:", data);
      
      if (onChatMessage) {
        onChatMessage({
          username: "System",
          message: `${data.username} joined the lobby`,
          timestamp: Date.now(),
          isSystem: true,
          isOwn: false
        });
      }
    });
    
    globalChatRoom.onMessage("user_left", (data) => {
      console.log("👋 User left global chat:", data);
      
      if (onChatMessage) {
        onChatMessage({
          username: "System", 
          message: `${data.username} left the lobby`,
          timestamp: Date.now(),
          isSystem: true,
          isOwn: false
        });
      }
    });

    globalChatRoom.onError((code, message) => {
      console.error("❌ Global chat room error:", code, message);
      connectedToGlobalChat = false;
      
      if (onChatConnected) {
        onChatConnected(false);
      }
    });
  }

  function disconnectFromGlobalChat() {
    console.log("🔌 Disconnecting from global chat...");
    
    if (globalChatRoom) {
      try {
        globalChatRoom.leave();
      } catch (err) {
        console.warn("Error leaving global chat room:", err);
      }
      globalChatRoom = null;
    }
    
    if (globalChatClient) {
      globalChatClient = null;
    }
    
    connectedToGlobalChat = false;
    
    // Notify parent of disconnection
    if (onChatConnected) {
      onChatConnected(false);
    }
  }

  // Handle chat input from unified chat component
  function handleChatInput(message) {
    console.log("📤 Sending global chat message:", message);
    
    if (globalChatRoom && connectedToGlobalChat) {
      try {
        globalChatRoom.send("chat_message", { text: message });
      } catch (err) {
        console.error("❌ Error sending global chat message:", err);
      }
    } else {
      console.warn("⚠️ Cannot send message - not connected to global chat");
    }
  }

  function selectGame(gameType) {
    if (connecting) return;
    console.log(`🎮 Selected game: ${gameType}`);
    
    // Disconnect from global chat before leaving (with small delay to prevent WebSocket errors)
    setTimeout(() => {
      disconnectFromGlobalChat();
    }, 100);
    
    onGameSelect(gameType);
  }
</script>

<!-- Game Selection Menu -->
<div class="min-h-screen flex flex-col">
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
  <div class="flex-1 px-6 pb-8">
    <div class="max-w-4xl mx-auto">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <!-- Available Games -->
        {#each availableGames as gameType}
          <div class="card card-hover cursor-pointer group" on:click={() => selectGame(gameType)}>
            <div class="text-center">
              <div class="text-6xl mb-4 group-hover:scale-110 transition-transform duration-300">
                {gameInfo[gameType].icon}
              </div>
              <h3 class="text-2xl font-bold mb-2 text-white">
                {gameInfo[gameType].name}
              </h3>
              <p class="text-gray-300 mb-6 leading-relaxed">
                {gameInfo[gameType].description}
              </p>
              
              <div class="space-y-3">
                <!-- Game Stats -->
                <div class="flex justify-between items-center text-sm">
                  <span class="text-gray-400">Players:</span>
                  <span class="text-white font-semibold">
                    {gameInfo[gameType].minPlayers === gameInfo[gameType].maxPlayers 
                      ? gameInfo[gameType].maxPlayers 
                      : `${gameInfo[gameType].minPlayers}-${gameInfo[gameType].maxPlayers}`}
                  </span>
                </div>
                
                <div class="flex justify-between items-center text-sm">
                  <span class="text-gray-400">Difficulty:</span>
                  <span class="text-green-400 font-semibold">{gameInfo[gameType].difficulty}</span>
                </div>
                
                <div class="flex justify-between items-center text-sm">
                  <span class="text-gray-400">Duration:</span>
                  <span class="text-blue-400 font-semibold">{gameInfo[gameType].estimatedTime}</span>
                </div>
                
                <!-- Play Button -->
                <button class="w-full btn btn-primary mt-4 group-hover:scale-105 transition-transform duration-300">
                  <span class="text-lg">🚀</span>
                  Play Now
                </button>
              </div>
            </div>
          </div>
        {/each}
        
        <!-- Coming Soon Games -->
        <div class="card opacity-50 cursor-not-allowed">
          <div class="text-center">
            <div class="text-6xl mb-4">🎯</div>
            <h3 class="text-2xl font-bold mb-2 text-white">More Games</h3>
            <p class="text-gray-300 mb-6">
              Additional skill-based games coming soon! Stay tuned!
            </p>
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
  </div>
</div>