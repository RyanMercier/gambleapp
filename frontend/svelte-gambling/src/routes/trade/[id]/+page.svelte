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
  let error = '';

  $: targetId = $page.params.id;
  $: stakeCost = target ? shares * (target.current_attention_score || 50) / 10 : 0;
  $: canAfford = $user && stakeCost <= $user.balance;
  $: hasPosition = portfolio && portfolio.attention_stakes > 0;
  $: maxSellShares = portfolio ? portfolio.attention_stakes / 10 : 0; // Convert stakes to shares

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
    error = '';
    try {
      const targets = await apiFetch('/targets');
      target = targets.find(t => t.id === parseInt(targetId));
      
      if (!target) {
        throw new Error('Target not found');
      }
    } catch (err) {
      error = err.message || 'Failed to load target data';
      setTimeout(() => goto('/browse'), 2000);
    } finally {
      loading = false;
    }
  }

  async function loadPortfolioData() {
    try {
      const portfolioData = await apiFetch('/portfolio');
      const position = portfolioData.positions.find(p => p.target_id === parseInt(targetId));
      portfolio = position || null;
    } catch (err) {
      console.error('Failed to load portfolio:', err);
    }
  }

  async function executeTrade() {
    if (!target || submitting) return;

    error = '';

    // Validation
    if (shares <= 0) {
      error = 'Please enter a valid amount';
      return;
    }

    if (tradeType === 'buy' && !canAfford) {
      error = 'Insufficient balance';
      return;
    }

    if (tradeType === 'sell' && shares > maxSellShares) {
      error = 'Insufficient position to sell';
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

      // Show success and reload data
      const action = tradeType === 'buy' ? 'opened long position' : 'closed position';
      alert(`Trade executed successfully! ${action} for $${stakeCost.toFixed(2)}`);

      // Reset form and reload data
      shares = 0;
      await loadPortfolioData();

    } catch (err) {
      error = err.message || 'Trade failed';
    } finally {
      submitting = false;
    }
  }

  async function flattenPosition() {
    if (!hasPosition || submitting) return;

    submitting = true;
    error = '';

    try {
      await apiFetch(`/trade/flatten/${targetId}`, {
        method: 'POST'
      });

      // Update user balance and reload data
      const updatedUser = await apiFetch('/auth/me');
      user.set(updatedUser);

      alert('Position flattened successfully!');
      shares = 0;
      await loadPortfolioData();

    } catch (err) {
      error = err.message || 'Failed to flatten position';
    } finally {
      submitting = false;
    }
  }

  function formatCurrency(amount) {
    return `$${parseFloat(amount || 0).toFixed(2)}`;
  }

  function formatNumber(num) {
    return new Intl.NumberFormat('en-US', {
      maximumFractionDigits: 2,
      minimumFractionDigits: 2
    }).format(num || 0);
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
</script>

<svelte:head>
  <title>{target ? `Trade ${target.name}` : 'Trade'} - TrendBet</title>
</svelte:head>

<div class="container">
  {#if loading}
    <div class="text-center py-12">
      <div class="w-8 h-8 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mx-auto mb-4"></div>
      <p class="text-gray-400">Loading target data...</p>
    </div>
  {:else if error && !target}
    <div class="text-center py-12">
      <div class="text-6xl mb-4">⚠️</div>
      <h2 class="text-2xl font-bold mb-2 text-red-400">Error Loading Target</h2>
      <p class="text-gray-400 mb-4">{error}</p>
      <a href="/browse" class="btn btn-primary">← Back to Browse</a>
    </div>
  {:else if target}
    <!-- Target Header -->
    <div class="flex items-center gap-4 mb-6">
      <button 
        class="btn btn-secondary"
        on:click={() => goto('/browse')}
      >
        ← Back
      </button>
      
      <div class="flex items-center gap-3 flex-1">
        <span class="text-3xl">{getTypeIcon(target.type)}</span>
        <div>
          <h1 class="text-3xl font-bold">{target.name}</h1>
          <p class="text-gray-400 capitalize">{target.type} • Attention Score: {formatNumber(target.current_attention_score)}</p>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <!-- Market Data Panel -->
      <div class="card">
        <h2 class="text-xl font-semibold mb-4">📊 Market Data</h2>
        
        <div class="space-y-4">
          <div class="flex justify-between items-center p-3 bg-white/5 rounded-lg">
            <span class="text-gray-400">Attention Score</span>
            <span class="text-xl font-bold text-emerald-400">{formatNumber(target.current_attention_score)}</span>
          </div>

          <div class="flex justify-between items-center p-3 bg-white/5 rounded-lg">
            <span class="text-gray-400">Equivalent Price</span>
            <span class="text-lg font-semibold text-blue-400">{formatCurrency((target.current_attention_score || 50) / 10)}/unit</span>
          </div>
          
          <div class="flex justify-between items-center p-3 bg-white/5 rounded-lg">
            <span class="text-gray-400">Last Updated</span>
            <span class="text-sm">{target.last_updated ? new Date(target.last_updated).toLocaleString() : 'Recently'}</span>
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
        <h2 class="text-xl font-semibold mb-4">💱 Trade Position</h2>
        
        <!-- Trade Type Toggle -->
        <div class="grid grid-cols-2 gap-2 mb-6">
          <button
            class="btn {tradeType === 'buy' ? 'btn-success' : 'btn-secondary'}"
            on:click={() => tradeType = 'buy'}
            disabled={submitting}
          >
            📈 Long
          </button>
          <button
            class="btn {tradeType === 'sell' ? 'btn-danger' : 'btn-secondary'}"
            on:click={() => tradeType = 'sell'}
            disabled={!hasPosition || submitting}
          >
            📉 Close
          </button>
        </div>

        <!-- Current Position (if any) -->
        {#if portfolio && portfolio.attention_stakes > 0}
          <div class="mb-6 p-3 bg-indigo-500/10 rounded-lg">
            <h3 class="font-medium mb-2">Your Position</h3>
            <div class="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span class="text-gray-400">Stake Amount:</span>
                <div class="font-medium">{formatCurrency(portfolio.attention_stakes)}</div>
              </div>
              <div>
                <span class="text-gray-400">Entry Score:</span>
                <div class="font-medium">{formatNumber(portfolio.average_entry_score)}</div>
              </div>
              <div>
                <span class="text-gray-400">Current Value:</span>
                <div class="font-medium">{formatCurrency(portfolio.current_value)}</div>
              </div>
              <div>
                <span class="text-gray-400">P&L:</span>
                <div class="font-medium {(portfolio.pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}">
                  {(portfolio.pnl || 0) >= 0 ? '+' : ''}{formatCurrency(portfolio.pnl || 0)} ({(portfolio.pnl_percent || 0) >= 0 ? '+' : ''}{formatNumber(portfolio.pnl_percent || 0)}%)
                </div>
              </div>
            </div>
          </div>
        {/if}

        <!-- Trade Form -->
        <form on:submit|preventDefault={executeTrade} class="space-y-4">
          <!-- Amount Input -->
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">
              Amount to {tradeType === 'buy' ? 'Stake' : 'Close'}
              {#if tradeType === 'sell' && hasPosition}
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
            <div class="p-4 bg-white/5 rounded-lg">
              <h4 class="font-medium mb-2">Order Summary</h4>
              <div class="flex justify-between text-sm mb-2">
                <span>Amount:</span>
                <span>{formatNumber(shares)} units</span>
              </div>
              <div class="flex justify-between text-sm mb-2">
                <span>Score:</span>
                <span>{formatNumber(target.current_attention_score)}</span>
              </div>
              <div class="flex justify-between font-medium border-t border-gray-600 pt-2">
                <span>Total {tradeType === 'buy' ? 'Cost' : 'Proceeds'}:</span>
                <span class="{tradeType === 'buy' ? 'text-red-400' : 'text-emerald-400'}">
                  {tradeType === 'buy' ? '-' : '+'}{formatCurrency(stakeCost)}
                </span>
              </div>
              
              {#if tradeType === 'buy'}
                <div class="flex justify-between text-xs text-gray-400 mt-1">
                  <span>Available Balance:</span>
                  <span class="{canAfford ? '' : 'text-red-400'}">
                    {formatCurrency($user?.balance || 0)}
                  </span>
                </div>
              {/if}
            </div>
          {/if}

          <!-- Error Message -->
          {#if error}
            <div class="p-3 bg-red-500/10 border border-red-500/20 rounded text-red-400 text-sm">
              {error}
            </div>
          {/if}

          <!-- Submit Button -->
          <button
            type="submit"
            class="btn {tradeType === 'buy' ? 'btn-success' : 'btn-danger'} w-full py-3"
            disabled={submitting || shares <= 0 || (tradeType === 'buy' && !canAfford) || (tradeType === 'sell' && shares > maxSellShares)}
          >
            {#if submitting}
              <div class="flex items-center justify-center gap-2">
                <div class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                Processing...
              </div>
            {:else}
              {tradeType === 'buy' ? 'Open Long Position' : 'Close Position'}
            {/if}
          </button>

          <!-- Flatten Button -->
          {#if hasPosition}
            <button
              type="button"
              class="btn btn-warning w-full"
              on:click={flattenPosition}
              disabled={submitting}
            >
              🔄 Flatten Entire Position
            </button>
          {/if}
        </form>

        <!-- Quick Actions -->
        <div class="mt-4 pt-4 border-t border-gray-700">
          <p class="text-xs text-gray-400 mb-2">Quick actions:</p>
          <div class="flex gap-2">
            <button
              class="btn btn-sm btn-secondary"
              on:click={() => shares = 1}
              disabled={submitting}
            >
              $10
            </button>
            <button
              class="btn btn-sm btn-secondary"
              on:click={() => shares = 5}
              disabled={submitting}
            >
              $50
            </button>
            <button
              class="btn btn-sm btn-secondary"
              on:click={() => shares = 10}
              disabled={submitting}
            >
              $100
            </button>
            {#if tradeType === 'sell' && hasPosition}
              <button
                class="btn btn-sm btn-secondary"
                on:click={() => shares = maxSellShares}
                disabled={submitting}
              >
                Max
              </button>
            {/if}
          </div>
        </div>
      </div>
    </div>
  {/if}
</div>