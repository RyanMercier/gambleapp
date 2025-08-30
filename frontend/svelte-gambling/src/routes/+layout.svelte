<script>
  import { onMount, onDestroy } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import apiFetch from '$lib/api';
  import PnLDisplay from '$lib/PnLDisplay.svelte';

  let user = null;
  let loading = false;
  let tournamentBalances = [];
  let totalBalance = 0;
  let updateInterval = null;

  // FIX 5: Real-time updates for navigation
  const NAV_UPDATE_INTERVAL = 45000; // 45 seconds

  onMount(async () => {
    await loadUserData();
    setupNavUpdates();
  });

  onDestroy(() => {
    if (updateInterval) {
      clearInterval(updateInterval);
    }
  });

  function setupNavUpdates() {
    if (updateInterval) clearInterval(updateInterval);
    
    updateInterval = setInterval(async () => {
      // Only update if user is logged in
      if (user) {
        await loadTournamentBalances();
      }
    }, NAV_UPDATE_INTERVAL);
  }

  async function loadUserData() {
    try {
      const token = localStorage.getItem('auth_token');
      if (!token) return;

      // Get user profile
      const userData = await apiFetch('/auth/me');
      user = userData;

      // Load tournament balances
      await loadTournamentBalances();

    } catch (err) {
      console.error('Failed to load user data:', err);
      // Clear invalid token
      localStorage.removeItem('auth_token');
      user = null;
    }
  }

  async function loadTournamentBalances() {
    if (!user) return;
    
    try {
      const balanceData = await apiFetch('/user/tournament-balances');
      tournamentBalances = balanceData.tournament_balances || [];
      totalBalance = tournamentBalances.reduce((sum, t) => sum + t.current_balance, 0);
    } catch (err) {
      console.error('Failed to load tournament balances:', err);
    }
  }

  async function logout() {
    localStorage.removeItem('auth_token');
    user = null;
    tournamentBalances = [];
    totalBalance = 0;
    goto('/auth/login');
  }

  function formatCurrency(value) {
    if (typeof value !== 'number') return '$0.00';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(value);
  }
</script>

<div class="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-indigo-900">
  <!-- Navigation Header -->
  <nav class="bg-gray-900/80 backdrop-blur-lg border-b border-gray-700/50 sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-16">
        
        <!-- Logo and Brand -->
        <div class="flex items-center">
          <a href="/" class="flex items-center space-x-3">
            <div class="text-2xl font-bold bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">
              TrendBet
            </div>
          </a>
        </div>

        <!-- Navigation Links -->
        <div class="hidden md:block">
          <div class="ml-10 flex items-baseline space-x-4">
            <a href="/browse" 
               class="nav-link {$page.url.pathname === '/browse' ? 'active' : ''}">
              📊 Browse
            </a>
            <a href="/tournaments" 
               class="nav-link {$page.url.pathname === '/tournaments' ? 'active' : ''}">
              🏆 Tournaments
            </a>
            <a href="/portfolio" 
               class="nav-link {$page.url.pathname === '/portfolio' ? 'active' : ''}">
              💼 Portfolio
            </a>
            <a href="/leaderboard" 
               class="nav-link {$page.url.pathname === '/leaderboard' ? 'active' : ''}">
              🏅 Leaderboard  
            </a>
          </div>
        </div>

        <!-- User Info and P&L -->
        <div class="flex items-center space-x-4">
          {#if user}
            <!-- FIX 2: Real-time P&L display in navigation -->
            <div class="hidden lg:block">
              <PnLDisplay showDetailed={false} />
            </div>

            <!-- Tournament Balance Display -->
            <div class="hidden md:flex items-center space-x-4">
              <div class="text-sm">
                <div class="text-gray-400 text-xs">Tournament Balance</div>
                <div class="font-semibold text-emerald-400">
                  {formatCurrency(totalBalance)}
                </div>
              </div>

              <!-- Active Tournament Indicator -->
              {#if tournamentBalances.length > 0}
                <div class="text-xs">
                  <div class="text-gray-400">Active Tournaments</div>
                  <div class="font-medium text-blue-400">
                    {tournamentBalances.length}
                  </div>
                </div>
              {/if}
            </div>

            <!-- User Menu -->
            <div class="relative group">
              <button class="flex items-center space-x-2 text-gray-300 hover:text-white transition-colors">
                <div class="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-sm font-semibold">
                  {user.username?.charAt(0).toUpperCase() || 'U'}
                </div>
                <span class="hidden md:block">{user.username}</span>
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                </svg>
              </button>

              <!-- Dropdown Menu -->
              <div class="absolute right-0 mt-2 w-48 bg-gray-800 border border-gray-700 rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                <div class="p-3 border-b border-gray-700">
                  <div class="text-sm font-medium text-white">{user.username}</div>
                  <div class="text-xs text-gray-400">{user.email}</div>
                </div>
                
                <!-- Mobile P&L Display -->
                <div class="lg:hidden p-3 border-b border-gray-700">
                  <PnLDisplay showDetailed={true} />
                </div>

                <div class="p-1">
                  <a href="/profile" class="block px-3 py-2 text-sm text-gray-300 hover:text-white hover:bg-gray-700 rounded transition-colors">
                    👤 Profile
                  </a>
                  <a href="/settings" class="block px-3 py-2 text-sm text-gray-300 hover:text-white hover:bg-gray-700 rounded transition-colors">
                    ⚙️ Settings
                  </a>
                  <button on:click={logout} class="w-full text-left px-3 py-2 text-sm text-gray-300 hover:text-white hover:bg-gray-700 rounded transition-colors">
                    🚪 Logout
                  </button>
                </div>
              </div>
            </div>
          {:else}
            <!-- Login/Register buttons -->
            <div class="flex items-center space-x-2">
              <a href="/auth/login" class="nav-button">
                Login
              </a>
              <a href="/auth/register" class="nav-button-primary">
                Register
              </a>
            </div>
          {/if}
        </div>
      </div>
    </div>

    <!-- Mobile Navigation -->
    <div class="md:hidden border-t border-gray-700/50">
      <div class="px-2 pt-2 pb-3 space-y-1 sm:px-3">
        <a href="/browse" class="mobile-nav-link {$page.url.pathname === '/browse' ? 'active' : ''}">
          📊 Browse
        </a>
        <a href="/tournaments" class="mobile-nav-link {$page.url.pathname === '/tournaments' ? 'active' : ''}">
          🏆 Tournaments
        </a>
        <a href="/portfolio" class="mobile-nav-link {$page.url.pathname === '/portfolio' ? 'active' : ''}">
          💼 Portfolio
        </a>
        <a href="/leaderboard" class="mobile-nav-link {$page.url.pathname === '/leaderboard' ? 'active' : ''}">
          🏅 Leaderboard
        </a>
      </div>

      <!-- Mobile P&L and Balance Display -->
      {#if user}
        <div class="border-t border-gray-700/50 p-3">
          <div class="flex justify-between items-center">
            <PnLDisplay showDetailed={false} />
            <div class="text-sm">
              <div class="text-gray-400 text-xs">Balance</div>
              <div class="font-semibold text-emerald-400">
                {formatCurrency(totalBalance)}
              </div>
            </div>
          </div>
        </div>
      {/if}
    </div>
  </nav>

  <!-- Main Content -->
  <main class="flex-1">
    <slot />
  </main>

  <!-- Footer -->
  <footer class="bg-gray-900/60 border-t border-gray-700/50 mt-auto">
    <div class="max-w-7xl mx-auto px-4 py-6">
      <div class="flex items-center justify-between">
        <div class="text-sm text-gray-400">
          © 2025 TrendBet. Trade attention, not just stocks.
        </div>
        <div class="flex space-x-6 text-sm text-gray-400">
          <a href="/about" class="hover:text-white transition-colors">About</a>
          <a href="/terms" class="hover:text-white transition-colors">Terms</a>
          <a href="/privacy" class="hover:text-white transition-colors">Privacy</a>
          <a href="/support" class="hover:text-white transition-colors">Support</a>
        </div>
      </div>
    </div>
  </footer>
</div>

<style>
  .nav-link {
    @apply px-3 py-2 rounded-md text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-700/50 transition-colors;
  }

  .nav-link.active {
    @apply bg-blue-600/20 text-blue-400 border border-blue-500/30;
  }

  .mobile-nav-link {
    @apply block px-3 py-2 rounded-md text-base font-medium text-gray-300 hover:text-white hover:bg-gray-700/50 transition-colors;
  }

  .mobile-nav-link.active {
    @apply bg-blue-600/20 text-blue-400 border border-blue-500/30;
  }

  .nav-button {
    @apply px-4 py-2 text-sm font-medium text-gray-300 hover:text-white border border-gray-600 rounded-lg hover:border-gray-500 transition-colors;
  }

  .nav-button-primary {
    @apply px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors;
  }

  /* Real-time update indicators */
  .updating {
    position: relative;
  }

  .updating::after {
    content: '';
    position: absolute;
    top: -2px;
    right: -2px;
    width: 6px;
    height: 6px;
    background: rgb(34, 197, 94);
    border-radius: 50%;
    animation: pulse 2s infinite;
  }

  @keyframes pulse {
    0%, 100% {
      opacity: 1;
    }
    50% {
      opacity: 0.5;
    }
  }
</style>