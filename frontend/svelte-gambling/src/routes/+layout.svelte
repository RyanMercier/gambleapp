<script>
  import "../app.css";
  import Chat from '$lib/Chat.svelte';
  import { onMount } from 'svelte';
  import { writable } from 'svelte/store';

  // Use a reactive store for user
  export const user = writable(null);

  onMount(() => {
    const stored = localStorage.getItem('user');
    if (stored) {
      user.set(JSON.parse(stored));
    }
  });

  function logout() {
  localStorage.removeItem('user');
  localStorage.removeItem('token');
  user.set(null);
  location.href = '/';
  }
</script>

<div class="min-h-screen flex flex-col bg-[#121214] text-[#f0f0f0] font-sans">
  <!-- Navbar -->
  <nav class="flex justify-between items-center px-6 py-4 bg-[#1c1c1f] shadow-md rounded-b-2xl z-10">
  <div class="text-2xl font-bold tracking-wide text-purple-400">🎲 Gamble Royale</div>
  <div class="flex items-center gap-3 text-sm">
    <button on:click={() => location.href = '/'} class="px-3 py-1 bg-gray-100 text-black hover:bg-gray-200 rounded-xl transition">
      Home
    </button>
    <button on:click={() => location.href = '/game'} class="px-3 py-1 bg-gray-100 text-black hover:bg-gray-200 rounded-xl transition">
      Play
    </button>
    <button on:click={() => location.href = '/profile'} class="px-3 py-1 bg-gray-100 text-black hover:bg-gray-200 rounded-xl transition">
      Profile
    </button>

    {#if $user}
      <span class="text-gray-400 ml-2">Hello, {$user.username}</span>
      <button on:click={logout} class="px-3 py-1 bg-purple-600 hover:bg-purple-700 rounded-xl text-sm transition text-white">
        Logout
      </button>
    {:else}
      <button on:click={() => location.href = '/login'} class="px-3 py-1 bg-purple-600 hover:bg-purple-700 rounded-xl text-sm transition text-white">
        Login
      </button>
    {/if}
  </div>
</nav>


  <!-- Main Content -->
  <div class="flex-1 flex overflow-hidden px-4 py-6 gap-6">
    <main class="flex-1 bg-[#1a1a1d] rounded-2xl p-6 overflow-y-auto shadow-lg">
      <slot />
    </main>

    <!-- Chat Sidebar -->
    <aside class="w-[420px] bg-[#1e1e22] border border-gray-700 rounded-2xl flex flex-col shadow-lg">
      <div class="p-4 border-b border-gray-700 font-semibold text-lg">Live Chat</div>
      <div class="flex-1 p-4 overflow-y-auto space-y-3 text-sm">
        <Chat />
      </div>
    </aside>
  </div>
</div>

<style>
  html, body {
    margin: 0;
    padding: 0;
    font-family: 'Inter', sans-serif;
  }

  a, button {
    text-decoration: none;
    color: black;
    font-size: 0.875rem;
    font-weight: 500;
  }
</style>
