<script>
  import "../app.css";
  import { onMount } from 'svelte';
  import { user } from '$lib/stores';

  onMount(() => {
    const stored = localStorage.getItem('user');
    if (stored) {
      try {
        user.set(JSON.parse(stored));
      } catch (e) {
        console.error('Failed to parse stored user data:', e);
        localStorage.removeItem('user');
      }
    }
  });

  function logout() {
    user.set(null);
    window.location.href = '/';
  }
</script>

<svelte:head>
  <title>Gamble Royale - Multiplayer Skill Games</title>
  <meta name="description" content="Compete in multiplayer skill-based games and climb the leaderboards!" />
</svelte:head>

<div class="min-h-screen flex flex-col bg-gradient-to-br from-gray-900 to-purple-900 text-white">
  <!-- Navigation -->
  <nav class="flex justify-between items-center px-6 py-4 bg-black/30 backdrop-blur-sm border-b border-white/10">
    <div class="flex items-center gap-3">
      <a href="/" class="text-2xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
        🎲 Gamble Royale
      </a>
      <div class="text-xs px-2 py-1 rounded-full bg-purple-500/20 text-purple-300">
        BETA
      </div>
    </div>
    
    <div class="flex items-center gap-4">
      <!-- Navigation Links -->
      <div class="hidden md:flex items-center gap-2">
        <a href="/" class="btn btn-secondary text-sm">
          🏠 Home
        </a>
        <a href="/game" class="btn btn-secondary text-sm">
          🎮 Play
        </a>
        <a href="/profile" class="btn btn-secondary text-sm">
          👤 Profile
        </a>
      </div>

      <!-- User Section -->
      {#if $user}
        <div class="flex items-center gap-3">
          <div class="hidden sm:flex items-center gap-2 px-3 py-2 rounded-full bg-white/10">
            <div class="w-6 h-6 rounded-full bg-gradient-to-br from-purple-400 to-blue-500 flex items-center justify-center text-xs text-white font-bold">
              {$user.username.charAt(0).toUpperCase()}
            </div>
            <span class="text-sm font-medium">{$user.username}</span>
          </div>
          <button class="btn btn-secondary text-sm" on:click={logout}>
            Logout
          </button>
        </div>
      {:else}
        <a href="/login" class="btn btn-primary text-sm">
          Login
        </a>
      {/if}
    </div>
  </nav>

  <!-- Main Content -->
  <main class="flex-1">
    <slot />
  </main>

  <!-- Footer -->
  <footer class="bg-black/30 border-t border-white/10 py-4 px-6">
    <div class="text-center text-sm text-gray-400">
      <p>© 2024 Gamble Royale • Built with ❤️ for gamers</p>
      <div class="flex items-center justify-center gap-4 mt-2">
        <span class="flex items-center gap-1">
          <div class="w-2 h-2 rounded-full bg-green-400"></div>
          Server Online
        </span>
        <span>•</span>
        <span>Made with SvelteKit & Colyseus</span>
      </div>
    </div>
  </footer>
</div>

<style>
  /* Prevent body from creating extra scrollbars */
  :global(body) {
    margin: 0;
    padding: 0;
    overflow-x: hidden;
  }
</style>