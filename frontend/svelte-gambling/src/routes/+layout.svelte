<script>
  import "../app.css";
  import { onMount, onDestroy } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { user } from '$lib/stores';
  import apiFetch from '$lib/api';
  import GlobalChat from '$lib/components/GlobalChat.svelte';

  let authChecked = false;
  let isCheckingAuth = true;
  let dailyPnL = 0;
  let tournamentBalances = [];

  // Define route patterns
  const publicRoutes = ['/', '/login'];
  const protectedRoutes = ['/dashboard', '/browse', '/tournaments', '/profile', '/portfolio', '/trade'];

  onMount(async () => {
    await checkAuthentication();
    if (authChecked && $user) {
      loadUserStats();
      startAutoRefresh();
    }
  });

  async function checkAuthentication() {
    const token = localStorage.getItem('token');
    const storedUser = localStorage.getItem('user');
    const currentPath = $page.url.pathname;
    
    if (token && storedUser) {
      try {
        const parsedUser = JSON.parse(storedUser);
        user.set(parsedUser);
        
        const currentUser = await apiFetch('/auth/me');
        user.set(currentUser);
        localStorage.setItem('user', JSON.stringify(currentUser));
        
        console.log('✅ Session restored successfully');
      } catch (error) {
        console.error('❌ Session validation failed:', error);
        
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        user.set(null);
        
        if (isProtectedRoute(currentPath)) {
          goto('/login');
        }
      }
    } else {
      if (isProtectedRoute(currentPath)) {
        goto('/login');
      }
    }
    
    authChecked = true;
    isCheckingAuth = false;
  }

  async function loadUserStats() {
    try {
      // Load daily P&L and tournament balances
      const [dailyData, balancesData] = await Promise.all([
        apiFetch('/user/daily-pnl').catch(() => ({ daily_pnl: 0 })),
        apiFetch('/user/tournament-balances').catch(() => ({ tournament_balances: [] }))
      ]);

      dailyPnL = dailyData.daily_pnl || 0;
      tournamentBalances = balancesData.tournament_balances || [];
    } catch (error) {
      console.error('Failed to load user stats:', error);
    }
  }

  // Auto-refresh P&L data
  let refreshInterval;
  function startAutoRefresh() {
    // Refresh P&L every 30 seconds
    refreshInterval = setInterval(() => {
      if ($user && authChecked) {
        loadUserStats();
      }
    }, 30000);
  }

  // Global function to refresh P&L immediately (for after trades)
  if (typeof window !== 'undefined') {
    window.refreshNavbarPnL = () => {
      if ($user && authChecked) {
        loadUserStats();
      }
    };
  }

  // Cleanup interval on component destroy
  onDestroy(() => {
    if (refreshInterval) {
      clearInterval(refreshInterval);
    }
  });

  function isProtectedRoute(path) {
    return protectedRoutes.some(route => path.startsWith(route));
  }

  function isPublicRoute(path) {
    return publicRoutes.includes(path) || path === '/';
  }

  function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    user.set(null);
    goto('/login');
  }

  function formatCurrency(amount) {
    return `$${parseFloat(amount || 0).toFixed(2)}`;
  }

  // Navigation items
  const navItems = [
    { href: '/dashboard', label: '📊 Dashboard', icon: '📊' },
    { href: '/browse', label: '🔍 Browse', icon: '🔍' },
    { href: '/tournaments', label: '🏆 Tournaments', icon: '🏆' },
    { href: '/portfolio', label: '💼 Portfolio', icon: '💼' },
    { href: '/profile', label: '👤 Profile', icon: '👤' }
  ];

  $: currentRoute = $page.url.pathname;
  $: showNavigation = authChecked && $user && !isPublicRoute(currentRoute);
</script>

<svelte:head>
  <title>TrendBet - Trade Attention Like Stocks</title>
  <meta name="description" content="The world's first attention economy trading platform. Buy and sell attention shares based on Google Trends data!" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
</svelte:head>

{#if isCheckingAuth}
  <!-- Loading state while checking authentication -->
  <div class="min-h-screen flex items-center justify-center bg-gray-900">
    <div class="text-center">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
      <div class="text-white text-lg font-medium">TrendBet</div>
      <div class="text-gray-400 text-sm mt-2">Loading...</div>
    </div>
  </div>
{:else}
  <!-- Main Application -->
  <div class="min-h-screen bg-gray-900 text-white">
    
    {#if showNavigation}
      <!-- Navigation Header -->
      <nav class="bg-gray-800 border-b border-gray-700 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div class="flex justify-between items-center h-16">
            
            <!-- Logo/Brand -->
            <div class="flex items-center">
              <a href="/dashboard" class="text-xl font-bold bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">
                TrendBet
              </a>
            </div>

            <!-- Navigation Links -->
            <div class="hidden md:flex items-center space-x-1">
              {#each navItems as item}
                <a
                  href={item.href}
                  class="px-3 py-2 rounded-md text-sm font-medium transition-colors {
                    currentRoute.startsWith(item.href)
                      ? 'bg-blue-900 text-blue-200'
                      : 'text-gray-300 hover:text-white hover:bg-gray-700'
                  }"
                >
                  <span class="mr-2">{item.icon}</span>
                  {item.label.replace(/^\S+\s/, '')}
                </a>
              {/each}
            </div>

            <!-- User Menu with Daily P&L -->
            <div class="flex items-center space-x-4">
              {#if $user}
                <!-- Daily P&L Display -->
                <div class="hidden sm:flex items-center bg-gray-700 rounded-lg px-3 py-2">
                  <span class="text-xs text-gray-400 mr-2">Today:</span>
                  <span class="font-medium {dailyPnL >= 0 ? 'text-emerald-400' : 'text-red-400'}">
                    {dailyPnL >= 0 ? '+' : ''}{formatCurrency(dailyPnL)}
                  </span>
                </div>

                <!-- Tournament Balances Dropdown -->
                {#if tournamentBalances.length > 0}
                  <div class="hidden lg:flex items-center bg-gray-700 rounded-lg px-3 py-2">
                    <span class="text-xs text-gray-400 mr-2">Tournaments:</span>
                    <span class="font-medium text-blue-400">{tournamentBalances.length}</span>
                  </div>
                {/if}

                <!-- User Profile & Logout -->
                <div class="flex items-center space-x-3">
                  <div class="w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center text-sm font-bold">
                    {$user.username.charAt(0).toUpperCase()}
                  </div>
                  <span class="hidden sm:block text-sm font-medium">{$user.username}</span>
                  <button
                    on:click={logout}
                    class="text-gray-400 hover:text-white p-2 rounded-md hover:bg-gray-700 transition-colors"
                    title="Logout"
                  >
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path>
                    </svg>
                  </button>
                </div>
              {/if}
            </div>
          </div>
        </div>

        <!-- Mobile Navigation -->
        <div class="md:hidden">
          <div class="px-2 pt-2 pb-3 space-y-1">
            {#each navItems as item}
              <a
                href={item.href}
                class="block px-3 py-2 rounded-md text-base font-medium {
                  currentRoute.startsWith(item.href)
                    ? 'bg-blue-900 text-blue-200'
                    : 'text-gray-300 hover:text-white hover:bg-gray-700'
                }"
              >
                <span class="mr-2">{item.icon}</span>
                {item.label.replace(/^\S+\s/, '')}
              </a>
            {/each}
            
            <!-- Mobile Daily P&L -->
            {#if $user}
              <div class="px-3 py-2 text-center bg-gray-700 rounded-md mt-2">
                <div class="text-xs text-gray-400">Today's P&L</div>
                <div class="font-medium {dailyPnL >= 0 ? 'text-emerald-400' : 'text-red-400'}">
                  {dailyPnL >= 0 ? '+' : ''}{formatCurrency(dailyPnL)}
                </div>
              </div>
            {/if}
          </div>
        </div>
      </nav>
    {/if}

    <!-- Main Content -->
    <main class="{showNavigation ? 'pt-0' : 'pt-16'} min-h-screen {$user ? 'pr-[20%]' : ''}">
      <slot />
    </main>

    <!-- Global Chat Component -->
    <GlobalChat />
  </div>
{/if}