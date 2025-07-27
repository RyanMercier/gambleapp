<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { user } from '$lib/stores';
  import apiFetch from '$lib/api';

  let portfolio = null;
  let recentTrades = [];
  let leaderboard = [];
  let tournaments = [];
  let loading = true;

  onMount(async () => {
    if (!$user) {
      goto('/login');
      return;
    }

    try {
      const [portfolioData, tradesData, leaderboardData, tournamentsData] = await Promise.all([
        apiFetch('/portfolio'),
        apiFetch('/trades/my'),
        apiFetch('/leaderboard'),
        apiFetch('/tournaments')
      ]);

      portfolio = portfolioData;
      recentTrades = tradesData.slice(0, 5);
      leaderboard = leaderboardData.slice(0, 5);
      tournaments = tournamentsData.slice(0, 3);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      loading = false;
    }
  });

  function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString();
  }

  function formatCurrency(amount) {
    return `$${parseFloat(amount).toFixed(2)}`;
  }

  function formatNumber(num) {
    return new Intl.NumberFormat('en-US', {
      maximumFractionDigits: 1,
      minimumFractionDigits: 1
    }).format(num);
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

  function getPerformanceColor(pnl) {
    if (pnl > 0) return 'text-emerald-400';
    if (pnl < 0) return 'text-red-400';
    return 'text-gray-400';
  }

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
      tournaments = tournamentsData.slice(0, 3);
    } catch (error) {
      alert('Failed to join tournament: ' + error.message);
    }
  }
</script>

<svelte:head>
  <title>Dashboard - TrendBet</title>
</svelte:head>

<div class="min-h-screen p-6">
  <div class="max-w-7xl mx-auto">
    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-3xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">
        Dashboard
      </h1>
      <p class="text-gray-400">Welcome back, {$user?.username || 'Trader'}! Here's your attention trading overview.</p>
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="w-8 h-8 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin"></div>
      </div>
    {:else}
      <!-- Stats Cards -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div class="card text-center">
          <div class="text-2xl font-bold text-blue-400 mb-1">{formatCurrency($user?.balance || 0)}</div>
          <div class="text-sm text-gray-400">Cash Balance</div>
        </div>
        
        <div class="card text-center">
          <div class="text-2xl font-bold text-indigo-400 mb-1">{formatCurrency(portfolio?.portfolio_value || 0)}</div>
          <div class="text-sm text-gray-400">Portfolio Value</div>
        </div>
        
        <div class="card text-center">
          <div class="text-2xl font-bold text-emerald-400 mb-1">{formatCurrency(portfolio?.total_value || 0)}</div>
          <div class="text-sm text-gray-400">Total Value</div>
        </div>
        
        <div class="card text-center">
          <div class="text-2xl font-bold {getPerformanceColor(portfolio?.total_pnl || 0)} mb-1">
            {portfolio?.total_pnl ? 
              (portfolio.total_pnl >= 0 ? '+' : '') + formatCurrency(portfolio.total_pnl) : 
              '$0.00'}
          </div>
          <div class="text-sm text-gray-400">
            Total P&L
            {#if portfolio?.total_pnl_percent}
              <span class="{getPerformanceColor(portfolio.total_pnl)}">
                ({portfolio.total_pnl_percent >= 0 ? '+' : ''}{formatNumber(portfolio.total_pnl_percent)}%)
              </span>
            {/if}
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        <!-- Recent Trades -->
        <div class="card">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-xl font-semibold">📈 Recent Trades</h2>
            <a href="/portfolio" class="text-blue-400 hover:text-blue-300 text-sm">View All</a>
          </div>
          
          {#if recentTrades.length > 0}
            <div class="space-y-4">
              {#each recentTrades as trade}
                <div class="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                  <div class="flex items-center gap-3">
                    <span class="text-lg">{getTypeIcon(trade.target_type)}</span>
                    <div class="flex-1">
                      <div class="font-medium text-sm">{trade.target_name}</div>
                      <div class="text-xs text-gray-400">
                        {trade.trade_type.toUpperCase()} • {formatNumber(trade.shares)} shares
                      </div>
                    </div>
                  </div>
                  <div class="text-right">
                    <div class="text-sm font-medium {trade.trade_type === 'buy' ? 'text-red-400' : 'text-emerald-400'}">
                      {trade.trade_type === 'buy' ? '-' : '+'}{formatCurrency(trade.total_amount)}
                    </div>
                    <div class="text-xs text-gray-400">
                      @{formatCurrency(trade.price_per_share)}
                    </div>
                  </div>
                </div>
              {/each}
            </div>
          {:else}
            <div class="text-center py-8 text-gray-400">
              <div class="text-3xl mb-2">📊</div>
              <p>No trades yet. <a href="/browse" class="text-blue-400 hover:text-blue-300">Start trading!</a></p>
            </div>
          {/if}
        </div>

        <!-- Top Positions -->
        <div class="card">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-xl font-semibold">💼 Top Positions</h2>
            <a href="/portfolio" class="text-blue-400 hover:text-blue-300 text-sm">View All</a>
          </div>
          
          {#if portfolio?.positions && portfolio.positions.length > 0}
            <div class="space-y-4">
              {#each portfolio.positions.slice(0, 5) as position}
                <div class="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                  <div class="flex items-center gap-3">
                    <span class="text-lg">{getTypeIcon(position.target_type)}</span>
                    <div>
                      <div class="font-medium text-sm">{position.target_name}</div>
                      <div class="text-xs text-gray-400">{formatNumber(position.shares_owned)} shares</div>
                    </div>
                  </div>
                  <div class="text-right">
                    <div class="text-sm font-medium">{formatCurrency(position.position_value)}</div>
                    <div class="text-xs {getPerformanceColor(position.pnl)}">
                      {position.pnl >= 0 ? '+' : ''}{formatNumber(position.pnl_percent)}%
                    </div>
                  </div>
                </div>
              {/each}
            </div>
          {:else}
            <div class="text-center py-8 text-gray-400">
              <div class="text-3xl mb-2">💼</div>
              <p>No positions yet. <a href="/browse" class="text-blue-400 hover:text-blue-300">Start building your portfolio!</a></p>
            </div>
          {/if}
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <!-- Active Tournaments -->
        <div class="card">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-xl font-semibold">🏆 Active Tournaments</h2>
            <a href="/tournaments" class="text-blue-400 hover:text-blue-300 text-sm">View All</a>
          </div>
          
          {#if tournaments.length > 0}
            <div class="space-y-4">
              {#each tournaments as tournament}
                <div class="p-4 bg-white/5 rounded-lg">
                  <div class="flex items-center justify-between mb-2">
                    <div>
                      <h3 class="font-medium text-sm">{tournament.name}</h3>
                      <p class="text-xs text-gray-400 capitalize">
                        {getTypeIcon(tournament.target_type)} {tournament.target_type} • {tournament.duration}
                      </p>
                    </div>
                    <div class="text-right">
                      <div class="text-sm font-medium text-emerald-400">{formatCurrency(tournament.prize_pool)}</div>
                      <div class="text-xs text-gray-400">Prize Pool</div>
                    </div>
                  </div>
                  
                  <div class="flex items-center justify-between">
                    <div class="text-xs text-gray-400">
                      Entry: {formatCurrency(tournament.entry_fee)} • {tournament.participants} participants
                    </div>
                    <button 
                      class="btn btn-primary text-xs px-3 py-1"
                      on:click={() => joinTournament(tournament.id)}
                    >
                      Join
                    </button>
                  </div>
                </div>
              {/each}
            </div>
          {:else}
            <div class="text-center py-8 text-gray-400">
              <div class="text-3xl mb-2">🏆</div>
              <p>No active tournaments</p>
            </div>
          {/if}
        </div>

        <!-- Leaderboard -->
        <div class="card">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-xl font-semibold">🌟 Top Traders</h2>
            <span class="text-sm text-gray-400">Ranked by total value</span>
          </div>
          
          {#if leaderboard.length > 0}
            <div class="space-y-3">
              {#each leaderboard as trader, index}
                <div class="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                  <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center text-sm font-bold">
                      #{trader.rank}
                    </div>
                    <div>
                      <div class="font-medium text-sm">{trader.username}</div>
                      <div class="text-xs text-gray-400">Portfolio: {formatCurrency(trader.portfolio_value)}</div>
                    </div>
                  </div>
                  <div class="text-right">
                    <div class="text-sm font-medium text-emerald-400">{formatCurrency(trader.total_value)}</div>
                    <div class="text-xs text-gray-400">Total Value</div>
                  </div>
                </div>
              {/each}
            </div>
          {:else}
            <div class="text-center py-8 text-gray-400">
              <div class="text-3xl mb-2">🌟</div>
              <p>Leaderboard loading...</p>
            </div>
          {/if}
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="mt-8 card">
        <h2 class="text-lg font-semibold mb-4">⚡ Quick Actions</h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <a href="/browse" class="btn btn-primary">
            🔍 Browse Targets
          </a>
          <a href="/portfolio" class="btn btn-secondary">
            💼 View Portfolio
          </a>
          <a href="/tournaments" class="btn btn-secondary">
            🏆 Tournaments
          </a>
          <button class="btn btn-secondary" on:click={() => goto('/browse')}>
            📈 Start Trading
          </button>
        </div>
      </div>
    {/if}
  </div>
</div>