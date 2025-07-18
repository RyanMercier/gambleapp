<script>
  import { onMount } from "svelte";
  import BalanceGame from "./BalanceGame.svelte";
  
  let currentView = "lobby"; // "lobby" | "balance"
  let availableGames = [];
  let client = null;
  let lobbyRoom = null;
  let gameRoom = null;
  let connecting = false;
  let error = null;
  let playersInLobby = 0;

  const gameInfo = {
    balance: {
      name: "Balance Game",
      description: "Keep your stick balanced while avoiding falling plates. Last player standing wins!",
      minPlayers: 2,
      maxPlayers: 8,
      difficulty: "Medium"
    }
  };

  onMount(async () => {
    connectToLobby();
  });

  async function connectToLobby() {
    try {
      connecting = true;
      error = null;
      
      const Colyseus = await import("colyseus.js");
      client = new Colyseus.Client("ws://localhost:2567");
      
      console.log("Connecting to lobby...");
      lobbyRoom = await client.joinOrCreate("lobby");
      console.log("Connected to lobby successfully");
      
      // Handle available games
      lobbyRoom.onMessage("available_games", (data) => {
        availableGames = data.games;
        console.log("Available games received:", availableGames);
      });

      // Handle lobby state changes
      lobbyRoom.onStateChange((state) => {
        playersInLobby = state.players?.size || 0;
      });

      connecting = false;
      
    } catch (err) {
      console.error("Failed to connect to lobby:", err);
      error = "Failed to connect to server. Make sure the server is running on port 2567.";
      connecting = false;
    }
  }

  async function joinGame(gameType) {
    if (!client || connecting) return;
    
    try {
      connecting = true;
      console.log(`Joining ${gameType} game...`);
      
      // Leave lobby
      if (lobbyRoom) {
        lobbyRoom.leave();
        lobbyRoom = null;
      }
      
      // Join game room
      gameRoom = await client.joinOrCreate(gameType);
      console.log(`Successfully joined ${gameType} game`);
      
      currentView = gameType;
      connecting = false;
      
    } catch (err) {
      console.error(`Failed to join ${gameType}:`, err);
      error = `Failed to join ${gameType} game. Please try again.`;
      connecting = false;
      
      // Reconnect to lobby
      setTimeout(connectToLobby, 1000);
    }
  }

  function backToLobby() {
    console.log("Returning to lobby...");
    
    // Leave game room
    if (gameRoom) {
      gameRoom.leave();
      gameRoom = null;
    }
    
    currentView = "lobby";
    
    // Reconnect to lobby
    setTimeout(connectToLobby, 500);
  }

  function retry() {
    error = null;
    connectToLobby();
  }
</script>

{#if error}
  <!-- Error State -->
  <div class="error-container">
    <div class="error-card">
      <div class="error-icon">!</div>
      <h2>Connection Error</h2>
      <p>{error}</p>
      <div class="error-actions">
        <button on:click={retry} class="retry-btn">
          Try Again
        </button>
        <button on:click={() => location.reload()} class="reload-btn">
          Reload Page
        </button>
      </div>
    </div>
  </div>

{:else if currentView === "balance"}
  <!-- Balance Game -->
  <BalanceGame {gameRoom} onBack={backToLobby} />

{:else}
  <!-- Lobby -->
  <div class="lobby-container">
    <div class="lobby-header">
      <h1>Game Lobby</h1>
      <p>Choose a game to play with other players</p>
      <div class="lobby-stats">
        <span class="stat">
          {playersInLobby} players in lobby
        </span>
        <span class="stat status-{connecting ? 'connecting' : 'connected'}">
          {connecting ? 'Connecting...' : 'Connected'}
        </span>
      </div>
    </div>

    {#if connecting}
      <div class="loading-state">
        <div class="spinner"></div>
        <p>Connecting to game lobby...</p>
      </div>
    
    {:else if availableGames.length === 0}
      <div class="no-games">
        <div class="no-games-icon">No Games</div>
        <h3>No games available</h3>
        <p>The server might be starting up. Please wait a moment.</p>
        <button on:click={retry} class="retry-btn">Refresh</button>
      </div>
    
    {:else}
      <div class="games-section">
        <h2>Available Games</h2>
        <div class="games-grid">
          {#each availableGames as gameType}
            {#if gameInfo[gameType]}
              {@const info = gameInfo[gameType]}
              <div class="game-card" class:connecting on:click={() => joinGame(gameType)}>
                <div class="game-header">
                  <div class="game-title">{info.name}</div>
                  <div class="game-difficulty difficulty-{info.difficulty.toLowerCase()}">
                    {info.difficulty}
                  </div>
                </div>
                
                <p class="game-description">{info.description}</p>
                
                <div class="game-meta">
                  <span class="players">{info.minPlayers}-{info.maxPlayers} players</span>
                </div>
                
                <button class="play-btn" disabled={connecting}>
                  {connecting ? 'Joining...' : 'Play Now'}
                </button>
              </div>
            {/if}
          {/each}
        </div>
      </div>
      
      <div class="lobby-footer">
        <p>More games coming soon! Open multiple tabs to test multiplayer.</p>
      </div>
    {/if}
  </div>
{/if}

<style>
  .lobby-container {
    padding: 2rem;
    max-width: 1000px;
    margin: 0 auto;
    min-height: 100vh;
  }

  .lobby-header {
    text-align: center;
    margin-bottom: 3rem;
  }

  .lobby-header h1 {
    font-size: 2.5rem;
    margin: 0 0 0.5rem 0;
    color: #A78BFA;
  }

  .lobby-header p {
    font-size: 1.1rem;
    color: #9CA3AF;
    margin: 0 0 1rem 0;
  }

  .lobby-stats {
    display: flex;
    justify-content: center;
    gap: 2rem;
    margin-top: 1rem;
  }

  .stat {
    padding: 0.5rem 1rem;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 20px;
    font-size: 0.9rem;
    color: #E5E7EB;
  }

  .status-connected {
    background: rgba(34, 197, 94, 0.1);
    color: #22C55E;
  }

  .status-connecting {
    background: rgba(249, 115, 22, 0.1);
    color: #F97316;
  }

  .games-section h2 {
    text-align: center;
    color: #F0F0F0;
    margin-bottom: 2rem;
  }

  .games-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 2rem;
    margin-bottom: 3rem;
  }

  .game-card {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0.08));
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 1.5rem;
    cursor: pointer;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
  }

  .game-card:hover:not(.connecting) {
    transform: translateY(-4px);
    border-color: #A78BFA;
    box-shadow: 0 8px 32px rgba(167, 139, 250, 0.2);
  }

  .game-card.connecting {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .game-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .game-emoji {
    font-size: 2.5rem;
  }

  .game-title {
    font-size: 1.5rem;
    font-weight: 600;
    color: #F0F0F0;
  }

  .game-difficulty {
    padding: 0.25rem 0.75rem;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  .difficulty-easy {
    background: rgba(34, 197, 94, 0.2);
    color: #22C55E;
  }

  .difficulty-medium {
    background: rgba(249, 115, 22, 0.2);
    color: #F97316;
  }

  .difficulty-hard {
    background: rgba(239, 68, 68, 0.2);
    color: #EF4444;
  }

  .game-card h3 {
    font-size: 1.5rem;
    margin: 0 0 1rem 0;
    color: #F0F0F0;
  }

  .game-description {
    color: #9CA3AF;
    line-height: 1.5;
    margin: 0 0 1.5rem 0;
  }

  .game-meta {
    margin-bottom: 1.5rem;
  }

  .players {
    color: #60A5FA;
    font-weight: 500;
    font-size: 0.9rem;
  }

  .play-btn {
    width: 100%;
    padding: 0.75rem;
    background: linear-gradient(135deg, #7C3AED, #A78BFA);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .play-btn:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(124, 58, 237, 0.4);
  }

  .play-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .loading-state, .no-games {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 3rem;
    text-align: center;
  }

  .no-games-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 3px solid rgba(167, 139, 250, 0.3);
    border-top: 3px solid #A78BFA;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 1rem;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  .error-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    padding: 2rem;
  }

  .error-card {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 16px;
    padding: 3rem;
    text-align: center;
    max-width: 400px;
  }

  .error-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
    color: #EF4444;
    font-weight: bold;
  }

  .error-card h2 {
    color: #EF4444;
    margin: 0 0 1rem 0;
  }

  .error-card p {
    color: #D1D5DB;
    margin: 0 0 2rem 0;
  }

  .error-actions {
    display: flex;
    gap: 1rem;
    justify-content: center;
  }

  .retry-btn, .reload-btn {
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 600;
    transition: all 0.2s;
  }

  .retry-btn {
    background: #7C3AED;
    color: white;
  }

  .retry-btn:hover {
    background: #6D28D9;
  }

  .reload-btn {
    background: #374151;
    color: white;
  }

  .reload-btn:hover {
    background: #4B5563;
  }

  .lobby-footer {
    text-align: center;
    padding: 2rem;
    color: #6B7280;
  }
</style>