<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { user } from '$lib/stores';
  import apiFetch from '$lib/api';

  let target = null;
  let tradeType = 'buy';
  let shares = 0;
  let loading = false;
  let submitting = false;
  let portfolio = null;

  $: targetId = $page.params.id;
  $: totalCost = target ? shares * target.current_price : 0;
  $: canAfford = $user && totalCost <= $user.balance;
  $: hasShares = portfolio && portfolio.shares_owned > 0;
  $: maxSellShares = portfolio ? portfolio.shares_owned : 0;

  onMount(async () => {
    if (!$user) {
      goto('/login');
      return;
    }

    // Get trade type from URL params
    const urlParams = new URLSearchParams(window.location.search);
    const typeParam = urlParams.get('type');
    if (typeParam === 'sell') {
      tradeType = 'sell';
    }

    await loadTargetData();
    await loadPortfolioData();
  });

  async function loadTargetData() {
    loading = true;
    try {
      const targets = await apiFetch('/targets');
      target = targets.find(t => t.id === parseInt(targetId));
      
      if (!target) {
        throw new Error('Target not found');
      }
    } catch (error) {
      console.error('Failed to load target:', error);
      alert('Failed to load target data');
      goto('/browse');
    } finally {
      loading = false;
    }
  }

  async function loadPortfolioData() {
    try {
      const portfolioData = await apiFetch('/portfolio');
      const position = portfolioData.positions.find(p => p.target_id === parseInt(targetId));
      portfolio = position || { shares_owned: 0, average_price: 0 };
    } catch (error) {
      console.error('Failed to load portfolio:', error);
    }
  }

  async function executeTrade() {
    if (!target || submitting) return;

    // Validation
    if (shares <= 0) {
      alert('Please enter a valid number of shares');
      return;
    }

    if (tradeType === 'buy' && !canAfford) {
      alert('Insufficient balance');
      return;
    }

    if (tradeType === 'sell' && shares > maxSellShares) {
      alert('Insufficient shares to sell');
      return;
    }

    submitting = true;

    try {
      const result = await apiFetch('/trade', {
        method: 'POST',
        body: JSON.stringify({
          target_id: parseInt(targetId),
          trade_type: tradeType,
          shares: shares
        })
      });

      // Update user balance
      const updatedUser = await apiFetch('/auth/me');
      user.set(updatedUser);

      alert(`Trade executed successfully! ${tradeType === 'buy' ? 'Bought' : 'Sold'} ${shares} shares for ${formatCurrency(result.total_amount)}`);
      
      // Reset form and reload data
      shares = 0;
      await loadPortfolioData();

    } catch (error) {
      console.error('Trade failed:', error);
      alert('Trade failed: ' + error.message);
    } finally {
      submitting = false;
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

  function getTypeIcon(type) {
    const icons = {
      politician: '🏛️',
      billionaire: '💰',
      country: '🌍',
      stock: '📈'
    };
    return icons[type] || '📊';
  }

  function calculatePotentialPnL() {
    if (!portfolio || tradeType !== 'sell' || shares <= 0) return null;
    
    const avgPrice = portfolio.average_price;
    const currentPrice = target.current_price;
    const totalProceeds = shares * currentPrice;
    const totalCost = shares * avgPrice;
    const pnl = totalProceeds - totalCost;
    const pnlPercent = (pnl / totalCost) * 100;
    
    return { pnl, pnlPercent };
  }

  $: potentialPnL = calculatePotentialPnL();
</script>

<svelte:head>
  <title>Trade {target?.name || 'Loading...'} - TrendBet</title>
</svelte:head>

<div class="min-h-screen p-6">
  <div class="max-w-4xl mx-auto">
    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="w-8 h-8 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin"></div>
      </div>
    {:else if target}
      <!-- Header -->
      <div class="mb-8">
        <button 
          class="btn btn-secondary mb-4"
          on:click={() => goto('/browse')}
        >
          ← Back to Browse
        </button>
        
        <div class="flex items-center gap-4 mb-4">
          <span class="text-4xl">{getTypeIcon(target.type)}</span>
          <div>
            <h1 class="text-3xl font-bold bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">
              {target.name}
            </h1>
            <p class="text-gray-400 capitalize">{target.type} • Attention Trading</p>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <!-- Target Info -->
        <div class="card">
          <h2 class="text-xl font-semibold mb-4">📊 Market Data</h2>
          
          <div class="space-y-4">
            <div class="flex justify-between items-center p-3 bg-white/5 rounded-lg">
              <span class="text-gray-400">Current Price</span>
              <span class="text-xl font-bold text-emerald-400">{formatCurrency(target.current_price)}</span>
            </div>
            
            <div class="flex justify-between items-center p-3 bg-white/5 rounded-lg">
              <span class="text-gray-400">Attention Score</span>
              <span class="text-xl font-bold text-blue-400">{formatNumber(target.attention_score)}</span>
            </div>
            
            <div class="flex justify-between items-center p-3 bg-white/5 rounded-lg">
              <span class="text-gray-400">Last Updated</span>
              <span class="text-sm">{new Date(target.last_updated).toLocaleString()}</span>
            </div>
          </div>

          {#if target.description}
            <div class="mt-4 p-3 bg-blue-500/10 rounded-lg">
              <p class="text-sm text-gray-300">{target.description}</p>
            </div>
          {/if}
        </div>

        <!-- Trading Panel -->
        <div class="card">
          <h2 class="text-xl font-semibold mb-4">💱 Trade Shares</h2>
          
          <!-- Trade Type Toggle -->
          <div class="grid grid-cols-2 gap-2 mb-6">
            <button
              class="btn {tradeType === 'buy' ? 'btn-success' : 'btn-secondary'}"
              on:click={() => tradeType = 'buy'}
            >
              📈 Buy
            </button>
            <button
              class="btn {tradeType === 'sell' ? 'btn-danger' : 'btn-secondary'}"
              on:click={() => tradeType = 'sell'}
              disabled={!hasShares}
            >
              📉 Sell
            </button>
          </div>

          <!-- Current Position (if any) -->
          {#if portfolio && portfolio.shares_owned > 0}
            <div class="mb-6 p-3 bg-indigo-500/10 rounded-lg">
              <h3 class="font-medium mb-2">Your Position</h3>
              <div class="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span class="text-gray-400">Shares Owned:</span>
                  <div class="font-medium">{formatNumber(portfolio.shares_owned)}</div>
                </div>
                <div>
                  <span class="text-gray-400">Avg Price:</span>
                  <div class="font-medium">{formatCurrency(portfolio.average_price)}</div>
                </div>
                <div>
                  <span class="text-gray-400">Position Value:</span>
                  <div class="font-medium">{formatCurrency(portfolio.position_value)}</div>
                </div>
                <div>
                  <span class="text-gray-400">P&L:</span>
                  <div class="font-medium {portfolio.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}">
                    {formatCurrency(portfolio.pnl)} ({portfolio.pnl_percent >= 0 ? '+' : ''}{formatNumber(portfolio.pnl_percent)}%)
                  </div>
                </div>
              </div>
            </div>
          {/if}

          <!-- Trade Form -->
          <form on:submit|preventDefault={executeTrade} class="space-y-4">
            <!-- Shares Input -->
            <div>
              <label class="block text-sm font-medium text-gray-300 mb-2">
                Number of Shares
                {#if tradeType === 'sell' && hasShares}
                  <span class="text-gray-400">(Max: {formatNumber(maxSellShares)})</span>
                {/if}
              </label>
              <input
                type="number"
                min="0.01"
                step="0.01"
                max={tradeType === 'sell' ? maxSellShares : undefined}
                bind:value={shares}
                class="input"
                placeholder="0.00"
                required
                disabled={submitting}
              />
            </div>

            <!-- Order Summary -->
            {#if shares > 0}
              <div class="p-4 bg-white/5 rounded-lg space-y-2">
                <h3 class="font-medium mb-2">Order Summary</h3>
                
                <div class="flex justify-between text-sm">
                  <span>Shares:</span>
                  <span>{formatNumber(shares)}</span>
                </div>
                
                <div class="flex justify-between text-sm">
                  <span>Price per Share:</span>
                  <span>{formatCurrency(target.current_price)}</span>
                </div>
                
                <hr class="border-white/10">
                
                <div class="flex justify-between font-medium">
                  <span>Total {tradeType === 'buy' ? 'Cost' : 'Proceeds'}:</span>
                  <span class="{tradeType === 'buy' ? 'text-red-400' : 'text-emerald-400'}">
                    {tradeType === 'buy' ? '-' : '+'}{formatCurrency(totalCost)}
                  </span>
                </div>

                {#if potentialPnL && tradeType === 'sell'}
                  <div class="flex justify-between text-sm">
                    <span>Potential P&L:</span>
                    <span class="{potentialPnL.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}">
                      {potentialPnL.pnl >= 0 ? '+' : ''}{formatCurrency(potentialPnL.pnl)} 
                      ({potentialPnL.pnlPercent >= 0 ? '+' : ''}{formatNumber(potentialPnL.pnlPercent)}%)
                    </span>
                  </div>
                {/if}

                <!-- Balance Check -->
                {#if tradeType === 'buy'}
                  <div class="flex justify-between text-xs">
                    <span class="text-gray-400">Available Balance:</span>
                    <span class="{canAfford ? 'text-gray-400' : 'text-red-400'}">
                      {formatCurrency($user?.balance || 0)}
                    </span>
                  </div>
                {/if}
              </div>
            {/if}

            <!-- Submit Button -->
            <button
              type="submit"
              class="btn {tradeType === 'buy' ? 'btn-success' : 'btn-danger'} w-full py-3 font-semibold"
              disabled={submitting || shares <= 0 || (tradeType === 'buy' && !canAfford) || (tradeType === 'sell' && shares > maxSellShares)}
            >
              {#if submitting}
                <div class="flex items-center justify-center gap-2">
                  <div class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  Processing...
                </div>
              {:else}
                {tradeType === 'buy' ? '📈 Buy Shares' : '📉 Sell Shares'}
              {/if}
            </button>
          </form>

          <!-- Warning Messages -->
          {#if tradeType === 'buy' && !canAfford && shares > 0}
            <div class="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
              ⚠️ Insufficient balance. You need {formatCurrency(totalCost - ($user?.balance || 0))} more.
            </div>
          {/if}

          {#if tradeType === 'sell' && !hasShares}
            <div class="mt-4 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg text-yellow-400 text-sm">
              ℹ️ You don't own any shares of {target.name} yet.
            </div>
          {/if}
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="mt-8 card">
        <h2 class="text-lg font-semibold mb-4">Quick Actions</h2>
        <div class="flex gap-4">
          <button 
            class="btn btn-secondary"
            on:click={() => goto(`/browse`)}
          >
            🔍 Browse More Targets
          </button>
          <button 
            class="btn btn-secondary"
            on:click={() => goto('/portfolio')}
          >
            💼 View Portfolio
          </button>
          <button 
            class="btn btn-secondary"
            on:click={() => goto('/tournaments')}
          >
            🏆 Join Tournaments
          </button>
        </div>
      </div>
    {:else}
      <div class="text-center py-12">
        <div class="text-6xl mb-4">❌</div>
        <h2 class="text-xl font-semibold mb-2">Target Not Found</h2>
        <p class="text-gray-400 mb-4">The attention target you're looking for doesn't exist.</p>
        <button class="btn btn-primary" on:click={() => goto('/browse')}>
          Browse Targets
        </button>
      </div>
    {/if}
  </div>
</div>