<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { user } from '$lib/stores';
  import apiFetch from '$lib/api';

  let tournament = null;
  let leaderboard = [];
  let userRank = null;
  let userBalance = null;
  let loading = true;
  let error = null;

  $: tournamentId = $page.params.id;

  onMount(async () => {
    if (!$user) {
      goto('/login');
      return;
    }

    await loadTournamentData();

    // Refresh leaderboard every 30 seconds
    const interval = setInterval(loadTournamentData, 30000);
    return () => clearInterval(interval);
  });

  async function loadTournamentData() {
    try {
      const [tournamentData, leaderboardData, userBalanceData] = await Promise.all([
        apiFetch(`/tournaments/${tournamentId}`),
        apiFetch(`/tournaments/${tournamentId}/leaderboard`),
        apiFetch(`/user/tournament-balances`).catch(() => ({ tournament_balances: [] }))
      ]);

      tournament = tournamentData;
      leaderboard = leaderboardData || [];

      // Find user's tournament balance and rank
      const userTournamentBalance = userBalanceData.tournament_balances.find(
        tb => tb.tournament_id === parseInt(tournamentId)
      );

      if (userTournamentBalance) {
        userBalance = userTournamentBalance;
        userRank = leaderboard.findIndex(entry => entry.user_id === $user.id) + 1;
      }

    } catch (err) {
      console.error('Failed to load tournament data:', err);
      error = err.message;
    } finally {
      loading = false;
    }
  }

  async function joinTournament() {
    try {
      await apiFetch('/tournaments/join', {
        method: 'POST',
        body: JSON.stringify({ tournament_id: parseInt(tournamentId) })
      });

      // Update user balance
      const updatedUser = await apiFetch('/auth/me');
      user.set(updatedUser);

      alert('Successfully joined tournament!');

      // Reload tournament data
      await loadTournamentData();
    } catch (error) {
      alert('Failed to join tournament: ' + error.message);
    }
  }

  function formatCurrency(amount) {
    return `$${parseFloat(amount || 0).toFixed(2)}`;
  }

  function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  function getTypeIcon(type) {
    const icons = {
      politician: '🏛️',
      celebrity: '🌟',
      country: '🌍',
      game: '🎮',
      stock: '📈',
      crypto: '₿'
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
    if (!endDate) return "No end date";

    const now = new Date();
    const end = new Date(endDate);
    const diff = end - now;

    if (diff <= 0) return "Ended";

    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    if (days > 0) return `${days}d ${hours}h ${minutes}m`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  }

  function getPerformanceColor(pnl) {
    if (pnl > 0) return 'text-emerald-400';
    if (pnl < 0) return 'text-red-400';
    return 'text-gray-400';
  }

  function getRankBadgeColor(rank) {
    if (rank === 1) return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
    if (rank === 2) return 'bg-gray-500/20 text-gray-300 border-gray-500/30';
    if (rank === 3) return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
    if (rank <= 10) return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
    return 'bg-gray-600/20 text-gray-400 border-gray-600/30';
  }

  $: isUserJoined = userBalance !== null;
  $: tournamentEnded = tournament && getTimeRemaining(tournament.end_date) === "Ended";
</script>

<svelte:head>
  <title>{tournament ? tournament.name : 'Tournament'} - TrendBet</title>
</svelte:head>

<div class="min-h-screen p-6">
  <div class="max-w-7xl mx-auto">
    <!-- Back Button -->
    <div class="mb-6">
      <button
        on:click={() => goto('/tournaments')}
        class="btn btn-secondary text-sm"
      >
        ← Back to Tournaments
      </button>
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="w-8 h-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
      </div>
    {:else if error}
      <div class="card text-center">
        <div class="text-4xl mb-4">❌</div>
        <h2 class="text-xl font-semibold mb-2">Tournament Not Found</h2>
        <p class="text-gray-400 mb-4">{error}</p>
        <button on:click={() => goto('/tournaments')} class="btn btn-primary">
          Back to Tournaments
        </button>
      </div>
    {:else if tournament}
      <!-- Tournament Header -->
      <div class="card mb-8">
        <div class="flex items-start justify-between mb-6">
          <div class="flex items-center gap-4">
            <div class="text-4xl">{getDurationIcon(tournament.duration)}</div>
            <div>
              <h1 class="text-3xl font-bold bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">
                {tournament.name}
              </h1>
              <p class="text-gray-400 flex items-center gap-2 mt-1">
                {getTypeIcon(tournament.target_type)}
                {tournament.target_type.charAt(0).toUpperCase() + tournament.target_type.slice(1)} Trading
                {#if tournamentEnded}
                  <span class="px-2 py-1 bg-red-500/20 text-red-400 rounded-full text-xs">ENDED</span>
                {:else}
                  <span class="px-2 py-1 bg-green-500/20 text-green-400 rounded-full text-xs">ACTIVE</span>
                {/if}
              </p>
            </div>
          </div>
          <div class="text-right">
            <div class="text-3xl font-bold text-emerald-400">{formatCurrency(tournament.prize_pool)}</div>
            <div class="text-sm text-gray-400">Total Prize Pool</div>
          </div>
        </div>

        <!-- Tournament Stats -->
        <div class="grid grid-cols-2 md:grid-cols-5 gap-6 mb-6">
          <div class="text-center">
            <div class="text-2xl font-bold text-blue-400">{formatCurrency(tournament.entry_fee)}</div>
            <div class="text-xs text-gray-400">Entry Fee</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-indigo-400">{tournament.current_participants || 0}</div>
            <div class="text-xs text-gray-400">Participants</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-purple-400">{formatCurrency(tournament.starting_balance)}</div>
            <div class="text-xs text-gray-400">Starting Balance</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-cyan-400">{formatDate(tournament.start_date)}</div>
            <div class="text-xs text-gray-400">Started</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-orange-400">{getTimeRemaining(tournament.end_date)}</div>
            <div class="text-xs text-gray-400">Time Remaining</div>
          </div>
        </div>

        <!-- User Status -->
        {#if isUserJoined}
          <div class="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
            <div class="flex items-center justify-between">
              <div>
                <h3 class="font-semibold text-blue-400">Your Performance</h3>
                <div class="flex items-center gap-4 mt-2">
                  <div>
                    <span class="text-gray-400">Current Balance:</span>
                    <span class="font-bold ml-2">{formatCurrency(userBalance.current_balance)}</span>
                  </div>
                  <div>
                    <span class="text-gray-400">P&L:</span>
                    <span class="font-bold ml-2 {getPerformanceColor(userBalance.pnl)}">
                      {userBalance.pnl >= 0 ? '+' : ''}{formatCurrency(userBalance.pnl)}
                    </span>
                  </div>
                  {#if userRank}
                    <div>
                      <span class="text-gray-400">Rank:</span>
                      <span class="font-bold ml-2 text-yellow-400">#{userRank}</span>
                    </div>
                  {/if}
                </div>
              </div>
              <a href="/browse" class="btn btn-primary">Continue Trading</a>
            </div>
          </div>
        {:else if !tournamentEnded}
          <div class="bg-green-500/10 border border-green-500/20 rounded-lg p-4">
            <div class="flex items-center justify-between">
              <div>
                <h3 class="font-semibold text-green-400">Join This Tournament</h3>
                <p class="text-gray-400 text-sm mt-1">Compete against {tournament.current_participants || 0} other traders</p>
              </div>
              <button
                class="btn btn-primary"
                on:click={joinTournament}
                disabled={$user.balance < tournament.entry_fee}
              >
                {$user.balance >= tournament.entry_fee ?
                  `Join for ${formatCurrency(tournament.entry_fee)}` :
                  'Insufficient Balance'}
              </button>
            </div>
          </div>
        {/if}
      </div>

      <!-- Leaderboard -->
      <div class="card">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-2xl font-semibold flex items-center gap-3">
            🏆 Tournament Leaderboard
          </h2>
          <div class="text-sm text-gray-400">
            Updates every 30 seconds • {leaderboard.length} traders
          </div>
        </div>

        {#if leaderboard.length > 0}
          <div class="space-y-3">
            {#each leaderboard as entry, index}
              <div class="flex items-center justify-between p-4 bg-gray-800/30 rounded-lg border border-gray-700/50 {entry.user_id === $user.id ? 'ring-2 ring-blue-500/50 bg-blue-500/10' : ''}">
                <div class="flex items-center gap-4">
                  <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-full {getRankBadgeColor(entry.rank)} border flex items-center justify-center font-bold">
                      {entry.rank}
                    </div>
                    <div>
                      <div class="font-semibold flex items-center gap-2">
                        {entry.username}
                        {#if entry.user_id === $user.id}
                          <span class="px-2 py-1 bg-blue-500/20 text-blue-400 rounded-full text-xs">YOU</span>
                        {/if}
                      </div>
                      <div class="text-xs text-gray-400">
                        {entry.trades_count || 0} trades
                      </div>
                    </div>
                  </div>
                </div>

                <div class="text-right">
                  <div class="font-bold text-lg">{formatCurrency(entry.current_balance)}</div>
                  <div class="text-sm {getPerformanceColor(entry.pnl)}">
                    {entry.pnl >= 0 ? '+' : ''}{formatCurrency(entry.pnl)}
                    <span class="text-gray-400 ml-1">
                      ({((entry.pnl / tournament.starting_balance) * 100).toFixed(1)}%)
                    </span>
                  </div>
                </div>
              </div>
            {/each}
          </div>
        {:else}
          <div class="text-center py-12 text-gray-400">
            <div class="text-4xl mb-3">👥</div>
            <p class="mb-3">No participants yet</p>
            {#if !isUserJoined && !tournamentEnded}
              <button on:click={joinTournament} class="btn btn-primary btn-sm">
                Be the First to Join!
              </button>
            {/if}
          </div>
        {/if}
      </div>

      <!-- Prize Distribution -->
      <div class="mt-8 grid grid-cols-1 md:grid-cols-2 gap-8">
        <div class="card">
          <h3 class="text-xl font-semibold mb-4">💰 Prize Distribution</h3>
          <div class="space-y-3">
            <div class="flex justify-between items-center">
              <span class="text-gray-400">🥇 1st Place:</span>
              <span class="font-bold text-yellow-400">50% • {formatCurrency(tournament.prize_pool * 0.5)}</span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-gray-400">🥈 2nd Place:</span>
              <span class="font-bold text-gray-300">30% • {formatCurrency(tournament.prize_pool * 0.3)}</span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-gray-400">🥉 3rd Place:</span>
              <span class="font-bold text-orange-400">20% • {formatCurrency(tournament.prize_pool * 0.2)}</span>
            </div>
          </div>
        </div>

        <div class="card">
          <h3 class="text-xl font-semibold mb-4">📊 Tournament Rules</h3>
          <div class="space-y-3 text-sm text-gray-300">
            <div class="flex items-start gap-2">
              <span class="text-blue-400">•</span>
              <span>Start with {formatCurrency(tournament.starting_balance)} virtual balance</span>
            </div>
            <div class="flex items-start gap-2">
              <span class="text-blue-400">•</span>
              <span>Trade only {tournament.target_type} targets</span>
            </div>
            <div class="flex items-start gap-2">
              <span class="text-blue-400">•</span>
              <span>Highest final balance wins</span>
            </div>
            <div class="flex items-start gap-2">
              <span class="text-blue-400">•</span>
              <span>Positions auto-close at tournament end</span>
            </div>
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  .btn {
    @apply px-4 py-2 rounded-lg font-medium transition-colors text-sm;
  }

  .btn-primary {
    @apply bg-blue-600 hover:bg-blue-700 text-white;
  }

  .btn-secondary {
    @apply bg-gray-700 hover:bg-gray-600 text-gray-200;
  }

  .btn-sm {
    @apply px-3 py-1.5 text-xs;
  }

  .card {
    @apply bg-gray-900/50 backdrop-blur-sm rounded-xl p-6 border border-gray-800/50;
  }
</style>