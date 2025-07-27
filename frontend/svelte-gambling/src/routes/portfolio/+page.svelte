<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { user } from '$lib/stores';
  import apiFetch from '$lib/api';

  let portfolio = null;
  let trades = [];
  let loading = true;
  let showTrades = false;

  onMount(async () => {
    if (!$user) {
      goto('/login');
      return;
    }

    await loadPortfolio();
    await loadTradeHistory();
  });

  async function loadPortfolio() {
    try {
      const data = await apiFetch('/portfolio');
      portfolio = data;
    } catch (error) {
      console.error('Failed to load portfolio:', error);
    }
  }

  async function loadTradeHistory() {
    try {
      const data = await apiFetch('/trades/my');
      trades = data.slice(0, 10); // Last 10 trades
    } catch (error) {
      console.error('Failed to load trade history:', error);
      trades = []; // Fallback to empty array
    } finally {
      loading = false;
    }
  }

  function formatCurrency(amount) {
    return `$${parseFloat(amount).toFixed(2)}`;
  }

  function formatNumber(num) {
    return new Intl.NumberFormat('en-US', {
      maximumFractionDigits: 2,
      minimumFractionDigits: 2
    }).format(num);
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

  function getOverallPerformance() {
    if (!portfolio || portfolio.total_pnl === undefined) return 'stable';
    if (portfolio.total_pnl > 0) return 'positive';
    if (portfolio.total_pnl < 0) return 'negative';
    return 'stable';
  }

  $: overallPerformance = getOverallPerformance();
</script>

<svelte:head>
  <title>Portfolio - TrendBet</title>
</svelte:head>

<div class="min-h-screen p-6">
  <div class="max-w-6xl mx-auto">
    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-3xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">
        Your Portfolio
      </h1>
      <p class="text-gray-400">Track your attention trading positions and performance</p>
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="w-8 h-8 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin"></div>
      </div>
    {:else}
      <!-- Portfolio Overview -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div class="card text-center">
          <div class="text-2xl font-bold text-blue-400 mb-1">{formatCurrency(portfolio?.cash_balance || 0)}</div>
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
          <div class="text-2xl font-bold {overallPerformance === 'positive' ? 'text-emerald-400' : overallPerformance === 'negative' ? 'text-red-400' : 'text-gray-400'} mb-1">
            {portfolio?.total_pnl !== undefined ? 
              (portfolio.total_pnl >= 0 ? '+' : '') + formatCurrency(portfolio.total_pnl) : 
              '$0.00'}
          </div>
          <div class="text-sm text-gray-400">
            Total P&L
            {#if portfolio?.total_pnl_percent !== undefined}
              <span class="{overallPerformance === 'positive' ? 'text-emerald-400' : overallPerformance === 'negative' ? 'text-red-400' : 'text-gray-400'}">
                ({portfolio.total_pnl_percent >= 0 ? '+' : ''}{formatNumber(portfolio.total_pnl_percent)}%)
              </span>
            {/if}
          </div>
        </div>
      </div>

      <!-- Active Positions -->
      <div class="card mb-8">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-xl font-semibold">💼 Active Positions</h2>
          <div class="text-sm text-gray-400">
            {portfolio?.positions?.length || 0} positions
          </div>
        </div>
        
        {#if portfolio?.positions && portfolio.positions.length > 0}
          <div class="overflow-x-auto">
            <table class="w-full">
              <thead>
                <tr class="text-left border-b border-white/10">
                  <th class="pb-3 text-sm font-medium text-gray-400">Target</th>
                  <th class="pb-3 text-sm font-medium text-gray-400 text-right">Shares</th>
                  <th class="pb-3 text-sm font-medium text-gray-400 text-right">Avg Price</th>
                  <th class="pb-3 text-sm font-medium text-gray-400 text-right">Current Price</th>
                  <th class="pb-3 text-sm font-medium text-gray-400 text-right">Value</th>
                  <th class="pb-3 text-sm font-medium text-gray-400 text-right">P&L</th>
                  <th class="pb-3 text-sm font-medium text-gray-400 text-center">Actions</th>
                </tr>
              </thead>
              <tbody>
                {#each portfolio.positions as position}
                  <tr class="border-b border-white/5 hover:bg-white/5">
                    <td class="py-3">
                      <div class="flex items-center gap-3">
                        <span class="text-lg">{getTypeIcon(position.target_type)}</span>
                        <div>
                          <div class="font-medium">{position.target_name}</div>
                          <div class="text-xs text-gray-400 capitalize">{position.target_type}</div>
                        </div>
                      </div>
                    </td>
                    <td class="py-3 text-right font-medium">
                      {formatNumber(position.shares_owned)}
                    </td>
                    <td class="py-3 text-right">
                      {formatCurrency(position.average_price)}
                    </td>
                    <td class="py-3 text-right">
                      {formatCurrency(position.current_price)}
                    </td>
                    <td class="py-3 text-right font-medium">
                      {formatCurrency(position.position_value)}
                    </td>
                    <td class="py-3 text-right">
                      <div class="font-medium {position.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}">
                        {position.pnl >= 0 ? '+' : ''}{formatCurrency(position.pnl)}
                      </div>
                      <div class="text-xs {position.pnl_percent >= 0 ? 'text-emerald-400' : 'text-red-400'}">
                        {position.pnl_percent >= 0 ? '+' : ''}{formatNumber(position.pnl_percent)}%
                      </div>
                    </td>
                    <td class="py-3 text-center">
                      <div class="flex gap-1 justify-center">
                        <button 
                          class="btn btn-success text-xs px-2 py-1"
                          on:click={() => goto(`/trade/${position.target_id}?type=buy`)}
                        >
                          Buy
                        </button>
                        <button 
                          class="btn btn-danger text-xs px-2 py-1"
                          on:click={() => goto(`/trade/${position.target_id}?type=sell`)}
                        >
                          Sell
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

      <!-- Navigation Tabs -->
      <div class="flex gap-2 mb-6">
        <button
          class="btn {!showTrades ? 'btn-primary' : 'btn-secondary'} text-sm"
          on:click={() => showTrades = false}
        >
          📊 Portfolio Summary
        </button>
        <button
          class="btn {showTrades ? 'btn-primary' : 'btn-secondary'} text-sm"
          on:click={() => showTrades = true}
        >
          📈 Trade History
        </button>
      </div>

      {#if showTrades}
        <!-- Trade History -->
        <div class="card">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-xl font-semibold">📈 Recent Trades</h2>
            <div class="text-sm text-gray-400">Last 10 trades</div>
          </div>
          
          {#if trades.length > 0}
            <div class="space-y-3">
              {#each trades as trade}
                <div class="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                  <div class="flex items-center gap-3">
                    <span class="text-lg">{getTypeIcon(trade.target_type)}</span>
                    <div>
                      <div class="font-medium">{trade.target_name}</div>
                      <div class="text-xs text-gray-400">
                        {formatDateTime(trade.timestamp)}
                      </div>
                    </div>
                  </div>
                  
                  <div class="text-center">
                    <div class="text-sm font-medium {trade.trade_type === 'buy' ? 'text-emerald-400' : 'text-red-400'}">
                      {trade.trade_type.toUpperCase()}
                    </div>
                    <div class="text-xs text-gray-400">
                      {formatNumber(trade.shares)} shares
                    </div>
                  </div>
                  
                  <div class="text-right">
                    <div class="font-medium">{formatCurrency(trade.price_per_share)}</div>
                    <div class="text-xs text-gray-400">per share</div>
                  </div>
                  
                  <div class="text-right">
                    <div class="font-medium {trade.trade_type === 'buy' ? 'text-red-400' : 'text-emerald-400'}">
                      {trade.trade_type === 'buy' ? '-' : '+'}{formatCurrency(trade.total_amount)}
                    </div>
                    <div class="text-xs text-gray-400">total</div>
                  </div>
                </div>
              {/each}
            </div>
          {:else}
            <div class="text-center py-8 text-gray-400">
              <div class="text-3xl mb-2">📈</div>
              <p>No trades yet. <a href="/browse" class="text-blue-400 hover:text-blue-300">Start trading!</a></p>
            </div>
          {/if}
        </div>
      {:else}
        <!-- Portfolio Analytics -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <!-- Performance Summary -->
          <div class="card">
            <h2 class="text-lg font-semibold mb-4">📊 Performance Summary</h2>
            <div class="space-y-3">
              <div class="flex justify-between">
                <span class="text-gray-400">Starting Balance:</span>
                <span class="font-medium">$1,000.00</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-400">Current Total Value:</span>
                <span class="font-medium">{formatCurrency(portfolio?.total_value || 0)}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-400">Total Return:</span>
                <span class="font-medium {overallPerformance === 'positive' ? 'text-emerald-400' : overallPerformance === 'negative' ? 'text-red-400' : 'text-gray-400'}">
                  {portfolio?.total_pnl !== undefined ? 
                    (portfolio.total_pnl >= 0 ? '+' : '') + formatCurrency(portfolio.total_pnl) : 
                    '$0.00'}
                </span>
              </div>
              <div class="flex justify-between">
                <span class="text-gray-400">Total Return %:</span>
                <span class="font-medium {overallPerformance === 'positive' ? 'text-emerald-400' : overallPerformance === 'negative' ? 'text-red-400' : 'text-gray-400'}">
                  {portfolio?.total_pnl_percent !== undefined ? 
                    (portfolio.total_pnl_percent >= 0 ? '+' : '') + formatNumber(portfolio.total_pnl_percent) + '%' : 
                    '0.00%'}
                </span>
              </div>
            </div>
          </div>

          <!-- Quick Actions -->
          <div class="card">
            <h2 class="text-lg font-semibold mb-4">⚡ Quick Actions</h2>
            <div class="space-y-3">
              <a href="/browse" class="btn btn-primary w-full">
                🔍 Browse Targets
              </a>
              <a href="/tournaments" class="btn btn-secondary w-full">
                🏆 Join Tournaments
              </a>
              <button class="btn btn-secondary w-full" on:click={() => showTrades = true}>
                📈 View Trade History
              </button>
              <a href="/dashboard" class="btn btn-secondary w-full">
                📊 Dashboard
              </a>
            </div>
          </div>
        </div>
      {/if}
    {/if}
  </div>
</div>