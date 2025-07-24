<script>
  import { onMount, onDestroy } from "svelte";
  import GameSelection from "$lib/GameSelection.svelte";
  import GameLobby from "$lib/GameLobby.svelte";
  import PongGame from "$lib/PongGame.svelte";
  import Chat from "$lib/Chat.svelte";

  // Navigation state
  let currentView = "selection"; // "selection" | "lobby" | "game"
  let selectedGame = null;
  
  // Chat state - unified across all views
  let chatMessages = [];
  let chatConnected = false;
  let currentChatHandler = null; // Store current component's chat handler
  
  // Game state
  let gameRoom = null;

  // Navigation handlers
  function handleGameSelection(gameType) {
    selectedGame = gameType;
    currentView = "lobby";
    // Clear messages when switching to lobby
    chatMessages = [];
    chatConnected = false;
  }

  function handleBackToSelection() {
    currentView = "selection";
    selectedGame = null;
    gameRoom = null;
    // Clear messages when going back to selection
    chatMessages = [];
    chatConnected = false;
  }

  function handleGameStart(room) {
    gameRoom = room;
    currentView = "game";
    // Clear messages when starting game
    chatMessages = [];
    chatConnected = false;
  }

  function handleBackToLobby() {
    currentView = "lobby";
    gameRoom = null;
    // Clear messages when going back to lobby
    chatMessages = [];
    chatConnected = false;
  }

  // Chat connection status handler
  function handleChatConnected(connected) {
    chatConnected = connected;
    console.log(`💬 Chat connection status: ${connected}`);
  }

  // Store chat handler from current component
  function handleChatHandlerReady(handler) {
    currentChatHandler = handler;
    console.log(`🔗 Chat handler ready for ${currentView}`);
  }

  // Chat message handler - receives messages from child components
  function handleChatMessage(message) {
    console.log(`📨 Received chat message in route:`, message);
    
    const chatMessage = {
      id: `${message.timestamp}_${Math.random()}`,
      username: message.username,
      message: message.message,
      timestamp: message.timestamp,
      isOwn: message.isOwn || false,
      isSystem: message.isSystem || false
    };
    
    chatMessages = [...chatMessages, chatMessage];
    
    // Keep only last 100 messages
    if (chatMessages.length > 100) {
      chatMessages = chatMessages.slice(-100);
    }
  }

  // Handle outgoing chat messages from Chat component
  function handleSendMessage(message) {
    console.log(`📤 Sending chat message: ${message}`);
    
    if (currentChatHandler) {
      try {
        currentChatHandler(message);
      } catch (err) {
        console.error("Error sending chat message:", err);
      }
    } else {
      console.warn("No chat handler available");
    }
  }

  // Get appropriate chat placeholder and title
  $: chatPlaceholder = currentView === "selection" 
    ? "Chat with all players..." 
    : currentView === "lobby" 
    ? "Chat with lobby players..." 
    : "Chat with your opponent...";

  $: chatTitle = currentView === "selection" 
    ? "🌍 Global Chat" 
    : currentView === "lobby" 
    ? `🏓 ${selectedGame?.toUpperCase()} Lobby` 
    : `🎮 Game Chat`;
</script>

<svelte:head>
  <title>Play Games - Gamble Royale</title>
  <meta name="description" content="Choose from our collection of skill-based multiplayer games" />
</svelte:head>

<div class="min-h-screen flex">
  <!-- Main Game Area -->
  <div class="flex-1 flex flex-col">
    {#if currentView === "selection"}
      <GameSelection 
        onGameSelect={handleGameSelection}
        onChatMessage={handleChatMessage}
        onChatConnected={handleChatConnected}
        onChatHandlerReady={handleChatHandlerReady}
      />
    {:else if currentView === "lobby"}
      <GameLobby 
        gameType={selectedGame}
        onBack={handleBackToSelection}
        onGameStart={handleGameStart}
        onChatMessage={handleChatMessage}
        onChatConnected={handleChatConnected}
        onChatHandlerReady={handleChatHandlerReady}
      />
    {:else if currentView === "game"}
      <PongGame 
        {gameRoom}
        onBack={handleBackToLobby}
        onChatMessage={handleChatMessage}
        onChatConnected={handleChatConnected}
        onChatHandlerReady={handleChatHandlerReady}
      />
    {/if}
  </div>

  <!-- Unified Chat Panel -->
  <div class="w-80 border-l border-white/10 bg-black/10 flex flex-col">
    <!-- Chat Header -->
    <div class="p-3 border-b border-white/10 bg-black/20 flex-shrink-0">
      <h3 class="font-semibold text-sm flex items-center gap-2">
        {chatTitle}
        {#if chatConnected}
          <span class="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
        {:else}
          <span class="w-2 h-2 bg-red-400 rounded-full"></span>
        {/if}
      </h3>
      <p class="text-xs text-gray-400 mt-1">
        {currentView === "selection" ? "Chat with players from all games" :
         currentView === "lobby" ? "Chat with players in this lobby" :
         "Chat with your game opponent"}
      </p>
    </div>
    
    <!-- Chat Component -->
    <div class="flex-1 min-h-0">
      <Chat 
        messages={chatMessages}
        onSendMessage={handleSendMessage}
        disabled={!chatConnected}
        placeholder={chatPlaceholder}
      />
    </div>
  </div>
</div>