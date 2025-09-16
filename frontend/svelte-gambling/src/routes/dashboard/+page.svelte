<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { user } from '$lib/stores';
  import apiFetch from '$lib/api';

  let stats = null;
  let recentTrades = [];
  let tournamentBalances = [];
  let activeTournaments = [];
  let topPositions = [];
  let loading = true;

  onMount(async () => {
    if (!$user) {
      goto('/login');
      return;
    }

    try {
      const [portfolioData, tradesResponse, balancesData, tournamentsData] = await Promise.all([
        apiFetch('/portfolio'),
        apiFetch('/trades/my'),
        apiFetch('/user/tournament-balances').catch(() => ({ tournament_balances: [] })),
        apiFetch('/tournaments').catch(() => [])
      ]);

      const trades = tradesResponse.trades || tradesResponse || [];
      recentTrades = trades.slice(0, 5);
      tournamentBalances = balancesData.tournament_balances || [];
      activeTournaments = tournamentsData.filter(t => t.status === 'active').slice(0, 3);
      topPositions = portfolioData.positions ? portfolioData.positions.slice(0, 5) : [];

      // Calculate comprehensive stats
      const closedTrades = trades.filter(t => t.is_closed);
      const winningTrades = closedTrades.filter(t => t.pnl > 0);
      const totalPnl = closedTrades.reduce((sum, t) => sum + (t.pnl || 0), 0);
      const totalTournamentValue = tournamentBalances.reduce((sum, t) => sum + (t.current_balance || 0), 0);
      const totalTournamentPnL = tournamentBalances.reduce((sum, t) => sum + (t.pnl || 0), 0);

      stats = {
        totalTrades: trades.length,
        activeTournaments: tournamentBalances.length,
        totalTournamentValue: totalTournamentValue,
        totalTournamentPnL: totalTournamentPnL,
        winRate: closedTrades.length > 0 ? (winningTrades.length / closedTrades.length * 100) : 0,
        totalPnl: totalPnl,
        bestTrade: closedTrades.length > 0 ? Math.max(...closedTrades.map(t => t.pnl || 0)) : 0,
        worstTrade: closedTrades.length > 0 ? Math.min(...closedTrades.map(t => t.pnl || 0)) : 0
      };

    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      loading = false;
    }
  });

  function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  function formatCurrency(amount) {
    return `$${parseFloat(amount || 0).toFixed(2)}`;
  }

  function formatNumber(num) {
    return new Intl.NumberFormat('en-US', {
      maximumFractionDigits: 1,
      minimumFractionDigits: 1
    }).format(num);
  }

  function formatPercent(value) {
    return `${(value || 0).toFixed(1)}%`;
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

  function getTournamentDurationIcon(duration) {
    const icons = {
      daily: '📅',
      weekly: '📊',
      monthly: '🏆'
    };
    return icons[duration] || '🏟️';
  }

  function getPerformanceColor(pnl) {
    if (pnl > 0) return 'text-emerald-400';
    if (pnl < 0) return 'text-red-400';
    return 'text-gray-400';
  }

  function getTradeTypeIcon(tradeType) {
    if (tradeType.includes('buy') || tradeType.includes('long')) return '📈';
    if (tradeType.includes('sell') || tradeType.includes('short')) return '📉';
    return '🔄';
  }

  function getTimeRemaining(endDate) {
    if (!endDate) return "No end date";

    const now = new Date();
    const end = new Date(endDate);
    const diff = end - now;

    if (diff <= 0) return "Ended";

    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));

    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h`;
    return "< 1h";
  }
</script>

<svelte:head>
  <title>Dashboard - TrendBet</title>
</svelte:head>

<div class="min-h-screen p-6">
  <div class="max-w-7xl mx-auto">
    <!-- Header -->
    <div class="mb-8">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-4xl font-bold mb-2 bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400 bg-clip-text text-transparent">
            Dashboard
          </h1>
          <p class="text-gray-400">Welcome back, {$user?.username || 'Trader'}! Here's your tournament trading overview.</p>
        </div>
        <div class="hidden md:flex space-x-3">
          <a href="/browse" class="btn btn-primary">
            🎯 Browse Targets
          </a>
          <a href="/tournaments" class="btn btn-secondary">
            🏆 View Tournaments
          </a>
        </div>
      </div>
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="w-8 h-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
      </div>
    {:else}
      <!-- Key Stats -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div class="card text-center hover:border-blue-500/50 transition-colors">
          <div class="text-3xl font-bold text-blue-400 mb-2">{stats?.activeTournaments || 0}</div>
          <div class="text-sm text-gray-400">Active Tournaments</div>
          <div class="text-xs text-gray-500 mt-1">Currently joined</div>
        </div>

        <div class="card text-center hover:border-indigo-500/50 transition-colors">
          <div class="text-3xl font-bold text-indigo-400 mb-2">{formatCurrency(stats?.totalTournamentValue || 0)}</div>
          <div class="text-sm text-gray-400">Total Portfolio</div>
          <div class="text-xs text-gray-500 mt-1">Across all tournaments</div>
        </div>

        <div class="card text-center hover:border-emerald-500/50 transition-colors">
          <div class="text-3xl font-bold {getPerformanceColor(stats?.totalTournamentPnL || 0)} mb-2">
            {stats?.totalTournamentPnL >= 0 ? '+' : ''}{formatCurrency(stats?.totalTournamentPnL || 0)}
          </div>
          <div class="text-sm text-gray-400">Tournament P&L</div>
          <div class="text-xs text-gray-500 mt-1">Combined performance</div>
        </div>

        <div class="card text-center hover:border-purple-500/50 transition-colors">
          <div class="text-3xl font-bold text-purple-400 mb-2">{formatPercent(stats?.winRate || 0)}</div>
          <div class="text-sm text-gray-400">Win Rate</div>
          <div class="text-xs text-gray-500 mt-1">{stats?.totalTrades || 0} total trades</div>
        </div>
      </div>

      <!-- Tournament Performance -->
      {#if tournamentBalances.length > 0}
        <div class="card mb-8">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-2xl font-semibold flex items-center gap-3">
              🏆 Your Tournaments
            </h2>
            <a href="/portfolio?tab=tournaments" class="btn btn-secondary btn-sm">View All</a>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {#each tournamentBalances.slice(0, 6) as tournament}
              <a
                href={`/tournaments/${tournament.tournament_id}`}
                class="p-4 bg-gray-800/30 rounded-lg border border-gray-700/50 hover:border-blue-500/50 transition-colors block"
              >
                <div class="flex items-center gap-3 mb-4">
                  <span class="text-2xl">{getTournamentDurationIcon(tournament.duration)}</span>
                  <div class="flex-1 min-w-0">
                    <div class="font-semibold truncate">{tournament.name}</div>
                    <div class="text-xs text-gray-400 capitalize flex items-center gap-2">
                      {tournament.duration}
                      {#if tournament.end_date}
                        <span class="text-orange-400">⏰ {getTimeRemaining(tournament.end_date)}</span>
                      {/if}
                    </div>
                  </div>
                </div>

                <div class="space-y-2 text-sm">
                  <div class="flex justify-between">
                    <span class="text-gray-400">Balance:</span>
                    <span class="font-medium">{formatCurrency(tournament.current_balance)}</span>
                  </div>
                  <div class="flex justify-between">
                    <span class="text-gray-400">P&L:</span>
                    <span class="font-medium {getPerformanceColor(tournament.pnl)}">
                      {tournament.pnl >= 0 ? '+' : ''}{formatCurrency(tournament.pnl)}
                    </span>
                  </div>
                  {#if tournament.rank}
                    <div class="flex justify-between">
                      <span class="text-gray-400">Rank:</span>
                      <span class="font-medium text-yellow-400">#{tournament.rank}</span>
                    </div>
                  {/if}
                </div>
              </a>
            {/each}
          </div>
        </div>
      {/if}

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        <!-- Recent Trades -->
        <div class="card">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-xl font-semibold flex items-center gap-2">
              📈 Recent Activity
            </h2>
            <a href="/portfolio?tab=history" class="text-blue-400 hover:text-blue-300 text-sm">View All</a>
          </div>

          {#if recentTrades.length > 0}
            <div class="space-y-3">
              {#each recentTrades as trade}
                <div class="flex items-center justify-between p-3 bg-gray-800/20 rounded-lg border border-gray-700/30 hover:border-gray-600/50 transition-colors">
                  <div class="flex items-center gap-3">
                    <span class="text-xl">{getTradeTypeIcon(trade.trade_type)}</span>
                    <div>
                      <div class="font-medium text-sm">{trade.target_name}</div>
                      <div class="text-xs text-gray-400">
                        {trade.trade_type.toUpperCase()} • {formatDate(trade.timestamp)}
                      </div>
                    </div>
                  </div>
                  <div class="text-right">
                    <div class="text-sm font-medium {getPerformanceColor(trade.pnl || 0)}">
                      {trade.pnl ? ((trade.pnl >= 0 ? '+' : '') + formatCurrency(trade.pnl)) : '-'}
                    </div>
                    <div class="text-xs text-gray-400">
                      {formatCurrency(trade.stake_amount || 0)}
                    </div>
                  </div>
                </div>
              {/each}
            </div>
          {:else}
            <div class="text-center py-8 text-gray-400">
              <div class="text-4xl mb-3">📊</div>
              <p class="mb-3">No trades yet</p>
              <a href="/browse" class="btn btn-primary btn-sm">Start Trading</a>
            </div>
          {/if}
        </div>

        <!-- Top Positions -->
        <div class="card">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-xl font-semibold flex items-center gap-2">
              💼 Current Positions
            </h2>
            <a href="/portfolio" class="text-blue-400 hover:text-blue-300 text-sm">View All</a>
          </div>

          {#if topPositions.length > 0}
            <div class="space-y-3">
              {#each topPositions as position}
                <div class="flex items-center justify-between p-3 bg-gray-800/20 rounded-lg border border-gray-700/30">
                  <div class="flex items-center gap-3">
                    <span class="text-xl">{getTypeIcon(position.target_type)}</span>
                    <div>
                      <div class="font-medium text-sm">{position.target_name}</div>
                      <div class="text-xs text-gray-400 capitalize">
                        {position.position_type || 'Long'} position
                      </div>
                    </div>
                  </div>
                  <div class="text-right">
                    <div class="text-sm font-medium {getPerformanceColor(position.unrealized_pnl || 0)}">
                      {position.unrealized_pnl >= 0 ? '+' : ''}{formatCurrency(position.unrealized_pnl || 0)}
                    </div>
                    <div class="text-xs text-gray-400">
                      {formatNumber(position.attention_stakes || 0)} stakes
                    </div>
                  </div>
                </div>
              {/each}
            </div>
          {:else}
            <div class="text-center py-8 text-gray-400">
              <div class="text-4xl mb-3">💼</div>
              <p class="mb-3">No open positions</p>
              <a href="/browse" class="btn btn-primary btn-sm">Browse Targets</a>
            </div>
          {/if}
        </div>
      </div>

      <!-- Available Tournaments -->
      {#if activeTournaments.length > 0}
        <div class="card">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-xl font-semibold flex items-center gap-2">
              🏟️ Join Active Tournaments
            </h2>
            <a href="/tournaments" class="text-blue-400 hover:text-blue-300 text-sm">View All</a>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            {#each activeTournaments as tournament}
              <div class="p-4 bg-gradient-to-br from-gray-800/40 to-gray-800/20 rounded-lg border border-gray-700/50 hover:border-blue-500/50 transition-colors">
                <div class="flex items-center gap-3 mb-3">
                  <span class="text-xl">{getTournamentDurationIcon(tournament.duration)}</span>
                  <div class="flex-1 min-w-0">
                    <div class="font-medium text-sm truncate">{tournament.name}</div>
                    <div class="text-xs text-gray-400 capitalize">{tournament.target_type} • {tournament.duration}</div>
                  </div>
                </div>

                <div class="space-y-2 text-xs text-gray-400 mb-4">
                  <div class="flex justify-between">
                    <span>Entry Fee:</span>
                    <span class="text-white">{tournament.entry_fee > 0 ? formatCurrency(tournament.entry_fee) : 'FREE'}</span>
                  </div>
                  <div class="flex justify-between">
                    <span>Starting Balance:</span>
                    <span class="text-emerald-400">{formatCurrency(tournament.starting_balance)}</span>
                  </div>
                  <div class="flex justify-between">
                    <span>Players:</span>
                    <span>{tournament.current_participants || 0}</span>
                  </div>
                </div>

                <a href={`/tournaments/${tournament.id}`} class="btn btn-primary btn-sm w-full">
                  View Tournament
                </a>
              </div>
            {/each}
          </div>
        </div>
      {/if}
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