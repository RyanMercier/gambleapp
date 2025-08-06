<script>
  import { createEventDispatcher } from 'svelte';
  import { user } from '$lib/stores';
  import apiFetch from '$lib/api';

  export let target;
  export let currentPosition = null;
  export let compact = false;

  const dispatch = createEventDispatcher();

  let tradeType = 'buy';
  let shares = 0;
  let submitting = false;
  let error = '';

  // Updated to use attention-based calculations
  $: stakeCost = target ? shares * (target.current_attention_score || target.attention_score || 50) / 10 : 0;
  $: canAfford = $user && stakeCost <= $user.balance;
  $: hasPosition = currentPosition && currentPosition.attention_stakes > 0;
  $: maxSellAmount = currentPosition ? currentPosition.attention_stakes : 0;
  // Convert attention_stakes back to "shares" for UI consistency (shares = stakes / 10)
  $: maxSellShares = maxSellAmount / 10;

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
          target_id: target.id,
          trade_type: tradeType,
          shares: shares // Backend converts this to stake_amount
        })
      });

      // Update user balance
      const updatedUser = await apiFetch('/auth/me');
      user.set(updatedUser);

      // Dispatch success event
      dispatch('trade-success', {
        type: tradeType,
        shares: shares,
        stake_cost: stakeCost
      });

      // Reset form
      shares = 0;
      error = '';

    } catch (err) {
      error = err.message || 'Trade failed';
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
</script>

<div class="card {compact ? 'p-4' : 'p-6'}">
  <div class="flex items-center justify-between mb-4">
    <h3 class="{compact ? 'text-lg' : 'text-xl'} font-semibold">Quick Trade</h3>
    {#if target}
      <div class="text-right">
        <div class="text-sm text-gray-400">Attention Score</div>
        <div class="font-bold text-emerald-400">{formatNumber(target.current_attention_score || target.attention_score || 50)}</div>
      </div>
    {/if}
  </div>

  {#if target}
    <!-- Trade Type Toggle -->
    <div class="grid grid-cols-2 gap-2 mb-4">
      <button
        class="btn {tradeType === 'buy' ? 'btn-success' : 'btn-secondary'} {compact ? 'text-sm py-2' : ''}"
        on:click={() => tradeType = 'buy'}
        disabled={submitting}
      >
        📈 Long
      </button>
      <button
        class="btn {tradeType === 'sell' ? 'btn-danger' : 'btn-secondary'} {compact ? 'text-sm py-2' : ''}"
        on:click={() => tradeType = 'sell'}
        disabled={!hasPosition || submitting}
      >
        📉 Short
      </button>
    </div>

    <!-- Current Position (if any) -->
    {#if currentPosition && currentPosition.attention_stakes > 0 && !compact}
      <div class="mb-4 p-3 bg-indigo-500/10 rounded-lg">
        <div class="text-sm font-medium mb-1">Your Position</div>
        <div class="flex justify-between text-xs text-gray-300">
          <span>Stake: ${formatNumber(currentPosition.attention_stakes)}</span>
          <span class="{(currentPosition.pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}">
            {(currentPosition.pnl || 0) >= 0 ? '+' : ''}${formatNumber(currentPosition.pnl || 0)}
          </span>
        </div>
      </div>
    {/if}

    <!-- Trade Form -->
    <form on:submit|preventDefault={executeTrade} class="space-y-3">
      <!-- Amount Input -->
      <div>
        <label class="block text-sm font-medium text-gray-300 mb-1">
          Amount to {tradeType === 'buy' ? 'Stake' : 'Withdraw'}
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
          class="input {compact ? 'text-sm' : ''}"
          placeholder="0.00"
          required
          disabled={submitting}
        />
      </div>

      <!-- Order Summary -->
      {#if shares > 0}
        <div class="p-3 bg-white/5 rounded-lg">
          <div class="flex justify-between text-sm mb-1">
            <span>Total {tradeType === 'buy' ? 'Cost' : 'Proceeds'}:</span>
            <span class="font-medium {tradeType === 'buy' ? 'text-red-400' : 'text-emerald-400'}">
              {tradeType === 'buy' ? '-' : '+'}${formatNumber(stakeCost)}
            </span>
          </div>
          
          {#if tradeType === 'buy'}
            <div class="flex justify-between text-xs text-gray-400">
              <span>Available:</span>
              <span class="{canAfford ? '' : 'text-red-400'}">
                ${formatNumber($user?.balance || 0)}
              </span>
            </div>
          {/if}
        </div>
      {/if}

      <!-- Error Message -->
      {#if error}
        <div class="p-2 bg-red-500/10 border border-red-500/20 rounded text-red-400 text-sm">
          {error}
        </div>
      {/if}

      <!-- Submit Button -->
      <button
        type="submit"
        class="btn {tradeType === 'buy' ? 'btn-success' : 'btn-danger'} w-full {compact ? 'text-sm py-2' : 'py-3'}"
        disabled={submitting || shares <= 0 || (tradeType === 'buy' && !canAfford) || (tradeType === 'sell' && shares > maxSellShares)}
      >
        {#if submitting}
          <div class="flex items-center justify-center gap-2">
            <div class="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            Processing...
          </div>
        {:else}
          {tradeType === 'buy' ? 'Open Long Position' : 'Close Position'}
        {/if}
      </button>

      <!-- Add Flatten Button if user has position -->
      {#if hasPosition && !compact}
        <button
          type="button"
          class="btn btn-warning w-full mt-2"
          on:click={() => {
            shares = maxSellShares;
            tradeType = 'sell';
          }}
          disabled={submitting}
        >
          🔄 Flatten Position
        </button>
      {/if}
    </form>
  {:else}
    <div class="text-center py-8 text-gray-400">
      <div class="text-3xl mb-2">📊</div>
      <p class="text-sm">Select a target to start trading</p>
    </div>
  {/if}
</div>