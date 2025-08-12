<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { user } from '$lib/stores';
  import apiFetch from '$lib/api';

  let stats = null;
  let recentTrades = [];
  let tournamentHistory = [];
  let loading = true;

  onMount(async () => {
    if (!$user) {
      goto('/login');
      return;
    }

    try {
      const [tradesResponse, portfolioData] = await Promise.all([
        apiFetch('/trades/my'),
        apiFetch('/portfolio')
      ]);

      const trades = tradesResponse.trades || tradesResponse || [];
      recentTrades = trades.slice(0, 10);
      
      // Calculate trading stats
      const closedTrades = trades.filter(t => t.is_closed);
      const winningTrades = closedTrades.filter(t => t.pnl > 0);
      const losingTrades = closedTrades.filter(t => t.pnl < 0);
      const totalPnl = closedTrades.reduce((sum, t) => sum + (t.pnl || 0), 0);
      
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
        currentPortfolioValue: portfolioData.total_portfolio_value || 0
      };

    } catch (error) {
      console.error('Failed to load profile data:', error);
    } finally {
      loading = false;
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
</script>

<svelte:head>
  <title>Profile - TrendBet</title>
</svelte:head>

<div class="min-h-screen p-6">
  <div class="max-w-6xl mx-auto">
    <!-- Profile Header -->
    <div class="card mb-8">
      <div class="flex items-center gap-6">
        <div class="w-20 h-20 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center text-2xl text-white font-bold">
          {$user?.username.charAt(0).toUpperCase()}
        </div>
        <div>
          <h1 class="text-3xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">
            {$user?.username}
          </h1>
          <p class="text-gray-400">Attention Trader • Member since {formatDate($user?.created_at || new Date())}</p>
          <div class="flex items-center gap-4 mt-2">
            <span class="text-sm text-gray-400">Balance: <span class="text-emerald-400 font-medium">{formatCurrency($user?.balance || 0)}</span></span>
            {#if stats}
              <span class="text-sm text-gray-400">Portfolio: <span class="text-blue-400 font-medium">{formatCurrency(stats.currentPortfolioValue)}</span></span>
            {/if}
          </div>
        </div>
      </div>
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="w-8 h-8 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin"></div>
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
          <div class="text-2xl font-bold text-emerald-400 mb-2">
            +{formatCurrency(stats.bestTrade)}
          </div>
          <div class="text-sm text-gray-400">Best Trade</div>
        </div>
        
        <div class="card text-center">
          <div class="text-2xl font-bold text-red-400 mb-2">
            {formatCurrency(stats.worstTrade)}
          </div>
          <div class="text-sm text-gray-400">Worst Trade</div>
        </div>
      </div>

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
                  <tr class="border-gray-700/50">
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
            <a href="/portfolio" class="btn btn-secondary">
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

      <!-- Tournament Performance (placeholder for future feature) -->
      <div class="card mt-8">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-2xl font-semibold">🏆 Tournament Performance</h2>
          <div class="text-sm text-gray-400">Coming soon</div>
        </div>
        
        <div class="text-center py-8 text-gray-400">
          <div class="text-4xl mb-4">🚧</div>
          <p>Tournament statistics will be available soon</p>
          <a href="/tournaments" class="btn btn-primary mt-4">
            View Active Tournaments
          </a>
        </div>
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