<script>
  import { user } from '$lib/stores';
</script>

<svelte:head>
  <title>Profile - Gamble Royale</title>
</svelte:head>

<div class="min-h-screen p-6">
  <div class="max-w-4xl mx-auto">
    <div class="card">
      <h1 class="text-3xl font-bold mb-6 bg-gradient-to-r from-purple-400 to-blue-500 bg-clip-text text-transparent">
        Player Profile
      </h1>
      
      {#if $user}
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h2 class="text-xl font-semibold mb-4">Account Information</h2>
            <div class="space-y-3">
              <div class="flex justify-between">
                <span class="text-gray-400">Username:</span>
                <span class="font-medium">{$user.username}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-400">Player ID:</span>
                <span class="font-medium">#{$user.id}</span>
              </div>
            </div>
          </div>
          
          <div>
            <h2 class="text-xl font-semibold mb-4">Game Statistics</h2>
            <div class="space-y-3">
              <div class="flex justify-between">
                <span class="text-gray-400">Wins:</span>
                <span class="font-medium text-green-400">{$user.wins || 0}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-400">Losses:</span>
                <span class="font-medium text-red-400">{$user.losses || 0}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-400">Win Rate:</span>
                <span class="font-medium">
                  {$user.wins || $user.losses ? Math.round(($user.wins || 0) / (($user.wins || 0) + ($user.losses || 0)) * 100) : 0}%
                </span>
              </div>
            </div>
          </div>
        </div>
      {:else}
        <div class="text-center py-12">
          <p class="text-gray-400 mb-4">Please log in to view your profile</p>
          <a href="/login" class="btn btn-primary">Login</a>
        </div>
      {/if}
    </div>
  </div>
</div>