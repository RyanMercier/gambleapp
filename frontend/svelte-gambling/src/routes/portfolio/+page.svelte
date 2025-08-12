<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { user } from '$lib/stores';
  import apiFetch from '$lib/api';

  let portfolio = null;
  let trades = [];
  let loading = true;
  let error = '';
  let showTrades = false;

  onMount(async () => {
    if (!$user) {
      goto('/login');
      return;
    }
    await loadData();
  });

  async function loadData() {
    loading = true;
    error = '';
    
    try {
      const [portfolioData, tradesData] = await Promise.all([
        apiFetch('/portfolio'),
        apiFetch('/trades/my').catch(() => ({ trades: [] }))
      ]);

      portfolio = portfolioData;
      trades = tradesData.trades || tradesData || [];
    } catch (err) {
      error = err.message || 'Failed to load portfolio data';
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

  async function closePositionFromPortfolio(targetId, positionType) {
    try {
      // Use query parameters instead of request body
      const result = await apiFetch(`/trade/close/${targetId}?position_type=${positionType}`, {
        method: 'POST'
      });

      const pnlText = result.pnl ? (result.pnl >= 0 ? `+$${result.pnl.toFixed(2)}` : `-$${Math.abs(result.pnl).toFixed(2)}`) : '';
      alert(`✅ ${positionType.toUpperCase()} position closed! ${pnlText ? `P&L: ${pnlText}` : ''}`);

      // Reload portfolio data
      await loadPortfolioData();

    } catch (err) {
      alert('Failed to close position: ' + (err.message || 'Unknown error'));
      console.error('Close position error:', err);
    }
  }

  // Function to reload portfolio data
  async function loadPortfolioData() {
    try {
      const portfolioData = await apiFetch('/portfolio');
      portfolio = portfolioData;
    } catch (error) {
      console.error('Failed to reload portfolio:', error);
    }
  }
</script>

<svelte:head>
  <title>Portfolio - TrendBet</title>
</svelte:head>

<div class="container">
  <div class="flex items-center justify-between mb-6">
    <h1 class="text-3xl font-bold">💼 Portfolio</h1>
    <button 
      class="btn btn-primary"
      on:click={loadData}
      disabled={loading}
    >
      {loading ? '⟳' : '🔄'} Refresh
    </button>
  </div>

  {#if error}
    <div class="alert alert-error mb-6">
      <div class="flex items-center gap-2">
        <span class="text-lg">⚠️</span>
        <div>
          <h3 class="font-semibold">Error Loading Portfolio</h3>
          <p class="text-sm text-red-300">{error}</p>
        </div>
      </div>
      <button class="btn btn-sm" on:click={loadData}>Try Again</button>
    </div>
  {/if}

  {#if loading}
    <div class="text-center py-12">
      <div class="w-8 h-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mx-auto mb-4"></div>
      <p class="text-gray-400">Loading your portfolio...</p>
    </div>
  {:else if portfolio}
    <!-- Portfolio Summary -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
      <div class="card text-center">
        <h3 class="text-lg font-semibold mb-2">💰 Cash Balance</h3>
        <div class="text-3xl font-bold text-blue-400">{formatCurrency(portfolio.cash_balance)}</div>
      </div>

      <div class="card text-center">
        <h3 class="text-lg font-semibold mb-2">📈 Positions Value</h3>
        <div class="text-3xl font-bold text-emerald-400">{formatCurrency(portfolio.total_value)}</div>
      </div>

      <div class="card text-center">
        <h3 class="text-lg font-semibold mb-2">💎 Total Portfolio</h3>
        <div class="text-3xl font-bold text-purple-400">{formatCurrency(portfolio.total_portfolio_value)}</div>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="flex gap-2 mb-6">
      <button
        class="btn {!showTrades ? 'btn-primary' : 'btn-secondary'} text-sm"
        on:click={() => showTrades = false}
      >
        📊 Positions
      </button>
      <button
        class="btn {showTrades ? 'btn-primary' : 'btn-secondary'} text-sm"
        on:click={() => showTrades = true}
      >
        📋 Trade History
      </button>
    </div>

    {#if !showTrades}
      <!-- Current Positions -->
      <div class="card">
        <h2 class="text-xl font-semibold mb-4">🎯 Current Positions</h2>
        
        {#if portfolio.positions && portfolio.positions.length > 0}
          <div class="overflow-x-auto">
            <table class="table w-full">
              <thead>
                <tr class="border-gray-700">
                  <th class="text-left">Target</th>
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
                  <tr class="border-gray-700/50">
                    <td class="py-3">
                      <div class="flex items-center gap-3">
                        <span class="text-xl">{getTypeIcon(position.target.type)}</span>
                        <div>
                          <div class="font-medium">{position.target.name}</div>
                          <div class="text-xs text-gray-400">{position.target.type}</div>
                        </div>
                      </div>
                    </td>
                    <td class="py-3 text-right">
                      <div class="font-medium">{formatCurrency(position.attention_stakes)}</div>
                    </td>
                    <td class="py-3 text-right">
                      <div class="font-medium">{formatNumber(position.average_entry_score)}</div>
                    </td>
                    <td class="py-3 text-right">
                      <div class="font-medium">{formatNumber(position.target.current_attention_score)}</div>
                    </td>
                    <td class="py-3 text-right">
                      <div class="font-medium">{formatCurrency(position.current_value)}</div>
                    </td>
                    <td class="py-3 text-right">
                      <div class="font-medium {getPerformanceColor(position.pnl)}">
                        {position.pnl >= 0 ? '+' : ''}{formatCurrency(position.pnl)}
                      </div>
                      <div class="text-xs {getPerformanceColor(position.pnl)}">
                        {position.pnl_percent >= 0 ? '+' : ''}{formatNumber(position.pnl_percent, 1)}%
                      </div>
                    </td>
                    <td class="py-3 text-center">
                      <div class="flex gap-1 justify-center">
                        <button 
                          class="btn btn-primary text-xs px-2 py-1"
                          on:click={() => goto(`/trade/${position.target.id}`)}
                        >
                          📊 View Chart
                        </button>
                        <button 
                          class="btn btn-danger text-xs px-2 py-1"
                          on:click={() => closePositionFromPortfolio(position.target.id, position.position_type)}
                        >
                          Close
                        </button>
                      </div>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {:else}
          <div class="text-center py-12">
            <div class="text-6xl mb-4">📊</div>
            <h3 class="text-xl font-semibold mb-2">No positions yet</h3>
            <p class="text-gray-400 mb-4">Start trading attention to build your portfolio</p>
            <a href="/browse" class="btn btn-primary">
              Browse Targets
            </a>
          </div>
        {/if}
      </div>
    {:else}
      <!-- Trade History -->
      <div class="card">
        <h2 class="text-xl font-semibold mb-4">📋 Recent Trades</h2>
        
        {#if trades && trades.length > 0}
          <div class="overflow-x-auto">
            <table class="table w-full">
              <thead>
                <tr class="border-gray-700">
                  <th class="text-left">Date</th>
                  <th class="text-left">Target</th>
                  <th class="text-center">Type</th>
                  <th class="text-right">Stake Amount</th>
                  <th class="text-right">Entry Score</th>
                  <th class="text-right">Status</th>
                </tr>
              </thead>
              <tbody>
                {#each trades as trade}
                  <tr class="border-gray-700/50">
                    <td class="py-3">
                      <div class="text-sm">{formatDate(trade.timestamp)}</div>
                    </td>
                    <td class="py-3">
                      <div class="flex items-center gap-2">
                        <span>{getTypeIcon(trade.target_type)}</span>
                        <span class="font-medium">{trade.target_name}</span>
                      </div>
                    </td>
                    <td class="py-3 text-center">
                      <span class="px-2 py-1 rounded-full text-xs font-medium {
                        trade.trade_type.includes('buy') ? 'bg-emerald-500/20 text-emerald-400' : 
                        'bg-red-500/20 text-red-400'
                      }">
                        {trade.trade_type.includes('buy') ? '📈 Long' : '📉 Close'}
                      </span>
                    </td>
                    <td class="py-3 text-right">
                      <div class="font-medium">{formatCurrency(trade.stake_amount)}</div>
                    </td>
                    <td class="py-3 text-right">
                      <div class="font-medium">{formatNumber(trade.attention_score_at_entry)}</div>
                    </td>
                    <td class="py-3 text-right">
                      <span class="text-xs px-2 py-1 rounded-full bg-blue-500/20 text-blue-400">
                        {trade.outcome || 'Active'}
                      </span>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {:else}
          <div class="text-center py-12 text-gray-400">
            <div class="text-6xl mb-4">📋</div>
            <h3 class="text-xl font-semibold mb-2">No trades yet</h3>
            <p class="mb-4">Start making some trades to see your history</p>
            <a href="/browse" class="btn btn-primary">
              Start Trading
            </a>
          </div>
        {/if}
      </div>
    {/if}
  {/if}
</div>

<style>
  .table {
    @apply w-full;
  }

  .table th {
    @apply py-3 px-4 text-sm font-medium text-gray-300 border-b;
  }

  .table td {
    @apply px-4 border-b;
  }

  .alert {
    @apply flex items-center justify-between p-4 rounded-lg;
  }

  .alert-error {
    @apply bg-red-500/10 border border-red-500/20 text-red-400;
  }
</style>