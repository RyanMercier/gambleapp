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
      <p class="text-xl md:text-2xl text-gray-300 mb-12 max-w-2xl mx-auto leading-relaxed">
        The ultimate prediction platform where data meets intuition. 
        Forecast trends and test your analytical skills against the community.
      </p>
    </div>

    <!-- Call to Action -->
    <div class="flex justify-center items-center mb-16">
      <button 
        on:click={handleGetStarted} 
        class="btn btn-primary text-xl px-12 py-6 text-white font-bold bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 transform hover:scale-105 transition-all duration-300 shadow-2xl border-2 border-blue-400/30 hover:border-blue-300/50"
      >
        🔮 Start Predicting
      </button>
    </div>

    <!-- Features Grid -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
      <div class="card text-center group hover:scale-105 transition-transform duration-300">
        <div class="text-4xl mb-4 group-hover:animate-bounce">📊</div>
        <h3 class="text-xl font-bold mb-2">Data-Driven Insights</h3>
        <p class="text-gray-400 text-sm">
          Make informed predictions using real-time data and historical trends
        </p>
      </div>
      
      <div class="card text-center group hover:scale-105 transition-transform duration-300">
        <div class="text-4xl mb-4 group-hover:animate-bounce">🏆</div>
        <h3 class="text-xl font-bold mb-2">Skill-Based Forecasting</h3>
        <p class="text-gray-400 text-sm">
          Earn rewards based on prediction accuracy and analytical prowess
        </p>
      </div>
      
      <div class="card text-center group hover:scale-105 transition-transform duration-300">
        <div class="text-4xl mb-4 group-hover:animate-bounce">🌐</div>
        <h3 class="text-xl font-bold mb-2">Global Trends</h3>
        <p class="text-gray-400 text-sm">
          Predict outcomes across technology, finance, social media, and more
        </p>
      </div>
    </div>

    <!-- Stats Display -->
    <div class="flex justify-center items-center gap-8 text-center">
      <div>
        <div class="text-2xl font-bold text-blue-400">500+</div>
        <div class="text-sm text-gray-400">Active Predictors</div>
      </div>
      <div class="w-px h-12 bg-white/20"></div>
      <div>
        <div class="text-2xl font-bold text-indigo-400">5K+</div>
        <div class="text-sm text-gray-400">Predictions Made</div>
      </div>
      <div class="w-px h-12 bg-white/20"></div>
      <div>
        <div class="text-2xl font-bold text-emerald-400">Live</div>
        <div class="text-sm text-gray-400">Real-Time Data</div>
      </div>
    </div>
  </div>
</div>