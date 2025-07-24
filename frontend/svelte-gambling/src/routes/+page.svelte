<script>
  import { goto } from '$app/navigation';
  import { user } from '$lib/stores';

  function handleGetStarted() {
    if ($user) {
      goto('/game');
    } else {
      goto('/login');
    }
  }
</script>

<div class="min-h-screen flex items-center justify-center relative overflow-hidden">
  <!-- Background Animation -->
  <div class="absolute inset-0 opacity-30">
    <div class="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-500 rounded-full mix-blend-multiply filter blur-xl animate-pulse"></div>
    <div class="absolute top-1/3 right-1/4 w-96 h-96 bg-blue-500 rounded-full mix-blend-multiply filter blur-xl animate-pulse" style="animation-delay: 1s;"></div>
    <div class="absolute bottom-1/4 left-1/3 w-96 h-96 bg-pink-500 rounded-full mix-blend-multiply filter blur-xl animate-pulse" style="animation-delay: 2s;"></div>
  </div>

  <!-- Hero Content -->
  <div class="relative z-10 text-center max-w-4xl mx-auto px-6">
    <div class="mb-8">
      <h1 class="text-6xl md:text-8xl font-bold mb-6 bg-gradient-to-r from-purple-400 via-blue-500 to-purple-600 bg-clip-text text-transparent">
        Gamble Royale
      </h1>
      <p class="text-xl md:text-2xl text-gray-300 mb-12 max-w-2xl mx-auto leading-relaxed">
        The ultimate multiplayer gaming arena where skill meets strategy. 
        Compete with players worldwide in fast-paced skill games.
      </p>
    </div>

    <!-- Single Action Button -->
    <div class="flex justify-center items-center mb-16">
      <button 
        on:click={handleGetStarted} 
        class="btn btn-primary text-xl px-12 py-6 text-white font-bold bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 transform hover:scale-105 transition-all duration-300 shadow-2xl border-2 border-purple-400/30 hover:border-purple-300/50"
      >
        🚀 Enter the Arena
      </button>
    </div>

    <!-- Features Grid -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
      <div class="card text-center group hover:scale-105 transition-transform duration-300">
        <div class="text-4xl mb-4 group-hover:animate-bounce">⚡</div>
        <h3 class="text-xl font-bold mb-2">Real-Time Gaming</h3>
        <p class="text-gray-400 text-sm">
          Experience lag-free multiplayer action with our advanced networking technology
        </p>
      </div>
      
      <div class="card text-center group hover:scale-105 transition-transform duration-300">
        <div class="text-4xl mb-4 group-hover:animate-bounce">🏆</div>
        <h3 class="text-xl font-bold mb-2">Competitive Rankings</h3>
        <p class="text-gray-400 text-sm">
          Climb the leaderboards and prove you're the ultimate champion
        </p>
      </div>
      
      <div class="card text-center group hover:scale-105 transition-transform duration-300">
        <div class="text-4xl mb-4 group-hover:animate-bounce">🎯</div>
        <h3 class="text-xl font-bold mb-2">Skill-Based Games</h3>
        <p class="text-gray-400 text-sm">
          Pure skill gameplay - no luck involved, just pure talent and strategy
        </p>
      </div>
    </div>

    <!-- Stats Display -->
    <div class="flex justify-center items-center gap-8 text-center">
      <div>
        <div class="text-2xl font-bold text-purple-400">1K+</div>
        <div class="text-sm text-gray-400">Active Players</div>
      </div>
      <div class="w-px h-12 bg-white/20"></div>
      <div>
        <div class="text-2xl font-bold text-blue-400">10K+</div>
        <div class="text-sm text-gray-400">Games Played</div>
      </div>
      <div class="w-px h-12 bg-white/20"></div>
      <div>
        <div class="text-2xl font-bold text-green-400">24/7</div>
        <div class="text-sm text-gray-400">Uptime</div>
      </div>
    </div>
  </div>
</div>