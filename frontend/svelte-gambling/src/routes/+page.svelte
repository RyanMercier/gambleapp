<script>
  import { goto } from '$app/navigation';
  import { user } from '$lib/stores';

  function handleGetStarted() {
    if ($user) {
      goto('/dashboard');
    } else {
      goto('/login');
    }
  }
</script>

<div class="min-h-screen flex items-center justify-center relative overflow-hidden">
  <!-- Background Animation -->
  <div class="absolute inset-0 opacity-30">
    <div class="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500 rounded-full mix-blend-multiply filter blur-xl animate-pulse"></div>
    <div class="absolute top-1/3 right-1/4 w-96 h-96 bg-indigo-500 rounded-full mix-blend-multiply filter blur-xl animate-pulse" style="animation-delay: 1s;"></div>
    <div class="absolute bottom-1/4 left-1/3 w-96 h-96 bg-cyan-500 rounded-full mix-blend-multiply filter blur-xl animate-pulse" style="animation-delay: 2s;"></div>
  </div>

  <!-- Hero Content -->
  <div class="relative z-10 text-center max-w-4xl mx-auto px-6">
    <div class="mb-8">
      <h1 class="text-6xl md:text-8xl font-bold mb-6 bg-gradient-to-r from-blue-400 via-indigo-500 to-blue-600 bg-clip-text text-transparent">
        TrendBet
      </h1>
      <p class="text-xl md:text-2xl text-gray-300 mb-6 max-w-3xl mx-auto leading-relaxed">
        The world's first <strong>attention economy trading platform</strong>. 
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
    <div class="grid grid-cols-2 md:grid-cols-4 gap-6 mb-12">
      <div class="card text-center group hover:scale-105 transition-transform duration-300">
        <div class="text-4xl mb-4 group-hover:animate-bounce">🏛️</div>
        <h3 class="text-lg font-bold mb-2">Politicians</h3>
        <p class="text-gray-400 text-sm">
          Trump, Biden, DeSantis & more
        </p>
      </div>
      
      <div class="card text-center group hover:scale-105 transition-transform duration-300">
        <div class="text-4xl mb-4 group-hover:animate-bounce">💰</div>
        <h3 class="text-lg font-bold mb-2">Billionaires</h3>
        <p class="text-gray-400 text-sm">
          Musk, Bezos, Gates & more
        </p>
      </div>
      
      <div class="card text-center group hover:scale-105 transition-transform duration-300">
        <div class="text-4xl mb-4 group-hover:animate-bounce">🌍</div>
        <h3 class="text-lg font-bold mb-2">Countries</h3>
        <p class="text-gray-400 text-sm">
          USA, China, Japan & more
        </p>
      </div>

      <div class="card text-center group hover:scale-105 transition-transform duration-300">
        <div class="text-4xl mb-4 group-hover:animate-bounce">📈</div>
        <h3 class="text-lg font-bold mb-2">Meme Stocks</h3>
        <p class="text-gray-400 text-sm">
          Tesla, GameStop, Bitcoin & more
        </p>
      </div>
    </div>

    <!-- How It Works -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
      <div class="card text-center">
        <div class="text-3xl mb-4">🔍</div>
        <h3 class="text-xl font-bold mb-2">1. Search Any Term</h3>
        <p class="text-gray-400 text-sm">
          Search for anyone or anything. We'll create a tradeable attention target instantly.
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
        <h3 class="text-xl font-bold mb-2">3. Trade & Profit</h3>
        <p class="text-gray-400 text-sm">
          Buy low, sell high. Build a portfolio of attention and compete in tournaments.
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

    <!-- Stats Display -->
    <div class="flex justify-center items-center gap-8 text-center">
      <div>
        <div class="text-2xl font-bold text-blue-400">Live</div>
        <div class="text-sm text-gray-400">Google Trends</div>
      </div>
      <div class="w-px h-12 bg-white/20"></div>
      <div>
        <div class="text-2xl font-bold text-indigo-400">100+</div>
        <div class="text-sm text-gray-400">Attention Targets</div>
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