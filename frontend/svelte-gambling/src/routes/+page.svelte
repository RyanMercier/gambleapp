<!-- frontend/svelte-gambling/src/routes/+page.svelte -->
<script>
  import { goto } from '$app/navigation';
  
  function handleGetStarted() {
    goto('/browse');
  }
</script>

<svelte:head>
  <title>TrendBet - Trade Attention Like Stocks</title>
  <meta name="description" content="The world's first attention economy trading platform. Trade Google Trends data on politicians, celebrities, countries, and games.">
</svelte:head>

<div class="min-h-screen flex flex-col items-center justify-center p-6 bg-gradient-to-br from-gray-900 via-blue-900 to-indigo-900">
  <div class="max-w-6xl mx-auto text-center">
    
    <!-- Hero Section -->
    <div class="mb-16">
      <h1 class="text-5xl md:text-7xl font-bold mb-6 bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400 bg-clip-text text-transparent">
        TrendBet
      </h1>
      <p class="text-xl md:text-2xl text-gray-300 mb-4">
        🌟 The world's first attention economy trading platform 🌟
      </p>
      <p class="text-lg text-gray-400 mb-4">
        Buy and sell attention shares based on real-time Google Trends data.
      </p>
      <p class="text-lg text-blue-300 mb-12">
        Trade attention like stocks • Real data, real profits, fake money (for now)
      </p>
    </div>

    <!-- Call to Action -->
    <div class="flex justify-center items-center mb-16">
      <button 
        on:click={handleGetStarted} 
        class="btn btn-primary text-xl px-12 py-6 text-white font-bold bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 transform hover:scale-105 transition-all duration-300 shadow-2xl border-2 border-blue-400/30 hover:border-blue-300/50"
      >
        📈 Start Trading Attention
      </button>
    </div>

    <!-- Trading Categories -->
    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-12">
      <div class="card text-center group hover:scale-105 transition-transform duration-300">
        <div class="text-3xl mb-3 group-hover:animate-bounce">🏛️</div>
        <h3 class="text-sm font-bold mb-1">Politicians</h3>
        <p class="text-gray-400 text-xs">
          Trump, Biden & more
        </p>
      </div>
      
      <div class="card text-center group hover:scale-105 transition-transform duration-300">
        <div class="text-3xl mb-3 group-hover:animate-bounce">🌟</div>
        <h3 class="text-sm font-bold mb-1">Celebrities</h3>
        <p class="text-gray-400 text-xs">
          Musk, MrBeast & more
        </p>
      </div>
      
      <div class="card text-center group hover:scale-105 transition-transform duration-300">
        <div class="text-3xl mb-3 group-hover:animate-bounce">🌍</div>
        <h3 class="text-sm font-bold mb-1">Countries</h3>
        <p class="text-gray-400 text-xs">
          USA, China & more
        </p>
      </div>

      <div class="card text-center group hover:scale-105 transition-transform duration-300">
        <div class="text-3xl mb-3 group-hover:animate-bounce">🎮</div>
        <h3 class="text-sm font-bold mb-1">Games</h3>
        <p class="text-gray-400 text-xs">
          Fortnite, League & more
        </p>
      </div>

      <div class="card text-center group hover:scale-105 transition-transform duration-300">
        <div class="text-3xl mb-3 group-hover:animate-bounce">📈</div>
        <h3 class="text-sm font-bold mb-1">Stocks</h3>
        <p class="text-gray-400 text-xs">
          Tesla, Apple & more
        </p>
      </div>

      <div class="card text-center group hover:scale-105 transition-transform duration-300">
        <div class="text-3xl mb-3 group-hover:animate-bounce">₿</div>
        <h3 class="text-sm font-bold mb-1">Crypto</h3>
        <p class="text-gray-400 text-xs">
          Bitcoin, Ethereum & more
        </p>
      </div>
    </div>

    <!-- How It Works -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
      <div class="card text-center">
        <div class="text-3xl mb-4">🔍</div>
        <h3 class="text-xl font-bold mb-2">1. Choose from Curated Lists</h3>
        <p class="text-gray-400 text-sm">
          Pick from pre-approved politicians, celebrities, countries, and games. No manipulation possible.
        </p>
      </div>
      
      <div class="card text-center">
        <div class="text-3xl mb-4">📊</div>
        <h3 class="text-xl font-bold mb-2">2. Track Attention</h3>
        <p class="text-gray-400 text-sm">
          Google Trends data drives share prices. High attention = higher prices.
        </p>
      </div>
      
      <div class="card text-center">
        <div class="text-3xl mb-4">💱</div>
        <h3 class="text-xl font-bold mb-2">3. Trade & Compete</h3>
        <p class="text-gray-400 text-sm">
          Buy low, sell high. Join tournaments and compete against other traders.
        </p>
      </div>
    </div>

    <!-- Features -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
      <div class="card text-left">
        <h3 class="text-xl font-bold mb-4 flex items-center gap-2">
          ⚡ Real-Time Trading
        </h3>
        <ul class="space-y-2 text-gray-300">
          <li>• Live Google Trends data updates</li>
          <li>• Instant buy/sell execution</li>
          <li>• Real-time P&L tracking</li>
          <li>• Dynamic pricing based on attention</li>
        </ul>
      </div>

      <div class="card text-left">
        <h3 class="text-xl font-bold mb-4 flex items-center gap-2">
          🏆 Competitive Tournaments
        </h3>
        <ul class="space-y-2 text-gray-300">
          <li>• Daily, weekly & monthly competitions</li>
          <li>• Prize pools from entry fees</li>
          <li>• Leaderboards & rankings</li>
          <li>• Skill-based, not gambling</li>
        </ul>
      </div>
    </div>

    <!-- New Features Highlight -->
    <div class="card mb-12 bg-gradient-to-r from-green-500/10 to-blue-500/10 border-green-500/20">
      <h3 class="text-xl font-bold mb-4 text-green-400">🎮 New Gaming Category!</h3>
      <p class="text-gray-300 mb-4">
        Trade attention on the hottest games: Fortnite, League of Legends, Minecraft, and more. 
        Perfect for the gaming community who understands competitive markets.
      </p>
      <div class="flex flex-wrap gap-2 justify-center">
        <span class="px-3 py-1 bg-blue-500/20 text-blue-300 rounded-full text-sm">🔥 Fortnite</span>
        <span class="px-3 py-1 bg-purple-500/20 text-purple-300 rounded-full text-sm">⚔️ League of Legends</span>
        <span class="px-3 py-1 bg-green-500/20 text-green-300 rounded-full text-sm">🟫 Minecraft</span>
        <span class="px-3 py-1 bg-orange-500/20 text-orange-300 rounded-full text-sm">🎯 Valorant</span>
      </div>
    </div>

    <!-- Anti-Manipulation Notice -->
    <div class="card mb-12 bg-gradient-to-r from-yellow-500/10 to-orange-500/10 border-yellow-500/20">
      <h3 class="text-lg font-bold mb-2 text-yellow-400">🛡️ Fair & Manipulation-Free</h3>
      <p class="text-gray-300 text-sm">
        Only pre-approved, quality targets can be traded. No obscure terms or manipulation possible. 
        Every tournament is fair competition on recognizable names everyone knows.
      </p>
    </div>

    <!-- Stats Display -->
    <div class="flex justify-center items-center gap-8 text-center">
      <div>
        <div class="text-2xl font-bold text-blue-400">Live</div>
        <div class="text-sm text-gray-400">Google Trends</div>
      </div>
      <div class="w-px h-12 bg-white/20"></div>
      <div>
        <div class="text-2xl font-bold text-indigo-400">300+</div>
        <div class="text-sm text-gray-400">Curated Targets</div>
      </div>
      <div class="w-px h-12 bg-white/20"></div>
      <div>
        <div class="text-2xl font-bold text-emerald-400">24/7</div>
        <div class="text-sm text-gray-400">Trading</div>
      </div>
      <div class="w-px h-12 bg-white/20"></div>
      <div>
        <div class="text-2xl font-bold text-cyan-400">$1000</div>
        <div class="text-sm text-gray-400">Starting Balance</div>
      </div>
    </div>

    <!-- Beta Notice -->
    <div class="mt-12 p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
      <p class="text-blue-300 text-sm">
        🚀 <strong>Beta Version</strong> - Currently using fake currency for testing. Real money trading coming soon!
      </p>
    </div>
  </div>
</div>

<style>
  .card {
    @apply bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-6;
  }
  
  .btn-primary {
    @apply bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed;
  }
</style>