<script>
  import { onMount } from "svelte";
  import BalanceGame from "./BalanceGame.svelte";
  
  let selectedGame = null;
  let availableGames = [];
  let client = null;
  let lobbyRoom = null;
  let gameRoom = null;
  let connecting = false;
  let error = null;

  const gameInfo = {
    balance: {
      name: "Balance Game",
      description: "Keep your stick balanced while avoiding falling plates",
      image: "🎯",
      players: "2-8 players",
      difficulty: "Medium"
    },
    race: {
      name: "Race Game", 
      description: "Navigate through obstacles to reach the finish line first",
      image: "🏁",
      players: "2-6 players",
      difficulty: "Easy"
    }
  };

  onMount(async () => {
    try {
      const Colyseus = await import("colyseus.js");
      client = new Colyseus.Client("ws://localhost:2567");
      
      // Connect to lobby to get available games
      lobbyRoom = await client.joinOrCreate("lobby");
      
      lobbyRoom.onMessage("available_games", (data) => {
        availableGames = data.games;
        console.log("Available games:", availableGames);
      });

      lobbyRoom.onMessage("redirect_to_game", (data) => {
        console.log("Redirecting to game:", data.gameType);
        joinGame(data.gameType);
      });

    } catch (err) {
      console.error("Failed to connect to lobby:", err);
      error = "Failed to connect to server. Please check if the server is running.";
    }
  });

  async function selectGame(gameType) {
    if (connecting) return;
    
    connecting = true;
    error = null;
    
    try {
      console.log("Selecting game:", gameType);
      
      // Leave lobby room
      if (lobbyRoom) {
        lobbyRoom.leave();
        lobbyRoom = null;
      }
      
      // Join the selected game directly
      await joinGame(gameType);
      
    } catch (err) {
      console.error("Failed to select game:", err);
      error = `Failed to join ${gameType} game. Please try again.`;
      connecting = false;
    }
  }

  async function joinGame(gameType) {
    try {
      console.log("Joining game:", gameType);
      gameRoom = await client.joinOrCreate(gameType);
      selectedGame = gameType;
      connecting = false;
      
      console.log("Successfully joined game:", gameType);
      
    } catch (err) {
      console.error("Failed to join game:", err);
      error = `Failed to join ${gameType} game. Please try again.`;
      connecting = false;
      selectedGame = null;
    }
  }

  function backToLobby() {
    if (gameRoom) {
      gameRoom.leave();
      gameRoom = null;
    }
    selectedGame = null;
    
    // Reconnect to lobby
    if (client) {
      client.joinOrCreate("lobby").then(room => {
        lobbyRoom = room;
        
        lobbyRoom.onMessage("available_games", (data) => {
          availableGames = data.games;
        });
      });
    }
  }
</script>

{#if error}
  <div class="error-message">
    <h3>Connection Error</h3>
    <p>{error}</p>
    <button on:click={() => location.reload()} class="retry-button">
      Retry Connection
    </button>
  </div>
{:else if selectedGame === "balance"}
  <BalanceGame {gameRoom} onBack={backToLobby} />
{:else if selectedGame === "race"}
  <div class="coming-soon">
    <h2>Race Game - Coming Soon!</h2>
    <button on:click={backToLobby} class="back-button">Back to Lobby</button>
  </div>
{:else}
  <!-- Game Selection Lobby -->
  <div class="lobby-container">
    <div class="lobby-header">
      <h1>🎮 Game Lobby</h1>
      <p>Choose a game to play with other players</p>
    </div>

    {#if connecting}
      <div class="connecting">
        <div class="spinner"></div>
        <p>Connecting to game...</p>
      </div>
    {:else if availableGames.length > 0}
      <div class="games-grid">
        {#each availableGames as gameType}
          {#if gameInfo[gameType]}
            <div class="game-card" on:click={() => selectGame(gameType)}>
              <div class="game-icon">{gameInfo[gameType].image}</div>
              <h3>{gameInfo[gameType].name}</h3>
              <p class="game-description">{gameInfo[gameType].description}</p>
              <div class="game-details">
                <span class="players">{gameInfo[gameType].players}</span>
                <span class="difficulty difficulty-{gameInfo[gameType].difficulty.toLowerCase()}">
                  {gameInfo[gameType].difficulty}
                </span>
              </div>
              <button class="play-button">Play Now</button>
            </div>
          {/if}
        {/each}
      </div>
    {:else}
      <div class="loading">
        <div class="spinner"></div>
        <p>Loading available games...</p>
      </div>
    {/if}

    <div class="lobby-footer">
      <p>More games coming soon!</p>
    </div>
  </div>
{/if}

<style>
  .lobby-container {
    padding: 2rem;
    max-width: 1200px;
    margin: 0 auto;
  }

  .lobby-header {
    text-align: center;
    margin-bottom: 3rem;
  }

  .lobby-header h1 {
    font-size: 3rem;
    margin: 0 0 1rem 0;
    color: #A78BFA;
  }

  .lobby-header p {
    font-size: 1.2rem;
    color: #9CA3AF;
    margin: 0;
  }

  .games-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 2rem;
    margin-bottom: 3rem;
  }

  .game-card {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 2rem;
    text-align: center;
    cursor: pointer;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
  }

  .game-card:hover {
    transform: translateY(-4px);
    border-color: #A78BFA;
    box-shadow: 0 8px 32px rgba(167, 139, 250, 0.3);
  }

  .game-icon {
    font-size: 4rem;
    margin-bottom: 1rem;
  }

  .game-card h3 {
    font-size: 1.5rem;
    margin: 0 0 1rem 0;
    color: #F0F0F0;
  }

  .game-description {
    color: #9CA3AF;
    margin: 0 0 1.5rem 0;
    line-height: 1.5;
  }

  .game-details {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
  }

  .players {
    color: #60A5FA;
    font-weight: 500;
  }

  .difficulty {
    padding: 0.25rem 0.75rem;
    border-radius: 12px;
    font-size: 0.875rem;
    font-weight: 600;
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

  .play-button {
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

  .play-button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(124, 58, 237, 0.4);
  }

  .loading, .connecting {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 3rem;
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

  .error-message {
    text-align: center;
    padding: 3rem;
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 16px;
    margin: 2rem;
  }

  .error-message h3 {
    color: #EF4444;
    margin: 0 0 1rem 0;
  }

  .retry-button, .back-button {
    padding: 0.75rem 1.5rem;
    background: #DC2626;
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 600;
    margin-top: 1rem;
  }

  .retry-button:hover, .back-button:hover {
    background: #B91C1C;
  }

  .coming-soon {
    text-align: center;
    padding: 3rem;
  }

  .coming-soon h2 {
    color: #A78BFA;
    margin: 0 0 2rem 0;
  }

  .lobby-footer {
    text-align: center;
    padding: 2rem;
    color: #6B7280;
  }
</style>