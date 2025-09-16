<script>
  import { onMount, onDestroy } from 'svelte';
  import { goto } from '$app/navigation';
  import { user } from '$lib/stores';
  import apiFetch from '$lib/api';

  let stats = null;
  let recentTrades = [];
  let tournamentBalances = [];
  let loading = true;
  let countdownInterval;

  onMount(async () => {
    if (!$user) {
      goto('/login');
      return;
    }

    try {
      const [tradesResponse, portfolioData, balancesData] = await Promise.all([
        apiFetch('/trades/my'),
        apiFetch('/portfolio'),
        apiFetch('/user/tournament-balances').catch(() => ({ tournament_balances: [] }))
      ]);

      const trades = tradesResponse.trades || tradesResponse || [];
      recentTrades = trades.slice(0, 10);
      tournamentBalances = balancesData.tournament_balances || [];

      // Calculate trading stats
      const closedTrades = trades.filter(t => t.is_closed);
      const winningTrades = closedTrades.filter(t => t.pnl > 0);
      const losingTrades = closedTrades.filter(t => t.pnl < 0);
      const totalPnl = closedTrades.reduce((sum, t) => sum + (t.pnl || 0), 0);

      // Calculate tournament stats
      const totalTournamentPnL = tournamentBalances.reduce((sum, t) => sum + (t.pnl || 0), 0);
      const totalTournamentValue = tournamentBalances.reduce((sum, t) => sum + (t.current_balance || 0), 0);

      stats = {
        totalTrades: trades.length,
        closedTrades: closedTrades.length,
        winningTrades: winningTrades.length,
        losingTrades: losingTrades.length,
        winRate: closedTrades.length > 0 ? (winningTrades.length / closedTrades.length * 100) : 0,
        totalPnl: totalPnl,
        averagePnl: closedTrades.length > 0 ? totalPnl / closedTrades.length : 0,
        bestTrade: closedTrades.length > 0 ? Math.max(...closedTrades.map(t => t.pnl || 0)) : 0,
        worstTrade: closedTrades.length > 0 ? Math.min(...closedTrades.map(t => t.pnl || 0)) : 0,
        currentPortfolioValue: portfolioData.total_portfolio_value || 0,
        totalTournaments: tournamentBalances.length,
        totalTournamentPnL: totalTournamentPnL,
        totalTournamentValue: totalTournamentValue,
        activeTournaments: tournamentBalances.filter(t => !t.is_finished).length
      };

      // Update countdowns every minute
      countdownInterval = setInterval(() => {
        // Force reactivity update by reassigning tournamentBalances
        tournamentBalances = [...tournamentBalances];
      }, 60000);

    } catch (error) {
      console.error('Failed to load profile data:', error);
    } finally {
      loading = false;
    }
  });

  onDestroy(() => {
    if (countdownInterval) {
      clearInterval(countdownInterval);
    }
  });

  function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  }

  function formatCurrency(amount) {
    return `$${parseFloat(amount || 0).toFixed(2)}`;
  }

  function formatPercent(value) {
    return `${(value || 0).toFixed(1)}%`;
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

    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  }

  function getTradeTypeIcon(tradeType) {
    if (tradeType.includes('buy') || tradeType.includes('long')) return '📈';
    if (tradeType.includes('sell') || tradeType.includes('short')) return '📉';
    if (tradeType.includes('close')) return '❌';
    if (tradeType.includes('flatten')) return '🔄';
    return '📊';
  }

  function getTradeOutcomeColor(pnl) {
    if (pnl > 0) return 'text-emerald-400';
    if (pnl < 0) return 'text-red-400';
    return 'text-gray-400';
  }

  function getTournamentDurationIcon(duration) {
    const icons = {
      daily: '🌅',
      weekly: '📅',
      monthly: '🗓️'
    };
    return icons[duration] || '⏰';
  }

  function getPerformanceColor(pnl) {
    if (pnl > 0) return 'text-emerald-400';
    if (pnl < 0) return 'text-red-400';
    return 'text-gray-400';
  }
</script>

<svelte:head>
  <title>Profile - TrendBet</title>
</svelte:head>

<div class="min-h-screen p-6">
  <div class="max-w-6xl mx-auto">
    <!-- Profile Header -->
    <div class="card mb-8">
      <div class="flex flex-col sm:flex-row items-start sm:items-center gap-6">
        <div class="w-20 h-20 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center text-2xl text-white font-bold">
          {$user?.username.charAt(0).toUpperCase()}
        </div>
        <div class="flex-1">
          <h1 class="text-3xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">
            {$user?.username}
          </h1>
          <p class="text-gray-400 mb-3">Attention Trader • Member since {formatDate($user?.created_at || new Date())}</p>

          {#if stats}
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
              <div>
                <span class="text-gray-400">Portfolio Value</span>
                <div class="font-medium text-blue-400">{formatCurrency(stats.currentPortfolioValue)}</div>
              </div>
              <div>
                <span class="text-gray-400">Total P&L</span>
                <div class="font-medium {getPerformanceColor(stats.totalPnl)}">
                  {stats.totalPnl >= 0 ? '+' : ''}{formatCurrency(stats.totalPnl)}
                </div>
              </div>
              <div>
                <span class="text-gray-400">Active Tournaments</span>
                <div class="font-medium text-purple-400">{stats.activeTournaments}</div>
              </div>
              <div>
                <span class="text-gray-400">Win Rate</span>
                <div class="font-medium text-yellow-400">{formatPercent(stats.winRate)}</div>
              </div>
            </div>
          {/if}
        </div>
      </div>
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="w-12 h-12 border-4 border-blue-400/30 border-t-blue-400 rounded-full animate-spin"></div>
      </div>
    {:else if stats}
      <!-- Trading Stats Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div class="card text-center">
          <div class="text-3xl font-bold text-blue-400 mb-2">{stats.totalTrades}</div>
          <div class="text-sm text-gray-400">Total Trades</div>
        </div>

        <div class="card text-center">
          <div class="text-3xl font-bold text-emerald-400 mb-2">{stats.winningTrades}</div>
          <div class="text-sm text-gray-400">Winning Trades</div>
        </div>

        <div class="card text-center">
          <div class="text-3xl font-bold text-red-400 mb-2">{stats.losingTrades}</div>
          <div class="text-sm text-gray-400">Losing Trades</div>
        </div>

        <div class="card text-center">
          <div class="text-3xl font-bold text-indigo-400 mb-2">{formatPercent(stats.winRate)}</div>
          <div class="text-sm text-gray-400">Win Rate</div>
        </div>
      </div>

      <!-- Performance Stats -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div class="card text-center">
          <div class="text-2xl font-bold {stats.totalPnl >= 0 ? 'text-emerald-400' : 'text-red-400'} mb-2">
            {stats.totalPnl >= 0 ? '+' : ''}{formatCurrency(stats.totalPnl)}
          </div>
          <div class="text-sm text-gray-400">Total P&L</div>
        </div>

        <div class="card text-center">
          <div class="text-2xl font-bold {stats.averagePnl >= 0 ? 'text-emerald-400' : 'text-red-400'} mb-2">
            {stats.averagePnl >= 0 ? '+' : ''}{formatCurrency(stats.averagePnl)}
          </div>
          <div class="text-sm text-gray-400">Average P&L</div>
        </div>

        <div class="card text-center">
          <div class="text-2xl font-bold mb-2" class:text-green-400={stats.bestTrade > 0} class:text-red-400={stats.bestTrade < 0} class:text-gray-400={stats.bestTrade === 0}>
            {stats.bestTrade >= 0 ? '+' : ''}{formatCurrency(stats.bestTrade)}
          </div>
          <div class="text-sm text-gray-400">Best Trade</div>
        </div>

        <div class="card text-center">
          <div class="text-2xl font-bold mb-2" class:text-green-400={stats.worstTrade > 0} class:text-red-400={stats.worstTrade < 0} class:text-gray-400={stats.worstTrade === 0}>
            {stats.worstTrade >= 0 ? '+' : ''}{formatCurrency(stats.worstTrade)}
          </div>
          <div class="text-sm text-gray-400">Worst Trade</div>
        </div>
      </div>

      <!-- Tournament Performance -->
      {#if tournamentBalances.length > 0}
        <div class="card mb-8">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-2xl font-semibold">🏆 Tournament Performance</h2>
            <a href="/portfolio?tab=tournaments" class="btn btn-secondary btn-sm">View All</a>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div class="p-4 bg-gray-800/50 rounded-lg text-center">
              <div class="text-2xl font-bold text-blue-400 mb-1">{stats.totalTournaments}</div>
              <div class="text-sm text-gray-400">Total Tournaments</div>
            </div>

            <div class="p-4 bg-gray-800/50 rounded-lg text-center">
              <div class="text-2xl font-bold text-purple-400 mb-1">{formatCurrency(stats.totalTournamentValue)}</div>
              <div class="text-sm text-gray-400">Total Balance</div>
            </div>

            <div class="p-4 bg-gray-800/50 rounded-lg text-center">
              <div class="text-2xl font-bold {getPerformanceColor(stats.totalTournamentPnL)} mb-1">
                {stats.totalTournamentPnL >= 0 ? '+' : ''}{formatCurrency(stats.totalTournamentPnL)}
              </div>
              <div class="text-sm text-gray-400">Tournament P&L</div>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {#each tournamentBalances.slice(0, 6) as tournament}
              <div class="p-4 bg-gray-800/50 rounded-lg border border-gray-700 hover:border-gray-600 transition-colors">
                <div class="flex items-center gap-3 mb-3">
                  <span class="text-xl">{getTournamentDurationIcon(tournament.duration)}</span>
                  <div class="flex-1 min-w-0">
                    <div class="font-medium truncate">{tournament.name}</div>
                    <div class="text-xs text-gray-400 capitalize">{tournament.duration}</div>
                    {#if tournament.end_date}
                      <div class="text-xs text-orange-400 font-medium">
                        ⏰ {getTimeRemaining(tournament.end_date)}
                      </div>
                    {/if}
                  </div>
                </div>

                <div class="flex justify-between items-center text-sm">
                  <span class="text-gray-400">Balance:</span>
                  <span class="font-medium">{formatCurrency(tournament.current_balance)}</span>
                </div>

                <div class="flex justify-between items-center text-sm mt-1">
                  <span class="text-gray-400">P&L:</span>
                  <span class="font-medium {getPerformanceColor(tournament.pnl)}">
                    {tournament.pnl >= 0 ? '+' : ''}{formatCurrency(tournament.pnl)}
                  </span>
                </div>

                {#if tournament.rank}
                  <div class="flex justify-between items-center text-sm mt-1">
                    <span class="text-gray-400">Rank:</span>
                    <span class="font-medium text-yellow-400">#{tournament.rank}</span>
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        </div>
      {:else}
        <div class="card mb-8">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-2xl font-semibold">🏆 Tournament Performance</h2>
          </div>

          <div class="text-center py-8 text-gray-400">
            <div class="text-4xl mb-4">🏆</div>
            <h3 class="text-lg font-semibold mb-2">No tournament entries yet</h3>
            <p class="mb-4">Join tournaments to compete with other traders</p>
            <a href="/tournaments" class="btn btn-primary">
              🎮 Browse Tournaments
            </a>
          </div>
        </div>
      {/if}

      <!-- Recent Trading Activity -->
      <div class="card">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-2xl font-semibold">📈 Recent Trading Activity</h2>
          <div class="text-sm text-gray-400">{recentTrades.length} recent trades</div>
        </div>

        {#if recentTrades.length > 0}
          <div class="overflow-x-auto">
            <table class="table w-full">
              <thead>
                <tr class="border-gray-700">
                  <th class="text-left">Date</th>
                  <th class="text-left">Target</th>
                  <th class="text-center">Type</th>
                  <th class="text-right">Amount</th>
                  <th class="text-right">Entry Score</th>
                  <th class="text-right">P&L</th>
                  <th class="text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {#each recentTrades as trade}
                  <tr class="border-gray-700/50 hover:bg-gray-800/50">
                    <td class="py-3">
                      <div class="text-sm">{formatDate(trade.timestamp)}</div>
                    </td>
                    <td class="py-3">
                      <div class="font-medium">{trade.target_name}</div>
                      <div class="text-xs text-gray-400 capitalize">{trade.target_type}</div>
                    </td>
                    <td class="py-3 text-center">
                      <span class="flex items-center justify-center gap-1">
                        {getTradeTypeIcon(trade.trade_type)}
                        <span class="text-xs capitalize">{trade.trade_type.replace('stake_', '').replace('_', ' ')}</span>
                      </span>
                    </td>
                    <td class="py-3 text-right">
                      <div class="font-medium">{formatCurrency(trade.stake_amount)}</div>
                    </td>
                    <td class="py-3 text-right">
                      <div class="font-medium">{trade.attention_score_at_entry.toFixed(1)}</div>
                    </td>
                    <td class="py-3 text-right">
                      <div class="font-medium {getTradeOutcomeColor(trade.pnl)}">
                        {trade.pnl && trade.pnl !== 0 ? (trade.pnl >= 0 ? '+' : '') + formatCurrency(trade.pnl) : '-'}
                      </div>
                    </td>
                    <td class="py-3 text-center">
                      <span class="px-2 py-1 rounded-full text-xs font-medium {
                        trade.is_closed ?
                          (trade.pnl > 0 ? 'bg-emerald-500/20 text-emerald-400' :
                           trade.pnl < 0 ? 'bg-red-500/20 text-red-400' : 'bg-gray-500/20 text-gray-400') :
                          'bg-yellow-500/20 text-yellow-400'
                      }">
                        {trade.is_closed ? 'Closed' : 'Open'}
                      </span>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>

          <div class="mt-6 text-center">
            <a href="/portfolio?tab=history" class="btn btn-secondary">
              📊 View Full Trading History
            </a>
          </div>
        {:else}
          <div class="text-center py-12">
            <div class="text-6xl mb-4">📈</div>
            <h3 class="text-xl font-semibold mb-2">No trades yet</h3>
            <p class="text-gray-400 mb-4">Start trading attention to build your profile</p>
            <a href="/browse" class="btn btn-primary">
              🔍 Browse Targets
            </a>
          </div>
        {/if}
      </div>
    {:else}
      <div class="text-center py-12">
        <div class="text-6xl mb-4">👤</div>
        <h3 class="text-xl font-semibold mb-2">Profile data unavailable</h3>
        <p class="text-gray-400">Unable to load your trading statistics</p>
      </div>
    {/if}
  </div>
</div>

<style>
  .card {
    @apply bg-gray-900/50 border border-gray-800 rounded-xl p-6 shadow-xl backdrop-blur-sm;
  }

  .btn {
    @apply px-4 py-2 rounded-lg font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-opacity-50 disabled:opacity-50 disabled:cursor-not-allowed;
  }

  .btn-primary {
    @apply bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500;
  }

  .btn-secondary {
    @apply bg-gray-700 text-gray-300 hover:bg-gray-600 focus:ring-gray-500;
  }

  .btn-sm {
    @apply px-3 py-1 text-sm;
  }

  .table {
    @apply w-full;
  }

  .table th {
    @apply py-3 px-4 text-sm font-medium text-gray-300 border-b border-gray-700;
  }

  .table td {
    @apply px-4 border-b border-gray-800/50;
  }
</style>