<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { user } from '$lib/stores';
  import apiFetch from '$lib/api';

  let tournaments = [];
  let leaderboard = [];
  let loading = true;
  let selectedTab = 'active';

  onMount(async () => {
    if (!$user) {
      goto('/login');
      return;
    }

    try {
      const [tournamentsData, leaderboardData] = await Promise.all([
        apiFetch('/tournaments'),
        apiFetch('/leaderboard')
      ]);

      tournaments = tournamentsData;
      leaderboard = leaderboardData;
    } catch (error) {
      console.error('Failed to load tournaments data:', error);
    } finally {
      loading = false;
    }
  });

  async function joinTournament(tournamentId) {
    try {
      await apiFetch('/tournaments/join', {
        method: 'POST',
        body: JSON.stringify({ tournament_id: tournamentId })
      });
      
      // Update user balance
      const updatedUser = await apiFetch('/auth/me');
      user.set(updatedUser);
      
      alert('Successfully joined tournament!');
      
      // Reload tournaments
      const tournamentsData = await apiFetch('/tournaments');
      tournaments = tournamentsData;
    } catch (error) {
      alert('Failed to join tournament: ' + error.message);
    }
  }

  function formatCurrency(amount) {
    return `$${parseFloat(amount).toFixed(2)}`;
  }

  function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString();
  }

  function formatDateTime(dateString) {
    return new Date(dateString).toLocaleString();
  }

  function getTypeIcon(type) {
    const icons = {
      politician: '🏛️',
      billionaire: '💰',
      country: '🌍',
      stock: '📈'
    };
    return icons[type] || '📊';
  }

  function getDurationIcon(duration) {
    const icons = {
      daily: '⚡',
      weekly: '📅',
      monthly: '🗓️'
    };
    return icons[duration] || '⏰';
  }

  function getTimeRemaining(endDate) {
    const now = new Date();
    const end = new Date(endDate);
    const diff = end - now;
    
    if (diff <= 0) return 'Ended';
    
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    
    if (days > 0) return `${days}d ${hours}h`;
    return `${hours}h`;
  }

  $: activeTournaments = tournaments.filter(t => getTimeRemaining(t.end_date) !== 'Ended');
  $: endedTournaments = tournaments.filter(t => getTimeRemaining(t.end_date) === 'Ended');
</script>

<svelte:head>
  <title>Tournaments - TrendBet</title>
</svelte:head>

<div class="min-h-screen p-6">
  <div class="max-w-7xl mx-auto">
    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-3xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">
        Trading Tournaments
      </h1>
      <p class="text-gray-400">Compete with other traders in skill-based attention trading competitions</p>
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="w-8 h-8 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin"></div>
      </div>
    {:else}
      <!-- Tournament Types Info -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div class="card text-center">
          <div class="text-3xl mb-3">⚡</div>
          <h3 class="font-semibold mb-2">Daily Tournaments</h3>
          <p class="text-sm text-gray-400 mb-3">24-hour trading competitions</p>
          <div class="text-lg font-bold text-emerald-400">$10 Entry Fee</div>
        </div>
        
        <div class="card text-center">
          <div class="text-3xl mb-3">📅</div>
          <h3 class="font-semibold mb-2">Weekly Tournaments</h3>
          <p class="text-sm text-gray-400 mb-3">7-day trading battles</p>
          <div class="text-lg font-bold text-blue-400">$25 Entry Fee</div>
        </div>
        
        <div class="card text-center">
          <div class="text-3xl mb-3">🗓️</div>
          <h3 class="font-semibold mb-2">Monthly Championships</h3>
          <p class="text-sm text-gray-400 mb-3">Month-long major competitions</p>
          <div class="text-lg font-bold text-indigo-400">$50 Entry Fee</div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <!-- Active Tournaments -->
        <div class="lg:col-span-2">
          <!-- Tab Navigation -->
          <div class="flex gap-2 mb-6">
            <button
              class="btn {selectedTab === 'active' ? 'btn-primary' : 'btn-secondary'} text-sm"
              on:click={() => selectedTab = 'active'}
            >
              🔥 Active ({activeTournaments.length})
            </button>
            <button
              class="btn {selectedTab === 'completed' ? 'btn-primary' : 'btn-secondary'} text-sm"
              on:click={() => selectedTab = 'completed'}
            >
              📋 Completed ({endedTournaments.length})
            </button>
          </div>

          <div class="card">
            <h2 class="text-xl font-semibold mb-6">
              {selectedTab === 'active' ? '🔥 Active Tournaments' : '📋 Completed Tournaments'}
            </h2>
            
            {#if selectedTab === 'active'}
              {#if activeTournaments.length > 0}
                <div class="space-y-4">
                  {#each activeTournaments as tournament}
                    <div class="p-4 bg-white/5 rounded-lg border border-white/10">
                      <div class="flex items-start justify-between mb-3">
                        <div class="flex items-center gap-3">
                          <div class="text-2xl">{getDurationIcon(tournament.duration)}</div>
                          <div>
                            <h3 class="font-semibold">{tournament.name}</h3>
                            <p class="text-sm text-gray-400 flex items-center gap-1">
                              {getTypeIcon(tournament.target_type)} {tournament.target_type.charAt(0).toUpperCase() + tournament.target_type.slice(1)} Trading
                            </p>
                          </div>
                        </div>
                        <div class="text-right">
                          <div class="text-lg font-bold text-emerald-400">{formatCurrency(tournament.prize_pool)}</div>
                          <div class="text-xs text-gray-400">Prize Pool</div>
                        </div>
                      </div>
                      
                      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4 text-sm">
                        <div>
                          <span class="text-gray-400">Entry Fee:</span>
                          <div class="font-medium">{formatCurrency(tournament.entry_fee)}</div>
                        </div>
                        <div>
                          <span class="text-gray-400">Participants:</span>
                          <div class="font-medium">{tournament.participants}</div>
                        </div>
                        <div>
                          <span class="text-gray-400">Ends:</span>
                          <div class="font-medium">{formatDate(tournament.end_date)}</div>
                        </div>
                        <div>
                          <span class="text-gray-400">Time Left:</span>
                          <div class="font-medium text-orange-400">{getTimeRemaining(tournament.end_date)}</div>
                        </div>
                      </div>
                      
                      <button 
                        class="btn btn-primary w-full"
                        on:click={() => joinTournament(tournament.id)}
                        disabled={$user.balance < tournament.entry_fee}
                      >
                        {$user.balance >= tournament.entry_fee ? 
                          `🏆 Join Tournament (${formatCurrency(tournament.entry_fee)})` : 
                          'Insufficient Balance'}
                      </button>
                    </div>
                  {/each}
                </div>
              {:else}
                <div class="text-center py-12">
                  <div class="text-6xl mb-4">🏆</div>
                  <h3 class="text-xl font-semibold mb-2">No Active Tournaments</h3>
                  <p class="text-gray-400">New tournaments are created regularly. Check back soon!</p>
                </div>
              {/if}
            {:else}
              {#if endedTournaments.length > 0}
                <div class="space-y-4">
                  {#each endedTournaments as tournament}
                    <div class="p-4 bg-white/5 rounded-lg border border-white/10 opacity-75">
                      <div class="flex items-start justify-between mb-3">
                        <div class="flex items-center gap-3">
                          <div class="text-2xl">{getDurationIcon(tournament.duration)}</div>
                          <div>
                            <h3 class="font-semibold">{tournament.name}</h3>
                            <p class="text-sm text-gray-400 flex items-center gap-1">
                              {getTypeIcon(tournament.target_type)} {tournament.target_type.charAt(0).toUpperCase() + tournament.target_type.slice(1)} Trading • Completed
                            </p>
                          </div>
                        </div>
                        <div class="text-right">
                          <div class="text-lg font-bold text-gray-400">{formatCurrency(tournament.prize_pool)}</div>
                          <div class="text-xs text-gray-400">Final Prize Pool</div>
                        </div>
                      </div>
                      
                      <div class="text-sm text-gray-500">
                        Ended: {formatDateTime(tournament.end_date)} • {tournament.participants} participants
                      </div>
                    </div>
                  {/each}
                </div>
              {:else}
                <div class="text-center py-12">
                  <div class="text-6xl mb-4">📋</div>
                  <h3 class="text-xl font-semibold mb-2">No Completed Tournaments</h3>
                  <p class="text-gray-400">Tournament history will appear here</p>
                </div>
              {/if}
            {/if}
          </div>
        </div>

        <!-- Sidebar -->
        <div class="space-y-6">
          <!-- Leaderboard -->
          <div class="card">
            <h2 class="text-lg font-semibold mb-4">🌟 Top Traders</h2>
            
            {#if leaderboard.length > 0}
              <div class="space-y-3">
                {#each leaderboard.slice(0, 5) as trader, index}
                  <div class="flex items-center justify-between p-2 bg-white/5 rounded">
                    <div class="flex items-center gap-2">
                      <div class="w-6 h-6 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center text-xs font-bold">
                        {trader.rank}
                      </div>
                      <span class="text-sm font-medium">{trader.username}</span>
                    </div>
                    <div class="text-right">
                      <div class="text-sm font-medium text-emerald-400">{formatCurrency(trader.total_value)}</div>
                    </div>
                  </div>
                {/each}
              </div>
            {:else}
              <div class="text-center py-4 text-gray-400">
                <div class="text-2xl mb-1">🌟</div>
                <p class="text-sm">Leaderboard loading...</p>
              </div>
            {/if}
          </div>

          <!-- Prize Distribution -->
          <div class="card">
            <h2 class="text-lg font-semibold mb-4">💰 Prize Distribution</h2>
            <div class="space-y-3">
              <div class="flex justify-between items-center">
                <span class="text-gray-400">🥇 1st Place:</span>
                <span class="font-bold text-yellow-400">50%</span>
              </div>
              <div class="flex justify-between items-center">
                <span class="text-gray-400">🥈 2nd Place:</span>
                <span class="font-bold text-gray-300">30%</span>
              </div>
              <div class="flex justify-between items-center">
                <span class="text-gray-400">🥉 3rd Place:</span>
                <span class="font-bold text-orange-400">20%</span>
              </div>
              <hr class="border-white/10">
              <div class="flex justify-between items-center">
                <span class="text-gray-400">Platform Fee:</span>
                <span class="font-bold text-blue-400">10%</span>
              </div>
            </div>
          </div>

          <!-- How It Works -->
          <div class="card">
            <h2 class="text-lg font-semibold mb-4">❓ How It Works</h2>
            <div class="space-y-3 text-sm text-gray-300">
              <div class="flex items-start gap-2">
                <span class="text-blue-400">1.</span>
                <span>Pay entry fee to join tournament</span>
              </div>
              <div class="flex items-start gap-2">
                <span class="text-blue-400">2.</span>
                <span>Get virtual starting balance ($1000)</span>
              </div>
              <div class="flex items-start gap-2">
                <span class="text-blue-400">3.</span>
                <span>Trade attention shares in your category</span>
              </div>
              <div class="flex items-start gap-2">
                <span class="text-blue-400">4.</span>
                <span>Highest final balance wins prizes</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>