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

<div class="min-h-screen flex flex-col" style="background: linear-gradient(135deg, #0F0F23 0%, #1A1A2E 50%, #16213E 100%); color: white;">
  <!-- Navigation -->
  <nav class="flex justify-between items-center px-6 py-4" style="background: rgba(0,0,0,0.2); backdrop-filter: blur(10px); border-bottom: 1px solid rgba(255,255,255,0.1);">
    <div class="flex items-center gap-3">
      <div class="text-2xl font-bold" style="background: linear-gradient(to right, #A78BFA, #60A5FA); -webkit-background-clip: text; background-clip: text; color: transparent;">
        🎲 Gamble Royale
      </div>
      <div class="text-xs px-2 py-1 rounded-full" style="background: rgba(167, 139, 250, 0.2); color: #C4B5FD;">
        BETA
      </div>
    </div>
    
    <div class="flex items-center gap-4">
      <!-- Navigation Links -->
      <div class="hidden md:flex items-center gap-1">
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
          <div class="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full" style="background: rgba(255,255,255,0.1);">
            <div class="w-6 h-6 rounded-full flex items-center justify-center text-xs text-white font-bold" style="background: linear-gradient(135deg, #A78BFA, #60A5FA);">
              {$user.username.charAt(0).toUpperCase()}
            </div>
            <span class="text-sm font-medium">{$user.username}</span>
            {#if $user.wins !== undefined}
              <span class="text-xs" style="color: #9CA3AF;">
                {$user.wins}W-{$user.losses}L
              </span>
            {/if}
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
  <footer class="text-center py-6 px-6" style="background: rgba(0,0,0,0.2); border-top: 1px solid rgba(255,255,255,0.1);">
    <div class="text-sm" style="color: #9CA3AF;">
      <p>© 2024 Gamble Royale • Built with ❤️ for gamers</p>
      <div class="flex items-center justify-center gap-4 mt-2">
        <span class="flex items-center gap-1">
          <div class="w-2 h-2 rounded-full" style="background: #10B981;"></div>
          Server Online
        </span>
        <span>•</span>
        <span>Made with SvelteKit & Colyseus</span>
      </div>
    </div>
  </footer>
</div>