<script>
  import { onMount } from "svelte";
  import GameLobby from "./GameLobby.svelte";
  
  let selectedGame = null;
  let connecting = false;
  let error = null;

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
    // Future games can be added here
  };

  // Available games (no server connection needed)
  const availableGames = Object.keys(gameInfo);

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
  <div class="min-h-screen game-container">
    <div class="max-w-6xl mx-auto p-6">
      <!-- Header -->
      <div class="text-center mb-12">
        <h1 class="text-4xl font-bold mb-4 bg-gradient-to-r from-purple-400 to-blue-500 bg-clip-text text-transparent">
          🎮 Choose Your Game
        </h1>
        <p class="text-xl text-gray-300 max-w-2xl mx-auto">
          Select a game to join and compete with players from around the world
        </p>
      </div>

      {#if error}
        <div class="card bg-red-500/10 border-red-500/20 text-center mb-8">
          <h3 class="text-red-400 font-semibold mb-2">Error</h3>
          <p class="text-gray-300 mb-4">{error}</p>
          <button class="btn btn-primary" on:click={() => error = null}>
            Try Again
          </button>
        </div>
      {/if}

      <!-- Game Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
        {#each availableGames as gameType}
          {@const game = gameInfo[gameType]}
          <div class="card card-hover cursor-pointer group" on:click={() => selectGame(gameType)}>
            <!-- Game Icon -->
            <div class="text-center mb-4">
              <div class="text-6xl mb-3 group-hover:scale-110 transition-transform duration-300">
                {game.icon}
              </div>
              <h3 class="text-xl font-bold text-white mb-2">{game.name}</h3>
            </div>

            <!-- Game Info -->
            <div class="space-y-3 mb-6">
              <p class="text-gray-300 text-sm leading-relaxed">
                {game.description}
              </p>
              
              <div class="flex items-center justify-between text-sm">
                <span class="text-blue-400 font-medium">
                  👥 {game.minPlayers}-{game.maxPlayers} players
                </span>
                <span class="px-2 py-1 rounded-full text-xs font-semibold {game.difficulty === 'Easy' ? 'bg-green-500/20 text-green-400' : game.difficulty === 'Medium' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-red-500/20 text-red-400'}">
                  {game.difficulty}
                </span>
              </div>
              
              <div class="text-xs text-gray-400">
                ⏱️ ~{game.estimatedTime}
              </div>
            </div>

            <!-- Play Button -->
            <button class="btn btn-primary w-full group-hover:scale-105 transition-transform duration-200">
              🚀 Join Game
            </button>
          </div>
        {/each}
      </div>

      <!-- Info Section -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="card text-center">
          <div class="text-3xl mb-2">⚡</div>
          <h3 class="font-semibold mb-2">Fast Matchmaking</h3>
          <p class="text-sm text-gray-400">
            Join game lobbies instantly - no waiting for connections
          </p>
        </div>
        
        <div class="card text-center">
          <div class="text-3xl mb-2">💬</div>
          <h3 class="font-semibold mb-2">In-Game Chat</h3>
          <p class="text-sm text-gray-400">
            Chat with other players while waiting and playing
          </p>
        </div>
        
        <div class="card text-center">
          <div class="text-3xl mb-2">🏆</div>
          <h3 class="font-semibold mb-2">Competitive Play</h3>
          <p class="text-sm text-gray-400">
            Climb the leaderboards and prove your skills
          </p>
        </div>
      </div>

      <!-- Footer -->
      <div class="text-center mt-12">
        <p class="text-gray-400">
          More games coming soon! Each game has its own lobby system.
        </p>
      </div>
    </div>
  </div>
{/if}

<style>
  .game-container {
    background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-tertiary) 100%);
  }
</style>