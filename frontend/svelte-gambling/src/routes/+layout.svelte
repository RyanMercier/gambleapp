<script>
  import "../app.css";
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { user } from '$lib/stores';
  import apiFetch from '$lib/api';

  let authChecked = false;
  let isCheckingAuth = true;

  // Define route patterns
  const publicRoutes = ['/', '/login'];
  const protectedRoutes = ['/dashboard', '/browse', '/tournaments', '/profile', '/portfolio'];

  onMount(async () => {
    await checkAuthentication();
  });

  async function checkAuthentication() {
    const token = localStorage.getItem('token');
    const storedUser = localStorage.getItem('user');
    const currentPath = $page.url.pathname;
    
    // If we have stored credentials, verify they're still valid
    if (token && storedUser) {
      try {
        // Parse stored user first
        const parsedUser = JSON.parse(storedUser);
        user.set(parsedUser);
        
        // Verify token is still valid by calling API
        const currentUser = await apiFetch('/auth/me');
        
        // Update user data if API call succeeds
        user.set(currentUser);
        localStorage.setItem('user', JSON.stringify(currentUser));
        
        console.log('✅ Session restored successfully');
      } catch (error) {
        console.error('❌ Session validation failed:', error);
        
        // Clear invalid session data
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        user.set(null);
        
        // Only redirect to login if we're on a protected route
        if (isProtectedRoute(currentPath)) {
          console.log('🔄 Redirecting to login from protected route');
          goto('/login');
        }
      }
    } else {
      // No stored session - check if we need to redirect
      if (isProtectedRoute(currentPath)) {
        console.log('🔄 No session, redirecting to login');
        goto('/login');
      }
    }
    
    authChecked = true;
    isCheckingAuth = false;
  }

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

            <!-- User Menu -->
            <div class="flex items-center space-x-4">
              {#if $user}
                <!-- Balance Display -->
                <div class="hidden sm:flex items-center bg-gray-700 rounded-lg px-3 py-2">
                  <span class="text-emerald-400 font-medium">
                    ${parseFloat($user.balance || 0).toFixed(2)}
                  </span>
                </div>

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
          </div>
        </div>
      </nav>
    {/if}

    <!-- Main Content -->
    <main class="{showNavigation ? 'pt-0' : ''}">
      <slot />
    </main>

    <!-- Global Toast/Notification Area (if needed) -->
    <div id="toast-container" class="fixed bottom-4 right-4 z-50 space-y-2">
      <!-- Toast notifications can be rendered here -->
    </div>
  </div>
{/if}

<style>
  /* Global styles */
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background-color: #111827;
    color: #ffffff;
  }

  :global(.card) {
    @apply bg-gray-800 rounded-lg p-6 shadow-xl border border-gray-700;
  }

  :global(.btn-primary) {
    @apply bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200;
  }

  :global(.btn-secondary) {
    @apply bg-gray-700 hover:bg-gray-600 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200;
  }

  :global(.input) {
    @apply bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent;
  }

  /* Loading animations */
  :global(.fade-in) {
    animation: fadeIn 0.3s ease-in-out;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
</style>