<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { user } from '$lib/stores';
  import apiFetch from '$lib/api';

  let portfolio = null;
  let tournamentBalances = [];
  let trades = [];
  let loading = true;
  let error = '';
  let activeTab = 'overview'; // 'overview', 'positions', 'tournaments', 'history'
  let selectedTournament = null;
  let showTournamentSelector = false;

  // Position management state
  let flattening = false;
  let closingPosition = null;

  onMount(async () => {
    if (!$user) {
      goto('/login');
      return;
    }
    await loadAllData();
  });

  async function loadAllData() {
    loading = true;
    error = '';

    try {
      const [portfolioData, balancesData, tradesData] = await Promise.all([
        apiFetch('/portfolio'),
        apiFetch('/user/tournament-balances').catch(() => ({ tournament_balances: [] })),
        apiFetch('/trades/my').catch(() => ({ trades: [] }))
      ]);

      portfolio = portfolioData;
      tournamentBalances = balancesData.tournament_balances || [];
      trades = tradesData.trades || tradesData || [];

      // Set default tournament if none selected
      if (!selectedTournament && tournamentBalances.length > 0) {
        selectedTournament = tournamentBalances[0];
      }

    } catch (err) {
      error = err.message || 'Failed to load portfolio data';
      console.error('Portfolio load error:', err);
    } finally {
      loading = false;
    }
  }

  function formatCurrency(amount) {
    return `$${parseFloat(amount || 0).toFixed(2)}`;
  }

  function formatNumber(num, decimals = 2) {
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    }).format(num || 0);
  }

  function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  function getTypeIcon(type) {
    const icons = {
      politician: '🏛️',
      celebrity: '⭐',
      billionaire: '💰',
      country: '🌍',
      stock: '📈',
      crypto: '₿',
      game: '🎮'
    };
    return icons[type] || '📊';
  }

  function getPerformanceColor(pnl) {
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

  async function closePosition(targetId, positionType, tournamentId = null) {
    if (closingPosition) return;

    try {
      closingPosition = `${targetId}-${positionType}`;

      let url = `/trade/close/${targetId}?position_type=${positionType}`;
      if (tournamentId) {
        url += `&tournament_id=${tournamentId}`;
      }

      const result = await apiFetch(url, {
        method: 'POST'
      });

      const pnlText = result.pnl ? (result.pnl >= 0 ? `+$${result.pnl.toFixed(2)}` : `-$${Math.abs(result.pnl).toFixed(2)}`) : '';

      // Show success notification
      const notification = document.createElement('div');
      notification.className = 'fixed top-4 right-4 bg-emerald-600 text-white px-4 py-3 rounded-lg shadow-lg z-50';
      notification.innerHTML = `
        <div class="flex items-center gap-2">
          <span>✅</span>
          <div>
            <div class="font-medium">${positionType.toUpperCase()} position closed!</div>
            ${pnlText ? `<div class="text-sm">P&L: ${pnlText}</div>` : ''}
          </div>
        </div>
      `;
      document.body.appendChild(notification);

      setTimeout(() => {
        document.body.removeChild(notification);
      }, 4000);

      // Reload data
      await loadAllData();

      // Refresh navbar P&L
      if (typeof window !== 'undefined' && window.refreshNavbarPnL) {
        window.refreshNavbarPnL();
      }

    } catch (err) {
      alert('Failed to close position: ' + (err.message || 'Unknown error'));
      console.error('Close position error:', err);
    } finally {
      closingPosition = null;
    }
  }

  async function flattenAllPositions(tournamentId = null) {
    if (!portfolio || !portfolio.positions || portfolio.positions.length === 0 || flattening) return;

    flattening = true;
    try {
      const positionsToClose = tournamentId
        ? portfolio.positions.filter(p => p.tournament_id === tournamentId)
        : portfolio.positions;

      if (positionsToClose.length === 0) {
        alert('No positions found to close');
        return;
      }

      const results = [];

      // Close all positions one by one
      for (const position of positionsToClose) {
        if (position.attention_stakes > 0) {
          try {
            let url = `/trade/close/${position.target.id}?position_type=${position.position_type}`;
            if (position.tournament_id) {
              url += `&tournament_id=${position.tournament_id}`;
            }

            const result = await apiFetch(url, {
              method: 'POST'
            });

            results.push({
              target: position.target.name,
              pnl: result.pnl || 0,
              success: true
            });
          } catch (err) {
            results.push({
              target: position.target.name,
              error: err.message,
              success: false
            });
          }
        }
      }

      // Calculate total P&L and show summary
      const totalPnL = results.filter(r => r.success).reduce((sum, r) => sum + (r.pnl || 0), 0);
      const successCount = results.filter(r => r.success).length;
      const failureCount = results.filter(r => !r.success).length;

      let message = `✅ Flattened ${successCount} positions`;
      if (totalPnL !== 0) {
        message += `\nTotal P&L: ${totalPnL >= 0 ? '+' : ''}$${totalPnL.toFixed(2)}`;
      }
      if (failureCount > 0) {
        message += `\n⚠️ ${failureCount} positions failed to close`;
      }

      alert(message);

      // Reload data
      await loadAllData();

      // Refresh navbar P&L
      if (typeof window !== 'undefined' && window.refreshNavbarPnL) {
        window.refreshNavbarPnL();
      }

    } catch (err) {
      alert('Failed to flatten positions: ' + (err.message || 'Unknown error'));
      console.error('Flatten all positions error:', err);
    } finally {
      flattening = false;
    }
  }

  // Filter positions by selected tournament
  $: filteredPositions = selectedTournament && portfolio?.positions ?
    portfolio.positions.filter(p => p.tournament_id === selectedTournament.id) :
    portfolio?.positions || [];

  // Calculate tournament-specific portfolio value
  $: tournamentPortfolioValue = filteredPositions.reduce((sum, pos) => sum + (pos.current_value || 0), 0);
  $: tournamentTotalPnL = filteredPositions.reduce((sum, pos) => sum + (pos.pnl || 0), 0);

  // Get overall portfolio metrics
  $: overallPositionValue = portfolio ? (portfolio.total_value || 0) : 0;
  $: overallPnL = portfolio?.positions ? portfolio.positions.reduce((sum, pos) => sum + (pos.pnl || 0), 0) : 0;
</script>

<svelte:head>
  <title>Portfolio - TrendBet</title>
</svelte:head>

<div class="min-h-screen p-6">
  <div class="max-w-7xl mx-auto">

    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between mb-8 gap-4">
      <div>
        <h1 class="text-4xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
          💼 Portfolio
        </h1>
        <p class="text-gray-400 mt-1">Manage your attention trading positions and tournaments</p>
      </div>

      <div class="flex gap-3">
        <button
          class="btn btn-secondary"
          on:click={loadAllData}
          disabled={loading}
        >
          {loading ? '⟳' : '🔄'} Refresh
        </button>
        <a href="/browse" class="btn btn-primary">
          🎯 Find Targets
        </a>
      </div>
    </div>

    {#if error}
      <div class="alert alert-error mb-8">
        <div class="flex items-center gap-3">
          <span class="text-xl">⚠️</span>
          <div>
            <h3 class="font-semibold">Error Loading Portfolio</h3>
            <p class="text-sm text-red-300 mt-1">{error}</p>
          </div>
        </div>
        <button class="btn btn-sm" on:click={loadAllData}>Try Again</button>
      </div>
    {/if}

    {#if loading}
      <div class="text-center py-16">
        <div class="w-12 h-12 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mx-auto mb-6"></div>
        <p class="text-gray-400 text-lg">Loading your portfolio...</p>
      </div>
    {:else if portfolio}

      <!-- Navigation Tabs -->
      <div class="flex flex-wrap gap-2 mb-8 border-b border-gray-700 pb-4">
        <button
          class="tab-btn {activeTab === 'overview' ? 'active' : ''}"
          on:click={() => activeTab = 'overview'}
        >
          📊 Overview
        </button>
        <button
          class="tab-btn {activeTab === 'positions' ? 'active' : ''}"
          on:click={() => activeTab = 'positions'}
        >
          🎯 Positions
        </button>
        <button
          class="tab-btn {activeTab === 'tournaments' ? 'active' : ''}"
          on:click={() => activeTab = 'tournaments'}
        >
          🏆 Tournaments
        </button>
        <button
          class="tab-btn {activeTab === 'history' ? 'active' : ''}"
          on:click={() => activeTab = 'history'}
        >
          📋 Trade History
        </button>
      </div>

      {#if activeTab === 'overview'}
        <!-- Portfolio Overview -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">

          <!-- Overall Portfolio Stats -->
          <div class="card">
            <h3 class="text-xl font-semibold mb-6 flex items-center gap-2">
              🌟 Overall Portfolio
            </h3>

            <div class="space-y-4">
              <div class="flex justify-between items-center p-4 bg-gray-800/50 rounded-lg">
                <span class="text-gray-300">Position Value</span>
                <span class="text-xl font-bold text-emerald-400">{formatCurrency(overallPositionValue)}</span>
              </div>

              <div class="flex justify-between items-center p-4 bg-gray-800/50 rounded-lg">
                <span class="text-gray-300">Total P&L</span>
                <span class="text-xl font-bold {getPerformanceColor(overallPnL)}">
                  {overallPnL >= 0 ? '+' : ''}{formatCurrency(overallPnL)}
                </span>
              </div>

              <div class="flex justify-between items-center p-4 bg-gray-800/50 rounded-lg">
                <span class="text-gray-300">Active Tournaments</span>
                <span class="text-xl font-bold text-blue-400">{tournamentBalances.length}</span>
              </div>

              <div class="flex justify-between items-center p-4 bg-gray-800/50 rounded-lg">
                <span class="text-gray-300">Total Positions</span>
                <span class="text-xl font-bold text-purple-400">{portfolio?.positions?.length || 0}</span>
              </div>
            </div>
          </div>

          <!-- Tournament Summary -->
          <div class="card">
            <h3 class="text-xl font-semibold mb-6 flex items-center gap-2">
              🏆 Tournament Activity
            </h3>

            {#if tournamentBalances.length > 0}
              <div class="space-y-3">
                {#each tournamentBalances.slice(0, 4) as tournament}
                  <div class="flex items-center justify-between p-4 bg-gray-800/50 rounded-lg hover:bg-gray-800 transition-colors">
                    <div class="flex items-center gap-3">
                      <span class="text-xl">{getTournamentDurationIcon(tournament.duration)}</span>
                      <div>
                        <div class="font-medium">{tournament.name}</div>
                        <div class="text-sm text-gray-400 capitalize">{tournament.duration} • {tournament.target_type}</div>
                      </div>
                    </div>
                    <div class="text-right">
                      <div class="font-medium">{formatCurrency(tournament.current_balance)}</div>
                      <div class="text-sm {getPerformanceColor(tournament.pnl)}">
                        {tournament.pnl >= 0 ? '+' : ''}{formatCurrency(tournament.pnl)}
                      </div>
                    </div>
                  </div>
                {/each}

                {#if tournamentBalances.length > 4}
                  <button
                    class="w-full text-center py-2 text-blue-400 hover:text-blue-300 text-sm"
                    on:click={() => activeTab = 'tournaments'}
                  >
                    View all {tournamentBalances.length} tournaments →
                  </button>
                {/if}
              </div>
            {:else}
              <div class="text-center py-8 text-gray-400">
                <div class="text-4xl mb-3">🏆</div>
                <p class="mb-4">No tournament entries yet</p>
                <a href="/tournaments" class="btn btn-primary btn-sm">
                  Join Tournaments
                </a>
              </div>
            {/if}
          </div>
        </div>

        <!-- Recent Activity -->
        {#if portfolio.positions && portfolio.positions.length > 0}
          <div class="card">
            <div class="flex items-center justify-between mb-6">
              <h3 class="text-xl font-semibold">🎯 Recent Positions</h3>
              <button
                class="btn btn-secondary btn-sm"
                on:click={() => activeTab = 'positions'}
              >
                View All
              </button>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {#each portfolio.positions.slice(0, 6) as position}
                <div class="p-4 bg-gray-800/50 rounded-lg hover:bg-gray-800 transition-colors">
                  <div class="flex items-center gap-3 mb-3">
                    <span class="text-xl">{getTypeIcon(position.target.type)}</span>
                    <div class="flex-1 min-w-0">
                      <div class="font-medium truncate">{position.target.name}</div>
                      <div class="text-xs text-gray-400">{position.position_type} • {formatCurrency(position.attention_stakes)}</div>
                    </div>
                  </div>

                  <div class="flex justify-between items-center">
                    <div class="text-sm text-gray-400">P&L</div>
                    <div class="font-medium {getPerformanceColor(position.pnl)}">
                      {position.pnl >= 0 ? '+' : ''}{formatCurrency(position.pnl)}
                    </div>
                  </div>
                </div>
              {/each}
            </div>
          </div>
        {/if}

      {:else if activeTab === 'positions'}
        <!-- Positions Tab -->
        <div class="card">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
            <h2 class="text-2xl font-semibold">🎯 Current Positions</h2>

            <div class="flex gap-3">
              {#if portfolio.positions && portfolio.positions.length > 0}
                <button
                  class="btn btn-warning btn-sm"
                  on:click={() => flattenAllPositions()}
                  disabled={flattening}
                >
                  {flattening ? '⏳' : '🔄'} Flatten All
                </button>
              {/if}
            </div>
          </div>

          {#if portfolio.positions && portfolio.positions.length > 0}
            <div class="overflow-x-auto">
              <table class="table w-full">
                <thead>
                  <tr class="border-gray-700">
                    <th class="text-left">Target</th>
                    <th class="text-left">Tournament</th>
                    <th class="text-right">Stake</th>
                    <th class="text-right">Entry Score</th>
                    <th class="text-right">Current Score</th>
                    <th class="text-right">Value</th>
                    <th class="text-right">P&L</th>
                    <th class="text-center">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {#each portfolio.positions as position}
                    <tr class="border-gray-700/50 hover:bg-gray-800/50">
                      <td class="py-4">
                        <div class="flex items-center gap-3">
                          <span class="text-xl">{getTypeIcon(position.target.type)}</span>
                          <div>
                            <div class="font-medium">{position.target.name}</div>
                            <div class="text-xs text-gray-400 flex items-center gap-2">
                              <span class="px-2 py-1 rounded-full text-xs {position.position_type === 'long' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}">
                                {position.position_type === 'long' ? '📈 Long' : '📉 Short'}
                              </span>
                              <span>{position.target.type}</span>
                            </div>
                          </div>
                        </div>
                      </td>
                      <td class="py-4">
                        <div class="text-sm font-medium">{position.tournament?.name || 'Unknown'}</div>
                        <div class="text-xs text-gray-400 capitalize">{position.tournament?.duration}</div>
                      </td>
                      <td class="py-4 text-right">
                        <div class="font-medium">{formatCurrency(position.attention_stakes)}</div>
                      </td>
                      <td class="py-4 text-right">
                        <div class="font-medium">{formatNumber(position.average_entry_score)}</div>
                      </td>
                      <td class="py-4 text-right">
                        <div class="font-medium">{formatNumber(position.target.current_attention_score)}</div>
                      </td>
                      <td class="py-4 text-right">
                        <div class="font-medium">{formatCurrency(position.current_value)}</div>
                      </td>
                      <td class="py-4 text-right">
                        <div class="font-medium {getPerformanceColor(position.pnl)}">
                          {position.pnl >= 0 ? '+' : ''}{formatCurrency(position.pnl)}
                        </div>
                        <div class="text-xs {getPerformanceColor(position.pnl)}">
                          {position.pnl_percent >= 0 ? '+' : ''}{formatNumber(position.pnl_percent, 1)}%
                        </div>
                      </td>
                      <td class="py-4 text-center">
                        <div class="flex gap-1 justify-center">
                          <button
                            class="btn btn-primary text-xs px-2 py-1"
                            on:click={() => goto(`/trade/${position.target.id}`)}
                          >
                            📊 Chart
                          </button>
                          <button
                            class="btn btn-danger text-xs px-2 py-1"
                            on:click={() => closePosition(position.target.id, position.position_type, position.tournament_id)}
                            disabled={closingPosition === `${position.target.id}-${position.position_type}`}
                          >
                            {closingPosition === `${position.target.id}-${position.position_type}` ? '⏳' : 'Close'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {:else}
            <div class="text-center py-16">
              <div class="text-6xl mb-4">📊</div>
              <h3 class="text-xl font-semibold mb-2">No positions yet</h3>
              <p class="text-gray-400 mb-6">Start trading attention to build your portfolio</p>
              <a href="/browse" class="btn btn-primary">
                🎯 Browse Targets
              </a>
            </div>
          {/if}
        </div>

      {:else if activeTab === 'tournaments'}
        <!-- Tournaments Tab - Enhanced Version -->
        <div class="space-y-6">
          <!-- Tournament Performance Overview -->
          {#if tournamentBalances.length > 0}
            <div class="card">
              <h2 class="text-2xl font-semibold mb-6">🏆 Tournament Performance</h2>

              <!-- Performance Summary -->
              <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                <div class="p-4 bg-gradient-to-r from-blue-500/20 to-blue-600/20 rounded-lg border border-blue-500/30">
                  <div class="text-sm text-blue-300 mb-1">Active Tournaments</div>
                  <div class="text-2xl font-bold text-blue-400">{tournamentBalances.length}</div>
                </div>

                <div class="p-4 bg-gradient-to-r from-emerald-500/20 to-emerald-600/20 rounded-lg border border-emerald-500/30">
                  <div class="text-sm text-emerald-300 mb-1">Total P&L</div>
                  <div class="text-2xl font-bold {getPerformanceColor(tournamentBalances.reduce((sum, t) => sum + t.pnl, 0))}">
                    {tournamentBalances.reduce((sum, t) => sum + t.pnl, 0) >= 0 ? '+' : ''}{formatCurrency(tournamentBalances.reduce((sum, t) => sum + t.pnl, 0))}
                  </div>
                </div>

                <div class="p-4 bg-gradient-to-r from-purple-500/20 to-purple-600/20 rounded-lg border border-purple-500/30">
                  <div class="text-sm text-purple-300 mb-1">Total Value</div>
                  <div class="text-2xl font-bold text-purple-400">
                    {formatCurrency(tournamentBalances.reduce((sum, t) => sum + t.current_balance, 0))}
                  </div>
                </div>

                <div class="p-4 bg-gradient-to-r from-yellow-500/20 to-yellow-600/20 rounded-lg border border-yellow-500/30">
                  <div class="text-sm text-yellow-300 mb-1">Avg Return</div>
                  <div class="text-2xl font-bold text-yellow-400">
                    {((tournamentBalances.reduce((sum, t) => sum + t.pnl, 0) / tournamentBalances.reduce((sum, t) => sum + t.starting_balance, 0)) * 100).toFixed(1)}%
                  </div>
                </div>
              </div>

              <!-- Tournament Cards -->
              <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                {#each tournamentBalances as tournament}
                  <div class="relative group">
                    <!-- Tournament Card -->
                    <div class="p-6 bg-gray-800/60 rounded-xl border border-gray-700 hover:border-gray-600 transition-all duration-300 group-hover:shadow-2xl group-hover:bg-gray-800/80">
                      <!-- Header -->
                      <div class="flex items-start justify-between mb-4">
                        <div class="flex items-center gap-3">
                          <span class="text-3xl">{getTournamentDurationIcon(tournament.duration)}</span>
                          <div>
                            <h3 class="font-bold text-lg leading-tight">{tournament.name}</h3>
                            <div class="flex items-center gap-2 text-sm text-gray-400">
                              <span class="capitalize">{tournament.duration}</span>
                              <span>•</span>
                              <span class="capitalize">{tournament.target_type}</span>
                            </div>
                          </div>
                        </div>

                        <!-- Status Badge -->
                        <div class="px-2 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400 border border-green-500/30">
                          Active
                        </div>
                      </div>

                      <!-- Progress Bar for Performance -->
                      <div class="mb-4">
                        <div class="flex justify-between text-xs text-gray-400 mb-1">
                          <span>Performance</span>
                          <span>{((tournament.pnl / tournament.starting_balance) * 100).toFixed(1)}%</span>
                        </div>
                        <div class="w-full bg-gray-700 rounded-full h-2">
                          <div
                            class="h-2 rounded-full transition-all duration-500 {tournament.pnl >= 0 ? 'bg-gradient-to-r from-emerald-500 to-emerald-400' : 'bg-gradient-to-r from-red-500 to-red-400'}"
                            style="width: {Math.min(Math.abs((tournament.pnl / tournament.starting_balance) * 100), 100)}%"
                          ></div>
                        </div>
                      </div>

                      <!-- Stats Grid -->
                      <div class="grid grid-cols-2 gap-4 mb-4">
                        <div class="text-center p-3 bg-gray-900/50 rounded-lg">
                          <div class="text-xs text-gray-400 mb-1">Current Balance</div>
                          <div class="font-bold text-lg">{formatCurrency(tournament.current_balance)}</div>
                        </div>

                        <div class="text-center p-3 bg-gray-900/50 rounded-lg">
                          <div class="text-xs text-gray-400 mb-1">P&L</div>
                          <div class="font-bold text-lg {getPerformanceColor(tournament.pnl)}">
                            {tournament.pnl >= 0 ? '+' : ''}{formatCurrency(tournament.pnl)}
                          </div>
                        </div>
                      </div>

                      <!-- Additional Stats -->
                      <div class="space-y-2 mb-4">
                        <div class="flex justify-between text-sm">
                          <span class="text-gray-400">Starting Balance</span>
                          <span class="font-medium">{formatCurrency(tournament.starting_balance)}</span>
                        </div>

                        {#if tournament.rank}
                          <div class="flex justify-between text-sm">
                            <span class="text-gray-400">Current Rank</span>
                            <span class="font-medium text-yellow-400">#{tournament.rank}</span>
                          </div>
                        {/if}

                        <!-- Tournament Positions Count -->
                        {#if portfolio?.positions}
                          {@const tournamentPositions = portfolio.positions.filter(p => p.tournament_id === tournament.id)}
                          <div class="flex justify-between text-sm">
                            <span class="text-gray-400">Active Positions</span>
                            <span class="font-medium text-blue-400">{tournamentPositions.length}</span>
                          </div>
                        {/if}
                      </div>

                      <!-- Action Buttons -->
                      <div class="flex gap-2">
                        <button
                          class="btn btn-primary btn-sm flex-1 transition-all duration-300 hover:scale-105"
                          on:click={() => goto(`/tournaments/${tournament.tournament_id}`)}
                        >
                          <span class="mr-1">🏆</span> View Leaderboard
                        </button>
                        <button
                          class="btn btn-outline btn-sm px-3 transition-all duration-300 hover:scale-105"
                          on:click={() => goto('/browse')}
                          title="Find New Targets"
                        >
                          <span>🎯</span>
                        </button>
                      </div>

                      <!-- Quick Flatten Button -->
                      {#if portfolio?.positions}
                        {@const tournamentPositions = portfolio.positions.filter(p => p.tournament_id === tournament.id)}
                        {#if tournamentPositions.length > 0}
                          <button
                            class="w-full mt-2 btn btn-ghost btn-sm text-red-400 hover:bg-red-500/10 transition-all duration-300"
                            on:click={() => flattenAllPositions()}
                            disabled={flattening}
                          >
                            {flattening ? '⏳ Flattening...' : '🔄 Flatten All Positions'}
                          </button>
                        {/if}
                      {/if}
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          {:else}
            <!-- Empty State -->
            <div class="card text-center py-16">
              <div class="text-8xl mb-6">🏆</div>
              <h3 class="text-3xl font-bold mb-4">Join Your First Tournament</h3>
              <p class="text-gray-400 text-lg mb-8 max-w-md mx-auto">
                Compete with other traders in skill-based tournaments. Test your attention trading strategies and climb the leaderboards!
              </p>

              <div class="flex flex-col sm:flex-row gap-4 justify-center">
                <a href="/tournaments" class="btn btn-primary btn-lg">
                  🎮 Browse Tournaments
                </a>
                <a href="/browse" class="btn btn-secondary btn-lg">
                  🎯 Find Targets
                </a>
              </div>

              <!-- Feature Highlights -->
              <div class="grid grid-cols-1 sm:grid-cols-3 gap-6 mt-12 text-sm">
                <div class="p-4 bg-gray-800/50 rounded-lg">
                  <div class="text-2xl mb-2">💰</div>
                  <div class="font-semibold mb-1">Virtual Balances</div>
                  <div class="text-gray-400">Start with $10,000 virtual money</div>
                </div>
                <div class="p-4 bg-gray-800/50 rounded-lg">
                  <div class="text-2xl mb-2">🏅</div>
                  <div class="font-semibold mb-1">Real Competition</div>
                  <div class="text-gray-400">Compete against other traders</div>
                </div>
                <div class="p-4 bg-gray-800/50 rounded-lg">
                  <div class="text-2xl mb-2">📈</div>
                  <div class="font-semibold mb-1">Skill Building</div>
                  <div class="text-gray-400">Perfect your trading strategies</div>
                </div>
              </div>
            </div>
          {/if}
        </div>

      {:else if activeTab === 'history'}
        <!-- Trade History Tab -->
        <div class="card">
          <h2 class="text-2xl font-semibold mb-6">📋 Trade History</h2>

          {#if trades && trades.length > 0}
            <div class="overflow-x-auto">
              <table class="table w-full">
                <thead>
                  <tr class="border-gray-700">
                    <th class="text-left">Date</th>
                    <th class="text-left">Target</th>
                    <th class="text-left">Tournament</th>
                    <th class="text-center">Type</th>
                    <th class="text-right">Stake Amount</th>
                    <th class="text-right">Entry Score</th>
                    <th class="text-right">P&L</th>
                    <th class="text-right">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {#each trades as trade}
                    <tr class="border-gray-700/50 hover:bg-gray-800/50">
                      <td class="py-3">
                        <div class="text-sm">{formatDate(trade.timestamp)}</div>
                      </td>
                      <td class="py-3">
                        <div class="flex items-center gap-2">
                          <span>{getTypeIcon(trade.target_type)}</span>
                          <span class="font-medium">{trade.target_name}</span>
                        </div>
                      </td>
                      <td class="py-3">
                        <div class="text-sm">{trade.tournament_name || 'Unknown'}</div>
                      </td>
                      <td class="py-3 text-center">
                        <span class="px-2 py-1 rounded-full text-xs font-medium {
                          trade.trade_type.includes('buy') || trade.trade_type.includes('long') ? 'bg-emerald-500/20 text-emerald-400' :
                          'bg-red-500/20 text-red-400'
                        }">
                          {trade.trade_type.includes('buy') || trade.trade_type.includes('long') ? '📈 Long' : '📉 Close'}
                        </span>
                      </td>
                      <td class="py-3 text-right">
                        <div class="font-medium">{formatCurrency(trade.stake_amount)}</div>
                      </td>
                      <td class="py-3 text-right">
                        <div class="font-medium">{formatNumber(trade.attention_score_at_entry)}</div>
                      </td>
                      <td class="py-3 text-right">
                        {#if trade.pnl !== null && trade.pnl !== undefined}
                          <div class="font-medium {getPerformanceColor(trade.pnl)}">
                            {trade.pnl >= 0 ? '+' : ''}{formatCurrency(trade.pnl)}
                          </div>
                        {:else}
                          <span class="text-gray-400">-</span>
                        {/if}
                      </td>
                      <td class="py-3 text-right">
                        <span class="text-xs px-2 py-1 rounded-full {
                          trade.is_closed ? 'bg-gray-500/20 text-gray-400' : 'bg-blue-500/20 text-blue-400'
                        }">
                          {trade.is_closed ? 'Closed' : 'Active'}
                        </span>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {:else}
            <div class="text-center py-16">
              <div class="text-6xl mb-4">📋</div>
              <h3 class="text-xl font-semibold mb-2">No trades yet</h3>
              <p class="text-gray-400 mb-6">Start making trades to see your history</p>
              <a href="/browse" class="btn btn-primary">
                🎯 Start Trading
              </a>
            </div>
          {/if}
        </div>
      {/if}
    {/if}
  </div>
</div>

<style>
  .container {
    @apply max-w-7xl mx-auto px-4 sm:px-6 lg:px-8;
  }

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

  .btn-warning {
    @apply bg-yellow-600 text-white hover:bg-yellow-700 focus:ring-yellow-500;
  }

  .btn-danger {
    @apply bg-red-600 text-white hover:bg-red-700 focus:ring-red-500;
  }

  .btn-sm {
    @apply px-3 py-1 text-sm;
  }

  .tab-btn {
    @apply px-4 py-2 rounded-lg font-medium transition-all duration-200 text-gray-400 hover:text-white hover:bg-gray-800;
  }

  .tab-btn.active {
    @apply text-blue-400 bg-blue-500/10 border border-blue-500/20;
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

  .alert {
    @apply flex items-center justify-between p-4 rounded-lg;
  }

  .alert-error {
    @apply bg-red-500/10 border border-red-500/20 text-red-400;
  }
</style>